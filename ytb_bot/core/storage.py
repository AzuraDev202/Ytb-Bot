"""Durable application tables, independent of Excel files and UI sessions."""
from contextlib import contextmanager
import datetime as dt
import json
from pathlib import Path
import sqlite3


class WorkspaceStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY, created TEXT NOT NULL, status TEXT NOT NULL,
                    keywords TEXT NOT NULL, rows TEXT NOT NULL, error TEXT NOT NULL DEFAULT ''
                );
            """)

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def keywords(self):
        with self._connection() as db:
            row = db.execute("SELECT value FROM settings WHERE name='keywords'").fetchone()
        return row[0] if row else "AI Automation\nAI Agent\ntạo video bằng AI"

    def save_keywords(self, text):
        if not isinstance(text, str) or len(text) > 2_000_000:
            raise ValueError("Danh sách từ khóa không hợp lệ hoặc quá lớn.")
        with self._connection() as db:
            db.execute("INSERT INTO settings VALUES ('keywords', ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (text,))
        return text

    def begin_run(self, keywords):
        with self._connection() as db:
            cursor = db.execute("INSERT INTO runs(created,status,keywords,rows) VALUES (?,?,?,?)",
                                (dt.datetime.now(dt.timezone.utc).isoformat(), "running", json.dumps(keywords, ensure_ascii=False), "[]"))
            return cursor.lastrowid

    def save_run(self, run_id, status, rows, error=""):
        with self._connection() as db:
            db.execute("UPDATE runs SET status=?, rows=?, error=? WHERE id=?",
                       (status, json.dumps(rows, ensure_ascii=False), error, run_id))

    def runs(self):
        with self._connection() as db:
            records = db.execute("SELECT id,created,status,json_array_length(rows) AS count,error FROM runs ORDER BY id DESC").fetchall()
        return [dict(row) for row in records]

    def result(self, run_id=None):
        with self._connection() as db:
            row = db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1" if run_id is None else "SELECT * FROM runs WHERE id=?",
                             () if run_id is None else (int(run_id),)).fetchone()
        if row is None:
            raise ValueError("Chưa có lượt quét. Hãy bắt đầu khám phá trước.")
        return {**dict(row), "rows": json.loads(row["rows"]), "keywords": json.loads(row["keywords"])}
