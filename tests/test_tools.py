# tests/test_tools.py
"""
Tests for financial tools.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.tools.stock_price import get_stock_price, get_stock_history
from src.tools.financial_ratios import get_financial_ratios
from src.tools.calculator import financial_calculator
from src.tools.news_search import search_financial_news


class TestStockPrice:
    def test_get_stock_price_valid_ticker(self):
        result = get_stock_price.invoke({"ticker": "AAPL"})
        assert "AAPL" in result or "Apple" in result
        assert "$" in result or "Price" in result

    def test_get_stock_price_invalid_ticker(self):
        result = get_stock_price.invoke({"ticker": "ZZZZZZZ"})
        # Should handle gracefully
        assert isinstance(result, str)

    def test_get_stock_history(self):
        result = get_stock_history.invoke({"ticker": "MSFT", "period": "1mo"})
        assert "MSFT" in result
        assert "Return" in result or "High" in result


class TestFinancialRatios:
    def test_get_ratios_valid_ticker(self):
        result = get_financial_ratios.invoke({"ticker": "GOOGL"})
        assert "Valuation" in result or "P/E" in result

    def test_ratios_contain_key_metrics(self):
        result = get_financial_ratios.invoke({"ticker": "AAPL"})
        assert any(
            term in result
            for term in ["P/E", "Margin", "ROE", "Profitability", "Valuation"]
        )


class TestCalculator:
    def test_cagr(self):
        params = '{"beginning_value": 100, "ending_value": 150, "years": 5}'
        result = financial_calculator.invoke(
            {"calculation_type": "cagr", "parameters": params}
        )
        assert "CAGR" in result
        assert "%" in result

    def test_dcf(self):
        params = '{"cash_flows": [100, 110, 120], "discount_rate": 0.10, "terminal_growth": 0.03}'
        result = financial_calculator.invoke(
            {"calculation_type": "dcf", "parameters": params}
        )
        assert "Enterprise Value" in result

    def test_wacc(self):
        params = '{"equity_weight": 0.7, "debt_weight": 0.3, "cost_of_equity": 0.12, "cost_of_debt": 0.05, "tax_rate": 0.21}'
        result = financial_calculator.invoke(
            {"calculation_type": "wacc", "parameters": params}
        )
        assert "WACC" in result

    def test_growth_rate(self):
        params = '{"old_value": 100, "new_value": 120}'
        result = financial_calculator.invoke(
            {"calculation_type": "growth_rate", "parameters": params}
        )
        assert "20.00%" in result

    def test_invalid_calc_type(self):
        result = financial_calculator.invoke(
            {"calculation_type": "invalid", "parameters": "{}"}
        )
        assert "Unknown" in result

    def test_invalid_json(self):
        result = financial_calculator.invoke(
            {"calculation_type": "cagr", "parameters": "not json"}
        )
        assert "Error" in result


class TestNewsSearch:
    def test_search_news(self):
        result = search_financial_news.invoke(
            {"query": "Apple stock", "max_results": 5}
        )
        assert isinstance(result, str)
        # Should return something — either articles or "no news found"
        assert len(result) > 10