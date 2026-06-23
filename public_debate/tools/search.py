from public_debate.tools.base import BaseTool
from ddgs import DDGS


class SearchTool(BaseTool):
    name = "search"
    description = (
        "Search DuckDuckGo for factual claims. "
        "Returns a 2-3 sentence summary to back up or refute an argument."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to fact-check a claim",
            }
        },
        "required": ["query"],
    }

    def execute(self, *, query: str) -> str:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return f"No results found for: {query}"
        summaries = []
        for r in results[:3]:
            if r.get("body"):
                summaries.append(r["body"])
        if not summaries:
            return f"No summary available for: {query}"
        combined = " ".join(summaries)
        # Truncate to roughly 2-3 sentences
        sentences = combined.split(". ")
        return ". ".join(sentences[:3]) + ("." if len(sentences) > 3 else "")
