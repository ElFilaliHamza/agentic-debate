# Fish Audio TTS Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Fish Audio as an alternative TTS provider selectable via `.env`, using the Strategy pattern with no fallback logic.

**Architecture:** A `TTSProvider` ABC defines the contract. `EdgeTTSStrategy` wraps existing Edge-TTS logic. `FishAudioStrategy` wraps the `fish-audio-sdk`. A factory reads `TTS_PROVIDER` from `.env` and returns the right strategy. The `voice/` module's public API simplifies to `speak(text, role)` and `get_voice_assignment()`.

**Tech Stack:** Python 3.13+, edge-tts, fish-audio-sdk, pygame, python-dotenv

---

## File Structure

| File | Responsibility |
|------|---------------|
| `voice/provider.py` | TTSProvider ABC + `get_provider()` factory |
| `voice/edge.py` | EdgeTTSStrategy — wraps existing Edge-TTS + voice pool logic |
| `voice/fish.py` | FishAudioStrategy — wraps fish-audio-sdk |
| `voice/__init__.py` | Public API: `speak(text, role)`, `get_voice_assignment()` |
| `voice/player.py` | Modified: accepts provider, no direct tts import |
| `voice/tts.py` | Deleted (logic moved to `edge.py`) |
| `voice/voices.py` | Deleted (logic moved to `edge.py`) |
| `normal_critic_debate/debate.py` | Modified: new import pattern |
| `public_debate/public_debate.py` | Modified: new import pattern |
| `.env.example` | Modified: add TTS vars |
| `pyproject.toml` | Modified: add `fish-audio-sdk` dependency |

---

### Task 1: Create TTSProvider ABC and factory

**Files:**
- Create: `voice/provider.py`

- [ ] **Step 1: Create `voice/provider.py`**

```python
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
    ) -> Path:
        """Generate an audio file from text.

        Args:
            text: The text to synthesize.
            voice: Provider-specific voice identifier.
            output_path: Where to save the audio. If None, creates a temp file.

        Returns:
            Path to the generated audio file.
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
```

- [ ] **Step 2: Commit**

```bash
git add voice/provider.py
git commit -m "feat: add TTSProvider ABC and get_provider factory"
```

---

### Task 2: Create EdgeTTSStrategy

**Files:**
- Create: `voice/edge.py`

- [ ] **Step 1: Create `voice/edge.py`**

This migrates the logic from `voice/tts.py` and `voice/voices.py` into a single strategy class.

```python
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

MODERATOR_VOICES = ["en-US-EricNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"]
PROPOSER_VOICES = ["en-US-GuyNeural", "en-US-BrianNeural", "en-US-JennyNeural"]
CRITIC_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"]
SPEAKER_A_VOICES = ["en-US-GuyNeural", "en-US-BrianNeural", "en-US-ChristopherNeural"]
SPEAKER_B_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"]
JUDGE_VOICES = ["en-US-ChristopherNeural", "en-US-EricNeural", "en-US-GuyNeural"]

VOICE_POOLS: dict[str, list[str]] = {
    "moderator": MODERATOR_VOICES,
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
    ) -> Path:
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
```

- [ ] **Step 2: Commit**

```bash
git add voice/edge.py
git commit -m "feat: add EdgeTTSStrategy with voice pools"
```

---

### Task 3: Create FishAudioStrategy

**Files:**
- Create: `voice/fish.py`

- [ ] **Step 1: Create `voice/fish.py`**

```python
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
    """Fish Audio TTS provider with per-role voice IDs from env vars."""

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
            value = os.getenv(env_key, "")
            if value:
                mapping[role] = value
            else:
                logger.warning(
                    "Env var %s is not set — role '%s' will have no voice.",
                    env_key,
                    role,
                )
        return mapping

    async def generate_audio(
        self,
        text: str,
        voice: str,
        output_path: Path | None = None,
    ) -> Path:
        from fishaudio import AsyncFishAudio

        if output_path is None:
            fd, name = tempfile.mkstemp(suffix=".mp3", prefix="debate_fish_")
            os.close(fd)
            output_path = Path(name)

        client = AsyncFishAudio(api_key=self._api_key)
        try:
            audio = await client.tts.convert(
                text=text,
                reference_id=voice,
            )
            with open(output_path, "wb") as f:
                f.write(audio)
        finally:
            await client.close()

        return output_path

    def get_voice(self, role: str) -> str:
        if role not in FISH_VOICE_ENV_KEYS:
            raise ValueError(
                f"Unknown role '{role}'. "
                f"Valid roles: {', '.join(FISH_VOICE_ENV_KEYS)}"
            )
        if role not in self._voice_map:
            raise ValueError(
                f"No voice configured for role '{role}'. "
                f"Set {FISH_VOICE_ENV_KEYS[role]} in your .env file."
            )
        return self._voice_map[role]

    def voice_assignment(self) -> dict[str, str]:
        return dict(self._voice_map)
```

- [ ] **Step 2: Commit**

```bash
git add voice/fish.py
git commit -m "feat: add FishAudioStrategy with per-role env config"
```

---

### Task 4: Rewrite voice/__init__.py public API

**Files:**
- Modify: `voice/__init__.py`

- [ ] **Step 1: Rewrite `voice/__init__.py`**

```python
"""Voice module — TTS generation and audio playback."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from voice.player import cleanup_audio, play_audio
from voice.provider import TTSProvider, get_provider

logger = logging.getLogger(__name__)

_provider: TTSProvider | None = None


def _get_provider() -> TTSProvider:
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


def speak(text: str, role: str) -> None:
    """Generate speech from text and play it aloud.

    Args:
        text: The text to synthesize.
        role: Role key ('moderator', 'proposer', 'critic',
              'speaker_a', 'speaker_b', 'judge').
    """
    try:
        provider = _get_provider()
        voice = provider.get_voice(role)
        audio_path = asyncio.run(provider.generate_audio(text, voice))
        play_audio(audio_path)
        cleanup_audio(audio_path)
    except Exception as e:
        logger.warning("Voice speak failed: %s. Continuing without audio.", e)


def generate_audio(text: str, role: str) -> Path:
    """Generate audio from text without playing it.

    Args:
        text: The text to synthesize.
        role: Role key.

    Returns:
        Path to the generated audio file.
    """
    provider = _get_provider()
    voice = provider.get_voice(role)
    return asyncio.run(provider.generate_audio(text, voice))


def get_voice_assignment() -> dict[str, str]:
    """Return the full role-to-voice mapping for the active provider."""
    return _get_provider().voice_assignment()


__all__ = [
    "speak",
    "generate_audio",
    "get_voice_assignment",
    "play_audio",
    "cleanup_audio",
    "TTSProvider",
    "get_provider",
]
```

- [ ] **Step 2: Commit**

```bash
git add voice/__init__.py
git commit -m "feat: rewrite voice/__init__.py with provider-based API"
```

---

### Task 5: Update voice/player.py

**Files:**
- Modify: `voice/player.py`

- [ ] **Step 1: Rewrite `voice/player.py`**

Remove the `speak()` function (it moves to `__init__.py`) and the direct `tts` import. Keep `play_audio` and `cleanup_audio` as-is.

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add voice/player.py
git commit -m "refactor: simplify player.py, remove speak() and tts import"
```

---

### Task 6: Delete old voice/tts.py and voice/voices.py

**Files:**
- Delete: `voice/tts.py`
- Delete: `voice/voices.py`

- [ ] **Step 1: Delete the old files**

```bash
git rm voice/tts.py voice/voices.py
```

- [ ] **Step 2: Commit**

```bash
git commit -m "refactor: remove old tts.py and voices.py (migrated to edge.py)"
```

---

### Task 7: Update consumers (debate.py, public_debate.py)

**Files:**
- Modify: `normal_critic_debate/debate.py`
- Modify: `public_debate/public_debate.py`

- [ ] **Step 1: Update `normal_critic_debate/debate.py`**

Replace:
```python
from voice.voices import VoiceAssignment
from voice.player import speak as voice_speak
```
With:
```python
from voice import speak
```

Replace all occurrences of `voice_speak(text, voice=voices.moderator)` → `speak(text, role="moderator")`
Replace all occurrences of `voice_speak(text, voice=voices.proposer)` → `speak(text, role="proposer")`
Replace all occurrences of `voice_speak(text, voice=voices.critic)` → `speak(text, role="critic")`
Replace all occurrences of `voice_speak(text, voice=voices.judge)` → `speak(text, role="judge")`

Remove the line `voices = VoiceAssignment()` — it's no longer needed; the provider manages voice assignment internally.

The `voice_enabled` check pattern changes from:
```python
if voice_enabled:
    voice_speak(text, voice=voices.moderator)
```
To:
```python
if voice_enabled:
    speak(text, role="moderator")
```

- [ ] **Step 2: Update `public_debate/public_debate.py`**

Same pattern as above. Replace:
```python
from voice.voices import VoiceAssignment
from voice.player import speak as voice_speak
```
With:
```python
from voice import speak
```

Replace all `voice_speak(text, voice=voices.X)` with `speak(text, role="X")`.
Remove `voices = VoiceAssignment()`.

Roles used in this file: `moderator`, `speaker_a`, `speaker_b`, `judge`.

- [ ] **Step 3: Commit**

```bash
git add normal_critic_debate/debate.py public_debate/public_debate.py
git commit -m "refactor: update consumers to use voice.speak(text, role=...)"
```

---

### Task 8: Add fish-audio-sdk dependency and update .env.example

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`

- [ ] **Step 1: Add `fish-audio-sdk` to `pyproject.toml` dependencies**

In `pyproject.toml`, add `"fish-audio-sdk>=1.0.0"` to the `dependencies` list, after the `edge-tts` line.

- [ ] **Step 2: Update `.env.example`**

Add a new `# Voice / TTS` section after the existing debate settings:

```env

# Voice / TTS
TTS_PROVIDER=edge

# Fish Audio settings (only needed when TTS_PROVIDER=fish)
FISH_API_KEY=
FISH_VOICE_MODERATOR=
FISH_VOICE_PROPOSER=
FISH_VOICE_CRITIC=
FISH_VOICE_SPEAKER_A=
FISH_VOICE_SPEAKER_B=
FISH_VOICE_JUDGE=
```

- [ ] **Step 3: Run `uv lock` to update the lockfile**

```bash
uv lock
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .env.example uv.lock
git commit -m "feat: add fish-audio-sdk dependency and TTS env config"
```

---

### Task 9: Smoke test with Edge-TTS (default provider)

- [ ] **Step 1: Verify the app runs with `TTS_PROVIDER=edge` (default)**

```bash
uv run python -c "from voice import speak, get_voice_assignment; print(get_voice_assignment())"
```

Expected: prints a dict like `{'moderator': 'en-US-EricNeural', 'proposer': 'en-US-JennyNeural', ...}`

- [ ] **Step 2: Verify imports in consumers**

```bash
uv run python -c "from normal_critic_debate.debate import run_debate; print('OK')"
uv run python -c "from public_debate.public_debate import run_debate; print('OK')"
```

Expected: both print `OK`

- [ ] **Step 3: Commit any fixes if needed**

---

### Task 10: Final cleanup and verification

- [ ] **Step 1: Run a full syntax check**

```bash
uv run python -m py_compile voice/provider.py
uv run python -m py_compile voice/edge.py
uv run python -m py_compile voice/fish.py
uv run python -m py_compile voice/__init__.py
uv run python -m py_compile voice/player.py
```

Expected: no output (all files compile cleanly)

- [ ] **Step 2: Verify no stale imports remain**

```bash
rg "from voice.tts import" --type py
rg "from voice.voices import" --type py
rg "from voice.player import speak" --type py
```

Expected: no results (all old imports replaced)

- [ ] **Step 3: Verify .env.example has TTS section**

```bash
grep "TTS_PROVIDER" .env.example
```

Expected: line present

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```