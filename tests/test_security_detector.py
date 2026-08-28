from unittest.mock import MagicMock, patch

from src.security.detector import (
    MAX_REPORT_FETCH_ATTEMPTS,
    _log_skillspector_final_result,
    _log_collector_event,
    _record_unavailable_report_attempt,
    _sanitize_json_value,
)


def test_sanitize_json_value_replaces_nested_nul_characters():
    value = {
        "plain": "unchanged",
        "nul\x00key": "value\x00with\x00nul",
        "nested": ["item\x00", {"tuple": ("a\x00b", 1, None)}],
    }

    assert _sanitize_json_value(value) == {
        "plain": "unchanged",
        "nul\\0key": "value\\0with\\0nul",
        "nested": ["item\\0", {"tuple": ["a\\0b", 1, None]}],
    }


def test_unavailable_report_is_finalized_after_retry_limit():
    details = {"skillspector_async": True}

    for attempt in range(1, MAX_REPORT_FETCH_ATTEMPTS + 1):
        details, exhausted = _record_unavailable_report_attempt(details, "FAILURE")
        assert details["skillspector_report_fetch_attempts"] == attempt
        assert exhausted is (attempt == MAX_REPORT_FETCH_ATTEMPTS)

    assert details["skillspector_collected"] is True
    assert details["skillspector_status"] == "FAILURE"
    assert details["skillspector_error"] == "report_unavailable"


def test_unavailable_report_attempt_recovers_from_invalid_counter():
    details, exhausted = _record_unavailable_report_attempt(
        {"skillspector_report_fetch_attempts": "invalid"},
        "UNSTABLE",
    )

    assert exhausted is False
    assert details["skillspector_report_fetch_attempts"] == 1
    assert details["skillspector_status"] == "UNSTABLE"
    assert "skillspector_collected" not in details


def test_missing_jenkins_artifact_is_finalized_immediately():
    details, exhausted = _record_unavailable_report_attempt(
        {"skillspector_async": True},
        "FAILURE",
        terminal=True,
    )

    assert exhausted is True
    assert details["skillspector_collected"] is True
    assert details["skillspector_report_fetch_attempts"] == 1
    assert details["skillspector_error"] == "report_unavailable"


def test_final_result_log_contains_report():
    with patch("src.security.detector.logger.info") as log_info:
        _log_skillspector_final_result(
            audit_id="audit-1",
            build_number=123,
            status="SUCCESS",
            outcome="report_collected",
            risk_level="low",
            score=8,
            signal_count=1,
        )

    message = log_info.call_args.args[1]
    assert '"event":"skillspector_final_result"' in message
    assert '"build_number":123' in message
    assert '"risk_level":"low"' in message
    assert '"score":8' in message


def test_missing_jenkins_build_is_terminal():
    response = MagicMock(status_code=404)
    client_context = MagicMock()
    client_context.__enter__.return_value.get.return_value = response

    from src.security.detector import SkillspectorClient

    client = SkillspectorClient("http://jenkins", "admin", "token")
    with patch("src.security.detector.httpx.Client", return_value=client_context):
        assert client.get_build_status(14194) == "NOT_FOUND"


def test_collector_event_log_contains_decision():
    with patch("src.security.detector.logger.debug") as log_debug:
        _log_collector_event(
            "item_deferred",
            audit_id="audit-1",
            build_number=456,
            jenkins_status="BUILDING",
            action="retry_next_poll",
        )

    message = log_debug.call_args.args[1]
    assert '"event":"item_deferred"' in message
    assert '"build_number":456' in message
    assert '"action":"retry_next_poll"' in message


def test_run_scan_uses_report_even_when_build_not_success():
    """Critical findings make the Jenkins build exit non-zero, but report.json
    still exists.  The report artifact must be treated as the source of truth."""
    from src.security.detector import SkillspectorClient

    client = SkillspectorClient("http://jenkins", "admin", "token")
    report = {"risk_assessment": {"severity": "CRITICAL", "score": 95}}
    report_md = "# Security Report"

    with (
        patch.object(client, "trigger_scan", return_value=42),
        patch.object(client, "wait_for_build", return_value="FAILURE"),
        patch.object(client, "fetch_report", return_value=report) as mock_fetch,
        patch.object(client, "fetch_report_md", return_value=report_md) as mock_fetch_md,
    ):
        result, md = client.run_scan("https://gitcode.com/openeuler/foo")

    mock_fetch.assert_called_once_with(42)
    mock_fetch_md.assert_called_once_with(42)
    assert result == report
    assert md == report_md


def test_run_scan_errors_when_report_unavailable():
    from src.security.detector import SkillspectorClient

    client = SkillspectorClient("http://jenkins", "admin", "token")

    with (
        patch.object(client, "trigger_scan", return_value=42),
        patch.object(client, "wait_for_build", return_value="SUCCESS"),
        patch.object(client, "fetch_report", return_value=None),
    ):
        result, _ = client.run_scan("https://gitcode.com/openeuler/foo")

    assert "error" in result
