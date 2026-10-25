import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

STATUSES = ("saved", "preparing", "applied", "interview", "offer", "rejected", "withdrawn")


class LocalStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / "career.sqlite3"
        self.db = sqlite3.connect(path)
        path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL CHECK(kind IN ('profile','job','application')),
                url TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS snapshot_resource ON snapshots(kind, url, id DESC);
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY,
                job_url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN (
                    'saved','preparing','applied','interview','offer','rejected','withdrawn'
                )),
                notes TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS application_events (
                id INTEGER PRIMARY KEY,
                application_id INTEGER NOT NULL REFERENCES applications(id),
                status TEXT NOT NULL,
                notes TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
        """)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.db.close()

    def snapshot(self, kind: str, content: dict) -> dict:
        captured_at = datetime.now(UTC).isoformat()
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO snapshots(kind,url,captured_at,content) VALUES(?,?,?,?)",
                (kind, content["url"], captured_at, json.dumps(content, ensure_ascii=False)),
            )
        return {"snapshot_id": cursor.lastrowid, "captured_at": captured_at, **content}

    def track(self, job_url: str, status: str, notes: str | None = None) -> dict:
        if status not in STATUSES:
            raise ValueError("Estado de candidatura desconocido.")
        job = self.db.execute(
            "SELECT content FROM snapshots WHERE kind='job' AND url=? ORDER BY id DESC LIMIT 1",
            (job_url,),
        ).fetchone()
        if job is None:
            raise ValueError("Primero captura la vacante con capture-job --url.")
        content = json.loads(job["content"])
        timestamp = datetime.now(UTC).isoformat()
        with self.db:
            cursor = self.db.execute(
                """INSERT INTO applications(job_url,title,company,status,notes,updated_at)
                   VALUES(?,?,?,?,?,?) ON CONFLICT(job_url) DO UPDATE SET
                   title=excluded.title, company=excluded.company, status=excluded.status,
                   notes=COALESCE(?,applications.notes), updated_at=excluded.updated_at
                   RETURNING *""",
                (job_url, content["title"], content["company"], status, notes or "", timestamp, notes),
            )
            application = dict(cursor.fetchone())
            self.db.execute(
                """INSERT INTO application_events(application_id,status,notes,recorded_at)
                   VALUES(?,?,?,?)""",
                (application["id"], status, application["notes"], timestamp),
            )
        return application

    def applications(self, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM applications"
        parameters = ()
        if status:
            query += " WHERE status=?"
            parameters = (status,)
        return [dict(row) for row in self.db.execute(
            query + " ORDER BY updated_at DESC, id DESC", parameters
        )]
