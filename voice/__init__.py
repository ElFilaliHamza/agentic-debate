"""Voice module — TTS generation and audio playback."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from voice.player import cleanup_audio, play_audio, play_audio_files
from voice.provider import TTSProvider, get_provider

logger = logging.getLogger(__name__)

_ROLE_ICONS: dict[str, str] = {
    "host": "🎙️",
    "proposer": "🛡️",
    "critic": "⚔️",
    "speaker_a": "🛡️",
    "speaker_b": "⚔️",
    "judge": "⚖️",
}

_provider: TTSProvider | None = None
_save_dir: Path | None = None


def _get_provider() -> TTSProvider:
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


def set_save_dir(directory: Path | None) -> None:
    """Set the directory where audio files are persisted.

    When set, all subsequent calls to :func:`speak` and
    :func:`generate_audio` will save audio files into this directory
    instead of using temporary files that are deleted after playback.

    Args:
        directory: Path to the save directory, or ``None`` to disable
                   persistence (revert to temp-file behaviour).
    """
    global _save_dir
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
    _save_dir = directory


def speak(text: str, role: str, label: str = "") -> None:
    """Generate speech from text and play it aloud.

    If a save directory has been configured via :func:`set_save_dir`,
    the generated audio is persisted there; otherwise a temporary file
    is used and deleted after playback.

    Args:
        text: The text to synthesize.
        role: Role key ('host', 'proposer', 'critic',
              'speaker_a', 'speaker_b', 'judge').
        label: Descriptive label for the audio file (e.g. "round_1",
               "opening"). Used to construct the filename when saving.
    """
    try:
        provider = _get_provider()
        voice = provider.get_voice(role)
        icon = _ROLE_ICONS.get(role, "🔊")
        display_label = role.replace("_", " ").title()
        logger.info("speak(): role='%s', voice='%s', text_len=%d", role, voice, len(text))

        output_path: Path | None = None
        if _save_dir is not None:
            filename = f"{role}_{label}.wav" if label else f"{role}.wav"
            output_path = _save_dir / filename

        from tui_formatter.console import console
        with console.status(f"  {icon} {display_label} — Generating speech...", spinner="dots"):
            audio_paths = asyncio.run(provider.generate_audio(text, voice, output_path=output_path))
        with console.status(f"  {icon} {display_label} — Speaking...", spinner="dots"):
            play_audio_files(audio_paths)
        if _save_dir is None:
            for audio_path in audio_paths:
                cleanup_audio(audio_path)
        else:
            logger.info("Audio saved: %s", ", ".join(str(p) for p in audio_paths))
    except Exception as e:
        logger.warning("Voice speak failed: %s. Continuing without audio.", e)


def generate_audio(text: str, role: str, label: str = "") -> list[Path]:
    """Generate audio from text without playing it.

    If a save directory has been configured via :func:`set_save_dir`,
    the audio is persisted there; otherwise a temporary file is used.

    Args:
        text: The text to synthesize.
        role: Role key.
        label: Descriptive label for the audio file.

    Returns:
        List of Paths to generated audio files, in playback order.
    """
    provider = _get_provider()
    voice = provider.get_voice(role)

    output_path: Path | None = None
    if _save_dir is not None:
        filename = f"{role}_{label}.wav" if label else f"{role}.wav"
        output_path = _save_dir / filename

    return asyncio.run(provider.generate_audio(text, voice, output_path=output_path))


def get_voice_assignment() -> dict[str, str]:
    """Return the full role-to-voice mapping for the active provider."""
    return _get_provider().voice_assignment()


__all__ = [
    "speak",
    "generate_audio",
    "get_voice_assignment",
    "set_save_dir",
    "play_audio",
    "cleanup_audio",
    "TTSProvider",
    "get_provider",
]