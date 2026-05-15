import httpx
from bs4 import BeautifulSoup

from .base import BaseTool, ToolResult


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract the main text content from a URL."

    async def run(self, url: str) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; AIAgent/1.0)"},
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # Limit output to avoid token explosion
            return ToolResult(success=True, output=text[:3000])
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def to_claude_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"}
                },
                "required": ["url"],
            },
        }
