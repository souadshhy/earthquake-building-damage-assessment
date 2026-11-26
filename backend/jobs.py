"""Persistent serial jobs with exclusive ownership of runtime storage."""
from datetime import datetime, timezone
from contextlib import contextmanager
import importlib
import logging
import os
from pathlib import Path
import sqlite3
from threading import Event, Thread
import uuid

from quake.io import read_json, write_json
from .results import build_results

LOG = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc).isoformat()


def configured_inference():
    target = os.environ.get("QUAKE_INFERENCE", "")
    if not target:
        return None, "Student 2's trained inference provider is not configured"
    try:
        module, name = target.split(":", 1)
        provider = getattr(importlib.import_module(module), name)
        if not callable(provider):
            raise ValueError("Provider must be callable")
        provider.check_ready()
        return provider, None
    except Exception as exc:
        LOG.exception("Inference provider unavailable")
        return None, f"Inference provider unavailable: {exc}"


class Jobs:
    def __init__(self, root, inference):
        self.root = Path(root)
        self.inference = inference
        self.stop_event = Event()
        self.wake = Event()
        self.thread = None
        self.lock = None

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.root / "jobs.sqlite3", timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def start(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = (self.root / "worker.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.lock.seek(0)
                if not self.lock.read(1):
                    self.lock.write(b"0")
                    self.lock.flush()
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            self.lock = None
            raise RuntimeError("This job directory already has an active backend worker")
        try:
            with self.connect() as connection:
                connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, pair_id TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT,
                    model_version TEXT)""")
                connection.execute("UPDATE jobs SET status='failed', error=?, updated_at=? WHERE status='running'",
                                   ("Inference was interrupted by a service restart; submit a new job", now()))
            self.thread = Thread(target=self.run, name="inference-worker", daemon=True)
            self.thread.start()
        except Exception:
            self.close()
            raise

    def close(self):
        self.stop_event.set()
        self.wake.set()
        if self.thread:
            self.thread.join()
        if self.lock:
            self.lock.close()
            self.lock = None

    def create(self, pair, job_id=None):
        job_id = job_id or uuid.uuid4().hex
        directory = self.root / job_id
        directory.mkdir(parents=True, exist_ok=True)
        write_json(directory / "input.json", pair)
        timestamp = now()
        with self.connect() as connection:
            connection.execute("INSERT INTO jobs VALUES (?, ?, 'queued', ?, ?, NULL, NULL)",
                               (job_id, pair["pair_id"], timestamp, timestamp))
        self.wake.set()
        return {"job_id": job_id, "pair_id": pair["pair_id"], "status": "queued",
                "created_at": timestamp, "updated_at": timestamp, "error": None, "model_version": None}

    def get(self, job_id):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def run(self):
        while not self.stop_event.is_set():
            self.wake.clear()
            if self.inference is None:
                self.wake.wait(1)
                continue
            with self.connect() as connection:
                row = connection.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at, job_id LIMIT 1").fetchone()
                if row:
                    connection.execute("UPDATE jobs SET status='running', updated_at=? WHERE job_id=?", (now(), row["job_id"]))
            if row is None:
                self.wake.wait(1)
                continue
            job_id = row["job_id"]
            directory = self.root / job_id
            try:
                pair = read_json(directory / "input.json")
                output = self.inference(pair)
                result = build_results(job_id, pair, output, directory)
                with self.connect() as connection:
                    connection.execute("UPDATE jobs SET status='completed', model_version=?, updated_at=? WHERE job_id=?",
                                       (result["model_version"], now(), job_id))
            except Exception as exc:
                LOG.exception("Job %s failed", job_id)
                with self.connect() as connection:
                    connection.execute("UPDATE jobs SET status='failed', error=?, updated_at=? WHERE job_id=?",
                                       (f"Inference failed: {exc}", now(), job_id))
