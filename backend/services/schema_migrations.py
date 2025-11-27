"""
Lightweight schema migrations for SQLite to keep the application working
without requiring Alembic. These run on application startup after
`db.create_all()` and add any newly required columns if they are missing.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from models import db


def _column_missing(connection: Connection, table_name: str, column_name: str) -> bool:
    inspector = inspect(connection)
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name not in columns


def _ensure_column(
    connection: Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    if _column_missing(connection, table_name, column_name):
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def run_schema_migrations() -> None:
    """Perform idempotent schema updates required by the application."""
    engine = db.engine
    with engine.connect() as connection:
        _ensure_column(connection, "chat_threads", "title", "VARCHAR(255)")
        _ensure_column(connection, "chat_threads", "auto_title", "VARCHAR(255)")
        _ensure_column(connection, "chat_threads", "last_message_at", "DATETIME")

        # Backfill new columns with sensible defaults
        connection.execute(
            text(
                """
                UPDATE chat_threads
                SET last_message_at = COALESCE(last_message_at, updated_at, created_at)
                WHERE last_message_at IS NULL
                """
            )
        )

