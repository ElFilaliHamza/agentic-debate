# Agent Harness Learning Project

A simple implementation of an AI agent harness using the Ollama API and function calling capabilities. This project demonstrates how to create an agent that can use external tools (like a calculator) to answer user queries.

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
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_API_KEY=your_api_key_here  # Optional if your Ollama instance doesn't require auth
   ```

## Usage

Run the agent from the command line:

```bash
uv run main.py
```

You'll be prompted to enter a question. For example:
- "What is the square root of 144?"
- "Calculate 25 * 4 + 10"
- "What is (15 + 5) * 3?"

The agent will use its calculator tool when needed to compute mathematical expressions.