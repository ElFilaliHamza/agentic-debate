from public_debate.tools.base import BaseTool
from ollama import Client
import random

from tui_formatter.roles import SPEAKER_A, SPEAKER_B


class PollTool(BaseTool):
    name = "poll"
    description = (
        "Generate a simulated audience poll result showing what percentage "
        "of the audience agrees with a position on the debate topic."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The debate question or point to poll the audience on",
            }
        },
        "required": ["question"],
    }

    CHEEKY_COMMENTS = [
        "The audience murmurs in agreement.",
        "A few gasps from the back row.",
        "Heads nod around the room.",
        "Some skeptical looks in the crowd.",
        "The crowd shifts uneasily.",
        "A ripple of applause.",
        "A moment of silence.",
        "Eyebrows raised across the room.",
        "Murmurs of dissent ripple through.",
        "The audience leans forward in their seats.",
    ]

    POLL_SYSTEM_PROMPT = (
        "You are scoring which side of a debate is more convincing "
        "on a specific point. Given a question, respond with ONLY "
        "a number between 0-100 where 100 means Speaker A is "
        "completely convincing and 0 means Speaker B is completely "
        "convincing. Respond with just the number, nothing else."
    )

    def __init__(self, client: Client | None = None, model: str = "glm-5.1:cloud"):
        self._client = client
        self._model = model

    def execute(self, *, question: str) -> str:
        client = self._client or Client()
        try:
            response = client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": self.POLL_SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
            )
            score_text = (
                response.message.content.strip() if response.message.content else "50"
            )
            score = int("".join(c for c in score_text if c.isdigit()) or 50)

            score = max(0, min(100, score))
        except Exception:
            score = 50

        percentage = max(10, min(90, score + random.randint(-15, 15)))
        side = SPEAKER_A.label if percentage > 50 else SPEAKER_B.label

        comment = random.choice(self.CHEEKY_COMMENTS)

        return (
            f"{percentage}% of the audience agrees with {side} on this point. {comment}"
        )
