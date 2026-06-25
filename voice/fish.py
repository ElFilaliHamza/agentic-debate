"""Fish Audio TTS strategy — uses the fish-audio-sdk for voice synthesis."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

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


class FishAudioStrategy(TTSProvider):
    """Fish Audio TTS provider with per-role voice IDs from env vars.

    Sends the full text in a single API call — Fish Audio handles internal
    chunking via its ``chunk_length`` parameter (range 100–300) with
    ``condition_on_previous_chunks`` enabled by default, which preserves
    prosody and voice consistency across the entire text.
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

    async def generate_audio(
        self,
        text: str,
        voice: str,
        output_path: Path | None = None,
    ) -> list[Path]:
        """Generate audio from text using Fish Audio TTS.

        The entire text is sent in a single request.  Fish Audio's server
        handles chunking internally (controlled by ``chunk_length`` in
        ``TTSConfig``), with ``condition_on_previous_chunks`` preserving
        prosody continuity across internal chunks.

        Args:
            text: The full text to synthesize.
            voice: Fish Audio reference_id (voice model ID).
            output_path: If provided, save the audio here; otherwise a temp file.

        Returns:
            A list containing the single path to the generated audio file.
        """
        from fishaudio import AsyncFishAudio
        from fishaudio.types import TTSConfig

        model = os.getenv("FISH_MODEL", "s2.1-pro")

        logger.info(
            "Fish TTS: generating audio for role='%s', text_len=%d chars, model=%s",
            voice,
            len(text),
            model,
        )

        if output_path is not None:
            destination = output_path
        else:
            fd, name = tempfile.mkstemp(suffix=".wav", prefix="debate_fish_")
            os.close(fd)
            destination = Path(name)

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

        with open(destination, "wb") as f:
            f.write(audio)

        logger.info(
            "Fish TTS: completed — %d chars -> %d bytes, saved to %s",
            len(text),
            len(audio),
            destination.name,
        )
        return [destination]

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