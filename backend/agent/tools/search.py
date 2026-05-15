from .base import BaseTool, ToolResult
from config import settings


class SearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information."

    async def run(self, query: str) -> ToolResult:
        if not settings.tavily_api_key:
            return ToolResult(success=False, error="TAVILY_API_KEY not set.")
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            response = client.search(query=query, max_results=5)
            results = "\n\n".join(
                f"**{r['title']}**\n{r['content']}\nSource: {r['url']}"
                for r in response.get("results", [])
            )
            return ToolResult(success=True, output=results or "No results found.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        }
