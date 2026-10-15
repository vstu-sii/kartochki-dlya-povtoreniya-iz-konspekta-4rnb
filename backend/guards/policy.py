"""Security decisions that must never be delegated to an LLM prompt."""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    code: str


_INJECTION_PATTERNS = (
    re.compile(r"ignore\W+(all\W+)?(previous|prior)\W+instructions", re.I),
    re.compile(r"(забудь|игнорируй)\W+(все\W+)?(предыдущие|системные)\W+инструкции", re.I),
    re.compile(r"(show|reveal|print|покажи|раскрой)\W+.{0,24}(system\W+prompt|системн\w*\W+промпт)", re.I),
    re.compile(r"<\s*(system|assistant|tool)\s*>", re.I),
)


def inspect_untrusted_text(text: str) -> GuardDecision:
    value = unicodedata.normalize("NFKC", str(text or ""))
    value = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", value)
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
