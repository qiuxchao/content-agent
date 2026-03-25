import os
from tavily import TavilyClient

_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search(keyword: str, max_results: int = 5) -> list[dict]:
    """
    搜索关键词，返回结构化结果列表。
    每条结果包含 title、content、url 字段。
    """
    response = _client.search(keyword, max_results=max_results)
    return response.get("results", [])