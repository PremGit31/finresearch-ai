"""Shared timeout, retry, and provenance helpers for external data providers."""
from datetime import datetime, timedelta, timezone
import math
from time import sleep
from typing import Callable, TypeVar

from curl_cffi import requests as curl_requests
import yfinance as yf

from config.settings import (
    MAX_FINANCIAL_DATA_AGE_DAYS,
    MAX_MARKET_DATA_AGE_HOURS,
    PROVIDER_MAX_RETRIES,
    PROVIDER_TIMEOUT_SECONDS,
)

T = TypeVar("T")


def retry_provider_call(provider: str, operation: Callable[[], T]) -> T:
    """Retry a provider operation a bounded number of times, then fail explicitly."""
    last_error = None
    for attempt in range(PROVIDER_MAX_RETRIES + 1):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt < PROVIDER_MAX_RETRIES:
                sleep(min(0.1 * (2 ** attempt), 0.5))
    raise RuntimeError(
        f"{provider} request failed after {PROVIDER_MAX_RETRIES + 1} attempts: "
        f"{last_error}"
    ) from last_error


def fetch_yfinance(ticker: str, operation: Callable[[object], T]) -> T:
    """Call yfinance with a transport-level timeout and bounded retries."""
    def request():
        session = curl_requests.Session(timeout=PROVIDER_TIMEOUT_SECONDS)
        try:
            return operation(yf.Ticker(ticker.upper(), session=session))
        finally:
            session.close()

    return retry_provider_call("Yahoo Finance", request)


def fetch_yfinance_info(ticker: str) -> dict:
    """Fetch ticker metadata and retry empty responses as provider failures."""
    def load_info(stock):
        info = stock.info
        if not info:
            raise RuntimeError(f"No quote data returned for {ticker.upper()}.")
        return info

    return fetch_yfinance(ticker, load_info)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_to_utc(value) -> datetime | None:
    """Parse provider timestamps expressed as datetimes, dates, or Unix epochs."""
    item = getattr(value, "item", None)
    if callable(item):
        try:
            value = item()
        except (TypeError, ValueError):
            return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def metric_provenance(
    value,
    *,
    source: str,
    fetched_at: datetime,
    as_of,
    units: str,
    definition: str,
    max_age: timedelta,
) -> dict:
    """Return a metric with provenance and suppress values that are not usable."""
    item = getattr(value, "item", None)
    if callable(item):
        try:
            value = item()
        except (TypeError, ValueError):
            value = None
    if isinstance(value, float) and not math.isfinite(value):
        value = None
    observed_at = timestamp_to_utc(as_of)
    if value is None:
        status = "missing"
        reason = "The provider did not return this metric."
    elif observed_at is None:
        status = "unverified"
        reason = "The provider did not provide a usable as-of timestamp."
    elif fetched_at - observed_at > max_age:
        status = "stale"
        reason = f"The observation is older than {max_age}."
    elif observed_at > fetched_at + timedelta(minutes=5):
        status = "unverified"
        reason = "The provider timestamp is unexpectedly in the future."
    else:
        status = "fresh"
        reason = None

    return {
        "value": value if status == "fresh" else None,
        "source": source,
        "fetched_at": fetched_at.isoformat(),
        "as_of": observed_at.isoformat() if observed_at else None,
        "units": units,
        "definition": definition,
        "status": status,
        "reason": reason,
        "freshness_window_hours": max_age.total_seconds() / 3600,
    }


def quote_metrics(info: dict, source: str) -> dict:
    """Build timestamped, freshness-checked standard quote metrics."""
    fetched_at = utc_now()
    as_of = (
        info.get("regularMarketTime")
        or info.get("postMarketTime")
        or info.get("preMarketTime")
    )
    market_age = timedelta(hours=MAX_MARKET_DATA_AGE_HOURS)
    currency = info.get("currency") or "provider-reported currency (code unavailable)"
    definitions = {
        "price": (f"{currency} per share", "Latest reported share price."),
        "trailing_pe": ("multiple", "Share price divided by trailing twelve-month EPS."),
        "forward_pe": ("multiple", "Share price divided by provider-estimated forward EPS."),
        "market_cap": (currency, "Provider-reported equity market capitalization."),
        "volume": ("shares", "Provider-reported trading volume for its stated market interval."),
    }
    values = {
        "price": info.get("currentPrice", info.get("regularMarketPrice")),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "market_cap": info.get("marketCap"),
        "volume": info.get("volume"),
    }
    metrics = {
        key: {
            **metric_provenance(
                value,
                source=source,
                fetched_at=fetched_at,
                as_of=as_of,
                units=units,
                definition=definition,
                max_age=market_age,
            ),
            **({"display_name": "Reported Price"} if key == "price" else {}),
        }
        for key, value in values.items()
        for units, definition in [definitions[key]]
    }
    metrics.update(ratio_metrics(info, source))
    return metrics


def ratio_metrics(info: dict, source: str) -> dict:
    """Return commonly used provider ratios with metric definitions and provenance."""
    fetched_at = utc_now()
    as_of = (
        info.get("regularMarketTime")
        or info.get("postMarketTime")
        or info.get("preMarketTime")
    )
    currency = info.get("currency") or "provider-reported currency (code unavailable)"
    definitions = {
        "trailing_pe": ("multiple", "Share price divided by trailing twelve-month EPS."),
        "forward_pe": ("multiple", "Share price divided by provider-estimated forward EPS."),
        "price_to_book": ("multiple", "Market price per share divided by book value per share."),
        "price_to_sales": ("multiple", "Market capitalization divided by trailing twelve-month revenue."),
        "peg_ratio": ("multiple", "Trailing P/E divided by provider-estimated earnings growth."),
        "ev_to_ebitda": ("multiple", "Enterprise value divided by EBITDA."),
        "ev_to_revenue": ("multiple", "Enterprise value divided by revenue."),
        "gross_margin": ("decimal fraction (1.0 = 100%)", "Gross profit divided by revenue."),
        "operating_margin": ("decimal fraction (1.0 = 100%)", "Operating income divided by revenue."),
        "profit_margin": ("decimal fraction (1.0 = 100%)", "Net income divided by revenue."),
        "roe": ("decimal fraction (1.0 = 100%)", "Net income divided by average shareholder equity."),
        "roa": ("decimal fraction (1.0 = 100%)", "Net income divided by average total assets."),
        "revenue_growth": ("decimal fraction (1.0 = 100%)", "Provider-reported year-over-year revenue growth."),
        "earnings_growth": ("decimal fraction (1.0 = 100%)", "Provider-reported earnings growth."),
        "current_ratio": ("multiple", "Current assets divided by current liabilities."),
        "debt_to_equity": ("provider-defined ratio", "Provider-reported total debt to equity."),
        "quick_ratio": ("multiple", "Liquid current assets divided by current liabilities."),
        "trailing_eps": (f"{currency} per share", "Provider-reported trailing twelve-month EPS."),
        "forward_eps": (f"{currency} per share", "Provider-estimated forward EPS."),
        "total_cash": (currency, "Provider-reported total cash and cash equivalents."),
        "total_debt": (currency, "Provider-reported total debt."),
        "free_cash_flow": (currency, "Provider-reported free cash flow."),
        "book_value": (f"{currency} per share", "Provider-reported book value per share."),
        "revenue_per_share": (f"{currency} per share", "Provider-reported revenue per share."),
        "dividend_yield": ("decimal fraction (1.0 = 100%)", "Provider-reported annual dividend yield."),
    }
    keys = {
        "trailing_pe": "trailingPE",
        "forward_pe": "forwardPE",
        "price_to_book": "priceToBook",
        "price_to_sales": "priceToSalesTrailing12Months",
        "peg_ratio": "pegRatio",
        "ev_to_ebitda": "enterpriseToEbitda",
        "ev_to_revenue": "enterpriseToRevenue",
        "gross_margin": "grossMargins",
        "operating_margin": "operatingMargins",
        "profit_margin": "profitMargins",
        "roe": "returnOnEquity",
        "roa": "returnOnAssets",
        "revenue_growth": "revenueGrowth",
        "earnings_growth": "earningsGrowth",
        "current_ratio": "currentRatio",
        "debt_to_equity": "debtToEquity",
        "quick_ratio": "quickRatio",
        "trailing_eps": "trailingEps",
        "forward_eps": "forwardEps",
        "total_cash": "totalCash",
        "total_debt": "totalDebt",
        "free_cash_flow": "freeCashflow",
        "book_value": "bookValue",
        "revenue_per_share": "revenuePerShare",
        "dividend_yield": "dividendYield",
    }
    labels = {
        "trailing_pe": "P/E (Trailing)",
        "forward_pe": "P/E (Forward)",
    }
    market_age = timedelta(hours=MAX_MARKET_DATA_AGE_HOURS)
    financial_age = timedelta(days=MAX_FINANCIAL_DATA_AGE_DAYS)
    as_of_keys = {
        "trailing_pe": "regularMarketTime",
        "forward_pe": "regularMarketTime",
        "price_to_book": "regularMarketTime",
        "price_to_sales": "regularMarketTime",
        "peg_ratio": "mostRecentQuarter",
        "ev_to_ebitda": "mostRecentQuarter",
        "ev_to_revenue": "mostRecentQuarter",
        "gross_margin": "mostRecentQuarter",
        "operating_margin": "mostRecentQuarter",
        "profit_margin": "mostRecentQuarter",
        "roe": "mostRecentQuarter",
        "roa": "mostRecentQuarter",
        "revenue_growth": "mostRecentQuarter",
        "earnings_growth": "mostRecentQuarter",
        "current_ratio": "mostRecentQuarter",
        "debt_to_equity": "mostRecentQuarter",
        "quick_ratio": "mostRecentQuarter",
        "trailing_eps": "regularMarketTime",
        "forward_eps": "regularMarketTime",
        "total_cash": "mostRecentQuarter",
        "total_debt": "mostRecentQuarter",
        "free_cash_flow": "mostRecentQuarter",
        "book_value": "mostRecentQuarter",
        "revenue_per_share": "mostRecentQuarter",
        "dividend_yield": "regularMarketTime",
    }
    return {
        name: {
            **metric_provenance(
                info.get(provider_key),
                source=source,
                fetched_at=fetched_at,
                as_of=(
                    as_of
                    if as_of_keys[name] == "regularMarketTime"
                    else info.get(as_of_keys[name])
                ),
                units=definitions[name][0],
                definition=definitions[name][1],
                max_age=(
                    market_age
                    if as_of_keys[name] == "regularMarketTime"
                    else financial_age
                ),
            ),
            **({"display_name": labels[name]} if name in labels else {}),
        }
        for name, provider_key in keys.items()
    }


def financial_statement_metrics(
    rows: dict, source: str, as_of
) -> dict:
    """Attach provenance and a quarterly freshness window to statement values."""
    fetched_at = utc_now()
    age = timedelta(days=MAX_FINANCIAL_DATA_AGE_DAYS)
    return {
        name: metric_provenance(
            value,
            source=source,
            fetched_at=fetched_at,
            as_of=as_of,
            units="provider-reported currency and scale",
            definition=f"{name}, as reported in the latest available financial statement.",
            max_age=age,
        )
        for name, value in rows.items()
    }
