import os
import sqlite3

db_paths = ["sql_app.db", "../sql_app.db", "backend/sql_app.db"]

for db_path in db_paths:
    if os.path.exists(db_path):
        print(f"\n--- Migrating {os.path.abspath(db_path)} ---")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(interview_sessions)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_cols}")

        migrations = [
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

        for col_name, col_def in migrations:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE interview_sessions ADD COLUMN {col_name} {col_def}")
                print(f"  + Added '{col_name}' column")
            else:
                print(f"  - '{col_name}' column already exists")

        conn.commit()

        cursor.execute("PRAGMA table_info(interview_sessions)")
        final_cols = [row[1] for row in cursor.fetchall()]
        print(f"Final columns ({len(final_cols)}): {final_cols}")
        conn.close()

print("\nAll database migrations complete!")
