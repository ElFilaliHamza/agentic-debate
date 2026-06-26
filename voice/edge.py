"""Edge-TTS strategy — wraps Microsoft Edge TTS with voice pools."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path

import edge_tts

from voice.provider import TTSProvider

MAX_TTS_LENGTH = 5000

HOST_VOICES = ["en-US-EricNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"]
PROPOSER_VOICES = ["en-US-GuyNeural", "en-US-BrianNeural", "en-US-JennyNeural"]
CRITIC_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"]
SPEAKER_A_VOICES = ["en-US-GuyNeural", "en-US-BrianNeural", "en-US-ChristopherNeural"]
SPEAKER_B_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"]
JUDGE_VOICES = ["en-US-ChristopherNeural", "en-US-EricNeural", "en-US-GuyNeural"]

VOICE_POOLS: dict[str, list[str]] = {
    "host": HOST_VOICES,
    "proposer": PROPOSER_VOICES,
    "critic": CRITIC_VOICES,
    "speaker_a": SPEAKER_A_VOICES,
    "speaker_b": SPEAKER_B_VOICES,
    "judge": JUDGE_VOICES,
}


class EdgeTTSStrategy(TTSProvider):
    """Edge-TTS provider with random voice assignment per role."""

    def __init__(self) -> None:
        import random
        self._assignments: dict[str, str] = {}
        self._used_voices: set[str] = set()
        self._rng = random.Random()

    def _pick_unique(self, pool: list[str]) -> str:
        available = [v for v in pool if v not in self._used_voices]
        if not available:
            available = pool
        voice = self._rng.choice(available)
        self._used_voices.add(voice)
        return voice

    async def generate_audio(
        self,
        text: str,
        voice: str = "en-US-AriaNeural",
        output_path: Path | None = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> list[Path]:
        if output_path is None:
            fd, name = tempfile.mkstemp(suffix=".mp3", prefix="debate_tts_")
            os.close(fd)
            output_path = Path(name)

        chunks = _split_text(text, MAX_TTS_LENGTH)

        if len(chunks) == 1:
            communicate = edge_tts.Communicate(
                text=chunks[0],
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            await communicate.save(str(output_path))
            return [output_path]

        result_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            fd, name = tempfile.mkstemp(suffix=".mp3", prefix=f"debate_chunk_{i}_")
            os.close(fd)
            chunk_path = Path(name)
            communicate = edge_tts.Communicate(
                text=chunk,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            await communicate.save(str(chunk_path))
            result_paths.append(chunk_path)

        return result_paths

    def get_voice(self, role: str) -> str:
        if role not in self._assignments:
            pool = VOICE_POOLS.get(role)
            if pool is None:
                raise ValueError(
                    f"Unknown role '{role}'. "
                    f"Valid roles: {', '.join(VOICE_POOLS)}"
                )
            self._assignments[role] = self._pick_unique(pool)
        return self._assignments[role]

    def voice_assignment(self) -> dict[str, str]:
        for role in VOICE_POOLS:
            self.get_voice(role)
        return dict(self._assignments)


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