import urllib.request
import urllib.error
import json
import random

from public_debate.tools.base import BaseTool


class QuoteTool(BaseTool):
    name = "quote"
    description = (
        "Drop a famous quote to add rhetorical weight and authority to your argument. "
        "Returns a relevant quote you can cite by name to make your point memorable."
    )
    parameters = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic or theme to find a relevant quote about",
            }
        },
        "required": ["topic"],
    }

    def execute(self, *, topic: str) -> str:
        # Try keyword search first
        result = self._search_quotes(topic)
        if result:
            return result

        # Fallback to a random quote
        result = self._random_quote()
        if result:
            return result

        return f"No relevant quote found for topic: {topic}"

    def _search_quotes(self, query: str) -> str | None:
        url = f"https://zenquotes.io/api/quotes/keyword={urllib.request.quote(query)}"

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                if not data:
                    return None
                q = random.choice(data)
                return f'"{q["q"]}" - {q["a"]}'
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            return None

    def _random_quote(self) -> str | None:
        url = "https://zenquotes.io/api/random"

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                if not data:
                    return None
                q = data[0]
                return f'"{q["q"]}" - {q["a"]}'
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            return None
