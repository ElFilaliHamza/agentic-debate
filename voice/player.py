"""Audio playback using sounddevice + miniaudio. Play audio files synchronously."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import miniaudio
import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

PLAYBACK_PADDING_SECONDS = 0.3


def decode_audio(file_path: Path) -> np.ndarray:
    """Decode an audio file (WAV or MP3) to float32 PCM frames (N, 2) at 44100 Hz."""
    decoded = miniaudio.decode_file(
        str(file_path),
        nchannels=2,
        sample_rate=44100,
        output_format=miniaudio.SampleFormat.SIGNED16,
    )
    frames = np.array(decoded.samples, dtype="float32").reshape(-1, 2)
    frames /= 32768.0
    return frames


def _play_frames(frames: np.ndarray, samplerate: int = 44100) -> None:
    """Play PCM frames, blocking until playback is fully complete."""
    silence_samples = int(PLAYBACK_PADDING_SECONDS * samplerate)
    silence = np.zeros((silence_samples, 2), dtype="float32")
    padded = np.concatenate([frames, silence], axis=0)

    sd.play(padded, samplerate=samplerate, blocking=True)
    time.sleep(0.15)


def play_audio(file_path: Path) -> None:
    """Play an audio file synchronously, blocking until playback completes."""
    try:
        frames = decode_audio(file_path)
        duration = frames.shape[0] / 44100
        logger.info("Player: loaded %s, duration=%.2fs, file_size=%d bytes",
                     file_path, duration, file_path.stat().st_size)

        _play_frames(frames)
        logger.info("Player: playback finished for %s", file_path.name)
    except Exception as e:
        logger.warning("Audio playback failed: %s", e)


def play_audio_files(file_paths: list[Path]) -> None:
    """Decode multiple audio files, concatenate PCM, and play as one seamless stream."""
    try:
        all_frames = [decode_audio(p) for p in file_paths]
        for i, (p, f) in enumerate(zip(file_paths, all_frames)):
            logger.info("Player: chunk %d/%d — %s, duration=%.2fs",
                         i + 1, len(file_paths), p.name, f.shape[0] / 44100)
        combined = np.concatenate(all_frames, axis=0)
        duration = combined.shape[0] / 44100
        logger.info("Player: playing %d files as one stream, total duration=%.2fs",
                      len(file_paths), duration)

        _play_frames(combined)
        logger.info("Player: playback finished")
    except Exception as e:
        logger.warning("Audio playback failed: %s", e)


def cleanup_audio(file_path: Path) -> None:
    """Delete a temporary audio file."""
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError as e:
        logger.warning("Failed to delete temp audio file %s: %s", file_path, e)