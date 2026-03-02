from __future__ import annotations

import logging
import random
import time

logger = logging.getLogger(__name__)

_WANTED_KEYS = [
    "currentPrice", "marketCap", "trailingPE", "forwardPE",
    "priceToBook", "debtToEquity", "returnOnEquity",
    "revenueGrowth", "earningsGrowth", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "sector", "industry", "fullTimeEmployees",
    "totalRevenue", "grossMargins", "operatingMargins", "profitMargins",
    "totalDebt", "totalCash", "freeCashflow",
]

MAX_RETRIES = 3


def fetch_market_data(ticker: str) -> dict:
    """Fetch live market data for a ticker using yfinance.

    Retries up to 3 times with exponential backoff to handle 429 rate-limiting.
    Never raises — returns an error key on failures.
    """
    import yfinance as yf

    last_error = ""
    for attempt in range(MAX_RETRIES):
        try:
            t = yf.Ticker(ticker)
            info = t.info

            if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
                return {"error": f"Ticker '{ticker}' not found or no data available", "ticker": ticker}

            result: dict = {"ticker": ticker}
            for key in _WANTED_KEYS:
                val = info.get(key)
                if val is not None:
                    result[key] = val

            return result

        except Exception as e:
            last_error = str(e)
            logger.warning(
                "fetch_market_data attempt %d/%d for %s failed: %s",
                attempt + 1, MAX_RETRIES, ticker, last_error,
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1) + random.uniform(0, 2))

    logger.error("fetch_market_data exhausted retries for %s: %s", ticker, last_error)
    return {"ticker": ticker, "error": f"Could not fetch market data after {MAX_RETRIES} attempts: {last_error}"}
