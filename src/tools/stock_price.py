# src/tools/stock_price.py
"""
Stock price retrieval tool using yfinance (no API key needed).
"""
import json
from datetime import timedelta

from langchain_core.tools import tool

from config.settings import PROVIDER_TIMEOUT_SECONDS
from src.tools.provider_utils import (
    fetch_yfinance,
    fetch_yfinance_info,
    metric_provenance,
    quote_metrics,
    utc_now,
)


@tool
def get_stock_price(ticker: str) -> str:
    """
    Get the current stock price and key market data for a given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')

    Returns:
        Current price, day range, 52-week range, volume, market cap, and P/E ratio.
    """
    try:
        info = fetch_yfinance_info(ticker)
        return json.dumps({
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker.upper()),
            "provider": "Yahoo Finance via yfinance",
            "metrics": quote_metrics(info, "Yahoo Finance via yfinance"),
        }, allow_nan=False)
    except Exception as e:
        return json.dumps({"error": f"Yahoo Finance quote failed for {ticker}: {e}"})


@tool
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """
    Get historical stock price data for a given ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        period: Time period — '1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max'

    Returns:
        Historical price data summary with key statistics.
    """
    try:
        def load_history(stock):
            history = stock.history(
                period=period,
                timeout=PROVIDER_TIMEOUT_SECONDS,
            )
            if history.empty:
                raise RuntimeError(f"No historical data returned for {ticker}.")
            return history

        hist = fetch_yfinance(ticker, load_history)

        closes = hist["Close"]
        end_date = hist.index[-1]
        fetched_at = utc_now()
        as_of = end_date.to_pydatetime()
        max_age = timedelta(days=7)
        definitions = {
            "start_close": ("provider-reported currency per share", "Closing share price on the first date in the requested period.", "Start Close"),
            "end_close": ("provider-reported currency per share", "Closing share price on the last returned date in the requested period.", "End Close"),
            "period_high": ("provider-reported currency per share", "Highest daily high during the requested period.", "High"),
            "period_low": ("provider-reported currency per share", "Lowest daily low during the requested period.", "Low"),
            "average_close": ("provider-reported currency per share", "Mean daily closing price during the requested period.", "Average Close"),
            "average_volume": ("shares per trading day", "Mean daily trading volume during the requested period.", "Average Volume"),
            "period_return": ("percent", "Percentage change from first to last returned closing price.", "Period Return"),
            "volatility": ("provider-reported currency per share", "Standard deviation of daily closing prices during the requested period.", "Volatility"),
        }
        period_return = ((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100
        values = {
            "start_close": float(closes.iloc[0]),
            "end_close": float(closes.iloc[-1]),
            "period_high": float(hist["High"].max()),
            "period_low": float(hist["Low"].min()),
            "average_close": float(closes.mean()),
            "average_volume": float(hist["Volume"].mean()),
            "period_return": float(period_return),
            "volatility": float(closes.std()),
        }
        metrics = {}
        for name, value in values.items():
            units, definition, display_name = definitions[name]
            metrics[name] = {
                **metric_provenance(
                    value,
                    source="Yahoo Finance via yfinance",
                    fetched_at=fetched_at,
                    as_of=as_of,
                    units=units,
                    definition=definition,
                    max_age=max_age,
                ),
                "display_name": display_name,
            }
        return json.dumps({
            "ticker": ticker.upper(),
            "period": period,
            "provider": "Yahoo Finance via yfinance",
            "start_date": hist.index[0].strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "metrics": metrics,
        }, allow_nan=False)
    except Exception as e:
        return f"Error fetching history for {ticker}: {e}"