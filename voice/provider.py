"""TTS provider abstraction and factory."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        voice: str,
        output_path: Path | None = None,
    ) -> list[Path]:
        """Generate audio files from text.

        Args:
            text: The text to synthesize.
            voice: Provider-specific voice identifier.
            output_path: Where to save the primary audio file. If None, creates a temp file.

        Returns:
            List of Paths to generated audio files, in playback order.
            For single-chunk generation, returns a list with one element.
        """
        ...

    @abstractmethod
    def get_voice(self, role: str) -> str:
        """Return the voice identifier for a given role.

        Args:
            role: One of 'moderator', 'proposer', 'critic',
                  'speaker_a', 'speaker_b', 'judge'.

        Returns:
            Provider-specific voice identifier string.
        """
        ...

    @abstractmethod
    def voice_assignment(self) -> dict[str, str]:
        """Return the full role-to-voice mapping."""
        ...


def get_provider() -> TTSProvider:
    """Return the configured TTS provider based on TTS_PROVIDER env var."""
    provider = os.getenv("TTS_PROVIDER", "edge").lower()
    if provider == "fish":
        from voice.fish import FishAudioStrategy

        return FishAudioStrategy()
    if provider == "edge":
        from voice.edge import EdgeTTSStrategy

        return EdgeTTSStrategy()
    raise ValueError(
        f"Unknown TTS_PROVIDER '{provider}'. Choose 'edge' or 'fish'."
    )