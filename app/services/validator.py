"""Server-side answer validation. Ground truth never leaves this module.

Each validator returns a ValidationResult. On an incorrect answer the message
must NOT reveal the expected value.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.loaders import load_ground_truth


@dataclass
class ValidationResult:
    correct: bool
    message: str


class ValidationError(ValueError):
    """Raised when the submitted answer is malformed (bad type/shape)."""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def _parse_ts(value: str) -> datetime:
    raw = _norm(value)
    if not raw:
        raise ValidationError("empty timestamp")
    # Accept trailing Z as UTC.
    candidate = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("timestamp is not valid ISO 8601") from exc
    if dt.tzinfo is None:
        raise ValidationError("timestamp must include a timezone (use ...Z)")
    return dt.astimezone(timezone.utc)


# --- per-type validators --------------------------------------------------

def _v_exact_match(spec: dict, answer) -> ValidationResult:
    submitted = _norm(answer)
    ok = submitted == _norm(spec["expected"])
    return ValidationResult(ok, "Correct." if ok else "Incorrect Event ID.")


def _v_normalized_string(spec: dict, answer) -> ValidationResult:
    submitted = _norm(answer).lower()
    accepted = {_norm(a).lower() for a in spec.get("accepted", [spec["expected"]])}
    ok = submitted in accepted
    return ValidationResult(ok, "Correct." if ok else "That account is not correct.")


def _v_ip_match(spec: dict, answer) -> ValidationResult:
    try:
        submitted = ipaddress.ip_address(_norm(answer))
    except ValueError as exc:
        raise ValidationError("not a valid IP address") from exc
    expected = ipaddress.ip_address(_norm(spec["expected"]))
    ok = submitted == expected
    return ValidationResult(ok, "Correct." if ok else "That source IP is not correct.")


def _v_integer_match(spec: dict, answer) -> ValidationResult:
    try:
        submitted = int(_norm(answer))
    except (ValueError, TypeError) as exc:
        raise ValidationError("answer must be an integer") from exc
    ok = submitted == int(spec["expected"])
    return ValidationResult(ok, "Correct." if ok else "That count is not correct.")


def _v_timestamp_window(spec: dict, answer) -> ValidationResult:
    if not isinstance(answer, dict):
        raise ValidationError("answer must include 'first' and 'last'")
    first = _parse_ts(answer.get("first", ""))
    last = _parse_ts(answer.get("last", ""))
    ok = first == _parse_ts(spec["first"]) and last == _parse_ts(spec["last"])
    return ValidationResult(ok, "Correct." if ok else "First/last timestamps do not match the burst.")


def _v_structured_choice(spec: dict, answer) -> ValidationResult:
    if not isinstance(answer, dict):
        raise ValidationError("answer must be a structured choice object")

    choice = _norm(answer.get("choice", "")).lower()
    valid_choices = {c.lower() for c in spec["choices"]}
    if choice not in valid_choices:
        raise ValidationError("choice not in allowed options")

    checks = [choice == _norm(spec["expected_choice"]).lower()]

    if spec.get("require_evidence"):
        evidence = _norm(answer.get("evidence", "")).lower()
        if not evidence:
            raise ValidationError("evidence is required")
        accepted = {_norm(e).lower() for e in spec.get("evidence_accepted", [])}
        checks.append(evidence in accepted)

    if spec.get("require_priority"):
        priority = _norm(answer.get("priority", "")).lower()
        valid_prio = {p.lower() for p in spec.get("priorities", [])}
        if priority not in valid_prio:
            raise ValidationError("priority not in allowed options")
        checks.append(priority == _norm(spec["expected_priority"]).lower())

    ok = all(checks)
    return ValidationResult(ok, "Correct." if ok else "Verdict or supporting evidence is not correct.")


_DISPATCH = {
    "exact_match": _v_exact_match,
    "normalized_string": _v_normalized_string,
    "ip_match": _v_ip_match,
    "integer_match": _v_integer_match,
    "timestamp_window": _v_timestamp_window,
    "structured_choice": _v_structured_choice,
}


def validate(task_id: str, answer) -> ValidationResult:
    gt = load_ground_truth()
    spec = gt.get("tasks", {}).get(task_id)
    if spec is None:
        raise ValidationError(f"unknown task {task_id}")
    validator = _DISPATCH.get(spec["validator_type"])
    if validator is None:
        raise ValidationError(f"no validator for {spec['validator_type']}")
    return validator(spec, answer)


def max_attempts(task_id: str) -> int:
    gt = load_ground_truth()
    return int(gt.get("tasks", {}).get(task_id, {}).get("max_attempts", 10))
