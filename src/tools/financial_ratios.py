# src/tools/financial_ratios.py
"""
Financial ratios and fundamentals retrieval tool.
"""
import json

from langchain_core.tools import tool

from src.tools.provider_utils import (
    fetch_yfinance,
    financial_statement_metrics,
    ratio_metrics,
)


@tool
def get_financial_ratios(ticker: str) -> str:
    """
    Get key financial ratios and fundamental data for a company.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

    Returns:
        Comprehensive financial ratios including profitability, liquidity,
        leverage, and valuation metrics.
    """
    try:
        def load_financials(stock):
            output = {"ticker": ticker.upper(), "provider": "Yahoo Finance via yfinance"}
            info = stock.info
            if not info:
                raise RuntimeError(f"No financial data returned for {ticker.upper()}.")
            output["company_name"] = info.get("longName", ticker.upper())
            output["metrics"] = ratio_metrics(info, "Yahoo Finance via yfinance")
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

        return json.dumps(
            fetch_yfinance(ticker, load_financials),
            default=str,
            allow_nan=False,
        )
    except Exception as e:
        return json.dumps({"error": f"Yahoo Finance ratios failed for {ticker}: {e}"})