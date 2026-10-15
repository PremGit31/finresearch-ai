# src/utils/helpers.py
"""
Utility functions used across the project.
"""
import re
from typing import Optional


def extract_ticker(text: str) -> Optional[str]:
    """Try to extract a stock ticker from text."""
    # Match common ticker patterns (1-5 uppercase letters)
    match = re.search(r'\b([A-Z]{1,5})\b', text)
    return match.group(1) if match else None


def format_currency(value: float, precision: int = 2) -> str:
    """Format a number as currency."""
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.{precision}f}T"
    elif abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.{precision}f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.{precision}f}M"
    else:
        return f"${value:,.{precision}f}"


def format_percentage(value: float, precision: int = 2) -> str:
    """Format a decimal as a percentage string."""
    return f"{value * 100:.{precision}f}%"


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length, adding ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def sanitize_ticker(ticker: str) -> str:
    """Clean and validate a ticker symbol."""
    cleaned = re.sub(r'[^A-Za-z.]', '', ticker).upper()
    if not cleaned or len(cleaned) > 10:
        raise ValueError(f"Invalid ticker symbol: {ticker}")
    return cleaned