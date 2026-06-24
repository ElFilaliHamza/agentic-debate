"""Edge-TTS wrapper: generate MP3 audio from text."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path

import edge_tts


MAX_TTS_LENGTH = 5000  # Edge-TTS practical limit per request


async def generate_audio(
    text: str,
    voice: str = "en-US-AriaNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
    output_path: Path | None = None,
) -> Path:
    """Generate an MP3 file from text using Edge-TTS.

    Args:
        text: The text to synthesize.
        voice: Edge-TTS voice name (e.g. "en-US-AriaNeural").
        rate: Speaking rate adjustment (e.g. "+10%", "-5%").
        pitch: Pitch adjustment (e.g. "+2Hz", "-3Hz").
        volume: Volume adjustment (e.g. "+20%", "-10%").
        output_path: Where to save the MP3. If None, creates a temp file.

    Returns:
        Path to the generated MP3 file.
    """
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
    else:
        chunk_paths: list[Path] = []
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
            chunk_paths.append(chunk_path)

        with open(output_path, "wb") as outfile:
            for chunk_path in chunk_paths:
                with open(chunk_path, "rb") as infile:
                    outfile.write(infile.read())
                chunk_path.unlink()

    return output_path


def generate_audio_sync(
    text: str,
    voice: str = "en-US-AriaNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
    output_path: Path | None = None,
) -> Path:
    """Synchronous wrapper for generate_audio."""
    return asyncio.run(
        generate_audio(text, voice, rate, pitch, volume, output_path)
    )


def _split_text(text: str, max_length: int) -> list[str]:
    """Split text on sentence boundaries if it exceeds max_length."""
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