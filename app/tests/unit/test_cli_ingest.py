from __future__ import annotations

import json
import sys
from pathlib import Path

from cli.client import main


def test_cli_ingest_kb_dry_run_outputs_report(monkeypatch, capsys):
    seed_path = Path(__file__).resolve().parents[2] / "kb" / "seed"
    monkeypatch.setattr(
        sys,
        "argv",
        ["rag-cli", "ingest-kb", "--seed-path", str(seed_path), "--dry-run"],
    )

    main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["document_count"] == 2
    assert payload["chunk_count"] >= 2
