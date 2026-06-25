# Sentiment & Joke Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Mood Reflector (sentiment analysis) and Joke Breaker (dad joke fetcher) tools to the debate agent system, following the existing BaseTool pattern.

**Architecture:** Two new `BaseTool` subclasses — `SentimentTool` using a local GoEmotions transformer model, and `JokeTool` using the icanhazdadjoke API. Both register in `ToolRegistry`, get icons in the TUI, and participate in random speaker assignment. No changes to debate logic or system prompts.

**Tech Stack:** Python 3.13, transformers (HuggingFace), torch (CPU), urllib (stdlib), existing BaseTool/ToolRegistry pattern.

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `public_debate/tools/sentiment.py` | SentimentTool class with GoEmotions model |
| Create | `public_debate/tools/joke.py` | JokeTool class with icanhazdadjoke API |
| Create | `tests/test_sentiment.py` | Tests for SentimentTool |
| Create | `tests/test_joke.py` | Tests for JokeTool |
| Modify | `public_debate/tools/__init__.py` | Export SentimentTool and JokeTool |
| Modify | `public_debate/tools/registry.py` | Register both new tools in `_register_defaults` |
| Modify | `tui_formatter/roles.py` | Add icons for `sentiment` and `joke` |
| Modify | `pyproject.toml` | Add `transformers` and `torch` dependencies |

---

### Task 1: JokeTool

**Files:**
- Create: `public_debate/tools/joke.py`
- Create: `tests/test_joke.py`

- [ ] **Step 1: Write the failing test for JokeTool**

Create `tests/test_joke.py`:

```python
import json
import urllib.request
from unittest.mock import patch, MagicMock
from public_debate.tools.joke import JokeTool


def test_joke_name():
    tool = JokeTool()
    assert tool.name == "joke"


def test_joke_description():
    tool = JokeTool()
    assert "joke" in tool.description.lower()


def test_joke_parameters_schema():
    tool = JokeTool()
    params = tool.parameters
    assert params["type"] == "object"
    assert "topic" in params["properties"]
    assert params["required"] == ["topic"]


def test_joke_execute_with_results():
    tool = JokeTool()
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "results": [
            {"joke": "Why do mathematicians hate the outdoors? Too many natural logs."}
        ]
    }).encode()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("public_debate.tools.joke.urllib.request.urlopen", return_value=mock_response):
        result = tool.execute(topic="math")
    assert "natural logs" in result


def test_joke_execute_no_results_falls_back_to_random():
    tool = JokeTool()
    call_count = 0

    def mock_urlopen(url, timeout=0):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if "search" in url:
            # No results for search
            mock_resp.read.return_value = json.dumps({"results": []}).encode()
        else:
            # Random joke fallback
            mock_resp.read.return_value = json.dumps([
                {"joke": "I told my opponent a chemistry joke. No reaction."}
            ]).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with patch("public_debate.tools.joke.urllib.request.urlopen", side_effect=mock_urlopen):
        result = tool.execute(topic="xyzzy_nonexistent_topic")
    assert call_count == 2  # search then random
    assert "chemistry" in result


def test_joke_execute_network_error_returns_fallback():
    tool = JokeTool()
    with patch("public_debate.tools.joke.urllib.request.urlopen", side_effect=Exception("Network error")):
        result = tool.execute(topic="anything")
    # Should return one of the hardcoded fallback jokes
    assert len(result) > 0
    assert isinstance(result, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_joke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'public_debate.tools.joke'`

- [ ] **Step 3: Write JokeTool implementation**

Create `public_debate/tools/joke.py`:

```python
import json
import random
import urllib.request
import urllib.error

from public_debate.tools.base import BaseTool


class JokeTool(BaseTool):
    name = "joke"
    description = (
        "Fetch a dad joke related to a topic to break tension or lighten the mood "
        "during a heated debate. The other speaker must acknowledge the joke before continuing."
    )
    parameters = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The debate topic or theme to find a related dad joke about",
            }
        },
        "required": ["topic"],
    }

    FALLBACK_JOKES = [
        "I told my opponent a chemistry joke. No reaction.",
        "Why don't debaters ever win at cards? Too many arguments.",
        "I used to hate facial hair, but then it grew on me.",
        "Parallel lines have so much in common. It's a shame they'll never meet.",
        "I'm reading a book on anti-gravity. I can't put it down.",
    ]

    def execute(self, *, topic: str) -> str:
        result = self._search_joke(topic)
        if result:
            return result

        result = self._random_joke()
        if result:
            return result

        return random.choice(self.FALLBACK_JOKES)

    def _search_joke(self, topic: str) -> str | None:
        url = f"https://icanhazdadjoke.com/search?term={urllib.request.quote(topic)}"
        headers = {"Accept": "application/json"}

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                results = data.get("results", [])
                if not results:
                    return None
                joke = random.choice(results)
                return joke["joke"]
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, OSError):
            return None

    def _random_joke(self) -> str | None:
        url = "https://icanhazdadjoke.com/"
        headers = {"Accept": "application/json"}

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                joke = data.get("joke")
                if joke:
                    return joke
                return None
        except (urllib.error.URLError, KeyError, json.JSONDecodeError, OSError):
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_joke.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add public_debate/tools/joke.py tests/test_joke.py
git commit -m "feat: add JokeTool with icanhazdadjoke API"
```

---

### Task 2: SentimentTool

**Files:**
- Create: `public_debate/tools/sentiment.py`
- Create: `tests/test_sentiment.py`

- [ ] **Step 1: Add transformers and torch dependencies**

Run: `uv add transformers torch`

This updates `pyproject.toml` and `uv.lock`. The model (`SamLowe/roberta-base-go_emotions`) downloads automatically on first pipeline creation via HuggingFace Hub.

- [ ] **Step 2: Write the failing test for SentimentTool**

Create `tests/test_sentiment.py`:

```python
from unittest.mock import patch, MagicMock
from public_debate.tools.sentiment import SentimentTool, EMOTION_MAPPING


def test_sentiment_name():
    tool = SentimentTool()
    assert tool.name == "sentiment"


def test_sentiment_description():
    tool = SentimentTool()
    assert "emotional tone" in tool.description.lower()


def test_sentiment_parameters_schema():
    tool = SentimentTool()
    params = tool.parameters
    assert params["type"] == "object"
    assert "text" in params["properties"]
    assert params["required"] == ["text"]


def test_emotion_mapping_covers_key_categories():
    """Verify the mapping includes the main debate-relevant labels."""
    assert "angry" in EMOTION_MAPPING
    assert "confident" in EMOTION_MAPPING
    assert "defensive" in EMOTION_MAPPING
    assert "desperate" in EMOTION_MAPPING


def test_sentiment_execute_with_pipeline():
    tool = SentimentTool()
    # Mock the pipeline to return a known emotion
    mock_pipeline_result = [[
        {"label": "optimism", "score": 0.72},
        {"label": "neutral", "score": 0.15},
        {"label": "fear", "score": 0.08},
    ]]

    mock_pipeline = MagicMock(return_value=mock_pipeline_result)
    tool._pipeline = mock_pipeline

    result = tool.execute(text="I'm absolutely certain we're right about this!")
    assert "confident" in result.lower() or "optimism" in result.lower()
    assert "72" in result  # confidence percentage
    mock_pipeline.assert_called_once()


def test_sentiment_execute_pipeline_failure_falls_back():
    tool = SentimentTool()

    # Make pipeline creation raise an exception
    with patch(
        "public_debate.tools.sentiment.pipeline",
        side_effect=OSError("Model not found"),
    ):
        result = tool.execute(text="I am absolutely certain this is terrible and wrong!")

    # Should fall back to keyword heuristic — "absolutely" and "terrible" should trigger something
    assert isinstance(result, str)
    assert len(result) > 0


def test_sentiment_fallback_heuristic_confident():
    tool = SentimentTool()
    with patch(
        "public_debate.tools.sentiment.pipeline",
        side_effect=OSError("No model"),
    ):
        result = tool.execute(text="This is clearly and absolutely the right path forward.")
    assert "confident" in result.lower()


def test_sentiment_fallback_heuristic_defensive():
    tool = SentimentTool()
    with patch(
        "public_debate.tools.sentiment.pipeline",
        side_effect=OSError("No model"),
    ):
        result = tool.execute(text="Maybe perhaps it could possibly be considered.")
    assert "defensive" in result.lower()


def test_sentiment_fallback_heuristic_angry():
    tool = SentimentTool()
    with patch(
        "public_debate.tools.sentiment.pipeline",
        side_effect=OSError("No model"),
    ):
        result = tool.execute(text="I hate this furious attack, it's awful and terrible!")
    assert "angry" in result.lower()


def test_sentiment_pipeline_lazy_loaded():
    """Pipeline should not exist until first execute call."""
    tool = SentimentTool()
    assert tool._pipeline is None


def test_sentiment_pipeline_cached_after_first_load():
    """Pipeline should be reused after first creation."""
    tool = SentimentTool()
    mock_pipeline_result = [[
        {"label": "neutral", "score": 0.9},
    ]]
    mock_pipeline = MagicMock(return_value=mock_pipeline_result)

    with patch("public_debate.tools.sentiment.pipeline", mock_pipeline):
        tool.execute(text="test one")
        tool.execute(text="test two")

    # Pipeline created once, called twice
    assert mock_pipeline.call_count == 1  # created once
    assert tool._pipeline.call_count == 2  # called twice
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_sentiment.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'public_debate.tools.sentiment'`

- [ ] **Step 4: Write SentimentTool implementation**

Create `public_debate/tools/sentiment.py`:

```python
from __future__ import annotations

import random
from typing import Any

from public_debate.tools.base import BaseTool

EMOTION_MAPPING: dict[str, str] = {
    # GoEmotions raw label -> debate-relevant label
    "anger": "angry",
    "annoyance": "angry",
    "optimism": "confident",
    "pride": "confident",
    "admiration": "confident",
    "nervousness": "defensive",
    "fear": "defensive",
    "embarrassment": "defensive",
    "grief": "desperate",
    "sadness": "desperate",
    "remorse": "desperate",
    "disapproval": "dismissive",
    "disgust": "dismissive",
    "excitement": "excited",
    "joy": "excited",
    "amusement": "excited",
    "neutral": "neutral",
    "approval": "neutral",
    "realization": "neutral",
}

CONTEXT_COMMENTS: dict[str, list[str]] = {
    "angry": [
        "Emotions are running high.",
        "They're clearly fired up about this.",
        "There's real heat behind those words.",
    ],
    "confident": [
        "They seem assured of their position.",
        "Strong conviction in their tone.",
        "They're speaking with real authority here.",
    ],
    "defensive": [
        "They may be on shaky ground.",
        "There's some uncertainty creeping in.",
        "Sounds like they're hedging their bets.",
    ],
    "desperate": [
        "They're grasping at straws.",
        "The argument feels like a last stand.",
        "There's a sense of resignation here.",
    ],
    "dismissive": [
        "They're not buying the other side at all.",
        "Clear rejection of the opposing view.",
        "They're brushing off the argument.",
    ],
    "excited": [
        "They're energized about this point.",
        "Real enthusiasm coming through.",
        "They're clearly passionate about this.",
    ],
    "neutral": [
        "Measured and even tone.",
        "Playing it close to the vest.",
        "Keeping things level-headed.",
    ],
}

# Fallback keyword heuristic for when the model fails to load
KEYWORD_LABELS: dict[str, list[str]] = {
    "confident": [
        "absolutely", "clearly", "obviously", "certainly", "definitely",
        "undoubtedly", "undeniably", "proven", "obvious", "sure",
    ],
    "defensive": [
        "maybe", "perhaps", "possibly", "might", "could be",
        "seems like", "arguably", "somewhat", "partially", "i suppose",
    ],
    "angry": [
        "hate", "angry", "furious", "terrible", "awful", "disgusting",
        "outrageous", "unacceptable", "ridiculous", "stupid",
    ],
    "desperate": [
        "please", "beg", "desperate", "last chance", "no choice",
        "nothing left", "help", "hopeless",
    ],
    "excited": [
        "amazing", "incredible", "wonderful", "exciting", "fantastic",
        "thrilling", "breakthrough", "game-changer",
    ],
}


class SentimentTool(BaseTool):
    name = "sentiment"
    description = (
        "Analyze the emotional tone of the opponent's statement. "
        "Returns a sentiment label (e.g., angry, confident, defensive, desperate) "
        "with a confidence score. Use this to read the room and adapt your rhetorical strategy."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The opponent's statement to analyze for emotional tone",
            }
        },
        "required": ["text"],
    }

    def __init__(self) -> None:
        self._pipeline: Any = None

    def _load_pipeline(self) -> Any:
        """Lazy-load the transformers pipeline on first use."""
        from transformers import pipeline

        self._pipeline = pipeline(
            "text-classification",
            model="SamLowe/roberta-base-go_emotions",
            top_k=3,
        )
        return self._pipeline

    def _fallback_heuristic(self, text: str) -> str:
        """Keyword-based fallback when the model fails to load."""
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for label, keywords in KEYWORD_LABELS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[label] = count

        if scores:
            best_label = max(scores, key=lambda k: scores[k])
            comment = random.choice(CONTEXT_COMMENTS.get(best_label, ["Tone detected."]))
            return f"The tone appears {best_label} (heuristic, {scores[best_label]} keyword(s) matched). {comment}"

        return "The tone appears neutral (heuristic, no strong emotional signals detected). Keeping it level-headed."

    def execute(self, *, text: str) -> str:
        try:
            if self._pipeline is None:
                self._load_pipeline()
            results = self._pipeline(text)
        except Exception:
            return self._fallback_heuristic(text)

        # results is a list of lists: [[{label, score}, ...]]
        # If the pipeline returns a flat list, handle both cases
        if results and isinstance(results[0], list):
            top_emotions = results[0]
        elif results and isinstance(results[0], dict):
            top_emotions = results
        else:
            return self._fallback_heuristic(text)

        if not top_emotions:
            return self._fallback_heuristic(text)

        top = top_emotions[0]
        raw_label = top["label"]
        score = top["score"]
        debate_label = EMOTION_MAPPING.get(raw_label, raw_label.lower())
        confidence_pct = int(score * 100)
        comment = random.choice(CONTEXT_COMMENTS.get(debate_label, ["Tone detected."]))

        return f"The tone appears {debate_label} ({raw_label}, {confidence_pct}% confidence). {comment}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_sentiment.py -v`
Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add public_debate/tools/sentiment.py tests/test_sentiment.py pyproject.toml uv.lock
git commit -m "feat: add SentimentTool with GoEmotions transformer model"
```

---

### Task 3: Integration — Wire up both tools

**Files:**
- Modify: `public_debate/tools/__init__.py`
- Modify: `public_debate/tools/registry.py`
- Modify: `tui_formatter/roles.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_tool_integration.py`:

```python
from public_debate.tools import SentimentTool, JokeTool
from public_debate.tools.registry import ToolRegistry


def test_registry_has_sentiment_tool():
    registry = ToolRegistry()
    assert "sentiment" in registry._tools


def test_registry_has_joke_tool():
    registry = ToolRegistry()
    assert "joke" in registry._tools


def test_registry_has_six_tools_total():
    registry = ToolRegistry()
    assert len(registry.get_all()) == 6


def test_sentiment_tool_schema_in_registry():
    registry = ToolRegistry()
    tool = registry.get("sentiment")
    schemas = registry.get_schemas([tool])
    assert schemas[0]["function"]["name"] == "sentiment"
    assert "text" in schemas[0]["function"]["parameters"]["properties"]


def test_joke_tool_schema_in_registry():
    registry = ToolRegistry()
    tool = registry.get("joke")
    schemas = registry.get_schemas([tool])
    assert schemas[0]["function"]["name"] == "joke"
    assert "topic" in schemas[0]["function"]["parameters"]["properties"]


def test_assign_random_includes_new_tools():
    registry = ToolRegistry()
    tools_a, tools_b = registry.assign_random()
    all_names = {t.name for t in tools_a} | {t.name for t in tools_b}
    assert "sentiment" in all_names
    assert "joke" in all_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tool_integration.py -v`
Expected: FAIL — `SentimentTool` and `JokeTool` not in registry

- [ ] **Step 3: Update `__init__.py`**

Modify `public_debate/tools/__init__.py` to:

```python
from public_debate.tools.base import BaseTool
from public_debate.tools.search import SearchTool
from public_debate.tools.fallacy import FallacyDetectorTool
from public_debate.tools.quote import QuoteTool
from public_debate.tools.poll import PollTool
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

- [ ] **Step 4: Update `registry.py`**

Modify `public_debate/tools/registry.py` imports and `_register_defaults`:

```python
from public_debate.tools import (
    BaseTool,
    SearchTool,
    FallacyDetectorTool,
    QuoteTool,
    PollTool,
    SentimentTool,
    JokeTool,
)
import random


class ToolRegistry:
    """Registry of available debate tools. Handles assignment and schema generation."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for tool_cls in [SearchTool, FallacyDetectorTool, QuoteTool, PollTool, SentimentTool, JokeTool]:
            instance = tool_cls()
            self._tools[instance.name] = instance

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools[name]

    def get_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self, tools: list[BaseTool]) -> list[dict]:
        """Return Ollama-format tool schemas for a subset of tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def assign_random(self) -> tuple[list[BaseTool], list[BaseTool]]:
        """Randomly split all tools into two groups for Speaker A and B."""
        all_tools = self.get_all()
        shuffled = random.sample(all_tools, len(all_tools))
        mid = len(shuffled) // 2
        return shuffled[:mid], shuffled[mid:]

    def judge_tools(self) -> list[BaseTool]:
        """Return the tools available to the judge (search only)."""
        return [self._tools["search"]]
```

- [ ] **Step 5: Update `tui_formatter/roles.py` TOOL_ICONS**

Add sentiment and joke icons to `TOOL_ICONS` dict in `tui_formatter/roles.py`:

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

- [ ] **Step 6: Run integration tests**

Run: `uv run pytest tests/test_tool_integration.py -v`
Expected: All 6 tests PASS

- [ ] **Step 7: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (including joke, sentiment, and integration tests)

- [ ] **Step 8: Commit**

```bash
git add public_debate/tools/__init__.py public_debate/tools/registry.py tui_formatter/roles.py tests/test_tool_integration.py
git commit -m "feat: integrate SentimentTool and JokeTool into registry and TUI"
```

---

### Task 4: Smoke test — verify end-to-end

- [ ] **Step 1: Verify imports work**

Run: `uv run python -c "from public_debate.tools import SentimentTool, JokeTool; from public_debate.tools.registry import ToolRegistry; r = ToolRegistry(); print([t.name for t in r.get_all()])"`
Expected: Output includes `['search', 'detect_fallacy', 'quote', 'poll', 'sentiment', 'joke']` (order may vary)

- [ ] **Step 2: Verify JokeTool works with live API (optional, requires internet)**

Run: `uv run python -c "from public_debate.tools import JokeTool; j = JokeTool(); print(j.execute(topic='debate'))"`
Expected: A dad joke string printed

- [ ] **Step 3: Verify SentimentTool schema works (model download on first use)**

Run: `uv run python -c "from public_debate.tools import SentimentTool; s = SentimentTool(); print(s.name, s.description[:50])"`
Expected: `sentiment Analyze the emotional tone of the oppo`

Note: Full model inference test requires downloading ~130MB on first run. This is expected and can be verified manually when desired.

- [ ] **Step 4: Final full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS