# src/tools/financial_ratios.py
"""
Financial ratios and fundamentals retrieval tool.
"""
from langchain_core.tools import tool
import yfinance as yf


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
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # Get financial statements
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow

        result = f"**Financial Ratios — {info.get('longName', ticker.upper())}**\n\n"

        # Valuation Ratios
        result += "📊 **Valuation Ratios:**\n"
        result += f"  - P/E (Trailing): {info.get('trailingPE', 'N/A')}\n"
        result += f"  - P/E (Forward): {info.get('forwardPE', 'N/A')}\n"
        result += f"  - P/B Ratio: {info.get('priceToBook', 'N/A')}\n"
        result += f"  - P/S Ratio: {info.get('priceToSalesTrailing12Months', 'N/A')}\n"
        result += f"  - PEG Ratio: {info.get('pegRatio', 'N/A')}\n"
        result += f"  - EV/EBITDA: {info.get('enterpriseToEbitda', 'N/A')}\n"
        result += f"  - EV/Revenue: {info.get('enterpriseToRevenue', 'N/A')}\n"

        # Profitability
        result += "\n💰 **Profitability:**\n"
        result += f"  - Gross Margin: {_fmt_pct(info.get('grossMargins'))}\n"
        result += f"  - Operating Margin: {_fmt_pct(info.get('operatingMargins'))}\n"
        result += f"  - Net Margin: {_fmt_pct(info.get('profitMargins'))}\n"
        result += f"  - ROE: {_fmt_pct(info.get('returnOnEquity'))}\n"
        result += f"  - ROA: {_fmt_pct(info.get('returnOnAssets'))}\n"

        # Growth
        result += "\n📈 **Growth:**\n"
        result += f"  - Revenue Growth: {_fmt_pct(info.get('revenueGrowth'))}\n"
        result += f"  - Earnings Growth: {_fmt_pct(info.get('earningsGrowth'))}\n"

        # Financial Health
        result += "\n🏦 **Financial Health:**\n"
        result += f"  - Current Ratio: {info.get('currentRatio', 'N/A')}\n"
        result += f"  - Debt-to-Equity: {info.get('debtToEquity', 'N/A')}\n"
        result += f"  - Quick Ratio: {info.get('quickRatio', 'N/A')}\n"
        result += f"  - Total Cash: ${info.get('totalCash', 0):,.0f}\n"
        result += f"  - Total Debt: ${info.get('totalDebt', 0):,.0f}\n"
        result += f"  - Free Cash Flow: ${info.get('freeCashflow', 0):,.0f}\n"

        # Per Share Data
        result += "\n📋 **Per Share Data:**\n"
        result += f"  - EPS (Trailing): ${info.get('trailingEps', 'N/A')}\n"
        result += f"  - EPS (Forward): ${info.get('forwardEps', 'N/A')}\n"
        result += f"  - Book Value: ${info.get('bookValue', 'N/A')}\n"
        result += f"  - Revenue/Share: ${info.get('revenuePerShare', 'N/A')}\n"

        # Recent Income Statement highlights
        if not income_stmt.empty:
            latest = income_stmt.iloc[:, 0]
            result += "\n📄 **Latest Annual Financials:**\n"
            for metric in ['Total Revenue', 'Gross Profit', 'Operating Income',
                          'Net Income', 'EBITDA']:
                if metric in latest.index:
                    val = latest[metric]
                    result += f"  - {metric}: ${val:,.0f}\n"

        return result
    except Exception as e:
        return f"Error fetching financial ratios for {ticker}: {str(e)}"


def _fmt_pct(value) -> str:
    """Format a decimal as percentage."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.2f}%"
    except (ValueError, TypeError):
        return str(value)