import sqlite3
import datetime
from pathlib import Path
from typing import Tuple, List, Optional


class JobDatabase:
    def __init__(self, db_path: str = "job_state.db", read_only: bool = False):
        self.db_path = db_path
        if read_only and Path(db_path).is_file():
            self.conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
        else:
            if not read_only and db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(":memory:" if read_only else db_path)
            self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(company, job_id)
                )
            """)

    def is_seen(self, company: str, job_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM seen_jobs WHERE company = ? AND job_id = ?",
            (company, job_id)
        )
        return cursor.fetchone() is not None

    def mark_seen(self, company: str, job_id: str, title: str, url: str) -> bool:
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO seen_jobs (company, job_id, title, url, first_seen_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (company, job_id, title, url, datetime.datetime.now(datetime.timezone.utc).isoformat())
                )
            return True
        except sqlite3.IntegrityError:
            # Job already recorded
            return False

    def get_seen_count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM seen_jobs")
        row = cursor.fetchone()
        return row[0] if row else 0

    def close(self):
        if self.conn:
            self.conn.close()
