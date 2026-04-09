from __future__ import annotations


def clean_document_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    lines = [line.strip() for line in normalized.splitlines()]

    cleaned_lines: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if previous_blank:
                continue
            previous_blank = True
            cleaned_lines.append("")
            continue

        previous_blank = False
        cleaned_lines.append(" ".join(line.split()))

    return "\n".join(cleaned_lines).strip()
