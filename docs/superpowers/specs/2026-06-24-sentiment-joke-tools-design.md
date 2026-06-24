# Mood Reflector & Joke Breaker Tools — Design Spec

**Date:** 2026-06-24  
**Status:** Approved  
**Approach:** Minimal — Direct Implementation (Approach 1)

---

## Overview

Add two new tools to the public debate agent system:

1. **SentimentTool** (`sentiment`) — Analyzes the emotional tone of the opponent's last statement using a tiny transformer model, returning a debate-relevant emotion label.
2. **JokeTool** (`joke`) — Fetches a dad joke related to the debate topic via the `icanhazdadjoke` API, providing a de-escalation tool for heated moments.

Both follow the existing `BaseTool` pattern and are randomly assigned to speakers via `ToolRegistry`, identical to the current 4 tools.

---

## SentimentTool

### File

`public_debate/tools/sentiment.py`

### Class

`SentimentTool(BaseTool)`

### Tool Schema (exposed to LLM)

- **name:** `"sentiment"`
- **description:** `"Analyze the emotional tone of the opponent's statement. Returns a sentiment label (e.g., angry, confident, defensive, desperate) with a confidence score. Use this to read the room and adapt your rhetorical strategy."`
- **parameters:**
  ```json
  {
    "type": "object",
    "properties": {
      "text": {
        "type": "string",
        "description": "The opponent's statement to analyze for emotional tone"
      }
    },
    "required": ["text"]
  }
  ```

### Model

`SamLowe/roberta-base-go_emotions` — a RoBERTa-based model fine-tuned on the GoEmotions dataset, outputting 28 emotion categories. ~130MB download on first use via HuggingFace Hub.

### Emotion Mapping

The 28 GoEmotions raw categories are grouped into debate-relevant labels:

| Debate Label | GoEmotions Categories |
|---|---|
| angry | anger, annoyance |
| confident | optimism, pride, admiration |
| defensive | nervousness, fear, embarrassment |
| desperate | grief, sadness, remorse |
| dismissive | disapproval, disgust |
| excited | excitement, joy, amusement |
| neutral | neutral, approval, realization |

Any raw category not present in this mapping is passed through as-is (lowercased).

### Lazy Model Loading

The `transformers` pipeline is created on the first `execute()` call and cached as an instance variable (`self._pipeline`). This avoids slow startup when the tool is not assigned to a speaker.

### Execute Flow

1. Load the `transformers` pipeline if not already initialized.
2. Run the pipeline on input text with `top_k=3` to get the top 3 emotion predictions.
3. Take the top prediction and map its raw label to a debate-relevant label via the mapping table.
4. Return a formatted string: `"The tone appears {debate_label} ({raw_label}, {score}% confidence). {contextual_comment}"`

Example outputs:
- `"The tone appears confident (optimism, 72% confidence). They seem assured of their position."`
- `"The tone appears defensive (nervousness, 58% confidence). They may be on shaky ground."`
- `"The tone appears angry (anger, 81% confidence). Emotions are running high."`

### Error Handling

If the model fails to load or inference throws an error, fall back to a simple rule-based heuristic that does keyword matching on the input text (e.g., words like "absolutely", "clearly" → confident; "maybe", "perhaps" → defensive). This ensures the debate never crashes due to a model issue.

The fallback heuristic uses a dictionary of keyword-to-label mappings covering the same debate labels.

---

## JokeTool

### File

`public_debate/tools/joke.py`

### Class

`JokeTool(BaseTool)`

### Tool Schema (exposed to LLM)

- **name:** `"joke"`
- **description:** `"Fetch a dad joke related to a topic to break tension or lighten the mood during a heated debate. The other speaker must acknowledge the joke before continuing."`
- **parameters:**
  ```json
  {
    "type": "object",
    "properties": {
      "topic": {
        "type": "string",
        "description": "The debate topic or theme to find a related dad joke about"
      }
    },
    "required": ["topic"]
  }
  ```

### API

- **Primary:** `https://icanhazdadjoke.com/search?term={topic}` — returns a JSON array of matching jokes.
- **Fallback:** `https://icanhazdadjoke.com/` — returns a single random joke.

Both endpoints use `Accept: application/json` header and a 5-second timeout, matching the `QuoteTool` pattern with `urllib.request`.

### Execute Flow

1. URL-encode the topic parameter.
2. Call the search endpoint.
3. Parse the JSON response; if results exist, pick one at random.
4. If no results for the topic, call the random joke endpoint.
5. Return the joke string.

### Error Handling

On any failure (network error, timeout, JSON parse error, empty response), return one of 3-5 hardcoded fallback jokes, chosen randomly. These are debate-themed dad jokes:

- "I told my opponent a chemistry joke. No reaction."
- "Why don't debaters ever win at cards? Too many arguments."
- "I used to hate facial hair, but then it grew on me."
- "Parallel lines have so much in common. It's a shame they'll never meet."
- "I'm reading a book on anti-gravity. I can't put it down."

### Dependencies

None beyond `urllib` (stdlib) and `json` (stdlib). Same approach as `QuoteTool`.

---

## Integration Points

### `public_debate/tools/__init__.py`

Add imports and exports:
```python
from public_debate.tools.sentiment import SentimentTool
from public_debate.tools.joke import JokeTool

__all__ = [
    "BaseTool",
    "SearchTool",
    "FallacyDetectorTool",
    "QuoteTool",
    "PollTool",
    "SentimentTool",
    "JokeTool",
]
```

### `public_debate/tools/registry.py`

Add both tools to `_register_defaults()`:
```python
for tool_cls in [SearchTool, FallacyDetectorTool, QuoteTool, PollTool, SentimentTool, JokeTool]:
    instance = tool_cls()
    self._tools[instance.name] = instance
```

### `tui_formatter/roles.py`

Add icons to `TOOL_ICONS`:
```python
TOOL_ICONS: dict[str, str] = {
    "search": "🔍",
    "detect_fallacy": "🎯",
    "quote": "📜",
    "poll": "📊",
    "sentiment": "🎭",
    "joke": "😄",
}
```

### `pyproject.toml`

Add dependencies:
```toml
dependencies = [
    # ... existing ...
    "transformers>=4.40.0",
    "torch>=2.0.0",
]
```

Note: `torch` is a large dependency. If disk space is a concern, consider `torch` CPU-only wheels. The model (`SamLowe/roberta-base-go_emotions`) downloads automatically on first pipeline creation via HuggingFace Hub.

---

## What This Does NOT Include

- **Caching of sentiment results** — Each call runs fresh inference. Can be added later.
- **Offline joke fallback beyond hardcoded jokes** — No bundled joke collection. Can be added later.
- **Emotion-based retort suggestions** — The speaker LLM already adapts its rhetoric based on tool output. No need to duplicate.
- **Sentiment history tracking** — Each call is stateless. Can be added later if desired.