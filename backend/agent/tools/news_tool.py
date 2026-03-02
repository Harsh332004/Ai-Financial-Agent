from __future__ import annotations

import logging
import random
import time

from backend.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def fetch_news(company_name: str, ticker: str, max_articles: int = 5) -> dict:
    """Fetch recent news for a company.

    Primary: NewsAPI (if NEWS_API_KEY is configured).
    Fallback: yfinance Ticker.news (no API key needed, with retry).

    Returns:
        {"articles": [{"title", "description", "url", "publishedAt", "source"}]}
    """
    articles: list[dict] = []

    # -- Primary: NewsAPI --
    if settings.NEWS_API_KEY:
        try:
            from newsapi import NewsApiClient
            client = NewsApiClient(api_key=settings.NEWS_API_KEY)
            query = f"{company_name} OR {ticker}"
            response = client.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                page_size=max_articles,
            )
            for art in (response.get("articles") or [])[:max_articles]:
                articles.append({
                    "title": art.get("title", ""),
                    "description": art.get("description", ""),
                    "url": art.get("url", ""),
                    "publishedAt": art.get("publishedAt", ""),
                    "source": art.get("source", {}).get("name", ""),
                })
        except Exception as e:
            logger.warning("NewsAPI failed: %s — falling back to yfinance", e)

    # -- Fallback: yfinance with retry --
    if not articles:
        import yfinance as yf

        last_error = ""
        for attempt in range(MAX_RETRIES):
            try:
                t = yf.Ticker(ticker)
                raw_news = t.news or []
                for item in raw_news[:max_articles]:
                    articles.append({
                        "title": item.get("title", ""),
                        "description": item.get("summary", ""),
                        "url": item.get("link", ""),
                        "publishedAt": str(item.get("providerPublishTime", "")),
                        "source": item.get("publisher", ""),
                    })
                break  # success
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "yfinance news attempt %d/%d for %s failed: %s",
                    attempt + 1, MAX_RETRIES, ticker, last_error,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5 * (attempt + 1) + random.uniform(0, 2))

        if not articles and last_error:
            logger.error("yfinance news exhausted retries for %s: %s", ticker, last_error)

    return {"articles": articles}
