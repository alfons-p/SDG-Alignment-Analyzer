"""Server-side folder ingest — shared by the CLI (scripts/batch_ingest.py) and
the Admin "Ingest a folder" button.

The browser only sends a command; the whole analysis loop runs here, on the
server, in a background thread. It's therefore tab-independent — the operator
can close the browser and reopen it to see progress. Reuses run_analysis_sync,
so every PDF is pool-isolated (bounded memory) with the per-file timeout, and
skips council-years that already have a completed analysis (resumable)."""

import hashlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from backend.app.dependencies import SessionLocal
from backend.app.models import Analysis, User
from backend.app.services.identity import parse_report_identity
from backend.app.services.analysis_service import run_analysis_sync, UPLOADS_DIR

log = logging.getLogger("batch_ingest")

# Optional safety fence: if set, an ingest --input must resolve under this dir.
INGEST_ROOT = os.getenv("INGEST_ROOT", "")


def _completed_exists(db, ident: dict) -> bool:
    if not (ident["year"] and ident["council_name"]):
        return False
    q = db.query(Analysis).filter(
        Analysis.status == "completed",
        Analysis.council_name == ident["council_name"],
        Analysis.year == ident["year"],
    )
    q = q.filter(Analysis.state == ident["state"]) if ident["state"] else q.filter(Analysis.state.is_(None))
    return db.query(q.exists()).scalar()


def resolve_folder(path: str) -> Path:
    """Validate a requested ingest folder. Raises FileNotFoundError / ValueError."""
    folder = Path(path).expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"Not a folder: {folder}")
    if INGEST_ROOT:
        root = Path(INGEST_ROOT).expanduser().resolve()
        if root not in folder.parents and folder != root:
            raise ValueError(f"Folder must be under {root}")
    return folder


# ── shared core ────────────────────────────────────────────────────────────


def ingest_folder(
    folder: Path,
    user_email: str,
    publish: bool,
    *,
    session_factory: Callable = SessionLocal,
    limit: int = 0,
    dry_run: bool = False,
    on_event: Optional[Callable[[str, dict, Optional[str]], None]] = None,
    should_cancel: Callable[[], bool] = lambda: False,
) -> dict:
    """Analyse every PDF under `folder` into the DB. `on_event(kind, counts,
    current)` is called on start/file/done/cancelled for progress reporting."""
    emit = on_event or (lambda *a: None)
    db = session_factory()
    try:
        user = db.query(User).filter(User.email == user_email.lower()).first()
        if not user:
            raise ValueError(f"owner {user_email!r} not found — register the account first")

        pdfs = sorted(folder.rglob("*.pdf"))
        if limit:
            pdfs = pdfs[:limit]
        counts = {"total": len(pdfs), "done": 0, "skipped": 0, "failed": 0}
        emit("start", counts, None)

        for i, p in enumerate(pdfs, 1):
            if should_cancel():
                emit("cancelled", counts, None)
                break
            emit("file", counts, p.name)
            ident = parse_report_identity(p.name)

            if _completed_exists(db, ident):
                counts["skipped"] += 1
                continue
            if dry_run:
                counts["done"] += 1
                continue

            try:
                content = p.read_bytes()
                h = hashlib.sha256(content).hexdigest()[:12]
                fp = UPLOADS_DIR / f"{p.stem}_{h}.pdf"
                fp.write_bytes(content)
                a = Analysis(
                    user_id=user.id, status="queued", original_filename=p.name,
                    file_path=str(fp), file_size=len(content), settings={},
                    council_name=ident["council_name"], state=ident["state"], year=ident["year"],
                )
                db.add(a)
                db.commit()
                db.refresh(a)
                run_analysis_sync(a.id, session_factory)
                db.refresh(a)
                if a.status == "completed":
                    counts["done"] += 1
                    if publish and not a.published:
                        a.published = True
                        db.commit()
                else:
                    counts["failed"] += 1
                    log.warning(f"ingest FAILED {p.name}: {(a.error_message or '').splitlines()[0][:160]}")
            except Exception as e:  # noqa: BLE001
                counts["failed"] += 1
                log.warning(f"ingest ERROR {p.name}: {type(e).__name__}: {e}")

        emit("done", counts, None)
        return counts
    finally:
        db.close()


# ── background job for the Admin endpoint ──────────────────────────────────

_state: dict[str, Any] = {
    "running": False, "total": 0, "done": 0, "skipped": 0, "failed": 0,
    "current": None, "path": None, "publish": False,
    "started_at": None, "finished_at": None, "error": None, "cancel": False,
}
_lock = threading.Lock()


def get_status() -> dict:
    with _lock:
        s = dict(_state)
    s.pop("cancel", None)
    return s


def request_cancel() -> bool:
    with _lock:
        if _state["running"]:
            _state["cancel"] = True
            return True
        return False


def _should_cancel() -> bool:
    with _lock:
        return _state["cancel"]


def _on_event(kind: str, counts: dict, current: Optional[str]) -> None:
    with _lock:
        _state.update(counts)
        _state["current"] = current


def start_ingest(path: str, user_email: str, publish: bool) -> None:
    """Validate + launch a background ingest. Raises if a run is already active
    or the folder is invalid."""
    folder = resolve_folder(path)  # raises before we mark running
    with _lock:
        if _state["running"]:
            raise RuntimeError("An ingest is already running")
        _state.update({
            "running": True, "total": 0, "done": 0, "skipped": 0, "failed": 0,
            "current": None, "path": str(folder), "publish": publish,
            "started_at": time.time(), "finished_at": None, "error": None, "cancel": False,
        })

    def _run():
        try:
            ingest_folder(folder, user_email, publish, on_event=_on_event, should_cancel=_should_cancel)
        except Exception as e:  # noqa: BLE001
            with _lock:
                _state["error"] = f"{type(e).__name__}: {e}"
            log.exception("ingest crashed")
        finally:
            with _lock:
                _state["running"] = False
                _state["finished_at"] = time.time()

    threading.Thread(target=_run, name="batch-ingest", daemon=True).start()
