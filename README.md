<div align="center">

# ⚔️ Debate Harness

**Tool-Augmented Multi-Agent Debate**

*LLM agents that argue, call tools, and sound human — not like Wikipedia.*

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/ollama-required-purple.svg)](https://ollama.ai)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Features](#key-features) · [Quick Start](#installation)

</div>

---

A multi-agent debate framework where LLM agents argue, call tools, and deliver verdicts — with voice playback, a TV-style host, and a humanizer protocol that makes every argument sound like a real person at a podium, not a bot reading bullet points.

## Why This Is Different

Most AI text reads like Wikipedia — flat, hedged, bullet-pointed. ToolMAD agents follow a 6-phase **Humanizer Protocol** (based on Wikipedia's Signs of AI Writing research) that forces every response through an anti-AI audit before it reaches the audience. The result: arguments that sound human — varied sentence length, actual opinions, rhetorical questions, no "additionally" or "crucially" in sight.

But sounding human isn't enough. Each speaker gets **randomly assigned tools** — search, fallacy detection, sentiment analysis, audience polls, quotes, even jokes — that create asymmetric capabilities and emergent strategy. You can't script this. Every session is unique because every agent has different weapons.

## Debate Modes

### Public Debate

Two speakers debate a motion across multiple rounds, each armed with random tools, a TV host transitions between them, and a judge delivers the final verdict.

```bash
uv run python -m public_debate.public_debate
```

### Proposer/Critic Debate

Enter a factual claim and watch a Proposer and Critic argue it out, with a Judge delivering a final verdict.

```bash
uv run python -m normal_critic_debate.debate
```

### Configuration

- `DEBATE_ROUNDS` — number of rounds (default: 3)
- `DEBATE_MAX_CHARS` — max response length per speaker (default: 300)
- `TYPING_DELAY` — delay between characters for streaming output (default: 0.02)

## Key Features

### Tool-Augmented Agents

Each speaker gets a random subset of tools each session:
- **Search** — find hard evidence to back claims
- **Fallacy Detection** — expose logical fallacies in the opponent's argument
- **Sentiment Analysis** — read the opponent's emotional tone and exploit weaknesses
- **Audience Polls** — claim popular backing with simulated poll numbers
- **Quotes** — drop authoritative quotes for rhetorical weight
- **Jokes** — break the opponent's momentum

No two debates have the same tool configuration.

### The Humanizer Protocol

Every agent response goes through a 6-phase pipeline.

Based on Wikipedia's [Signs of AI Writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) maintained by WikiProject AI Cleanup.

### TV-Style Host

A host agent introduces the debate, transitions between speakers with reactive commentary on what just landed, and closes before the judge — like watching a real broadcast.

### Voice Playback

Each role gets a distinct neural voice (Edge-TTS or Fish Audio). The host, speakers, and judge all speak aloud. Debates feel like watching a live broadcast.

### Judge with Tools

The judge doesn't just opine — they can search for evidence before delivering the verdict.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/debate-harness.git
   cd debate-harness
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root with your Ollama configuration:
   ```env
   OLLAMA_API_URL=http://localhost:11434
   OLLAMA_API_KEY=your_api_key_here  # Optional
   ```

4. For voice playback (optional):
   - Internet connection (Edge-TTS voices are cloud-synthesized)
   - Audio output device

### Disabling Voice

```bash
# Public debate without voice
uv run python -m public_debate.public_debate --no-voice

# Proposer/Critic debate without voice
uv run python -m normal_critic_debate.debate --no-voice
```

The host's text commentary still appears in the terminal with `--no-voice`.

### Voice Assignment

Each debate session randomly assigns distinct voices to each role (Proposer, Critic, Speaker A, Speaker B, Judge, Host) from curated voice pools. No two roles share the same voice in a session.
