"""Web Search 工具 - 多后端，国内默认 Bing（免费），配置 TAVILY_API_KEY 后用 Tavily（更稳）"""
from crewai.tools import tool

from config import SEARCH_MAX_RESULTS, TAVILY_API_KEY


@tool("Web Search")
def web_search(query: str) -> str:
    """搜索互联网获取最新信息。输入搜索关键词（中英文皆可），返回多条相关网页摘要。
    用于查找最新事实、数据、新闻、行业报告。每次调用搜索一个关键词。"""
    # 优先级：Tavily（配了 key）→ Bing（国内默认）→ DuckDuckGo（兜底）
    if TAVILY_API_KEY:
        result = _tavily_search(query)
        if "失败" not in result and "未找到" not in result:
            return result

    # 国内默认用 Bing（DuckDuckGo 被墙）
    result = _bing_search(query)
    if "失败" not in result and "未找到" not in result:
        return result

    # Bing 失败兜底试 DuckDuckGo
    return _ddg_search(query)


def _bing_search(query: str) -> str:
    """Bing 中国搜索（免费，无需 key，国内可用）"""
    import requests
    from lxml import html

    try:
        resp = requests.get(
            "https://cn.bing.com/search",
            params={"q": query, "count": SEARCH_MAX_RESULTS * 2},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=10,
        )
        resp.raise_for_status()
        tree = html.fromstring(resp.text)
        results = []
        for li in tree.xpath('//li[@class="b_algo"]')[:SEARCH_MAX_RESULTS]:
            title_a = li.xpath(".//h2/a")
            if not title_a:
                continue
            title = title_a[0].text_content().strip()
            link = title_a[0].get("href", "")
            snippet_nodes = li.xpath(
                './/div[contains(@class,"b_caption")]//p//text()'
            )
            body = " ".join(
                s.strip() for s in snippet_nodes if s.strip()
            )
            results.append({"title": title, "body": body, "href": link})
        return _format_results(results, keys=("title", "body", "href"))
    except Exception as e:
        return f"Bing 搜索失败：{e}"


def _ddg_search(query: str) -> str:
    """DuckDuckGo 免费搜索（国内通常不可用，仅作兜底）"""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "错误：未安装 duckduckgo-search"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=SEARCH_MAX_RESULTS))
    except Exception as e:
        return f"DuckDuckGo 搜索失败（国内通常被墙）：{e}\n建议配置 TAVILY_API_KEY 使用更稳定的搜索。"

    return _format_results(results, keys=("title", "body", "href"))


def _tavily_search(query: str) -> str:
    """Tavily 搜索（最稳定，需要 API key，免费 1000 次/月）"""
    try:
        from tavily import TavilyClient
    except ImportError:
        return "错误：未安装 tavily-python"

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query, max_results=SEARCH_MAX_RESULTS)
    except Exception as e:
        return f"Tavily 搜索失败：{e}"

    return _format_results(response.get("results", []), keys=("title", "content", "url"))


def _format_results(results: list, keys: tuple) -> str:
    """把搜索结果格式化成模型易读的文本"""
    if not results:
        return "未找到相关结果，建议换关键词重试。"

    title_key, body_key, url_key = keys
    blocks = []
    for i, r in enumerate(results, 1):
        title = r.get(title_key, "")
        body = r.get(body_key, "")
        url = r.get(url_key, "")
        blocks.append(f"[{i}] {title}\n{body}\n来源: {url}")
    return "\n\n---\n\n".join(blocks)
