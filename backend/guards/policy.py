"""Security decisions that must never be delegated to an LLM prompt."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    code: str


_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"(забудь|игнорируй)\s+(все\s+)?(предыдущие|системные)\s+инструкции", re.I),
    re.compile(r"(show|reveal|print|покажи|раскрой)\s+.{0,24}(system\s+prompt|системн\w*\s+промпт)", re.I),
    re.compile(r"<\s*(system|assistant|tool)\s*>", re.I),
)


def inspect_untrusted_text(text: str) -> GuardDecision:
    value = str(text or "")
    if any(pattern.search(value) for pattern in _INJECTION_PATTERNS):
        return GuardDecision(False, "PROMPT_INJECTION_BLOCKED")
    return GuardDecision(True, "OK")


def authorize_model_tool(*, user_id: str, resource_owner_id: str, action: str) -> GuardDecision:
    """Allow one read-only tool and reject cross-user or mutating actions."""
    if not user_id or user_id != resource_owner_id:
        return GuardDecision(False, "TOOL_FORBIDDEN")
    if action != "lookup_source":
        return GuardDecision(False, "TOOL_ACTION_NOT_ALLOWED")
    return GuardDecision(True, "OK")
