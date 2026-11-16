"""Local records and a process lock shared by the desktop and CLI."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"uploads": {}, "plan": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("uploads"), dict):
        raise ValueError("Invalid upload state. Restore a backup; do not delete the history.")
    state.setdefault("plan", {})
    if not isinstance(state["plan"], dict):
        raise ValueError("Invalid reserved plan in upload state.")
    for record in state["uploads"].values():
        if not isinstance(record, dict) or not record.get("video_id"):
            raise ValueError("Incomplete upload record. Reconcile its YouTube ID before continuing.")
    return state


def save_state(path: Path, state: dict) -> None:
    write_private(path, json.dumps(state, ensure_ascii=False, indent=2))


@contextmanager
def state_lock(path: Path):
    """OS releases the lock even if the process crashes; keep the lock file."""
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError("Another publisher is using this state file.") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
