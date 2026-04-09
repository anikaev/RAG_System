from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


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
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

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
