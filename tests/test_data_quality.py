import json
from datetime import datetime, timedelta, timezone

import pytest

from src.agents.data_quality import (
    assess_research_data,
    format_data_quality,
    is_fresh_metric,
    redact_unsupported_current_claims,
)
from src.tools import provider_utils
from src.tools.provider_utils import metric_provenance


def make_metric(value, as_of, source="Provider A", definition=None, units="multiple"):
    return {
        "value": value,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of,
        "units": units,
        "definition": definition or "Trailing P/E definition",
        "status": "fresh",
        "reason": None,
    }


def test_quote_timeout_uses_transport_timeout_and_bounded_retries(monkeypatch):
    class FakeSession:
        def __init__(self, timeout):
            assert timeout == provider_utils.PROVIDER_TIMEOUT_SECONDS

        def close(self):
            pass

    calls = []

    class FakeYahoo:
        def __init__(self, ticker, session):
            calls.append(ticker)
            raise TimeoutError("provider timed out")

    monkeypatch.setattr(provider_utils.curl_requests, "Session", FakeSession)
    monkeypatch.setattr(provider_utils.yf, "Ticker", FakeYahoo)
    monkeypatch.setattr(provider_utils, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        provider_utils.fetch_yfinance("AAPL", lambda stock: stock.info)

    assert calls == ["AAPL"] * 3


def test_missing_or_stale_quote_metrics_are_unavailable():
    now = datetime.now(timezone.utc)
    missing = metric_provenance(
        None,
        source="Yahoo",
        fetched_at=now,
        as_of=now,
        units="multiple",
        definition="Trailing P/E",
        max_age=timedelta(hours=24),
    )
    stale = metric_provenance(
        30,
        source="Yahoo",
        fetched_at=now,
        as_of=now - timedelta(days=2),
        units="multiple",
        definition="Trailing P/E",
        max_age=timedelta(hours=24),
    )

    assert missing["status"] == "missing"
    assert missing["value"] is None
    assert stale["status"] == "stale"
    assert stale["value"] is None
    assert not is_fresh_metric(stale)


def test_only_equivalent_same_date_metrics_are_compared():
    observed = datetime.now(timezone.utc).isoformat()
    data = {
        "quote_a": json.dumps({"metrics": {
            "trailing_pe": make_metric(30, observed, "Yahoo Finance")
        }}),
        "quote_b": json.dumps({"metrics": {
            "trailing_pe": make_metric(35, observed, "Other source")
        }}),
        "forward_metric": json.dumps({"metrics": {
            "forward_pe": make_metric(
                40, observed, "Other source", "Forward P/E definition"
            )
        }}),
    }

    assessment = assess_research_data(data)

    assert len(assessment["conflicts"]) == 1
    conflict = assessment["conflicts"][0]
    assert conflict["metric"] == "trailing_pe"
    assert conflict["as_of"] == observed
    assert {item["value"] for item in conflict["values"]} == {30, 35}
    assert "not averaged" in format_data_quality(assessment)


def test_different_observation_dates_are_unverified_not_conflicts():
    now = datetime.now(timezone.utc)
    data = {
        "quote_a": json.dumps({"metrics": {
            "trailing_pe": make_metric(30, now.isoformat(), "Yahoo Finance")
        }}),
        "quote_b": json.dumps({"metrics": {
            "trailing_pe": make_metric(
                35, (now - timedelta(hours=2)).isoformat(), "Other source"
            )
        }}),
    }

    assessment = assess_research_data(data)

    assert assessment["conflicts"] == []
    assert assessment["non_comparable"][0]["status"] == "unverified"


def test_report_removes_current_quote_claim_when_quote_is_unavailable():
    assessment = {
        "unavailable_metrics": [
            {"metric": "price", "status": "stale"},
            {"metric": "trailing_pe", "status": "missing"},
        ]
    }

    report = redact_unsupported_current_claims(
        "The current share price is $100. Revenue grew last year.", assessment
    )

    assert "current share price" not in report.lower()
    assert "Revenue grew last year." in report


def test_report_does_not_select_one_conflicting_metric():
    assessment = {
        "unavailable_metrics": [],
        "conflicts": [{"metric": "trailing_pe"}],
    }

    report = redact_unsupported_current_claims(
        "The current P/E is 30. Revenue grew last year.", assessment
    )

    assert "P/E is 30" not in report
    assert "Revenue grew last year." in report
