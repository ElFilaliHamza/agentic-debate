"""Fish Audio TTS strategy — uses the fish-audio-sdk for voice synthesis."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

import miniaudio

from voice.provider import TTSProvider

logger = logging.getLogger(__name__)

FISH_VOICE_ENV_KEYS: dict[str, str] = {
    "moderator": "FISH_VOICE_MODERATOR",
    "proposer": "FISH_VOICE_PROPOSER",
    "critic": "FISH_VOICE_CRITIC",
    "speaker_a": "FISH_VOICE_SPEAKER_A",
    "speaker_b": "FISH_VOICE_SPEAKER_B",
    "judge": "FISH_VOICE_JUDGE",
}

# Maximum characters per TTS request.  Fish Audio truncates audio beyond
# ~30 seconds per request (~460 chars at typical speaking rate).  We use 300
# chars to stay well within that limit while producing the fewest chunks possible.
MAX_CHUNK_LENGTH = 300


def _split_text(text: str, max_length: int = MAX_CHUNK_LENGTH) -> list[str]:
    """Split text into chunks that respect paragraph and sentence boundaries.

    Tries paragraph boundaries first (double newlines), then sentence
    boundaries.  Never splits mid-sentence.  Produces the fewest, largest
    chunks possible within *max_length*.

    Args:
        text: The text to split.
        max_length: Maximum characters per chunk.

    Returns:
        A list of text chunks, each no longer than *max_length*.
    """
    if len(text) <= max_length:
        return [text]

    # First try splitting on paragraph boundaries (double newlines).
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If a single paragraph exceeds max_length, split it by sentences.
        if len(para) > max_length:
            # Flush whatever we've accumulated so far.
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            sentences = re.split(r"(?<=[.!?])\s+", para)
            sentence_chunk = ""

            for sentence in sentences:
                if len(sentence_chunk) + len(sentence) + 1 > max_length:
                    if sentence_chunk:
                        chunks.append(sentence_chunk.strip())
                    sentence_chunk = sentence
                else:
                    sentence_chunk = f"{sentence_chunk} {sentence}".strip()

            if sentence_chunk:
                # Try to merge with the next chunk if it fits.
                if not current_chunk and len(chunks) > 0:
                    last = chunks[-1]
                    if len(last) + len(sentence_chunk) + 1 <= max_length:
                        chunks[-1] = f"{last} {sentence_chunk}".strip()
                        continue
                current_chunk = sentence_chunk
        elif len(current_chunk) + len(para) + 2 > max_length:
            # This paragraph doesn't fit in the current chunk — start a new one.
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Filter empty chunks and validate.
    chunks = [c for c in chunks if c]
    if not chunks:
        return [text]

    return chunks


class FishAudioStrategy(TTSProvider):
    """Fish Audio TTS provider with per-role voice IDs from env vars.

    Splits long texts into paragraph/sentence-boundary chunks and generates
    audio for each chunk separately, returning multiple files that are
    played seamlessly by the player.  This avoids Fish Audio's server-side
    truncation for long inputs.
    """

    def __init__(self) -> None:
        api_key = os.getenv("FISH_API_KEY", "")
        if not api_key:
            raise ValueError(
                "FISH_API_KEY is required when TTS_PROVIDER=fish. "
                "Set it in your .env file."
            )
        self._api_key = api_key
        self._voice_map: dict[str, str] = self._load_voice_map()

    def _load_voice_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for role, env_key in FISH_VOICE_ENV_KEYS.items():
            value = os.getenv(env_key, "") or ""
            value = value.strip()
            if value:
                mapping[role] = value
            else:
                logger.info(
                    "FISH_VOICE_%s is not set — role '%s' will be skipped during voice playback.",
                    role.upper(),
                    role,
                )
        return mapping

    async def _generate_single(
        self,
        text: str,
        voice: str,
        model: str,
        output_path: Path,
    ) -> Path:
        """Generate audio for a single text chunk using Fish Audio TTS.

        Args:
            text: The text chunk to synthesize.
            voice: Fish Audio reference_id (voice model ID).
            model: Model name (e.g. "s2.1-pro").
            output_path: Where to save the audio file.

        Returns:
            Path to the generated audio file.
        """
        from fishaudio import AsyncFishAudio
        from fishaudio.types import TTSConfig

        client = AsyncFishAudio(api_key=self._api_key)
        try:
            audio = await client.tts.convert(
                text=text,
                reference_id=voice,
                config=TTSConfig(
                    chunk_length=300,
                    max_new_tokens=4096,
                    latency="normal",
                    format="wav",
                    sample_rate=44100,
                ),
                model=model,
            )
        except Exception:
            logger.exception(
                "Fish TTS: API call failed for role='%s', text_len=%d",
                voice,
                len(text),
            )
            raise
        finally:
            await client.close()

        with open(output_path, "wb") as f:
            f.write(audio)

        logger.info(
            "Fish TTS: chunk completed — %d chars -> %d bytes, saved to %s",
            len(text),
            len(audio),
            output_path.name,
        )
        return output_path

    async def generate_audio(
        self,
        text: str,
        voice: str,
        output_path: Path | None = None,
    ) -> list[Path]:
        """Generate audio from text using Fish Audio TTS.

        Long texts are split at paragraph or sentence boundaries into
        chunks of at most ``MAX_CHUNK_LENGTH`` characters.  Each chunk is
        sent as a separate API call and saved as its own file.  The player
        concatenates all files into a seamless stream.

        Args:
            text: The full text to synthesize.
            voice: Fish Audio reference_id (voice model ID).
            output_path: If provided, used as a base filename; chunks get
                         ``_part1``, ``_part2`` suffixes.  If None, temp
                         files are created.

        Returns:
            A list of Paths to generated audio files, in playback order.
        """
        model = os.getenv("FISH_MODEL", "s2.1-pro")

        chunks = _split_text(text, MAX_CHUNK_LENGTH)

        if len(chunks) > 1:
            logger.info(
                "Fish TTS: splitting %d-char text into %d chunks (max %d chars each)",
                len(text),
                len(chunks),
                MAX_CHUNK_LENGTH,
            )

        if len(chunks) == 1:
            # Single chunk — simple case, no suffix.
            if output_path is not None:
                destination = output_path
            else:
                fd, name = tempfile.mkstemp(suffix=".wav", prefix="debate_fish_")
                os.close(fd)
                destination = Path(name)

            logger.info(
                "Fish TTS: generating audio for role='%s', text_len=%d chars, model=%s",
                voice,
                len(text),
                model,
            )
            path = await self._generate_single(chunks[0], voice, model, destination)

            # Diagnostic: log audio duration and seconds-per-char ratio.
            self._log_diagnostics(path, voice, len(text))

            return [path]

        # Multiple chunks — generate each separately.
        result_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            if output_path is not None:
                # e.g. speaker_a_round_1.wav -> speaker_a_round_1_part1.wav
                stem = output_path.stem
                suffix = output_path.suffix
                chunk_path = output_path.with_name(f"{stem}_part{i + 1}{suffix}")
            else:
                fd, name = tempfile.mkstemp(suffix=".wav", prefix=f"debate_fish_{i}_")
                os.close(fd)
                chunk_path = Path(name)

            logger.info(
                "Fish TTS: generating chunk %d/%d for role='%s', chunk_len=%d chars, model=%s",
                i + 1,
                len(chunks),
                voice,
                len(chunk),
                model,
            )
            path = await self._generate_single(chunk, voice, model, chunk_path)
            result_paths.append(path)

        # Diagnostic: log total duration across all chunks.
        self._log_diagnostics(result_paths, voice, len(text))

        return result_paths

    def _log_diagnostics(
        self,
        paths: Path | list[Path],
        voice: str,
        text_len: int,
    ) -> None:
        """Log audio duration and seconds-per-char ratio for diagnostics."""
        if isinstance(paths, Path):
            paths = [paths]

        total_duration = 0.0
        total_bytes = 0
        for p in paths:
            try:
                total_bytes += p.stat().st_size
                decoded = miniaudio.decode_file(
                    str(p),
                    nchannels=1,
                    sample_rate=44100,
                    output_format=miniaudio.SampleFormat.SIGNED16,
                )
                total_duration += len(decoded.samples) / decoded.sample_rate
            except Exception:
                pass

        secs_per_char = total_duration / text_len if text_len > 0 else 0
        logger.warning(
            "Fish TTS diagnostic: role='%s' text_len=%d chars "
            "audio_duration=%.2fs bytes=%d secs_per_char=%.4f chunks=%d",
            voice,
            text_len,
            total_duration,
            total_bytes,
            secs_per_char,
            len(paths),
        )

    def get_voice(self, role: str) -> str:
        if role not in FISH_VOICE_ENV_KEYS:
            raise ValueError(
                f"Unknown role '{role}'. "
                f"Valid roles: {', '.join(FISH_VOICE_ENV_KEYS)}"
            )
        if role not in self._voice_map:
            raise ValueError(
                f"No voice ID configured for role '{role}'. "
                f"Set {FISH_VOICE_ENV_KEYS[role]} in your .env file, "
                f"or remove it to skip voice playback for this role."
            )
        return self._voice_map[role]

    def voice_assignment(self) -> dict[str, str]:
        return dict(self._voice_map)