"""Deterministic freshness and equivalence checks for research-tool evidence."""
import json
import math
from datetime import datetime, timedelta, timezone

from config.settings import MAX_MARKET_DATA_AGE_HOURS


def _metric_records(research_data: dict):
    def walk(source_name, value, path=()):
        if isinstance(value, list):
            for index, child in enumerate(value):
                yield from walk(source_name, child, (*path, str(index)))
            return
        if not isinstance(value, dict):
            return
        if {"value", "status", "source", "units", "definition"}.issubset(value):
            metric_path = tuple(part for part in path if not part.isdigit())
            if metric_path and metric_path[0] == "metrics":
                metric_path = metric_path[1:]
            yield source_name, ":".join(metric_path), value
            return
        for key, child in value.items():
            yield from walk(source_name, child, (*path, str(key)))

    for source_name, payload in research_data.items():
        if not isinstance(payload, str):
            continue
        try:
            parsed = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            continue
        yield from walk(source_name, parsed)


def is_fresh_metric(record: dict, now: datetime | None = None) -> bool:
    """Only treat explicitly timestamped, fresh values as current evidence."""
    if record.get("status") != "fresh" or record.get("value") is None:
        return False
    try:
        as_of = datetime.fromisoformat(record["as_of"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, TypeError, ValueError):
        return False
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    max_age_hours = record.get(
        "freshness_window_hours", MAX_MARKET_DATA_AGE_HOURS
    )
    return (
        as_of <= now + timedelta(minutes=5)
        and now - as_of <= timedelta(hours=max_age_hours)
    )


def assess_research_data(research_data: dict) -> dict:
    """Find unavailable values and only compare metrics with matching definitions."""
    grouped = {}
    unavailable = []
    fresh_metric_names = set()
    observed_metric_names = set()
    for tool_name, metric_name, record in _metric_records(research_data):
        observed_metric_names.add(metric_name)
        if not is_fresh_metric(record):
            unavailable.append({
                "metric": metric_name,
                "source": record.get("source", tool_name),
                "status": record.get("status", "unverified"),
                "as_of": record.get("as_of"),
                "reason": record.get("reason", "No fresh value is available."),
            })
            continue
        fresh_metric_names.add(metric_name)
        key = (
            metric_name,
            record.get("definition"),
            record.get("units"),
        )
        grouped.setdefault(key, []).append(record)

    conflicts = []
    non_comparable = []
    signatures_by_metric = {}
    for (metric, definition, units), records in grouped.items():
        signatures_by_metric.setdefault(metric, set()).add((definition, units))
        by_date = {}
        for record in records:
            by_date.setdefault(record.get("as_of"), []).append(record)
        if len(by_date) > 1:
            non_comparable.append({
                "metric": metric,
                "definition": definition,
                "units": units,
                "as_of_dates": sorted(str(date) for date in by_date),
                "status": "unverified",
                "reason": "Equivalent metrics have different observation dates; they were not compared.",
            })
        for as_of, dated_records in by_date.items():
            numeric = [
                record for record in dated_records
                if isinstance(record.get("value"), (int, float))
                and math.isfinite(record["value"])
            ]
            if len(numeric) < 2:
                continue
            values = [record["value"] for record in numeric]
            tolerance = max(1e-9, max(abs(value) for value in values) * 1e-9)
            if max(values) - min(values) <= tolerance:
                continue
            conflicts.append({
                "metric": metric,
                "definition": definition,
                "units": units,
                "as_of": as_of,
                "status": "conflict",
                "values": [
                    {"source": record.get("source"), "value": record["value"]}
                    for record in numeric
                ],
            })

    for metric, signatures in signatures_by_metric.items():
        if len(signatures) > 1:
            non_comparable.append({
                "metric": metric,
                "status": "unverified",
                "reason": "Providers used different metric definitions or units; values were not compared.",
                "definitions": [
                    {"definition": definition, "units": units}
                    for definition, units in sorted(
                        signatures, key=lambda entry: (str(entry[0]), str(entry[1]))
                    )
                ],
            })

    unavailable = [
        item for item in unavailable if item["metric"] not in fresh_metric_names
    ]
    for metric in ("price", "trailing_pe", "forward_pe", "market_cap"):
        if metric not in observed_metric_names:
            unavailable.append({
                "metric": metric,
                "source": "research sources",
                "status": "missing",
                "as_of": None,
                "reason": "No provider returned this metric during the research run.",
            })
    return {
        "unavailable_metrics": unavailable,
        "conflicts": conflicts,
        "non_comparable": non_comparable,
        "fresh_metrics": sorted(fresh_metric_names),
    }


def format_data_quality(assessment: dict) -> str:
    """Render a concise, deterministic limitation/conflict note for reports."""
    lines = ["## Data quality and source reconciliation"]
    unavailable = assessment.get("unavailable_metrics", [])
    conflicts = assessment.get("conflicts", [])
    non_comparable = assessment.get("non_comparable", [])
    if not unavailable and not conflicts and not non_comparable:
        lines.append("No missing, stale, or conflicting quote metrics were detected.")
    if unavailable:
        lines.append("Unavailable, stale, or unverified metrics:")
        for item in unavailable:
            lines.append(
                f"- {item['metric']} from {item['source']}: {item['status']}; "
                f"as of {item['as_of'] or 'unknown'}. {item['reason']}"
            )
    if conflicts:
        lines.append("Conflicting equivalent metric values (not averaged):")
        for item in conflicts:
            values = "; ".join(
                f"{value['source']}={value['value']}" for value in item["values"]
            )
            lines.append(
                f"- {item['metric']} ({item['definition']}; {item['units']}) "
                f"as of {item['as_of']}: {values}. Treat as unverified."
            )
    if non_comparable:
        lines.append("Metrics not compared because their dates, definitions, or units differ:")
        for item in non_comparable:
            if item.get("definitions"):
                descriptions = "; ".join(
                    f"{entry['definition']} ({entry['units']})"
                    for entry in item["definitions"]
                )
                lines.append(
                    f"- {item['metric']}: differing definitions/units: {descriptions}. "
                    "Treat as unverified."
                )
                continue
            lines.append(
                f"- {item['metric']} ({item['definition']}; {item['units']}): "
                f"{', '.join(item['as_of_dates'])}. Treat as unverified."
            )
    return "\n".join(lines)


def tool_result_error(result) -> str | None:
    """Identify explicit provider/tool error payloads returned as strings."""
    if isinstance(result, dict):
        return str(result["error"]) if result.get("error") else None
    if not isinstance(result, str):
        return None
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and parsed.get("error"):
        return str(parsed["error"])
    if result.startswith("Provider errors:"):
        return result
    if result.startswith(("Error:", "Error fetching", "No data returned")):
        return result
    return None


def tool_result_warnings(result) -> list[str]:
    """Extract partial-provider failures and unavailable core quote fields."""
    warnings = []
    if not isinstance(result, str):
        return warnings
    for line in result.splitlines():
        if line.startswith("Provider errors:"):
            warnings.append(line)
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        return warnings
    if not isinstance(parsed, dict):
        return warnings
    metrics = parsed.get("metrics")
    if not isinstance(metrics, dict):
        return warnings
    unavailable = [
        name for name in ("price", "trailing_pe", "forward_pe", "market_cap")
        if isinstance(metrics.get(name), dict)
        and metrics[name].get("status") != "fresh"
    ]
    if unavailable:
        warnings.append(
            "No fresh provider value for: " + ", ".join(unavailable)
        )
    return warnings


def redact_unsupported_current_claims(report: str, assessment: dict) -> str:
    """Guard against current-market assertions when corresponding metrics are unavailable."""
    import re

    unavailable = {
        item["metric"] for item in assessment.get("unavailable_metrics", [])
    }
    unavailable.update(
        item["metric"] for item in assessment.get("conflicts", [])
    )
    unavailable.update(
        item["metric"] for item in assessment.get("non_comparable", [])
    )
    trailing_pe_unavailable = "trailing_pe" in unavailable
    forward_pe_unavailable = "forward_pe" in unavailable
    patterns = []
    if "price" in unavailable:
        patterns.append(
            r"\bprice\b|currently\s+trading"
            r"|(?:share|stock)\s+price"
        )
    if trailing_pe_unavailable and forward_pe_unavailable:
        patterns.append(r"\bP/E\b|(?:current|latest)\s+valuation|currently\s+valued")
    elif trailing_pe_unavailable:
        patterns.append(
            r"(?:current|latest)\s+valuation|currently\s+valued"
            r"|trailing\s+P/E|(?<!forward\s)\bP/E\b(?!\s*\(Forward\))"
        )
    elif forward_pe_unavailable:
        patterns.append(
            r"(?:current|latest)\s+valuation|currently\s+valued"
            r"|forward\s+P/E|(?<!trailing\s)\bP/E\b(?!\s*\(Trailing\))"
        )
    if "market_cap" in unavailable:
        patterns.append(
            r"(?:current|latest)\s+market\s+(?:capitalization|cap)"
            r"|market\s+(?:capitalization|cap)"
        )
    if "price" in unavailable:
        patterns.append(r"(?:shares|stock)\s+trade\s+at|trading\s+at\s+\$")
    statement_terms = {
        metric.split(":")[-1].replace("_", " ")
        for metric in unavailable
        if ":" in metric
    }
    patterns.extend(
        r"\b" + r"\s+".join(re.escape(part) for part in term.split()) + r"\b"
        for term in statement_terms
    )
    if not patterns:
        return report

    guard = re.compile("|".join(patterns), re.IGNORECASE)
    sentences = re.split(r"(?<=[.!?])\s+", report)
    return " ".join(
        sentence for sentence in sentences if not guard.search(sentence)
    )
