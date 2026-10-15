# src/tools/calculator.py
"""
Financial calculation tool for DCF, ratios, growth rates, etc.
"""
import json
from langchain_core.tools import tool


@tool
def financial_calculator(calculation_type: str, parameters: str) -> str:
    """
    Perform financial calculations.

    Args:
        calculation_type: Type of calculation. One of:
            'dcf' — Discounted Cash Flow valuation
            'cagr' — Compound Annual Growth Rate
            'wacc' — Weighted Average Cost of Capital
            'ratio' — Calculate a financial ratio
            'growth_rate' — Simple growth rate
            'present_value' — Present value of future cash flows
        parameters: JSON string of parameters for the calculation.
            For DCF: {"cash_flows": [100, 110, 120], "discount_rate": 0.10, "terminal_growth": 0.03}
            For CAGR: {"beginning_value": 100, "ending_value": 150, "years": 5}
            For WACC: {"equity_weight": 0.7, "debt_weight": 0.3, "cost_of_equity": 0.12,
                       "cost_of_debt": 0.05, "tax_rate": 0.21}
            For ratio: {"numerator": 500, "denominator": 200, "name": "Current Ratio"}
            For growth_rate: {"old_value": 100, "new_value": 120}
            For present_value: {"future_value": 1000, "rate": 0.08, "years": 5}

    Returns:
        Calculation result with detailed breakdown.
    """
    try:
        params = json.loads(parameters)
    except json.JSONDecodeError:
        return "Error: parameters must be a valid JSON string."

    calcs = {
        "dcf": _calc_dcf,
        "cagr": _calc_cagr,
        "wacc": _calc_wacc,
        "ratio": _calc_ratio,
        "growth_rate": _calc_growth_rate,
        "present_value": _calc_present_value,
    }

    calc_fn = calcs.get(calculation_type.lower())
    if not calc_fn:
        return f"Unknown calculation type: {calculation_type}. Available: {list(calcs.keys())}"

    try:
        return calc_fn(params)
    except Exception as e:
        return f"Calculation error: {str(e)}"


def _calc_dcf(params: dict) -> str:
    """Discounted Cash Flow valuation."""
    cash_flows = params["cash_flows"]
    discount_rate = params["discount_rate"]
    terminal_growth = params.get("terminal_growth", 0.03)

    result = "**DCF Valuation:**\n"
    pv_total = 0

    for i, cf in enumerate(cash_flows, 1):
        pv = cf / ((1 + discount_rate) ** i)
        pv_total += pv
        result += f"  Year {i}: CF=${cf:,.2f} → PV=${pv:,.2f}\n"

    # Terminal value
    terminal_cf = cash_flows[-1] * (1 + terminal_growth)
    terminal_value = terminal_cf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** len(cash_flows))

    result += f"\n  Terminal Value: ${terminal_value:,.2f}\n"
    result += f"  PV of Terminal Value: ${pv_terminal:,.2f}\n"
    result += f"\n  **Total Enterprise Value: ${pv_total + pv_terminal:,.2f}**\n"

    return result


def _calc_cagr(params: dict) -> str:
    """Compound Annual Growth Rate."""
    beg = params["beginning_value"]
    end = params["ending_value"]
    years = params["years"]

    cagr = (end / beg) ** (1 / years) - 1

    return (
        f"**CAGR Calculation:**\n"
        f"  Beginning Value: ${beg:,.2f}\n"
        f"  Ending Value: ${end:,.2f}\n"
        f"  Years: {years}\n"
        f"  **CAGR: {cagr * 100:.2f}%**\n"
    )


def _calc_wacc(params: dict) -> str:
    """Weighted Average Cost of Capital."""
    e_w = params["equity_weight"]
    d_w = params["debt_weight"]
    ke = params["cost_of_equity"]
    kd = params["cost_of_debt"]
    tax = params["tax_rate"]

    wacc = (e_w * ke) + (d_w * kd * (1 - tax))

    return (
        f"**WACC Calculation:**\n"
        f"  Equity Weight: {e_w * 100:.1f}%\n"
        f"  Debt Weight: {d_w * 100:.1f}%\n"
        f"  Cost of Equity: {ke * 100:.2f}%\n"
        f"  Cost of Debt: {kd * 100:.2f}%\n"
        f"  Tax Rate: {tax * 100:.1f}%\n"
        f"  **WACC: {wacc * 100:.2f}%**\n"
    )


def _calc_ratio(params: dict) -> str:
    """Calculate a financial ratio."""
    num = params["numerator"]
    den = params["denominator"]
    name = params.get("name", "Ratio")
    ratio = num / den if den != 0 else float("inf")
    return f"**{name}:** {num:,.2f} / {den:,.2f} = **{ratio:.4f}**\n"


def _calc_growth_rate(params: dict) -> str:
    """Simple growth rate."""
    old = params["old_value"]
    new = params["new_value"]
    growth = ((new - old) / old) * 100
    return (
        f"**Growth Rate:**\n"
        f"  Old Value: ${old:,.2f}\n"
        f"  New Value: ${new:,.2f}\n"
        f"  **Growth: {growth:+.2f}%**\n"
    )


def _calc_present_value(params: dict) -> str:
    """Present value calculation."""
    fv = params["future_value"]
    rate = params["rate"]
    years = params["years"]
    pv = fv / ((1 + rate) ** years)
    return (
        f"**Present Value:**\n"
        f"  Future Value: ${fv:,.2f}\n"
        f"  Discount Rate: {rate * 100:.2f}%\n"
        f"  Years: {years}\n"
        f"  **Present Value: ${pv:,.2f}**\n"
    )