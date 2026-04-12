from __future__ import annotations

from app.core.security import find_blocked_code_patterns, redact_internal_paths, sanitize_excerpt


def test_find_blocked_code_patterns_detects_multiple_hits() -> None:
    code = "import os\nprint(open('/tmp/data.txt').read())\n"

    hits = find_blocked_code_patterns(
        code,
        ("import os", "open(", "socket."),
    )

    assert hits == ["import os", "open("]


def test_sanitize_excerpt_compacts_and_truncates() -> None:
    excerpt = sanitize_excerpt(
        "  Это   очень длинный   текст\nс лишними пробелами, который должен быть "
        "сокращён до безопасного короткого фрагмента.  ",
        max_length=60,
    )

    assert "  " not in excerpt
    assert len(excerpt) <= 60
    assert excerpt.endswith("...")


def test_redact_internal_paths_hides_local_paths() -> None:
    text = "Смотри /Users/k.anikaev/project/app/main.py и /tmp/private/file.txt"

    redacted = redact_internal_paths(text)

    assert "/Users/k.anikaev" not in redacted
    assert "/tmp/private" not in redacted
    assert redacted.count("[redacted-path]") == 2
