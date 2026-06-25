"""Fish Audio TTS strategy — uses the fish-audio-sdk for voice synthesis."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

from voice.provider import TTSProvider

logger = logging.getLogger(__name__)

FISH_CHUNK_LENGTH = 300

FISH_VOICE_ENV_KEYS: dict[str, str] = {
    "moderator": "FISH_VOICE_MODERATOR",
    "proposer": "FISH_VOICE_PROPOSER",
    "critic": "FISH_VOICE_CRITIC",
    "speaker_a": "FISH_VOICE_SPEAKER_A",
    "speaker_b": "FISH_VOICE_SPEAKER_B",
    "judge": "FISH_VOICE_JUDGE",
}


class FishAudioStrategy(TTSProvider):
    """Fish Audio TTS provider with per-role voice IDs from env vars."""

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

    async def generate_audio(
        self,
        text: str,
        voice: str,
        output_path: Path | None = None,
    ) -> list[Path]:
        from fishaudio import AsyncFishAudio
        from fishaudio.types import TTSConfig

        chunks = _split_text(text, FISH_CHUNK_LENGTH)
        logger.info(
            "Fish TTS: generating audio for role='%s', text_len=%d chars, chunks=%d",
            voice,
            len(text),
            len(chunks),
        )

        result_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            fd, name = tempfile.mkstemp(suffix=".mp3", prefix=f"debate_fish_{i}_")
            os.close(fd)
            chunk_path = Path(name)

            client = AsyncFishAudio(api_key=self._api_key)
            try:
                audio = await client.tts.convert(
                    text=chunk,
                    reference_id=voice,
                    config=TTSConfig(max_new_tokens=4096),
                )
            finally:
                await client.close()

            with open(chunk_path, "wb") as f:
                f.write(audio)
            logger.info(
                "Fish TTS: chunk %d/%d — %d chars -> %d bytes | text: %s",
                i + 1,
                len(chunks),
                len(chunk),
                len(audio),
                chunk[:80] + "..." if len(chunk) > 80 else chunk,
            )
            result_paths.append(chunk_path)

        return result_paths

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


def _split_text(text: str, max_length: int) -> list[str]:
    if len(text) <= max_length:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk = f"{current_chunk} {sentence}".strip()

    if current_chunk:
        chunks.append(current_chunk.strip())

    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_length:
            final_chunks.append(chunk)
        else:
            for i in range(0, len(chunk), max_length):
                final_chunks.append(chunk[i : i + max_length])

    return final_chunks