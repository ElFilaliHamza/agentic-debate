# Voice-Enabled Debate with AI Moderator — Design Spec

**Date:** 2026-06-23  
**Status:** Approved

## Overview

Add real-time voice playback to both debate formats (Proposer/Critic and Public Debate) using Edge-TTS. Introduce a new Moderator agent that acts as a TV debate host — introducing the motion, transitioning between speakers with commentary, and closing before the judge. Voice is always-on by default; `--no-voice` disables audio but keeps moderator text in the TUI.

## Decisions

| Aspect | Decision |
|--------|----------|
| TTS Engine | Edge-TTS (free, SSML support, high-quality neural voices) |
| Voice Assignment | Randomized from curated pools per role; no duplicates within a session |
| Playback Mode | Wait-then-speak: text streams via Rich TUI first, then voice reads the complete response |
| Default Behavior | Voice always-on; `--no-voice` flag silences audio |
| Moderator | New AI agent — TV debate host that introduces speakers, transitions with commentary, and closes before the judge |
| Architecture | Approach C — Full TV Debate Producer with SSML-enhanced moderator |

## Architecture & Module Structure

```
agent-harness/
├── voice/
│   ├── __init__.py
│   ├── tts.py              # Edge-TTS engine wrapper
│   ├── voices.py            # Role-to-voice mapping & randomization pools
│   └── player.py            # Audio playback (async play, queue management)
│
├── moderator/
│   ├── __init__.py
│   ├── moderator.py          # Moderator agent logic (opening, transition, closing)
│   └── moderator_prompt.py   # System prompt for the TV host
│
├── tui_formatter/
│   ├── formatter.py          # (modify) Add moderator display functions
│   └── roles.py              # (modify) Add MODERATOR role
│
├── public_debate/
│   └── public_debate.py      # (modify) Integrate moderator + voice
│
├── normal_critic_debate/
│   └── debate.py             # (modify) Integrate moderator + voice
│
└── pyproject.toml            # (modify) Add edge-tts, pygame dependencies
```

## Voice Engine — Edge-TTS Integration

### `voice/tts.py`

- Uses `edge_tts` Python package (async-native)
- Accepts text + voice name + optional SSML parameters (rate, pitch, volume)
- Returns a temp MP3 file path
- Handles long text by splitting on sentence boundaries (Edge-TTS has length limits)
- Async interface

### `voice/voices.py`

Curated voice pools per role:

```python
MODERATOR_VOICES = ["en-US-DavisNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"]
PROPOSER_VOICES = ["en-US-DavisNeural", "en-US-GuyNeural", "en-US-JennyNeural"]
CRITIC_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-SaraNeural"]
SPEAKER_A_VOICES = ["en-US-GuyNeural", "en-US-DavisNeural", "en-US-ChristopherNeural"]
SPEAKER_B_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-SaraNeural"]
JUDGE_VOICES = ["en-US-ChristopherNeural", "en-US-DavisNeural", "en-US-GuyNeural"]
```

- Randomly picks one voice from each pool at the start of each debate
- No duplicate voices across roles in the same session

### `voice/player.py`

- Uses `pygame` for MP3 playback (blocking, synchronous)
- Plays the generated audio file, then deletes the temp file
- Provides a `speak(text, voice, ssml_params)` convenience function: generate → play → cleanup

### Dependencies

- `edge-tts` — TTS generation
- `pygame` — Audio playback

## Moderator Agent

### `moderator/moderator_prompt.py`

System prompt instructs the agent to be a compelling TV debate host:

- **Be brief** — 2-3 sentences max per transition
- **Be engaging** — Build tension, reference what was just said, tease what's coming
- **Never argue** — Moderator doesn't take sides, only frames
- **Use SSML cues** — Prompt instructs the agent to use natural pauses and emphasis markers convertible to SSML
- **Three modes:**
  - `OPENING` — Introduce the motion and speakers
  - `TRANSITION` — Bridge between speakers, reflect on what was said
  - `CLOSING` — Hand off to the judge
- **Character limit:** ~200 chars per moderator segment to keep transitions snappy
- Uses the same anti-AI writing protocol from the existing system prompts

### `moderator/moderator.py`

```python
async def opening(motion: str, speaker_a_voice: str, speaker_b_voice: str) -> str
async def transition(transcript_so_far: list, next_speaker: str, round_num: int, total_rounds: int) -> str
async def closing(transcript: list) -> str
```

- Uses the same Ollama client and model as the debate
- Receives transcript context to reference what was actually said
- Returns the moderator's text, ready for TTS

### `tui_formatter/roles.py` — New role

```python
MODERATOR = Role(
    key="moderator",
    label="Moderator",
    icon="🎙️",
    style="moderator",
    text_style="moderator.text",
)
```

### `tui_formatter/console.py` — New theme colors

```python
"moderator": "bold yellow",
"moderator.text": "yellow",
```

## Debate Flow Integration

### Public Debate (modified flow)

```
1. User enters motion
2. [MODERATOR] Opening: "Tonight's motion — [motion]. Let's hear from Speaker A."
3. [VOICE] Moderator's opening plays aloud
4. Round loop:
   a. [MODERATOR] Transition: "A bold claim from Speaker A. Speaker B, your response?"
   b. [VOICE] Moderator transition plays
   c. Speaker A/B generates response (Rich streaming still works)
   d. [VOICE] Speaker's response plays aloud
5. [MODERATOR] Closing: "Both sides have made their case. Over to the judge."
6. [VOICE] Moderator closing plays
7. Judge delivers verdict
8. [VOICE] Judge's verdict plays aloud
```

### Proposer/Critic Debate (modified flow)

Same pattern — moderator opens (introducing "the Proposer" and "the Critic"), transitions between proposer/critic turns, and closes before the judge. The moderator uses the appropriate role labels for each format.

### `--no-voice` flag behavior

- All moderator text **still displays** in the Rich TUI (yellow/amber theme)
- All speaker text **still displays** as normal
- No audio generation or playback
- Moderator agent **still runs** — its commentary adds value even as text-only

### Async orchestration

The debate runs in an `asyncio` event loop. Sequential flow:

1. Moderator generates text (Ollama API call)
2. Display moderator text in Rich TUI
3. Send moderator text to Edge-TTS → get MP3
4. Play MP3 (blocking audio)
5. Next speaker generates text (Ollama API call, Rich streaming)
6. Send full speaker text to Edge-TTS → get MP3
7. Play MP3 (blocking audio)
8. Repeat

Each step is sequential — no overlapping audio. The audience hears one voice at a time, like a real broadcast.

## Error Handling

- **Edge-TTS fails** (network error): Log warning, skip audio, text still displays. Debate continues.
- **Audio playback fails** (no audio device): Log warning, skip audio, text still displays. Debate continues.
- **Moderator agent fails** (Ollama error): Log warning, skip moderator segment, debate continues without commentary.

Voice and moderator are enhancements, not blockers. The debate must always be able to run without them.