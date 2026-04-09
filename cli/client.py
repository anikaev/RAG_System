from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import httpx

from app.core.config import Settings
from app.db.bootstrap import seed_knowledge_chunks
from app.db.session import DatabaseSessionManager
from app.kb.ingest import build_ingestion_report, build_seed_chunks
from app.providers.factory import build_embedding_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI demo client for RAG Tutor API")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RAG_API_URL", "http://127.0.0.1:8000"),
        help="API base URL",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check API health")

    chat_parser = subparsers.add_parser("chat", help="Send a tutoring message")
    chat_parser.add_argument("message", help="User message")
    chat_parser.add_argument("--session-id", default=None)
    chat_parser.add_argument("--user-id", default="cli-user")

    code_parser = subparsers.add_parser("code-check", help="Validate Python code")
    code_parser.add_argument("--code", default=None, help="Inline code snippet")
    code_parser.add_argument("--file", default=None, help="Path to Python file")
    code_parser.add_argument("--session-id", default=None)
    code_parser.add_argument("--user-id", default="cli-user")

    ingest_parser = subparsers.add_parser("ingest-kb", help="Prepare or import knowledge chunks")
    ingest_parser.add_argument("--seed-path", default="app/kb/seed")
    ingest_parser.add_argument(
        "--database-url",
        default=os.environ.get("RAG_POSTGRES_URL"),
        help="Optional database URL for importing chunks",
    )
    ingest_parser.add_argument("--bootstrap-schema", action="store_true")
    ingest_parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ingest-kb":
        seed_path = Path(args.seed_path)
        chunks = build_seed_chunks(seed_path)
        report = build_ingestion_report(chunks)

        if args.dry_run or not args.database_url:
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
            return

        settings = Settings(
            postgres_url=args.database_url,
            seed_demo_data_on_startup=False,
            database_bootstrap_schema=args.bootstrap_schema,
        )
        db_manager = DatabaseSessionManager(settings)
        if args.bootstrap_schema:
            db_manager.create_schema()
        imported = seed_knowledge_chunks(
            db_manager,
            seed_path,
            embedding_provider=build_embedding_provider(settings),
            chunk_size_chars=settings.kb_chunk_size_chars,
            overlap_paragraphs=settings.kb_chunk_overlap_paragraphs,
        )
        payload = asdict(report)
        payload["imported_chunks"] = imported
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    with httpx.Client(base_url=args.base_url, timeout=10.0) as client:
        if args.command == "health":
            response = client.get("/health")
        elif args.command == "chat":
            response = client.post(
                "/v1/chat/respond",
                json={
                    "session_id": args.session_id,
                    "user_id": args.user_id,
                    "message": args.message,
                },
            )
        else:
            code = args.code
            if args.file:
                code = Path(args.file).read_text(encoding="utf-8")
            if not code:
                raise SystemExit("Provide --code or --file for code-check.")

            response = client.post(
                "/v1/code/check",
                json={
                    "session_id": args.session_id,
                    "user_id": args.user_id,
                    "language": "python",
                    "code": code,
                },
            )

    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
