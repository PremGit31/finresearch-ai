# src/mcp/financial_data_server.py
"""
MCP Server exposing financial data tools.
Run with: python -m src.mcp.financial_data_server
"""
import json
import math
from collections.abc import Mapping

from mcp.server.fastmcp import FastMCP

from src.tools.provider_utils import (
    fetch_yfinance,
    fetch_yfinance_info,
    financial_statement_metrics,
    quote_metrics,
)

mcp = FastMCP("FinancialData")


def _json_safe(value):
    """Convert provider values to strict JSON-compatible values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return _json_safe(tolist())

    item = getattr(value, "item", None)
    if callable(item):
        try:
            scalar = item()
        except (TypeError, ValueError):
            pass
        else:
            if scalar is not value:
                return _json_safe(scalar)
    return value


def _dump_json(value) -> str:
    return json.dumps(_json_safe(value), default=str, allow_nan=False, indent=2)


@mcp.tool()
def stock_quote(ticker: str) -> str:
    """Get real-time stock quote for a given ticker symbol."""
    try:
        info = fetch_yfinance_info(ticker)
        return _dump_json({
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "metrics": quote_metrics(info, "Yahoo Finance via yfinance"),
        })
    except Exception as e:
        return _dump_json({"error": str(e)})


@mcp.tool()
def company_financials(ticker: str) -> str:
    """Get comprehensive financial data including income statement, balance sheet, and cash flows."""
    try:
        def load_statements(stock):
            output = {}
            for name, statement in (
                ("income_statement", stock.income_stmt),
                ("balance_sheet", stock.balance_sheet),
                ("cash_flow", stock.cashflow),
            ):
                if not statement.empty:
                    latest = statement.iloc[:, 0]
                    rows = {
                        key: float(value)
                        for key, value in latest.items()
                        if not (hasattr(value, "__iter__") and not isinstance(value, str))
                    }
                    output[name] = financial_statement_metrics(
                        rows,
                        "Yahoo Finance via yfinance",
                        statement.columns[0],
                    )
            return output

        result = {"ticker": ticker.upper()}
        statements = fetch_yfinance(ticker, load_statements)
        if not statements:
            raise RuntimeError(f"No financial statements returned for {ticker.upper()}.")
        result.update(statements)
        return _dump_json(result)
    except Exception as e:
        return _dump_json({"error": str(e)})


@mcp.tool()
def compare_stocks(tickers: str) -> str:
    """Compare key metrics for multiple stocks. Pass tickers comma-separated like 'AAPL,MSFT,GOOGL'."""
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        comparison = []

        for ticker in ticker_list:
            info = fetch_yfinance_info(ticker)
            comparison.append({
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "metrics": quote_metrics(info, "Yahoo Finance via yfinance"),
            })

        return _dump_json(comparison)
    except Exception as e:
        return _dump_json({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")