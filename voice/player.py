"""Audio playback using pygame. Play MP3 files synchronously."""

from __future__ import annotations

import logging
from pathlib import Path

from voice.tts import generate_audio_sync

logger = logging.getLogger(__name__)

_pygame_initialized = False


def _ensure_pygame_init() -> None:
    """Initialize pygame mixer once."""
    global _pygame_initialized
    if not _pygame_initialized:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        _pygame_initialized = True


def play_audio(file_path: Path) -> None:
    """Play an MP3 file synchronously via pygame, then unload."""
    _ensure_pygame_init()
    import pygame

    try:
        pygame.mixer.music.load(str(file_path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(30)
        pygame.mixer.music.unload()
    except pygame.error as e:
        logger.warning("Audio playback failed: %s", e)


def cleanup_audio(file_path: Path) -> None:
    """Delete a temporary audio file."""
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError as e:
        logger.warning("Failed to delete temp audio file %s: %s", file_path, e)


def speak(
    text: str,
    voice: str = "en-US-AriaNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
) -> None:
    """Generate speech from text and play it aloud.

    Convenience function that combines TTS generation and playback.
    Creates a temp MP3, plays it, then cleans up.
    """
    try:
        audio_path = generate_audio_sync(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        play_audio(audio_path)
        cleanup_audio(audio_path)
    except Exception as e:
        logger.warning("Voice speak failed: %s. Continuing without audio.", e)