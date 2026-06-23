from public_debate.tools.base import BaseTool
from ollama import Client


class FallacyDetectorTool(BaseTool):
    name = "detect_fallacy"
    description = (
        "Analyze the opponent's text for logical fallacies "
        "(straw man, ad hominem, false dilemma, etc.). "
        "Returns the fallacy name and a one-line explanation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The opponent's argument to analyze for logical fallacies",
            }
        },
        "required": ["text"],
    }

    FALLACY_SYSTEM_PROMPT = (
        "You are a debate fallacy detector. "
        "Given text, identify any logical fallacies. "
        "Respond in this exact format: "
        "FALLACY_NAME - one line explanation. "
        "If no fallacy is found, respond: "
        "NO_FALLACY - the argument appears logically sound. "
        "Be specific. Possible fallacies include: "
        "ad hominem, straw man, false dilemma, "
        "slippery slope, appeal to authority, "
        "circular reasoning, hasty generalization, "
        "red herring, tu quoque, appeal to emotion, "
        "bandwagon, post hoc, non sequitur."
    )

    def __init__(self, client: Client | None = None, model: str = "glm-5.1:cloud"):
        self._client = client
        self._model = model

    def execute(self, *, text: str) -> str:
        client = self._client or Client()
        response = client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": self.FALLACY_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return (
            response.message.content
            if response.message
            else "NO_FALLACY - the argument appears logically sound."
        )
