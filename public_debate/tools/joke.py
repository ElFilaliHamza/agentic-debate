import json
import random
import urllib.request
import urllib.error

from public_debate.tools.base import BaseTool


class JokeTool(BaseTool):
    name = "joke"
    description = (
        "Break your opponent's momentum with a well-timed joke. "
        "Lightens the mood, wins the audience, and forces the other speaker to acknowledge it before continuing."
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