import sqlite3
import datetime
from typing import Tuple, List, Optional


class JobDatabase:
    def __init__(self, db_path: str = "job_state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
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
