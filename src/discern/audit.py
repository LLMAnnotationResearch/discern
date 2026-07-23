"""Audit trail: append an atomic JSONL event for every LLM request/response/failure the moment it
happens, and persist each pipeline stage atomically with a manifest. An interruption then loses
nothing already computed (the reviewer's P1: the legacy harness only flushed its call log at the
end). Thread-safe: appends are serialized under a lock, each a single write() of one line.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path


class Audit:
    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.run_dir / "events.jsonl"
        self._lock = threading.Lock()
        # continue the event counter across a resume (don't restart at 0 -> duplicate IDs)
        self._counter = 0
        if self.events_path.exists():
            with open(self.events_path) as f:
                self._counter = sum(1 for _ in f)

    def event(self, stage: str, kind: str, **fields) -> None:
        """Append one event atomically. kind is e.g. request|response|failure|note.
        Called around every LLM call, including failures, before anything else proceeds."""
        with self._lock:
            self._counter += 1
            rec = {"i": self._counter, "wall": round(time.time(), 3), "stage": stage, "kind": kind}
            rec.update(fields)
            line = json.dumps(rec, default=str) + "\n"
            # single append write; flush + fsync so an interruption keeps the line
            with open(self.events_path, "a") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())

    def write_stage(self, name: str, obj, status: str = "complete") -> Path:
        """Persist a stage artifact atomically (write temp, then rename) with a status manifest.
        A stage file only appears once fully written — a partial run never yields a truncated JSON."""
        path = self.run_dir / f"{name}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(obj, indent=2, default=str))
        os.replace(tmp, path)
        # update the manifest of completed stages
        man_path = self.run_dir / "manifest.json"
        man = json.loads(man_path.read_text()) if man_path.exists() else {"stages": []}
        man["stages"] = [s for s in man["stages"] if s["name"] != name]
        man["stages"].append({"name": name, "status": status, "wall": round(time.time(), 3)})
        man_tmp = man_path.with_suffix(".json.tmp")
        man_tmp.write_text(json.dumps(man, indent=2, default=str))
        os.replace(man_tmp, man_path)
        return path

    def load_stage(self, name: str):
        """Return a previously completed stage artifact, or None (used for resume)."""
        path = self.run_dir / f"{name}.json"
        return json.loads(path.read_text()) if path.exists() else None
