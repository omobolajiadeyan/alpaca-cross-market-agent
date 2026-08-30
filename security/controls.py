"""Security controls mapped in SECURITY.md to NIST AI RMF and SSDF outcomes."""

from __future__ import annotations

import html
import re
from copy import deepcopy
from urllib.parse import urlparse


SENSITIVE_KEY = re.compile(r"(secret|token|password|api.?key|credential)", re.I)
INSTRUCTION_PATTERN = re.compile(
    r"(ignore\s+(all\s+)?previous|system\s+prompt|developer\s+message|execute\s+tool|"
    r"reveal\s+(the\s+)?secret|api[_ -]?key)", re.I,
)


class SecurityViolation(RuntimeError):
    """A fail-closed security boundary prevented an unsafe operation."""


def redact(value):
    """Recursively remove credential-shaped fields before persistence/export."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def sanitize_external_text(value, max_length=500):
    """Bound and neutralize untrusted prose such as news headlines."""
    text = " ".join(str(value or "").split())[:max_length]
    if INSTRUCTION_PATTERN.search(text):
        return "[UNTRUSTED INSTRUCTION-LIKE CONTENT REMOVED]"
    return html.escape(text, quote=True)


def validate_paper_endpoint(base_url):
    """Accept only Alpaca HTTPS paper endpoints for broker mutations."""
    parsed = urlparse(base_url or "")
    valid = (parsed.scheme == "https" and parsed.hostname == "paper-api.alpaca.markets"
             and not parsed.username and not parsed.password)
    if not valid:
        raise SecurityViolation("broker mutation blocked: endpoint is not the Alpaca paper host")
    return True


def security_posture(config):
    """Produce a secret-free, judge-visible posture report."""
    checks = [
        {"control": "Paper endpoint", "passed": config.get("paper_endpoint", False),
         "why": "Prevents accidental real-money routing."},
        {"control": "Public execution disabled", "passed": not config.get("public_execution", False),
         "why": "A public visitor must not control the owner's broker account."},
        {"control": "Live data required", "passed": config.get("require_live_data", False),
         "why": "Fallback evidence cannot authorize a financial action."},
        {"control": "Credential presence", "passed": config.get("credentials_present", False),
         "why": "Missing credentials fail setup explicitly rather than creating false evidence."},
    ]
    return {"passed": all(item["passed"] for item in checks), "checks": checks,
            "residual_risk": "Prototype controls reduce risk; they do not constitute NIST certification."}


def safe_copy(value):
    return redact(deepcopy(value))
