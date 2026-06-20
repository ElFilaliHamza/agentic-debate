# Agent Harness Learning Project

Multi-mode AI debate agents using the Ollama API. Two debate formats are available — a proposer/critic debate for fact-checking claims, and a public debate between two speakers with a judge's verdict.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd agent-harness
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root with your Ollama configuration:
   ```env
   OLLAMA_API_URL=http://localhost:11434
   OLLAMA_API_KEY=your_api_key_here  # Optional if your Ollama instance doesn't require auth
   ```

## Usage

### Proposer/Critic Debate

Enter a factual claim and watch a Proposer and Critic argue it out, with a Judge delivering a final verdict:

```bash
uv run python -m normal_critic_debate.debate
```

### Public Debate

Two speakers debate a motion for/against across multiple rounds, then a Judge picks a winner:

```bash
uv run python -m public_debate.public_debate
```

Configurable via environment variables:
- `DEBATE_ROUNDS` — number of rounds (default: 3)
- `DEBATE_MAX_CHARS` — max response length per speaker (default: 300)
- `TYPING_DELAY` — delay between characters for streaming output (default: 0.02)