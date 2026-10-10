"""Validator unit tests — correct, incorrect, and malformed answers."""
import pytest

from app.services import validator


def test_t1_exact_match():
    assert validator.validate("T1", "4625").correct
    assert validator.validate("T1", " 4625 ").correct
    assert not validator.validate("T1", "4624").correct


def test_t2_normalized_string():
    assert validator.validate("T2", "jsmith").correct
    assert validator.validate("T2", "  JSmith ").correct
    assert not validator.validate("T2", "mwilson").correct


def test_t3_ip_match_canonical():
    assert validator.validate("T3", "198.51.100.42").correct
    # leading-zero / spacing variations still parse to the same address
    assert validator.validate("T3", " 198.51.100.42 ").correct
    assert not validator.validate("T3", "198.51.100.77").correct


def test_t3_invalid_ip_raises():
    with pytest.raises(validator.ValidationError):
        validator.validate("T3", "not-an-ip")


def test_t4_integer_match():
    assert validator.validate("T4", "12").correct
    assert validator.validate("T4", 12).correct
    assert not validator.validate("T4", "11").correct


def test_t4_non_integer_raises():
    with pytest.raises(validator.ValidationError):
        validator.validate("T4", "twelve")


def test_t5_timestamp_window():
    ok = {"first": "2026-10-09T02:14:05Z", "last": "2026-10-09T02:17:40Z"}
    assert validator.validate("T5", ok).correct
    swapped = {"first": ok["last"], "last": ok["first"]}
    assert not validator.validate("T5", swapped).correct


def test_t5_timestamp_without_tz_raises():
    with pytest.raises(validator.ValidationError):
        validator.validate("T5", {"first": "2026-10-09T02:14:05", "last": "2026-10-09T02:17:40Z"})


def test_t6_structured_choice_with_evidence():
    assert validator.validate("T6", {"choice": "yes", "evidence": "4624"}).correct
    assert validator.validate("T6", {"choice": "yes", "evidence": "1020"}).correct
    assert not validator.validate("T6", {"choice": "no", "evidence": "4624"}).correct
    # correct choice but wrong evidence fails
    assert not validator.validate("T6", {"choice": "yes", "evidence": "9999"}).correct


def test_t6_missing_evidence_raises():
    with pytest.raises(validator.ValidationError):
        validator.validate("T6", {"choice": "yes"})


def test_t7_verdict_and_priority():
    assert validator.validate("T7", {"choice": "escalate", "priority": "high"}).correct
    assert not validator.validate("T7", {"choice": "monitor", "priority": "high"}).correct
    assert not validator.validate("T7", {"choice": "escalate", "priority": "low"}).correct


def test_t7_invalid_choice_raises():
    with pytest.raises(validator.ValidationError):
        validator.validate("T7", {"choice": "ignore", "priority": "high"})


def test_t8_logon_type_integer_match():
    assert validator.validate("T8", "3").correct
    assert validator.validate("T8", 3).correct
    assert not validator.validate("T8", "2").correct


def test_t8_non_integer_raises():
    with pytest.raises(validator.ValidationError):
        validator.validate("T8", "network")


def test_incorrect_message_never_leaks_answer():
    r = validator.validate("T2", "wrong")
    assert "jsmith" not in r.message.lower()
