"""Server-side batch ingest.

Analyse a folder of council annual-report PDFs directly into the app database —
no browser, no per-file HTTP, no Cloudflare tunnel. This is the robust path for
large batches (hundreds to thousands of files); the browser uploader is for
ad-hoc handfuls.

Properties:
- **Resumable / idempotent** — skips any council-year that already has a
  completed analysis (same skip-if-exists rule as the web upload). Re-run it and
  it continues where it stopped; failed/interrupted files are retried.
- **Memory-bounded** — reuses `run_analysis_sync`, so every PDF is processed in
  the recycling worker subprocess (RSS stays flat) with the per-file timeout.
- **Detachable** — run under `nohup … &`; it doesn't depend on any tab.

Usage:
    python scripts/batch_ingest.py --input /path/to/pdf/folder
    python scripts/batch_ingest.py --input data/raw --publish        # publish as it goes
    python scripts/batch_ingest.py --input data/raw --limit 5        # test a few
    python scripts/batch_ingest.py --input data/raw --dry-run        # show plan only

    # unattended, survives terminal close, logs to a file:
    nohup python scripts/batch_ingest.py --input data/raw --publish > /tmp/ingest.log 2>&1 &
"""

import argparse
import hashlib
import logging
import sys
import time
from pathlib import Path

# Make the project root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.dependencies import SessionLocal, ADMIN_EMAILS  # noqa: E402
from backend.app.models import Analysis, User  # noqa: E402
from backend.app.services.identity import parse_report_identity  # noqa: E402
from backend.app.services.analysis_service import run_analysis_sync, UPLOADS_DIR  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("batch_ingest")


def _completed_exists(db, ident: dict) -> bool:
    """True if this user already has a completed analysis for the same
    council-year (skip only when identity is strong enough to dedup)."""
    if not (ident["year"] and ident["council_name"]):
        return False
    q = db.query(Analysis).filter(
        Analysis.status == "completed",
        Analysis.council_name == ident["council_name"],
        Analysis.year == ident["year"],
    )
    q = q.filter(Analysis.state == ident["state"]) if ident["state"] else q.filter(Analysis.state.is_(None))
    return db.query(q.exists()).scalar()


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyse a folder of council report PDFs into the app DB.")
    ap.add_argument("--input", required=True, help="folder of PDFs (searched recursively)")
    ap.add_argument("--user", default=None, help="owner email (default: first ADMIN_EMAILS, else alfonsp@gmail.com)")
    ap.add_argument("--publish", action="store_true", help="mark each analysis published as it completes")
    ap.add_argument("--limit", type=int, default=0, help="process at most N files (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="list what would be analysed/skipped, do nothing")
    args = ap.parse_args()

    folder = Path(args.input)
    if not folder.is_dir():
        log.error(f"--input is not a folder: {folder}")
        return 2

    db = SessionLocal()

    email = (args.user or (sorted(ADMIN_EMAILS)[0] if ADMIN_EMAILS else None) or "alfonsp@gmail.com").lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        log.error(f"owner {email!r} not found — pass --user with a registered account email")
        return 2

    pdfs = sorted(folder.rglob("*.pdf"))
    if args.limit:
        pdfs = pdfs[: args.limit]
    log.info(f"{len(pdfs)} PDFs under {folder} · owner={email} · publish={args.publish} · dry_run={args.dry_run}")

    done = skipped = failed = 0
    t0 = time.time()
    for i, p in enumerate(pdfs, 1):
        ident = parse_report_identity(p.name)
        tag = f"[{i}/{len(pdfs)}] {p.name}"

        if _completed_exists(db, ident):
            skipped += 1
            continue

        if args.dry_run:
            log.info(f"{tag} → would analyse ({ident['council_name']} · {ident['state']} · {ident['year']})")
            done += 1
            continue

        try:
            content = p.read_bytes()
            h = hashlib.sha256(content).hexdigest()[:12]
            fp = UPLOADS_DIR / f"{p.stem}_{h}.pdf"
            fp.write_bytes(content)
            a = Analysis(
                user_id=user.id,
                status="queued",
                original_filename=p.name,
                file_path=str(fp),
                file_size=len(content),
                settings={},
                council_name=ident["council_name"],
                state=ident["state"],
                year=ident["year"],
            )
            db.add(a)
            db.commit()
            db.refresh(a)
            aid = a.id

            run_analysis_sync(aid, SessionLocal)  # pool-isolated, blocks until done/failed

            db.refresh(a)
            if a.status == "completed":
                done += 1
                if args.publish and not a.published:
                    a.published = True
                    db.commit()
            else:
                failed += 1
                log.warning(f"{tag} → FAILED: {(a.error_message or '').splitlines()[0][:160]}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            log.warning(f"{tag} → ERROR: {type(e).__name__}: {e}")

        if i % 10 == 0 or i == len(pdfs):
            rate = i / max(1e-9, time.time() - t0)
            log.info(f"{tag} · done={done} skipped={skipped} failed={failed} · {rate * 60:.1f} files/min")

    log.info(f"BATCH DONE: {done} analysed, {skipped} skipped, {failed} failed of {len(pdfs)}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
