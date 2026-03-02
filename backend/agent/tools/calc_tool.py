from __future__ import annotations


def _interp(value: float | None, good_range: tuple, bad_range: tuple) -> str:
    """Return 'good', 'neutral', or 'bad' based on thresholds."""
    if value is None:
        return "unknown"
    if good_range[0] <= value <= good_range[1]:
        return "good"
    if value < bad_range[0] or value > bad_range[1]:
        return "bad"
    return "neutral"


def calculate_financial_ratios(data: dict) -> dict:
    """Calculate and interpret key financial ratios from market/RAG data.

    Accepts a flat dict with raw financial fields (compatible with yfinance info).
    Returns calculated ratios with values + interpretation labels.
    """

    def safe_div(a, b):
        try:
            return round(a / b, 4) if b and b != 0 else None
        except (TypeError, ZeroDivisionError):
            return None

    pe = data.get("trailingPE")
    forward_pe = data.get("forwardPE")
    pb = data.get("priceToBook")
    de = data.get("debtToEquity")
    roe = data.get("returnOnEquity")
    rev_growth = data.get("revenueGrowth")
    earn_growth = data.get("earningsGrowth")
    gross_margin = data.get("grossMargins")
    op_margin = data.get("operatingMargins")
    net_margin = data.get("profitMargins")

    current_price = data.get("currentPrice")
    market_cap = data.get("marketCap")
    total_revenue = data.get("totalRevenue")
    total_debt = data.get("totalDebt")
    total_cash = data.get("totalCash")
    free_cashflow = data.get("freeCashflow")

    ratios = {
        "pe_ratio": {
            "value": pe,
            "interpretation": _interp(pe, (5, 25), (0, 50)),
            "note": "Price-to-Earnings: <25 is healthy for most sectors",
        },
        "forward_pe": {
            "value": forward_pe,
            "interpretation": _interp(forward_pe, (5, 20), (0, 40)),
            "note": "Forward P/E based on projected earnings",
        },
        "price_to_book": {
            "value": pb,
            "interpretation": _interp(pb, (0, 3), (0, 10)),
            "note": "P/B <3 is considered reasonable",
        },
        "debt_to_equity": {
            "value": de,
            "interpretation": _interp(de, (0, 1), (3, float("inf"))),
            "note": "D/E <1 is conservative, >3 is high risk",
        },
        "return_on_equity": {
            "value": round(roe * 100, 2) if roe else None,
            "interpretation": _interp(roe, (0.15, 1.0), (0, 0.05)),
            "unit": "%",
            "note": "ROE >15% is strong",
        },
        "revenue_growth_yoy": {
            "value": round(rev_growth * 100, 2) if rev_growth else None,
            "interpretation": _interp(rev_growth, (0.05, 1.0), (-1.0, 0)),
            "unit": "%",
            "note": "YoY revenue growth: >5% healthy, <0% is a warning",
        },
        "earnings_growth_yoy": {
            "value": round(earn_growth * 100, 2) if earn_growth else None,
            "interpretation": _interp(earn_growth, (0.05, 1.0), (-1.0, 0)),
            "unit": "%",
            "note": "YoY earnings growth",
        },
        "gross_margin": {
            "value": round(gross_margin * 100, 2) if gross_margin else None,
            "interpretation": _interp(gross_margin, (0.4, 1.0), (0, 0.2)),
            "unit": "%",
            "note": "Gross margin >40% is strong",
        },
        "operating_margin": {
            "value": round(op_margin * 100, 2) if op_margin else None,
            "interpretation": _interp(op_margin, (0.15, 1.0), (0, 0.05)),
            "unit": "%",
            "note": "Operating margin >15% is healthy",
        },
        "net_margin": {
            "value": round(net_margin * 100, 2) if net_margin else None,
            "interpretation": _interp(net_margin, (0.1, 1.0), (0, 0.02)),
            "unit": "%",
            "note": "Net margin >10% is healthy",
        },
        "price_to_sales": {
            "value": safe_div(market_cap, total_revenue),
            "interpretation": "N/A",
            "note": "Market cap / revenue",
        },
        "net_debt": {
            "value": (total_debt - total_cash) if total_debt and total_cash else None,
            "interpretation": "N/A",
            "note": "Total debt minus cash",
        },
        "free_cashflow": {
            "value": free_cashflow,
            "interpretation": "good" if free_cashflow and free_cashflow > 0 else "bad",
            "note": "Positive FCF is essential for financial health",
        },
    }

    # Filter out None values for clean output
    return {k: v for k, v in ratios.items() if v.get("value") is not None}
