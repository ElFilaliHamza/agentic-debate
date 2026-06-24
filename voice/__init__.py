"""Voice module — Edge-TTS generation and audio playback."""

from voice.player import speak, play_audio, cleanup_audio
from voice.voices import VoiceAssignment
from voice.tts import generate_audio, generate_audio_sync

__all__ = [
    "speak",
    "play_audio",
    "cleanup_audio",
    "VoiceAssignment",
    "generate_audio",
    "generate_audio_sync",
]