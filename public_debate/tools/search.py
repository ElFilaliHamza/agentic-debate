from public_debate.tools.base import BaseTool
from ddgs import DDGS


class SearchTool(BaseTool):
    name = "search"
    description = (
        "Find hard evidence to back your claims. Use this before making any factual assertion — "
        "returning real search results you can cite and argue from."
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
