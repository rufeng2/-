"""Input, retrieved-context and output guardrails for the AI boundary."""
from __future__ import annotations

from dataclasses import dataclass
import re

from backend.services.observability import SAFETY_EVENTS


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    text: str
    reason: str = ""
    redactions: int = 0


class AIGuardrails:
    _injection = re.compile(
        r"(ignore|disregard|forget).{0,30}(previous|above|system).{0,20}(instruction|prompt)"
        r"|忽略.{0,12}(之前|以上|系统).{0,8}(指令|提示词)"
        r"|泄露.{0,8}(系统提示词|system prompt)|developer message|jailbreak",
        re.I | re.S,
    )
    _credential_request = re.compile(r"(输出|显示|告诉我|导出).{0,16}(API.?Key|密钥|密码|访问令牌|token)", re.I)
    _secret = re.compile(r"(?i)(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
    _id_card = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
    _phone = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
    _email = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
    _context_instruction = re.compile(
        r"(?im)^.*(ignore previous|system prompt|developer message|忽略之前|忽略系统指令|执行以下指令).*$"
    )

    def check_input(self, text: str) -> SafetyResult:
        if self._injection.search(text):
            SAFETY_EVENTS.labels(stage="input", outcome="blocked_injection").inc()
            return SafetyResult(False, "", "prompt_injection")
        if self._credential_request.search(text):
            SAFETY_EVENTS.labels(stage="input", outcome="blocked_secret_request").inc()
            return SafetyResult(False, "", "credential_exfiltration")
        SAFETY_EVENTS.labels(stage="input", outcome="allowed").inc()
        return SafetyResult(True, text)

    def sanitize_context(self, text: str) -> SafetyResult:
        cleaned, removed = self._context_instruction.subn("[REMOVED UNTRUSTED INSTRUCTION]", text)
        SAFETY_EVENTS.labels(stage="context", outcome="sanitized" if removed else "allowed").inc()
        return SafetyResult(True, cleaned, redactions=removed)

    def sanitize_output(self, text: str) -> SafetyResult:
        if self._injection.search(text) and "system prompt" in text.lower():
            SAFETY_EVENTS.labels(stage="output", outcome="blocked").inc()
            return SafetyResult(False, "抱歉，回答触发了安全策略，无法展示。", "unsafe_instruction_disclosure")
        redactions = 0
        cleaned = text
        for pattern, replacement in (
            (self._secret, "[REDACTED_SECRET]"),
            (self._id_card, "[REDACTED_ID]"),
            (self._phone, "[REDACTED_PHONE]"),
            (self._email, "[REDACTED_EMAIL]"),
        ):
            cleaned, count = pattern.subn(replacement, cleaned)
            redactions += count
        SAFETY_EVENTS.labels(stage="output", outcome="redacted" if redactions else "allowed").inc()
        return SafetyResult(True, cleaned, redactions=redactions)

    def contains_sensitive(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in (self._secret, self._id_card, self._phone))


ai_guardrails = AIGuardrails()
