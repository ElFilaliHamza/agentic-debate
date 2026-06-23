import urllib.request
import urllib.error
import json
import random

from public_debate.tools.base import BaseTool


class QuoteTool(BaseTool):
    name = "quote"
    description = (
        "Retrieve a famous quote relevant to a topic "
        "to strengthen an argument or add rhetorical flair."
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
        # Try search endpoint first
        result = self._search_quotes(topic)

        if result:
            return result

        # Fallback to random quotes
        result = self._random_quotes(topic)
        if result:
            return result
        return f"No relevant quote found for topic: {topic}"

    def _search_quotes(self, query: str) -> str | None:
        url = f"https://api.quotable.io/search/quotes?query={urllib.request.quote(query)}&limit=5"

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                quotes = data.get("results", [])
                if not quotes:
                    return None
                q = random.choice(quotes)
                return f'"{q["content"]}" - {q["author"]}'
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            return None

    def _random_quotes(self, query: str) -> str | None:
        url = f"https://api.quotable.io/random?tags={urllib.request.quote(query)}"

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                return f'"{data["content"]}" - {data["author"]}'
        except (urllib.error.URLError, KeyError, json.JSONDecodeError):
            return None
