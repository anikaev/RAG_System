from __future__ import annotations

import re
from collections.abc import Sequence

PATH_PATTERN = re.compile(r"(/[A-Za-z0-9._-]+)+")


def find_blocked_code_patterns(code: str, patterns: Sequence[str]) -> list[str]:
    normalized = code.lower()
    hits = {pattern for pattern in patterns if pattern.lower() in normalized}
    return sorted(hits)


def sanitize_excerpt(text: str, *, max_length: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 3].rstrip()}..."


def redact_internal_paths(text: str) -> str:
    return PATH_PATTERN.sub("[redacted-path]", text)
