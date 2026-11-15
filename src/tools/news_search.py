# src/tools/news_search.py
"""
Financial news search using free RSS feeds and NewsAPI free tier.
"""
import feedparser
import httpx
from langchain_core.tools import tool
from config.settings import NEWS_API_KEY, PROVIDER_TIMEOUT_SECONDS
from src.tools.provider_utils import retry_provider_call


@tool
def search_financial_news(query: str, max_results: int = 10) -> str:
    """
    Search for recent financial news about a company or topic.

    Args:
        query: Search query (company name, ticker, or financial topic)
        max_results: Maximum number of results to return (default 10)

    Returns:
        List of recent news articles with titles, sources, dates, and summaries.
    """
    articles = []
    provider_errors = []

    # Strategy 1: Google News RSS (always available, no API key)
    try:
        rss_articles = _search_google_news_rss(query, max_results)
        articles.extend(rss_articles)
    except Exception as exc:
        provider_errors.append(f"Google News RSS: {exc}")

    # Strategy 2: NewsAPI (if key available)
    if NEWS_API_KEY and len(articles) < max_results:
        try:
            remaining = max_results - len(articles)
            newsapi_articles = _search_newsapi(query, remaining)
            articles.extend(newsapi_articles)
        except Exception as exc:
            provider_errors.append(f"NewsAPI: {exc}")

    # Strategy 3: Yahoo Finance RSS
    try:
        yahoo_articles = _search_yahoo_finance_rss(query, max_results=3)
        articles.extend(yahoo_articles)
    except Exception as exc:
        provider_errors.append(f"Yahoo Finance RSS: {exc}")

    if not articles:
        message = f"No recent news found for '{query}'."
        if provider_errors:
            return "Provider errors: " + "; ".join(provider_errors) + "\n" + message
        return message

    # Deduplicate by title similarity
    seen_titles = set()
    unique_articles = []
    for art in articles:
        title_key = art["title"][:50].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_articles.append(art)

    # Format output
    result = f"**Recent News: '{query}'** ({len(unique_articles)} articles)\n\n"
    for i, art in enumerate(unique_articles[:max_results], 1):
        result += f"{i}. **{art['title']}**\n"
        result += f"   Source: {art.get('source', 'Unknown')} | "
        result += f"Date: {art.get('date', 'Unknown')}\n"
        if art.get("summary"):
            result += f"   {art['summary'][:200]}...\n"
        if art.get("url"):
            result += f"   URL: {art['url']}\n"
        result += "\n"

    if provider_errors:
        result += "Provider errors: " + "; ".join(provider_errors) + "\n"
    return result


def _search_google_news_rss(query: str, max_results: int) -> list[dict]:
    """Search Google News RSS feed."""
    response = retry_provider_call(
        "Google News RSS",
        lambda: _get(
            "https://news.google.com/rss/search",
            params={"q": f"{query} finance", "hl": "en-US", "gl": "US", "ceid": "US:en"},
        ),
    )
    feed = feedparser.parse(response.content)
    articles = []
    for entry in feed.entries[:max_results]:
        articles.append({
            "title": entry.get("title", ""),
            "source": entry.get("source", {}).get("title", "Google News"),
            "date": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "url": entry.get("link", ""),
        })
    return articles


def _search_newsapi(query: str, max_results: int) -> list[dict]:
    """Search using NewsAPI free tier."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": max_results,
        "apiKey": NEWS_API_KEY,
    }
    response = retry_provider_call(
        "NewsAPI", lambda: _get(url, params=params)
    )
    data = response.json()

    articles = []
    for art in data.get("articles", []):
        articles.append({
            "title": art.get("title", ""),
            "source": art.get("source", {}).get("name", "Unknown"),
            "date": art.get("publishedAt", ""),
            "summary": art.get("description", ""),
            "url": art.get("url", ""),
        })
    return articles


def _search_yahoo_finance_rss(query: str, max_results: int) -> list[dict]:
    """Search Yahoo Finance RSS."""
    # Yahoo Finance RSS for specific tickers
    ticker = query.upper().strip()
    response = retry_provider_call(
        "Yahoo Finance RSS",
        lambda: _get(
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            params={"s": ticker, "region": "US", "lang": "en-US"},
        ),
    )
    feed = feedparser.parse(response.content)
    articles = []
    for entry in feed.entries[:max_results]:
        articles.append({
            "title": entry.get("title", ""),
            "source": "Yahoo Finance",
            "date": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "url": entry.get("link", ""),
        })
    return articles


def _get(url: str, params: dict) -> httpx.Response:
    response = httpx.get(url, params=params, timeout=PROVIDER_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response