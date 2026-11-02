import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("uvicorn.error")


def run_auto_migrations(engine: Engine):
    """
    Automatically and idempotently inspect database schema and add missing columns
    to the 'interview_sessions' table without dropping tables or losing any existing data.
    """
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        if "interview_sessions" not in table_names:
            return

        existing_columns = {col["name"] for col in inspector.get_columns("interview_sessions")}

        required_migrations = [
            ("evaluations", "VARCHAR NOT NULL DEFAULT '[]'"),
            ("answered_count", "INTEGER NOT NULL DEFAULT 0"),
            ("questions", "VARCHAR NOT NULL DEFAULT '[]'"),
            ("job_description", "TEXT"),
            ("interview_language", "VARCHAR DEFAULT 'English'"),
            ("resume_skills", "VARCHAR DEFAULT '[]'"),
            ("selected_skills", "VARCHAR DEFAULT '[]'"),
            ("source_context", "VARCHAR DEFAULT '[]'"),
            ("resume_profile", "VARCHAR DEFAULT '{}'"),
            ("adaptive_state", "VARCHAR DEFAULT '{}'"),
        ]

        with engine.begin() as conn:
            for col_name, col_def in required_migrations:
                if col_name not in existing_columns:
                    logger.info("Auto-migration: Adding missing column '%s' to 'interview_sessions'", col_name)
                    conn.execute(text(f"ALTER TABLE interview_sessions ADD COLUMN {col_name} {col_def}"))
                    print(f"[AUTO-MIGRATION] Added column '{col_name}' to 'interview_sessions'.")
                else:
                    print(f"[AUTO-MIGRATION] Column '{col_name}' already exists.")

    except Exception as e:
        logger.error("Auto-migration failed: %s", str(e), exc_info=True)
