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