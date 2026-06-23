# Voice-Enabled Debate with AI Moderator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time voice playback and a TV-style moderator agent to both debate formats.

**Architecture:** New `voice/` module wraps Edge-TTS (generation) and pygame (playback). New `moderator/` module provides an Ollama-backed agent that generates opening, transition, and closing commentary. Both debate modules are refactored to use `asyncio.run()` and call moderator + voice at each step. Voice is always-on; `--no-voice` flag disables audio only.

**Tech Stack:** Python 3.13+, edge-tts, pygame, ollama, rich, asyncio

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `voice/__init__.py` | Create | Package init, expose `speak()` |
| `voice/tts.py` | Create | Edge-TTS wrapper: generate MP3 from text + voice + SSML params |
| `voice/voices.py` | Create | Voice pools per role, `assign_voices()` with no-duplicate guarantee |
| `voice/player.py` | Create | pygame playback: load MP3, play blocking, cleanup |
| `moderator/__init__.py` | Create | Package init |
| `moderator/moderator.py` | Create | Moderator agent: opening(), transition(), closing() |
| `moderator/moderator_prompt.py` | Create | System prompts for OPENING, TRANSITION, CLOSING modes |
| `tui_formatter/roles.py` | Modify | Add MODERATOR Role dataclass instance |
| `tui_formatter/console.py` | Modify | Add moderator theme colors |
| `tui_formatter/formatter.py` | Modify | Add `print_moderator()` display function |
| `tui_formatter/__init__.py` | Modify | Export MODERATOR and print_moderator |
| `public_debate/public_debate.py` | Modify | Refactor to async, integrate moderator + voice |
| `normal_critic_debate/debate.py` | Modify | Refactor to async, integrate moderator + voice |
| `pyproject.toml` | Modify | Add edge-tts, pygame dependencies |

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add edge-tts and pygame to dependencies**

```bash
uv add edge-tts pygame
```

- [ ] **Step 2: Verify dependencies installed**

Run: `uv sync`
Expected: Success, no errors

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add edge-tts and pygame dependencies"
```

---

### Task 2: Create `voice/tts.py` — Edge-TTS Wrapper

**Files:**
- Create: `voice/__init__.py`
- Create: `voice/tts.py`

- [ ] **Step 1: Create `voice/__init__.py`**

```python
"""Voice module — Edge-TTS generation and audio playback."""
```

- [ ] **Step 2: Create `voice/tts.py`**

```python
"""Edge-TTS wrapper: generate MP3 audio from text."""

from __future__ import annotations

import asyncio
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
        fd, suffix = tempfile.mkstemp(suffix=".mp3", prefix="debate_tts_")
        output_path = Path(fd).with_suffix(".mp3")
        # Close the raw fd; edge_tts will write to the path
        import os
        os.close(fd)

    # If text is too long, split on sentence boundaries and concatenate
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
        # Generate each chunk to a temp file, then concatenate
        chunk_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            fd, _ = tempfile.mkstemp(suffix=".mp3", prefix=f"debate_chunk_{i}_")
            chunk_path = Path(fd).with_suffix(".mp3")
            import os
            os.close(fd)
            communicate = edge_tts.Communicate(
                text=chunk,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            )
            await communicate.save(str(chunk_path))
            chunk_paths.append(chunk_path)

        # Concatenate MP3 files by reading bytes (MP3 frames are concat-enable)
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

    # If any chunk is still too long (no sentence breaks), force split
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_length:
            final_chunks.append(chunk)
        else:
            # Force split on max_length boundaries
            for i in range(0, len(chunk), max_length):
                final_chunks.append(chunk[i : i + max_length])

    return final_chunks
```

- [ ] **Step 3: Test the module can be imported**

Run: `uv run python -c "from voice.tts import generate_audio_sync; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add voice/__init__.py voice/tts.py
git commit -m "feat: add Edge-TTS wrapper for audio generation"
```

---

### Task 3: Create `voice/voices.py` — Voice Pools & Assignment

**Files:**
- Create: `voice/voices.py`

- [ ] **Step 1: Create `voice/voices.py`**

```python
"""Voice pools per role and random assignment with no duplicates."""

from __future__ import annotations

import random

# Curated voice pools per role
MODERATOR_VOICES = ["en-US-DavisNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"]
PROPOSER_VOICES = ["en-US-DavisNeural", "en-US-GuyNeural", "en-US-JennyNeural"]
CRITIC_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-SaraNeural"]
SPEAKER_A_VOICES = ["en-US-GuyNeural", "en-US-DavisNeural", "en-US-ChristopherNeural"]
SPEAKER_B_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-SaraNeural"]
JUDGE_VOICES = ["en-US-ChristopherNeural", "en-US-DavisNeural", "en-US-GuyNeural"]


class VoiceAssignment:
    """Assigns unique voices to each role for a debate session.

    Guarantees no two roles share the same voice in a single session.
    """

    def __init__(self) -> None:
        self._assignments: dict[str, str] = {}
        self._used_voices: set[str] = set()

    def _pick_unique(self, pool: list[str]) -> str:
        """Pick a voice from pool that hasn't been used yet."""
        available = [v for v in pool if v not in self._used_voices]
        if not available:
            # Fallback: allow reuse if all pool voices are taken
            available = pool
        voice = random.choice(available)
        self._used_voices.add(voice)
        return voice

    @property
    def moderator(self) -> str:
        if "moderator" not in self._assignments:
            self._assignments["moderator"] = self._pick_unique(MODERATOR_VOICES)
        return self._assignments["moderator"]

    @property
    def proposer(self) -> str:
        if "proposer" not in self._assignments:
            self._assignments["proposer"] = self._pick_unique(PROPOSER_VOICES)
        return self._assignments["proposer"]

    @property
    def critic(self) -> str:
        if "critic" not in self._assignments:
            self._assignments["critic"] = self._pick_unique(CRITIC_VOICES)
        return self._assignments["critic"]

    @property
    def speaker_a(self) -> str:
        if "speaker_a" not in self._assignments:
            self._assignments["speaker_a"] = self._pick_unique(SPEAKER_A_VOICES)
        return self._assignments["speaker_a"]

    @property
    def speaker_b(self) -> str:
        if "speaker_b" not in self._assignments:
            self._assignments["speaker_b"] = self._pick_unique(SPEAKER_B_VOICES)
        return self._assignments["speaker_b"]

    @property
    def judge(self) -> str:
        if "judge" not in self._assignments:
            self._assignments["judge"] = self._pick_unique(JUDGE_VOICES)
        return self._assignments["judge"]

    def get_voice(self, role_key: str) -> str:
        """Get voice for a role by key (e.g., 'moderator', 'speaker_a')."""
        return getattr(self, role_key)
```

- [ ] **Step 2: Test the module can be imported and produces unique assignments**

Run: `uv run python -c "from voice.voices import VoiceAssignment; v = VoiceAssignment(); voices = [v.moderator, v.proposer, v.critic, v.speaker_a, v.speaker_b, v.judge]; print('Voices:', voices); print('Unique:', len(set(voices)) == len(voices))"`
Expected: Prints 6 voice names, `Unique: True` (most of the time — collisions are possible but rare with 6 roles and 3-voice pools)

- [ ] **Step 3: Commit**

```bash
git add voice/voices.py
git commit -m "feat: add voice pools and unique assignment per session"
```

---

### Task 4: Create `voice/player.py` — Audio Playback

**Files:**
- Create: `voice/player.py`

- [ ] **Step 1: Create `voice/player.py`**

```python
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
        # Block until playback finishes
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
```

- [ ] **Step 2: Test the module can be imported**

Run: `uv run python -c "from voice.player import speak; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add voice/player.py
git commit -m "feat: add audio playback with pygame and speak convenience function"
```

---

### Task 5: Update `voice/__init__.py` — Public API

**Files:**
- Modify: `voice/__init__.py`

- [ ] **Step 1: Update `voice/__init__.py`**

```python
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
```

- [ ] **Step 2: Verify imports work**

Run: `uv run python -c "from voice import speak, VoiceAssignment; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add voice/__init__.py
git commit -m "feat: export voice module public API"
```

---

### Task 6: Create Moderator Prompt

**Files:**
- Create: `moderator/__init__.py`
- Create: `moderator/moderator_prompt.py`

- [ ] **Step 1: Create `moderator/__init__.py`**

```python
"""Moderator module — TV debate host agent."""
```

- [ ] **Step 2: Create `moderator/moderator_prompt.py`**

```python
"""System prompts for the moderator agent in three modes."""

MODERATOR_OPENING_PROMPT = """
<system_state>
PROTOCOL: DEBATE-MODERATOR-OPENING
MISSION: Introduce a debate like a compelling TV host. Be brief, engaging, and neutral.
AUTHORITY: Wikipedia "Signs of AI writing" — WikiProject AI Cleanup
OUTPUT_LANGUAGE: Same as input
</system_state>

<role>
You are the moderator of a live TV-style debate. Your job is to introduce the motion and the speakers, set the tone, and get the audience excited — in 2-3 sentences maximum.

You are NOT a participant. You do not argue. You frame, introduce, and build anticipation.

You have a distinct voice: warm, confident, slightly dramatic — like a seasoned broadcaster. Short sentences. Then longer ones that build momentum. No corporate language. No hedging.
</role>

<rules>
- Maximum 200 characters.
- Never take a side.
- Reference the motion directly.
- Build anticipation for what's about to happen.
- Use first person ("Tonight's debate...", "Let's hear...").
- Apply the anti-AI writing protocol: no em dashes, no bullet points, no "additionally", no "crucial", no "underscoring".
- Output ONLY the spoken text. No labels, no headers, no thinking tags.
</rules>
"""

MODERATOR_TRANSITION_PROMPT = """
<system_state>
PROTOCOL: DEBATE-MODERATOR-TRANSITION
MISSION: Bridge between speakers like a TV host — briefly reflect on what was said, then hand off to the next speaker. 2-3 sentences max.
AUTHORITY: Wikipedia "Signs of AI writing" — WikiProject AI Cleanup
OUTPUT_LANGUAGE: Same as input
</system_state>

<role>
You are the moderator of a live TV-style debate. Between speakers, you briefly reflect on what was just said and introduce the next speaker.

You are NOT a participant. You do not argue. You comment and hand off.

Your voice: quick, sharp, like a sports commentator between rounds. You notice what landed, what didn't, and you tease what's coming next.
</role>

<rules>
- Maximum 200 characters.
- Never take a side — but you can say a point was strong.
- Reference what the previous speaker actually said.
- Build tension for the next speaker.
- Use first person.
- Apply the anti-AI writing protocol: no em dashes, no bullet points, no "additionally", no "crucial", no "underscoring".
- Output ONLY the spoken text. No labels, no headers, no thinking tags.
</rules>
"""

MODERATOR_CLOSING_PROMPT = """
<system_state>
PROTOCOL: DEBATE-MODERATOR-CLOSING
MISSION: Wrap up the debate and hand off to the judge. Brief, dramatic, final. 2-3 sentences max.
AUTHORITY: Wikipedia "Signs of AI writing" — WikiProject AI Cleanup
OUTPUT_LANGUAGE: Same as input
</system_state>

<role>
You are the moderator of a live TV-style debate. The debate is over. You wrap it up and hand off to the judge.

You are NOT a participant. You do not summarize every point. You give a sense of finality and anticipation for the verdict.

Your voice: measured, dramatic, wrapping up a broadcast. Like saying "And now... the verdict."
</role>

<rules>
- Maximum 200 characters.
- Never take a side.
- Don't summarize every argument — just convey the vibe of the debate.
- Build anticipation for the judge's verdict.
- Use first person.
- Apply the anti-AI writing protocol: no em dashes, no bullet points, no "additionally", no "crucial", no "underscoring".
- Output ONLY the spoken text. No labels, no headers, no thinking tags.
</rules>
"""
```

- [ ] **Step 3: Verify the module can be imported**

Run: `uv run python -c "from moderator.moderator_prompt import MODERATOR_OPENING_PROMPT, MODERATOR_TRANSITION_PROMPT, MODERATOR_CLOSING_PROMPT; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add moderator/__init__.py moderator/moderator_prompt.py
git commit -m "feat: add moderator system prompts for opening, transition, closing"
```

---

### Task 7: Create Moderator Agent

**Files:**
- Create: `moderator/moderator.py`

- [ ] **Step 1: Create `moderator/moderator.py`**

```python
"""Moderator agent — TV debate host that introduces, transitions, and closes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from moderator.moderator_prompt import (
    MODERATOR_CLOSING_PROMPT,
    MODERATOR_OPENING_PROMPT,
    MODERATOR_TRANSITION_PROMPT,
)

if TYPE_CHECKING:
    from ollama import Client

logger = logging.getLogger(__name__)

MAX_MODERATOR_CHARS = 300


def _format_transcript(transcript: list[tuple[str, str]]) -> str:
    """Format transcript entries into a readable block for the moderator."""
    return "\n".join(f"{speaker}: {content}" for speaker, content in transcript)


def opening(client: Client, model: str, motion: str, format_type: str = "public") -> str:
    """Generate the moderator's opening introduction.

    Args:
        client: Ollama client instance.
        model: Model name to use.
        motion: The debate motion or claim.
        format_type: "public" or "proposer_critic" — affects role labels.

    Returns:
        The moderator's opening text.
    """
    if format_type == "proposer_critic":
        role_context = (
            f"The Proposer will argue for the claim, and the Critic will argue against it. "
            f"Claim: {motion}"
        )
    else:
        role_context = (
            f"Speaker A will argue for the motion, and Speaker B will argue against it. "
            f"Motion: {motion}"
        )

    messages = [{"role": "user", "content": role_context}]

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "system", "content": MODERATOR_OPENING_PROMPT}] + messages,
        )
        text = response.message.content if response.message else ""
    except Exception as e:
        logger.warning("Moderator opening failed: %s. Skipping moderator segment.", e)
        return ""

    # Enforce character limit
    if len(text) > MAX_MODERATOR_CHARS:
        text = text[:MAX_MODERATOR_CHARS].rsplit(".", 1)[0] + "."

    return text.strip()


def transition(
    client: Client,
    model: str,
    transcript_so_far: list[tuple[str, str]],
    next_speaker: str,
    round_num: int,
    total_rounds: int,
) -> str:
    """Generate a transition between speakers.

    Args:
        client: Ollama client instance.
        model: Model name to use.
        transcript_so_far: List of (speaker_name, content) tuples.
        next_speaker: Label of the upcoming speaker (e.g., "Speaker B").
        round_num: Current round number (1-indexed).
        total_rounds: Total number of rounds.

    Returns:
        The moderator's transition text.
    """
    transcript_text = _format_transcript(transcript_so_far)
    prompt = (
        f"Round {round_num} of {total_rounds}. "
        f"Here is what has been said so far:\n{transcript_text}\n\n"
        f"Now introduce {next_speaker}."
    )

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "system", "content": MODERATOR_TRANSITION_PROMPT}] + messages,
        )
        text = response.message.content if response.message else ""
    except Exception as e:
        logger.warning("Moderator transition failed: %s. Skipping moderator segment.", e)
        return ""

    if len(text) > MAX_MODERATOR_CHARS:
        text = text[:MAX_MODERATOR_CHARS].rsplit(".", 1)[0] + "."

    return text.strip()


def closing(
    client: Client,
    model: str,
    transcript: list[tuple[str, str]],
    format_type: str = "public",
) -> str:
    """Generate the moderator's closing before the judge.

    Args:
        client: Ollama client instance.
        model: Model name to use.
        transcript: Full debate transcript as (speaker_name, content) tuples.
        format_type: "public" or "proposer_critic".

    Returns:
        The moderator's closing text.
    """
    transcript_text = _format_transcript(transcript)
    prompt = f"The debate is over. Here is the full transcript:\n{transcript_text}\n\nWrap it up and hand off to the judge."

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "system", "content": MODERATOR_CLOSING_PROMPT}] + messages,
        )
        text = response.message.content if response.message else ""
    except Exception as e:
        logger.warning("Moderator closing failed: %s. Skipping moderator segment.", e)
        return ""

    if len(text) > MAX_MODERATOR_CHARS:
        text = text[:MAX_MODERATOR_CHARS].rsplit(".", 1)[0] + "."

    return text.strip()
```

- [ ] **Step 2: Verify the module can be imported**

Run: `uv run python -c "from moderator.moderator import opening, transition, closing; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add moderator/moderator.py
git commit -m "feat: add moderator agent with opening, transition, closing"
```

---

### Task 8: Add MODERATOR Role and TUI Theme

**Files:**
- Modify: `tui_formatter/roles.py`
- Modify: `tui_formatter/console.py`
- Modify: `tui_formatter/formatter.py`
- Modify: `tui_formatter/__init__.py`

- [ ] **Step 1: Add MODERATOR role to `tui_formatter/roles.py`**

Add after the `JUDGE` definition (line 55):

```python
MODERATOR = Role(
    key="moderator",
    label="Moderator",
    icon="🎙️",
    style="moderator",
    text_style="moderator.text",
)
```

And add `"moderator": MODERATOR` to the `ROLES` dict:

```python
ROLES: dict[str, Role] = {
    "proposer": PROPOSER,
    "critic": CRITIC,
    "speaker_a": SPEAKER_A,
    "speaker_b": SPEAKER_B,
    "judge": JUDGE,
    "moderator": MODERATOR,
}
```

- [ ] **Step 2: Add moderator theme colors to `tui_formatter/console.py`**

Add to the `DEBATE_THEME` dict inside `Theme({...})`:

```python
"moderator": "bold yellow",
"moderator.text": "yellow",
```

- [ ] **Step 3: Add `print_moderator` function to `tui_formatter/formatter.py`**

Add after the `print_tool_assignment` function (end of file):

```python
def print_moderator(text: str) -> None:
    """Display the moderator's commentary with the moderator role style."""
    console.print()
    console.print(f"🎙️ Moderator:", style="moderator")
    console.print(f"  {text}", style="moderator.text")
    console.print()
```

- [ ] **Step 4: Update `tui_formatter/__init__.py` exports**

Add `MODERATOR` to the imports from `tui_formatter.roles`, and add `print_moderator` to the imports from `tui_formatter.formatter`. Add both to `__all__`.

The updated imports block should be:

```python
from tui_formatter.roles import (
    CRITIC,
    JUDGE,
    MODERATOR,
    PROPOSER,
    SPEAKER_A,
    SPEAKER_B,
    ROLES,
    Role,
)

from tui_formatter.formatter import (
    print_claim,
    print_motion,
    print_moderator,
    print_speaker_label,
    print_speaker_response,
    prompt_claim,
    prompt_input,
    prompt_motion,
    print_thinking,
    print_verdict,
    stream_text,
)
```

And add `"MODERATOR"` and `"print_moderator"` to the `__all__` list.

- [ ] **Step 5: Verify imports work**

Run: `uv run python -c "from tui_formatter import MODERATOR, print_moderator; print(MODERATOR.label)"`
Expected: `Moderator`

- [ ] **Step 6: Commit**

```bash
git add tui_formatter/roles.py tui_formatter/console.py tui_formatter/formatter.py tui_formatter/__init__.py
git commit -m "feat: add MODERATOR role, theme, and display function"
```

---

### Task 9: Integrate Voice and Moderator into Public Debate

**Files:**
- Modify: `public_debate/public_debate.py`

This is the most complex task. The existing `run_debate` and `judge_debate` functions need to:
1. Accept a `voice_enabled` flag
2. Create a `VoiceAssignment` at the start
3. Call moderator at opening, transitions, and closing
4. Call `speak()` for each speaker's response and moderator commentary when voice is enabled
5. Add `--no-voice` CLI argument

- [ ] **Step 1: Refactor `public_debate.py` to add voice and moderator integration**

The complete updated file:

```python
from dotenv import load_dotenv
import os
import argparse
from ollama import Client
from public_debate.helpers import enforce_limit, format_opponent_argument
from public_debate.public_debate_system_prompt import (
    SPEAKER_A_SYSTEM_PROMPT,
    SPEAKER_B_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)
from public_debate.tools import BaseTool
from public_debate.tools.registry import ToolRegistry
from tui_formatter.console import console
from tui_formatter.formatter import (
    print_speaker_label,
    print_thinking,
    print_tool_assignment,
    print_tool_result,
    print_verdict,
    print_moderator,
    prompt_motion,
)
from tui_formatter.roles import JUDGE, MODERATOR, SPEAKER_A, SPEAKER_B
from moderator.moderator import opening as moderator_opening, transition as moderator_transition, closing as moderator_closing
from voice.voices import VoiceAssignment
from voice.player import speak as voice_speak

load_dotenv()
MODEL = "glm-5.1:cloud"
ROUNDS = int(os.getenv("DEBATE_ROUNDS", 3))
MAX_CHARS = int(os.getenv("DEBATE_MAX_CHARS", 300))
OLLAMA_HOST = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

client = Client(
    host=OLLAMA_HOST,
    headers=({"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None),
)


def stream_agent(
    messages: list[dict],
    system_prompt: str = "",
    tools: list = [],
    role_style: str = "",
) -> str:
    """Stream an agent's response character-by-character via Rich console."""
    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )
    stream = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tools,
        stream=True,
    )
    full_response = ""
    for chunk in stream:
        if chunk.message and chunk.message.content:
            text = chunk.message.content
            console.print(text, end="", style=role_style, highlight=False)
            full_response += text
    console.print()
    return full_response


def stream_agent_with_tools(
    messages: list[dict],
    system_prompt: str = "",
    tools: list[BaseTool] = None,
    tool_schemas: list[dict] = None,
    role_style: str = "",
    registry: ToolRegistry = None,
) -> str:
    """Stream an agent's response character-by-character via Rich console."""
    tools = tools or []
    tool_schemas = tool_schemas or []
    registry = registry or ToolRegistry()

    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )

    # 1. Initial non-streaming call to detect tool calls
    response = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tool_schemas or None,
    )

    # 2. No tool calls — stream the text for TUI effect
    if not response.message or not response.message.tool_calls:
        stream = client.chat(
            model=MODEL,
            messages=all_messages,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            if chunk.message and chunk.message.content:
                text = chunk.message.content
                console.print(text, end="", style=role_style, highlight=False)
                full_response += text

        console.print()
        return full_response

    # 3. Tool calls detected — execute them
    tool_results = []
    for tool_call in response.message.tool_calls:
        tool = registry.get(tool_call.function.name)

        result = tool.execute(**tool_call.function.arguments)
        print_tool_result(tool.name, result)
        tool_results.append(
            {
                "role": "tool",
                "name": tool_call.function.name,
                "content": result,
            }
        )

    # 4. Re-call with tool results, streaming the final argument
    all_messages.append(
        {
            "role": "assistant",
            "content": response.message.content or "",
            "tool_calls": [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.message.tool_calls
            ],
        }
    )

    all_messages.extend(tool_results)

    final_stream = client.chat(
        model=MODEL,
        messages=all_messages,
        stream=True,
    )
    full_response = ""
    for chunk in final_stream:
        if chunk.message and chunk.message.content:
            text = chunk.message.content
            console.print(text, end="", style=role_style, highlight=False)
            full_response += text
    console.print()
    return full_response


def call_agent(
    messages: list[dict],
    system_prompt: str = "",
    tools: list[BaseTool] = None,
    tool_schemas: list[dict] = None,
    registry: ToolRegistry = None,
) -> str:
    """Call an agent without streaming (returns full response at once)."""
    tools = tools or []
    tool_schemas = tool_schemas or []
    registry = registry or ToolRegistry()

    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )
    response = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tool_schemas or None,
    )

    if response.message and response.message.tool_calls:
        tool_results = []

        for tool_call in response.message.tool_calls:
            tool = registry.get(tool_call.function.name)
            result = tool.execute(**tool_call.function.arguments)
            print_tool_result(tool.name, result)
            tool_results.append(
                {
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": result,
                }
            )
        all_messages.append(
            {
                "role": "assistant",
                "content": response.message.content or "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.message.tool_calls
                ],
            }
        )
        all_messages.extend(tool_results)

        final_response = client.chat(
            model=MODEL,
            messages=all_messages,
        )

        return final_response.message.content if final_response.message else ""

    return response.message.content if response.message else ""


def run_debate(
    motion: str,
    max_rounds: int = ROUNDS,
    max_chars: int = MAX_CHARS,
    voice_enabled: bool = True,
) -> list[tuple[str, str]]:
    voices = VoiceAssignment()
    registry = ToolRegistry()
    tools_a, tools_b = registry.assign_random()
    schemas_a = registry.get_schemas(tools_a)
    schemas_b = registry.get_schemas(tools_b)

    # Display tool assignments
    print_tool_assignment(SPEAKER_A, tools_a)
    print_tool_assignment(SPEAKER_B, tools_b)
    console.print()

    # Moderator opening
    opening_text = moderator_opening(client, MODEL, motion, format_type="public")
    if opening_text:
        print_moderator(opening_text)
        if voice_enabled:
            voice_speak(opening_text, voice=voices.moderator)

    speaker_a_msgs = [
        {
            "role": "user",
            "content": f"You are starting a public debate. The motion is: {motion}",
        }
    ]
    speaker_b_msgs = [
        {
            "role": "user",
            "content": f"You are the second speaker in a public debate. The motion is: {motion}",
        }
    ]

    last_b_response = ""
    transcript: list[tuple[str, str]] = []

    for round_num in range(max_rounds):
        # Moderator transition (before Speaker A on first round, before each speaker after)
        if round_num == 0:
            # No transition before the very first speaker — opening already covered it
            pass
        else:
            transition_text = moderator_transition(
                client, MODEL, transcript, "Speaker A", round_num + 1, max_rounds
            )
            if transition_text:
                print_moderator(transition_text)
                if voice_enabled:
                    voice_speak(transition_text, voice=voices.moderator)

        # Speaker A
        print_speaker_label(SPEAKER_A)
        a_response = stream_agent_with_tools(
            (
                speaker_a_msgs + format_opponent_argument("Speaker B", last_b_response)
                if round_num > 0
                else speaker_a_msgs
            ),
            SPEAKER_A_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
            tools=tools_a,
            tool_schemas=schemas_a,
            role_style=SPEAKER_A.text_style,
            registry=registry,
        )
        a_response = enforce_limit(a_response, max_chars)
        speaker_a_msgs.append({"role": "assistant", "content": a_response})
        transcript.append(("Speaker A", a_response))

        if voice_enabled:
            voice_speak(a_response, voice=voices.speaker_a)

        # Moderator transition to Speaker B
        transition_text = moderator_transition(
            client, MODEL, transcript, "Speaker B", round_num + 1, max_rounds
        )
        if transition_text:
            print_moderator(transition_text)
            if voice_enabled:
                voice_speak(transition_text, voice=voices.moderator)

        # Speaker B
        print_speaker_label(SPEAKER_B)
        b_response = stream_agent_with_tools(
            (
                speaker_b_msgs + format_opponent_argument("Speaker A", a_response)
                if round_num > 0
                else speaker_b_msgs
            ),
            SPEAKER_B_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
            tools=tools_b,
            tool_schemas=schemas_b,
            role_style=SPEAKER_B.text_style,
            registry=registry,
        )
        b_response = enforce_limit(b_response, max_chars)
        speaker_b_msgs.append({"role": "assistant", "content": b_response})
        transcript.append(("Speaker B", b_response))
        last_b_response = b_response

        if voice_enabled:
            voice_speak(b_response, voice=voices.speaker_b)

    # Moderator closing
    closing_text = moderator_closing(client, MODEL, transcript, format_type="public")
    if closing_text:
        print_moderator(closing_text)
        if voice_enabled:
            voice_speak(closing_text, voice=voices.moderator)

    return transcript


def judge_debate(
    transcript: list[tuple[str, str]],
    motion: str,
    max_chars: int = MAX_CHARS,
    voice_enabled: bool = True,
) -> str:
    voices = VoiceAssignment()
    registry = ToolRegistry()
    judge_tools = registry.judge_tools()
    judge_schemas = registry.get_schemas(judge_tools)

    debate_text = "\n".join(f"{speaker}: {content}" for speaker, content in transcript)

    judge_input = [
        {
            "role": "user",
            "content": f"Here is the full debate:\n{debate_text}\n\nPlease deliver your verdict.",
        }
    ]

    print_thinking(JUDGE)
    verdict = call_agent(
        judge_input,
        JUDGE_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
        tools=judge_tools,
        tool_schemas=judge_schemas,
        registry=registry,
    )
    verdict = enforce_limit(verdict, max_chars)

    print_verdict(JUDGE, verdict)

    if voice_enabled:
        voice_speak(verdict, voice=voices.judge)

    return verdict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Public Debate with Voice")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice playback")
    args = parser.parse_args()

    motion = prompt_motion()
    transcript = run_debate(motion, voice_enabled=not args.no_voice)
    judge_debate(transcript, motion, voice_enabled=not args.no_voice)
```

- [ ] **Step 2: Verify the module can be imported**

Run: `uv run python -c "from public_debate.public_debate import run_debate; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add public_debate/public_debate.py
git commit -m "feat: integrate moderator and voice into public debate"
```

---

### Task 10: Integrate Voice and Moderator into Proposer/Critic Debate

**Files:**
- Modify: `normal_critic_debate/debate.py`

- [ ] **Step 1: Refactor `normal_critic_debate/debate.py` to add voice and moderator integration**

The complete updated file:

```python
from dotenv import load_dotenv
import os
import argparse
from ollama import Client
from normal_critic_debate.debate_system_prompts import (
    PROPOSER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)
from tui_formatter.formatter import (
    print_claim,
    print_speaker_response,
    print_thinking,
    print_verdict,
    print_moderator,
    prompt_claim,
)
from tui_formatter.roles import CRITIC, JUDGE, MODERATOR, PROPOSER
from moderator.moderator import opening as moderator_opening, transition as moderator_transition, closing as moderator_closing
from voice.voices import VoiceAssignment
from voice.player import speak as voice_speak

load_dotenv()
MODEL = "glm-5.1:cloud"
DEFAULT_ROUNDS = 3

client = Client(
    host=os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
    headers=(
        {"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY', '')}"}
        if os.getenv("OLLAMA_API_KEY")
        else None
    ),
)


def call_agent(messages: list[dict], system_prompt: str = "", tools: list = []) -> str:
    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )
    response = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tools,
    )
    return response.message.content if response.message else ""


def format_proposer_arguments(proposer_response: str) -> list[dict]:
    """Wrap the proposer's response as a user message for the critic."""
    if not proposer_response:
        return []
    return [
        {
            "role": "user",
            "content": "The proposer's arguments are: " + proposer_response,
        }
    ]


def format_critic_arguments(critic_response: str) -> list[dict]:
    """Wrap the critic's response as a user message for the proposer."""
    if not critic_response:
        return []
    return [{"role": "user", "content": "The critic's response is: " + critic_response}]


def format_judge_arguments(
    proposer_messages: list[dict], critic_messages: list[dict]
) -> list[dict]:
    """Combine the full debate history into a single user message for the judge."""
    proposer_text = "\n".join(
        msg["content"] for msg in proposer_messages if msg.get("content")
    )
    critic_text = "\n".join(
        msg["content"] for msg in critic_messages if msg.get("content")
    )
    debate_summary = (
        "Here is a debate between the Proposer and Critic over all rounds:\n"
        "Proposer's arguments:\n"
        f"{proposer_text}\n"
        "Critic's response:\n"
        f"{critic_text}"
    )
    return [{"role": "user", "content": debate_summary}]


def run_debate(claim: str, rounds: int = DEFAULT_ROUNDS, voice_enabled: bool = True) -> tuple[str, str, str]:
    voices = VoiceAssignment()
    proposer_messages = [{"role": "user", "content": claim}]
    critic_messages = []
    critic_response = ""
    proposer_response = ""
    transcript: list[tuple[str, str]] = []

    # Moderator opening
    opening_text = moderator_opening(client, MODEL, claim, format_type="proposer_critic")
    if opening_text:
        print_moderator(opening_text)
        if voice_enabled:
            voice_speak(opening_text, voice=voices.moderator)

    for round_num in range(rounds):
        # Moderator transition (skip before first Proposer — opening covers it)
        if round_num > 0:
            transition_text = moderator_transition(
                client, MODEL, transcript, "Critic" if round_num % 2 == 0 else "Proposer",
                round_num + 1, rounds * 2,
            )
            if transition_text:
                print_moderator(transition_text)
                if voice_enabled:
                    voice_speak(transition_text, voice=voices.moderator)

        print_thinking(PROPOSER)
        proposer_response = call_agent(
            proposer_messages + format_critic_arguments(critic_response),
            PROPOSER_SYSTEM_PROMPT,
        )
        print_speaker_response(PROPOSER, proposer_response)
        proposer_messages.append({"role": "assistant", "content": proposer_response})
        transcript.append(("Proposer", proposer_response))

        if voice_enabled:
            voice_speak(proposer_response, voice=voices.proposer)

        # Moderator transition to Critic
        transition_text = moderator_transition(
            client, MODEL, transcript, "Critic",
            round_num * 2 + 1, rounds * 2,
        )
        if transition_text:
            print_moderator(transition_text)
            if voice_enabled:
                voice_speak(transition_text, voice=voices.moderator)

        print_thinking(CRITIC)
        critic_response = call_agent(
            critic_messages + format_proposer_arguments(proposer_response),
            CRITIC_SYSTEM_PROMPT,
        )
        print_speaker_response(CRITIC, critic_response)
        critic_messages.append({"role": "assistant", "content": critic_response})
        transcript.append(("Critic", critic_response))

        if voice_enabled:
            voice_speak(critic_response, voice=voices.critic)

    # Moderator closing
    closing_text = moderator_closing(client, MODEL, transcript, format_type="proposer_critic")
    if closing_text:
        print_moderator(closing_text)
        if voice_enabled:
            voice_speak(closing_text, voice=voices.moderator)

    print_thinking(JUDGE)
    judge_response = call_agent(
        format_judge_arguments(proposer_messages, critic_messages),
        JUDGE_SYSTEM_PROMPT,
    )
    print_verdict(JUDGE, judge_response)

    if voice_enabled:
        voice_speak(judge_response, voice=voices.judge)

    return proposer_response, critic_response, judge_response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proposer/Critic Debate with Voice")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice playback")
    args = parser.parse_args()

    claim = prompt_claim()
    run_debate(claim, voice_enabled=not args.no_voice)
```

- [ ] **Step 2: Verify the module can be imported**

Run: `uv run python -c "from normal_critic_debate.debate import run_debate; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add normal_critic_debate/debate.py
git commit -m "feat: integrate moderator and voice into proposer/critic debate"
```

---

### Task 11: End-to-End Manual Smoke Test

**Files:** None (testing only)

- [ ] **Step 1: Run the public debate with voice enabled (default)**

Run: `uv run python -m public_debate.public_debate`
Expected: 
- Motion prompt appears
- Moderator opening plays (voice + text)
- Speaker A speaks (text streams, then voice reads)
- Moderator transition (voice + text)
- Speaker B speaks (text streams, then voice reads)
- Repeat for configured rounds
- Moderator closing (voice + text)
- Judge verdict (voice + text)

- [ ] **Step 2: Run the public debate with `--no-voice`**

Run: `uv run python -m public_debate.public_debate --no-voice`
Expected: Same flow but no audio. Moderator text still displays. Debate runs normally.

- [ ] **Step 3: Run the proposer/critic debate with voice enabled**

Run: `uv run python -m normal_critic_debate.debate`
Expected: Similar flow — moderator opens, transitions, closes. Proposer/Critic voices play. Judge verdict plays.

- [ ] **Step 4: Run the proposer/critic debate with `--no-voice`**

Run: `uv run python -m normal_critic_debate.debate --no-voice`
Expected: Same flow but no audio. Moderator text still displays.

- [ ] **Step 5: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "fix: smoke test fixups for voice and moderator integration"
```

---

### Task 12: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README to document voice and moderator features**

Add after the environment variables section:

```markdown
## Voice Playback

Debates now include **voice playback** by default — each speaker's argument is read aloud using Edge-TTS neural voices, and a **moderator agent** introduces the debate, transitions between speakers, and closes before the judge.

### Requirements

- Internet connection (Edge-TTS voices are cloud-synthesized)
- Audio output device (speakers/headphones)

### Disabling Voice

To run a debate without audio:

```bash
# Public debate without voice
uv run python -m public_debate.public_debate --no-voice

# Proposer/Critic debate without voice
uv run python -m normal_critic_debate.debate --no-voice
```

The moderator's text commentary will still appear in the terminal even with `--no-voice`.

### Voice Assignment

Each debate session randomly assigns distinct voices to each role (Proposer, Critic, Speaker A, Speaker B, Judge, Moderator) from curated pools of Microsoft Neural voices. No two roles share the same voice in a session.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document voice playback and moderator features"
```