#!/usr/bin/env python3
"""
Database migration helper for the RAG API.

Applies Alembic revisions defined under app/db/migrations/versions:

  0001_enable_pgvector          — enable pgvector extension + initial chunks table
  0002_documents_and_chunks     — documents table, reshape chunks (384-d, FK, HNSW)
  0003_conversations_messages   — conversations + messages for chat history

Prerequisites
-------------
1. Copy .env.example → .env and set DATABASE_URL
2. Install deps: poetry install
3. Database must be reachable (e.g. Supabase Postgres with permissions to
   CREATE EXTENSION / tables)

Usage
-----
  poetry run python scripts/migrate.py              # upgrade to head
  poetry run python scripts/migrate.py upgrade
  poetry run python scripts/migrate.py current
  poetry run python scripts/migrate.py history
  poetry run python scripts/migrate.py downgrade -1
  poetry run python scripts/migrate.py downgrade base
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_alembic(args: list[str]) -> int:
    cmd = [sys.executable, "-m", "alembic", *args]
    print(f"+ {' '.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Alembic migrations for rag-api (reads DATABASE_URL from .env).",
    )
    sub = parser.add_subparsers(dest="command")

    upgrade = sub.add_parser("upgrade", help="Apply migrations (default: head)")
    upgrade.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision (default: head)",
    )

    downgrade = sub.add_parser("downgrade", help="Roll back migrations")
    downgrade.add_argument(
        "revision",
        help="Target revision (e.g. -1, base, 0002_documents_and_chunks)",
    )

    sub.add_parser("current", help="Show the current database revision")
    sub.add_parser("history", help="Show migration history")
    sub.add_parser("heads", help="Show head revision(s)")

    # Default to upgrade head when no subcommand is given.
    parsed = parser.parse_args(argv)
    command = parsed.command or "upgrade"

    if command == "upgrade":
        revision = getattr(parsed, "revision", "head") or "head"
        return _run_alembic(["upgrade", revision])
    if command == "downgrade":
        return _run_alembic(["downgrade", parsed.revision])
    if command == "current":
        return _run_alembic(["current"])
    if command == "history":
        return _run_alembic(["history", "--verbose"])
    if command == "heads":
        return _run_alembic(["heads"])

    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
