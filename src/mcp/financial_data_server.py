# src/mcp/financial_data_server.py
"""
MCP Server exposing financial data tools.
Run with: python -m src.mcp.financial_data_server
"""
import json
import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("FinancialData")


@mcp.tool()
def stock_quote(ticker: str) -> str:
    """Get real-time stock quote for a given ticker symbol."""
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        return json.dumps({
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "price": info.get("currentPrice"),
            "change": info.get("currentPrice", 0) - info.get("previousClose", 0),
            "change_pct": (
                (info.get("currentPrice", 0) - info.get("previousClose", 0))
                / info.get("previousClose", 1) * 100
            ),
            "volume": info.get("volume"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
        }, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def company_financials(ticker: str) -> str:
    """Get comprehensive financial data including income statement, balance sheet, and cash flows."""
    try:
        stock = yf.Ticker(ticker.upper())

        result = {"ticker": ticker.upper()}

        # Income statement
        income = stock.income_stmt
        if not income.empty:
            latest = income.iloc[:, 0]
            result["income_statement"] = {
                k: float(v) for k, v in latest.items()
                if not (hasattr(v, '__iter__') and not isinstance(v, str))
            }

        # Balance sheet
        bs = stock.balance_sheet
        if not bs.empty:
            latest = bs.iloc[:, 0]
            result["balance_sheet"] = {
                k: float(v) for k, v in latest.items()
                if not (hasattr(v, '__iter__') and not isinstance(v, str))
            }

        # Cash flow
        cf = stock.cashflow
        if not cf.empty:
            latest = cf.iloc[:, 0]
            result["cash_flow"] = {
                k: float(v) for k, v in latest.items()
                if not (hasattr(v, '__iter__') and not isinstance(v, str))
            }

        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def compare_stocks(tickers: str) -> str:
    """Compare key metrics for multiple stocks. Pass tickers comma-separated like 'AAPL,MSFT,GOOGL'."""
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        comparison = []

        for ticker in ticker_list:
            stock = yf.Ticker(ticker)
            info = stock.info
            comparison.append({
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "price": info.get("currentPrice"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "profit_margin": info.get("profitMargins"),
                "revenue_growth": info.get("revenueGrowth"),
                "roe": info.get("returnOnEquity"),
                "debt_to_equity": info.get("debtToEquity"),
            })

        return json.dumps(comparison, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")