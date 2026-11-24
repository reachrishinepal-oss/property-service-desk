"""
PURPOSE: Turn the guardrail's two outcomes (filtered prompt, filtered completion) and a length cut into a plain stop with a message for the resident, and log each event.
LAYER:   Security/Controls
SESSION: S04
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import openai

# The tutor's wording. No phone number: the app does not know the building's emergency line.
SAFETY_FALLBACK = (
    "I can't help with that message here. If anyone is hurt or in danger, call the building's emergency line "
    "or the emergency services right away. Otherwise, please rephrase and tell me your building and unit number."
)
LENGTH_MESSAGE = "My reply was cut off because it reached its length limit. Please ask again in a shorter way."


class FilterStop(Exception):
    """The call did not give a usable reply. kind is prompt_blocked, reply_cut or length; message is what to show."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.safety = kind in ("prompt_blocked", "reply_cut")


def severities(filters: list | None) -> str:
    """Read 'source: category=severity' pairs out of a content_filters list, where the service sent one."""
    parts = []
    for part in filters or []:
        results = part.get("content_filter_results", {})
        levels = [f"{name}={info.get('severity')}" for name, info in results.items() if info.get("severity")]
        if levels:
            parts.append(f"{part.get('source_type', '?')}: {', '.join(levels)}")
    return "; ".join(parts) or "none given"


def log_event(kind: str, code: str, filters: list | None) -> None:
    """Print one log line per event: kind, code, time and the per-category severities."""
    print(f"[filter] kind={kind} code={code} time={datetime.now():%Y-%m-%d %H:%M:%S} severities={severities(filters)}")


def call_with_filter_check(create: Callable[[], object]):
    """Run one Responses API call and return the response, or raise FilterStop if a guardrail or a length limit stopped it."""
    # AI-103 1.4.a: the guardrail answers in two ways, and the app handles both instead of crashing.
    # A filtered prompt: the call fails with HTTP 400 and code content_filter, and the model never runs.
    try:
        response = create()
    except openai.BadRequestError as error:
        if error.code != "content_filter":
            raise
        body = error.body if isinstance(error.body, dict) else {}
        inner = (body.get("innererror") or {}).get("content_filter_result")  # the older Azure shape of the same verdict
        filters = body.get("content_filters") or ([{"source_type": "prompt", "content_filter_results": inner}] if inner else None)
        log_event("prompt_blocked", "content_filter", filters)
        raise FilterStop("prompt_blocked", SAFETY_FALLBACK) from error
    # AI-103 1.4.a: a filtered completion: HTTP 200, but status is incomplete with reason content_filter (the reply was cut).
    # Reason max_output_tokens is not a safety event: it is a length problem, and a cut reply is never proof it was safe.
    if getattr(response, "status", None) == "incomplete":
        reason = getattr(response.incomplete_details, "reason", None)
        filters = (getattr(response, "model_extra", None) or {}).get("content_filters")
        if reason == "content_filter":
            log_event("reply_cut", reason, filters)
            raise FilterStop("reply_cut", SAFETY_FALLBACK)
        log_event("length", str(reason), filters)
        raise FilterStop("length", LENGTH_MESSAGE)
    return response
