"""Audio playback using pygame. Play MP3 files synchronously."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_pygame_initialized = False


def _ensure_pygame_init() -> None:
    """Initialize pygame mixer once."""
    global _pygame_initialized
    if not _pygame_initialized:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
        _pygame_initialized = True


def play_audio(file_path: Path) -> None:
    """Play an MP3 file synchronously via pygame, then unload."""
    _ensure_pygame_init()
    import pygame
    import time

    try:
        pygame.mixer.music.load(str(file_path))
        logger.info("Player: loaded %s, file_size=%d bytes", file_path, file_path.stat().st_size)
        start = time.monotonic()
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(30)
        pygame.time.wait(500)
        elapsed = time.monotonic() - start
        logger.info("Player: playback finished in %.2f seconds", elapsed)
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