"""Apply pending SQL migrations from db/migrations/, in filename order."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def applied_versions(conn: psycopg.Connection) -> set[str]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url) as conn:
        applied = applied_versions(conn)
        conn.commit()

        pending = sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.stem not in applied)
        if not pending:
            print("No pending migrations.")
            return

        for path in pending:
            print(f"Applying {path.name} ...")
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,)
                )
            print(f"Applied {path.name}")


if __name__ == "__main__":
    main()
