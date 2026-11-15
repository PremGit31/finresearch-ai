"""Tests for strict JSON output from financial-data MCP tools."""
import json
import time

import numpy as np
import pandas as pd

from src.mcp import financial_data_server
from src.tools import provider_utils


def parse_strict_json(payload):
    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(payload, parse_constant=reject_constant)


class FakeTicker:
    def __init__(self, ticker, session=None):
        self.ticker = ticker
        self.info = {
            "longName": f"{ticker} Inc.",
            "currentPrice": np.float64(np.nan),
            "previousClose": 10.0,
            "volume": 100,
            "marketCap": np.float64(np.inf),
            "trailingPE": np.float64(-np.inf),
            "forwardPE": 12.0,
            "pegRatio": np.float64(np.nan),
            "profitMargins": 0.2,
            "revenueGrowth": np.float64(np.inf),
            "returnOnEquity": np.float64(np.nan),
            "debtToEquity": 0.5,
            "dividendYield": None,
            "regularMarketTime": time.time(),
        }
        statement = pd.DataFrame(
            {"latest": [np.nan, np.inf, 123.5]},
            index=["Interest Income", "Interest Expense", "Revenue"],
        )
        statement.columns = [pd.Timestamp.now(tz="UTC")]
        self.income_stmt = statement
        self.balance_sheet = statement
        self.cashflow = statement


def test_stock_quote_serializes_non_finite_values_as_null(monkeypatch):
    monkeypatch.setattr(provider_utils.yf, "Ticker", FakeTicker)

    result = parse_strict_json(financial_data_server.stock_quote("TEST"))

    assert result["metrics"]["price"]["value"] is None
    assert result["metrics"]["market_cap"]["value"] is None
    assert result["metrics"]["trailing_pe"]["value"] is None
    assert result["metrics"]["forward_pe"]["value"] == 12.0
    assert result["metrics"]["forward_pe"]["source"] == "Yahoo Finance via yfinance"
    assert result["metrics"]["forward_pe"]["as_of"]
    assert result["metrics"]["forward_pe"]["units"] == "multiple"


def test_company_financials_serializes_non_finite_statement_values_as_null(monkeypatch):
    monkeypatch.setattr(provider_utils.yf, "Ticker", FakeTicker)

    result = parse_strict_json(financial_data_server.company_financials("TEST"))

    assert result["income_statement"]["Interest Income"]["value"] is None
    assert result["income_statement"]["Interest Expense"]["value"] is None
    assert result["income_statement"]["Revenue"]["value"] == 123.5
    assert result["balance_sheet"]["Interest Income"]["value"] is None
    assert result["cash_flow"]["Interest Expense"]["value"] is None


def test_compare_stocks_serializes_non_finite_values_as_null(monkeypatch):
    monkeypatch.setattr(provider_utils.yf, "Ticker", FakeTicker)

    result = parse_strict_json(financial_data_server.compare_stocks("TEST,OTHER"))

    assert len(result) == 2
    assert result[0]["metrics"]["price"]["value"] is None
    assert result[0]["metrics"]["market_cap"]["value"] is None
    assert result[0]["metrics"]["trailing_pe"]["value"] is None
    assert result[1]["metrics"]["price"]["source"] == "Yahoo Finance via yfinance"
