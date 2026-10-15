# src/tools/stock_price.py
"""
Stock price retrieval tool using yfinance (no API key needed).
"""
from langchain_core.tools import tool
import yfinance as yf


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
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or "currentPrice" not in info:
            # Fallback: try fast_info
            fast = stock.fast_info
            return (
                f"**{ticker.upper()}**\n"
                f"- Last Price: ${fast.last_price:.2f}\n"
                f"- Market Cap: ${fast.market_cap:,.0f}\n"
                f"- 50-Day Avg: ${fast.fifty_day_average:.2f}\n"
                f"- 200-Day Avg: ${fast.two_hundred_day_average:.2f}\n"
            )

        result = f"**{info.get('longName', ticker.upper())}** ({ticker.upper()})\n"
        result += f"- Current Price: ${info.get('currentPrice', 'N/A')}\n"
        result += f"- Previous Close: ${info.get('previousClose', 'N/A')}\n"
        result += f"- Day Range: ${info.get('dayLow', 'N/A')} - ${info.get('dayHigh', 'N/A')}\n"
        result += f"- 52-Week Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}\n"
        result += f"- Volume: {info.get('volume', 'N/A'):,}\n"
        result += f"- Market Cap: ${info.get('marketCap', 0):,.0f}\n"
        result += f"- P/E Ratio (Trailing): {info.get('trailingPE', 'N/A')}\n"
        result += f"- P/E Ratio (Forward): {info.get('forwardPE', 'N/A')}\n"
        result += f"- Dividend Yield: {info.get('dividendYield', 'N/A')}\n"
        result += f"- Sector: {info.get('sector', 'N/A')}\n"
        result += f"- Industry: {info.get('industry', 'N/A')}\n"
        return result
    except Exception as e:
        return f"Error fetching stock data for {ticker}: {str(e)}"


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
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)

        if hist.empty:
            return f"No historical data found for {ticker}"

        result = f"**{ticker.upper()} — {period} Price History**\n"
        result += f"- Start: ${hist['Close'].iloc[0]:.2f} ({hist.index[0].strftime('%Y-%m-%d')})\n"
        result += f"- End: ${hist['Close'].iloc[-1]:.2f} ({hist.index[-1].strftime('%Y-%m-%d')})\n"
        result += f"- High: ${hist['High'].max():.2f}\n"
        result += f"- Low: ${hist['Low'].min():.2f}\n"
        result += f"- Avg Close: ${hist['Close'].mean():.2f}\n"
        result += f"- Avg Volume: {hist['Volume'].mean():,.0f}\n"

        pct_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        result += f"- Period Return: {pct_change:+.2f}%\n"
        result += f"- Volatility (Std Dev): ${hist['Close'].std():.2f}\n"

        return result
    except Exception as e:
        return f"Error fetching history for {ticker}: {str(e)}"