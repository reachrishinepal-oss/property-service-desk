"""
PURPOSE: Prove the filter handling turns each guardrail outcome into the right stop and message, using fake errors and responses.
LAYER:   Security/Controls
SESSION: S04
Run:     python -m pytest tests/test_filter_outcomes.py
"""
from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

import httpx
import openai

from src.governance.filter_outcomes import (
    LENGTH_MESSAGE, SAFETY_FALLBACK, SELF_HARM_FALLBACK, FilterStop, call_with_filter_check,
)

REQUEST = httpx.Request("POST", "https://example.invalid/openai/v1/responses")
SEVERITIES = [{"source_type": "prompt", "content_filter_results": {
    "self_harm": {"filtered": True, "severity": "medium"}, "hate": {"filtered": False, "severity": "safe"}}}]
HATE_ONLY = [{"source_type": "prompt", "content_filter_results": {
    "self_harm": {"filtered": False, "severity": "safe"}, "hate": {"filtered": True, "severity": "low"}}},
    {"source_type": "completion", "content_filter_results": {"self_harm": {"filtered": False, "severity": "safe"}}}]
SELF_HARM_IN_COMPLETION = [{"source_type": "prompt", "content_filter_results": {"self_harm": {"severity": "safe"}}},
                           {"source_type": "completion", "content_filter_results": {"self_harm": {"severity": "low"}}}]


def bad_request(code: str, body: dict | None = None) -> openai.BadRequestError:
    """A fake HTTP 400 like the one the service sends; the SDK reads code from the body."""
    return openai.BadRequestError("blocked", response=httpx.Response(400, request=REQUEST), body={"code": code, **(body or {})})


def fake_response(status: str = "completed", reason: str | None = None, filters: list | None = None):
    return SimpleNamespace(status=status, output_text="Hello",
                           incomplete_details=SimpleNamespace(reason=reason) if reason else None,
                           model_extra={"content_filters": filters} if filters else {})


def raise_(error: Exception):
    raise error


def stop_from(create) -> tuple[FilterStop, str]:
    """Run the check, expecting a FilterStop; return it with the log line printed."""
    printed = StringIO()
    with redirect_stdout(printed), unittest.TestCase().assertRaises(FilterStop) as caught:
        call_with_filter_check(create)
    return caught.exception, printed.getvalue()


class FilterOutcomeTests(unittest.TestCase):
    def test_normal_reply_passes_through(self):
        response = fake_response()
        self.assertIs(call_with_filter_check(lambda: response), response)

    def test_blocked_prompt_with_self_harm_gives_caring_fallback_and_logs_severities(self):
        stop, log = stop_from(lambda: raise_(bad_request("content_filter", {"content_filters": SEVERITIES})))
        self.assertEqual((stop.kind, stop.message, stop.safety), ("prompt_blocked", SELF_HARM_FALLBACK, True))
        self.assertIn("kind=prompt_blocked code=content_filter", log)
        self.assertIn("self_harm=medium", log)

    def test_blocked_prompt_without_self_harm_gives_general_fallback(self):
        stop, _ = stop_from(lambda: raise_(bad_request("content_filter", {"content_filters": HATE_ONLY})))
        self.assertEqual(stop.message, SAFETY_FALLBACK)

    def test_blocked_prompt_with_no_verdict_gives_general_fallback(self):
        stop, _ = stop_from(lambda: raise_(bad_request("content_filter")))
        self.assertEqual(stop.message, SAFETY_FALLBACK)

    def test_blocked_prompt_reads_older_innererror_shape(self):
        body = {"innererror": {"content_filter_result": SEVERITIES[0]["content_filter_results"]}}
        stop, log = stop_from(lambda: raise_(bad_request("content_filter", body)))
        self.assertIn("prompt: self_harm=medium", log)
        self.assertEqual(stop.message, SELF_HARM_FALLBACK)

    def test_other_bad_request_is_not_hidden(self):
        with self.assertRaises(openai.BadRequestError):
            call_with_filter_check(lambda: raise_(bad_request("invalid_value")))

    def test_cut_reply_with_self_harm_in_completion_gives_caring_fallback(self):
        stop, log = stop_from(lambda: fake_response("incomplete", "content_filter", SELF_HARM_IN_COMPLETION))
        self.assertEqual((stop.kind, stop.message, stop.safety), ("reply_cut", SELF_HARM_FALLBACK, True))
        self.assertIn("kind=reply_cut", log)

    def test_cut_reply_without_self_harm_gives_general_fallback(self):
        stop, _ = stop_from(lambda: fake_response("incomplete", "content_filter", HATE_ONLY))
        self.assertEqual(stop.message, SAFETY_FALLBACK)

    def test_length_limit_is_not_a_safety_event(self):
        stop, log = stop_from(lambda: fake_response("incomplete", "max_output_tokens"))
        self.assertEqual((stop.kind, stop.message, stop.safety), ("length", LENGTH_MESSAGE, False))
        self.assertIn("severities=none given", log)


if __name__ == "__main__":
    unittest.main()
