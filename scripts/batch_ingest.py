"""Server-side batch ingest (CLI).

Analyse a folder of council annual-report PDFs directly into the app database —
no browser, no per-file HTTP, no Cloudflare tunnel. Same engine as the Admin
"Ingest a folder" button (backend/app/services/batch_ingest_service.py).

- Resumable / idempotent — skips council-years that already have a completed
  analysis; re-run continues where it stopped.
- Memory-bounded — each PDF runs in the recycling worker subprocess with the
  per-file timeout.
- Detachable — run under `nohup … &`; it doesn't depend on any tab.

Usage:
    python scripts/batch_ingest.py --input /path/to/pdf/folder
    python scripts/batch_ingest.py --input data/raw --publish
    python scripts/batch_ingest.py --input data/raw --limit 5
    python scripts/batch_ingest.py --input data/raw --dry-run
    nohup python scripts/batch_ingest.py --input data/raw --publish > /tmp/ingest.log 2>&1 &
"""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.dependencies import ADMIN_EMAILS  # noqa: E402
from backend.app.services.batch_ingest_service import ingest_folder, resolve_folder  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("batch_ingest")


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyse a folder of council report PDFs into the app DB.")
    ap.add_argument("--input", required=True, help="folder of PDFs (searched recursively)")
    ap.add_argument("--user", default=None, help="owner email (default: first ADMIN_EMAILS, else alfonsp@gmail.com)")
    ap.add_argument("--publish", action="store_true", help="mark each analysis published as it completes")
    ap.add_argument("--limit", type=int, default=0, help="process at most N files (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="list what would be analysed/skipped, do nothing")
    args = ap.parse_args()

    try:
        folder = resolve_folder(args.input)
    except (FileNotFoundError, ValueError) as e:
        log.error(str(e))
        return 2

    email = (args.user or (sorted(ADMIN_EMAILS)[0] if ADMIN_EMAILS else None) or "alfonsp@gmail.com").lower()
    t0 = time.time()

    def on_event(kind: str, counts: dict, current):
        if kind == "start":
            log.info(f"{counts['total']} PDFs under {folder} · owner={email} · publish={args.publish} · dry_run={args.dry_run}")
        elif kind == "done":
            log.info(f"BATCH DONE: {counts['done']} analysed, {counts['skipped']} skipped, {counts['failed']} failed of {counts['total']}")
        elif kind == "cancelled":
            log.info("cancelled")
        elif kind == "file":
            processed = counts["done"] + counts["skipped"] + counts["failed"]
            if processed and processed % 10 == 0:
                rate = processed / max(1e-9, time.time() - t0)
                log.info(f"[{processed}/{counts['total']}] done={counts['done']} skipped={counts['skipped']} failed={counts['failed']} · {rate * 60:.1f} files/min")

    try:
        ingest_folder(folder, email, args.publish, limit=args.limit, dry_run=args.dry_run, on_event=on_event)
    except ValueError as e:
        log.error(str(e))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
