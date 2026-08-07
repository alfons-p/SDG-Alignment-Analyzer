# Handoff: SDG Analyzer V2 — OCR fallback, role-based access, Aug-3 design reconciliation

**Generated**: 2026-08-07
**Branch**: V2 (even with origin/V2, all pushed through `052cdc7`)
**Status**: Ready for Review — no pending tasks

## Goal

V2 SDG Alignment Analyzer: FastAPI backend (`backend/app/`) + React/TS/Vite frontend (`frontend/src/`), deployed on macOS via 3 LaunchAgents + Cloudflare tunnel (public `sdg.alnura.app`, api `sdg-api.alnura.app`). This session: recover all failed PDFs via OCR, add a 4-tier access model, and reconcile the app with the Aug-3 design handoff.

## Completed

- [x] **OCR fallback** for image-only/scanned PDFs (`src/ocr_extractor.py`) — Tesseract via pytesseract, per-page merge (embedded text kept where real, OCR only image-only pages), content-addressed cache. Wired as rung 3 of the extraction ladder.
- [x] **Full dataset recovered**: failed analyses went **33 → 0**. DB = 1541 completed, all published, 0 duplicates, 0 failed.
- [x] **Admin ingest**: `replace` option + fixed duplicate-row accumulation (`_delete_identity_rows` supersedes prior rows for a council-year).
- [x] **4-tier authz**: anyone (public read) / registered (export) / officer (upload own council) / admin. Officer requests council at signup → admin approves → upload gated to matching `{state}+{council}`.
- [x] **Access page merged** with Aug-3 handoff: council picklist, role selector, name + position fields, "Request received" state, 10-char password.
- [x] **Landing**: "Latest" → "All years" (union across years); wired "The dataset"/"Findings" nav; brand → `/`.
- [x] **Council page**: "Compare with peers" + "How much this report described" density card.
- [x] Design handoff refreshed to Aug-3 bundle; app fully reconciled.

## Not Yet Done

Deferred security hardening (user chose "not now" — see `.claude/projects/.../memory/security-backlog.md`):
- [ ] **H1**: rate limiter keys on `request.client.host` (always `127.0.0.1` behind the tunnel) → one global bucket. Fix: key on `CF-Connecting-IP` header in `backend/app/routers/auth.py:_check_rate_limit`.
- [ ] **M1**: Vite dev server serves the public frontend — should serve `npm run build` static output.
- [ ] **M2**: `MAX_UPLOAD_BYTES=0` (unlimited) — set a cap in the backend LaunchAgent env.
- [ ] **M3**: `INGEST_ROOT` unset → admin browse spans whole home dir — set to `data/raw`.
- [ ] Cloudflare dashboard (user-side): Bot Fight Mode, `/api/*` rate rule, Security→Analytics.

Optional data cleanup (parked, not blocking):
- [ ] Nothing left failing. 3 councils that were bad source PDFs (Waverley/South Burnett/Three Springs) were replaced by the user and re-ingested successfully.

## Failed Approaches (Don't Repeat These)

- **OCR trigger on document-average chars/page** — misfired on mixed docs. Yarrabah (90pp) has 84 image-only pages but 6 dense text pages lifted the average to 138 cpp, clearing a 50-cpp gate, so OCR was skipped and it failed "no activities". **Fix**: trigger on the *fraction of image-only pages* (`<30 chars` + ≥1 image ≥ `OCR_PAGE_FRACTION=0.3`), not the average. See `ActivityExtractor._image_only_fraction`.
- **Chasing "JWT_SECRET not set — using insecure default" in logs** — that warning comes from **CLI/one-off Python processes** (batch_ingest, probes) that don't import the app's `EnvLoader`. The **running uvicorn backend loads `.env`** and has the real secret. Confirmed by forging a token with the dev secret against the live API → `401 Invalid token`. Do NOT assume the server uses the dev default.
- **Chasing exit code 138 on extraction scripts** — it's a **pre-existing native-teardown segfault** (torch/fitz/spaCy atexit), fires *after* all output, on both OCR and non-OCR paths. Harmless; in the pool the worker returns results via IPC before teardown and recycles. Not an OCR bug.
- **`git add -A` swept `backend/sdg_analyzer.db.bak-*` (424 MB) into a commit** → push rejected (>100 MB). Now gitignored (`backend/*.db.bak-*`). Don't stage DB backups.
- **`npx tsc --noEmit` is looser than `npm run build`** (`tsc -b`). Always verify the frontend with `npm run build`.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Admin role is NEVER stored on the user row | It's the `ADMIN_EMAILS` env allow-list, resolved by `effective_role()`. A DB write / stray ORM flush can't escalate to admin. `role` column only holds `registered`/`officer`. |
| Officer council via **picklist from dataset**, not free text | Guarantees the assignment matches a real council, so upload filename-match can't miss on a typo. |
| OCR **per-page merge** (not whole-doc) | Keeps sharper embedded text on good pages; OCRs only image-only pages. Faster + better on mixed docs (Paroo 49% good pages). |
| Subprocess pool with `maxtasksperchild` recycling + per-task timeout | Bounds a native memory leak and kills hung workers. `BATCH_TASK_TIMEOUT=900` (raised from 600 to cover OCR). |
| Skipped email verification / magic link | No mailer. Manual admin approval IS the "checked by hand against published council details" step. |

## Current State

**Working**: Everything. Backend `200`, all 3 LaunchAgents up, public site live. 1541 completed+published analyses. Auth tiers enforced and tested.

**Broken**: Nothing.

**Uncommitted Changes**: Only `.wolf/` OpenWolf session state (auto-tracked, ignore). App tree clean.

## Files to Know

| File | Why It Matters |
|------|----------------|
| `src/ocr_extractor.py` | OCR rung-3: Tesseract, per-page merge, SHA256 text cache |
| `src/activity_extractor.py` | Extraction ladder (fitz → pdfplumber → OCR); `_maybe_ocr` / `_image_only_fraction` gate the OCR |
| `backend/app/dependencies.py` | `effective_role`, `require_uploader`, `get_current_admin`, startup migrations (`_migrate_user_columns`) |
| `backend/app/routers/auth.py` | register (officer request, 10-char), `/me`, `_check_rate_limit` (H1 lives here) |
| `backend/app/routers/analysis.py` | `/upload` (officer council-match gate), admin officer endpoints, ingest |
| `backend/app/services/batch_ingest_service.py` | `ingest_folder` (+ `replace`, `_delete_identity_rows` dedup) |
| `frontend/src/pages/AccessPage.tsx` | Merged Access: picklist, role selector, name/position, Request-received |
| `frontend/src/pages/AdminPage.tsx` | Roles tab: officer approval queue + user table |
| `frontend/src/pages/LandingPage.tsx` | "All years" union logic + nav wiring (raw HTML string + d3) |

## Code Context

**Role resolution (backend, `dependencies.py`)** — admin is allow-list only:
```python
def effective_role(user: User) -> str:      # 'admin' | 'officer' | 'registered'
    if is_admin(user):                        # email in ADMIN_EMAILS env
        return "admin"
    return user.role if user.role in ("officer", "registered") else "registered"

def require_uploader(user) -> User:           # dependency on /upload
    if effective_role(user) not in ("officer", "admin"):
        raise HTTPException(403, "Uploading is limited to approved council officers.")
```

**Officer upload gate (`analysis.py:upload_pdf`)** — filename must match assignment:
```python
if effective_role(user) == "officer":
    fid = parse_report_identity(filename)     # {state, council_name, year}
    if fid["state"].upper() != user.assigned_state.upper() \
       or fid["council_name"].lower() != user.assigned_council.lower():
        raise HTTPException(403, "You can only upload reports for <assigned council>…")
```

**GET /api/auth/me** response:
```json
{ "id":"…","email":"…","name":"Jane Doe","position":"Sustainability Officer",
  "is_admin":false,"role":"registered","assigned_state":null,"assigned_council":null,
  "officer_request_pending":true,"requested_state":"WA","requested_council":"Carnamah" }
```

**POST /api/auth/register** body (officer path):
```json
{ "email":"…","password":"≥10 chars","name":"Jane Doe","request_officer":true,
  "state":"WA","council":"Carnamah","position":"Sustainability Officer" }
```

**Admin officer endpoints** (all `get_current_admin`):
`GET /api/analysis/admin/users` → `{users:[…], pending_officer_requests:[…]}`;
`POST /api/analysis/admin/users/{id}/approve-officer` | `/deny-officer` | `/revoke-officer`.

**OCR gate (`activity_extractor.py`)** — the non-obvious per-page logic:
```python
# OCR fires only when a large fraction of pages are image-only, NOT on doc average.
frac = self._image_only_fraction(pdf_path)   # pages with <30 chars AND ≥1 image
if frac >= self.ocr_page_fraction:            # default 0.3
    result = self._get_ocr_extractor().extract_text_from_pdf(pdf_path)
```

## Resume Instructions

1. **Restart backend after backend code changes** (LaunchAgent, picks up code + runs migrations):
   `launchctl kickstart -k gui/$(id -u)/com.sdg.backend` — wait for `curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/api/health` → `200`.
2. **Frontend**: Vite dev server (com.sdg.frontend) HMRs live. Before committing, verify: `cd frontend && npm run build` → expect `✓ built in …`.
3. **Run OCR tests**: `python -m pytest tests/test_ocr_extractor.py -q`
   - Expected: `5 passed` (~40s, runs real Tesseract on WA Carnamah).
   - If skipped: `tesseract` binary missing → `brew install tesseract`.
4. **Re-ingest a folder** (skips completed, OCRs image-only): `nohup python scripts/batch_ingest.py --input data/raw --publish > /tmp/ingest.log 2>&1 &` then watch for `BATCH DONE` in the log. Add `--replace` to re-run already-completed council-years.
5. **Get an admin token for testing** (you operate the server): read `JWT_SECRET` from `.env`, mint `jwt.encode({"sub": <alfonsp user id>, "exp": …}, secret, "HS256")`. There is no admin password.

## Setup Required

- Native dep: `tesseract` (`brew install tesseract`) for OCR. `pytesseract` in `requirements.txt`.
- Backend env (LaunchAgent `~/Library/LaunchAgents/com.sdg.backend.plist`): `ADMIN_EMAILS=alfonsp@gmail.com`, `CORS_ORIGINS` incl `https://sdg.alnura.app`. `JWT_SECRET` + `HF_TOKEN` come from `.env` (auto-loaded by `EnvLoader`).
- Admin account: `alfonsp@gmail.com` (only email in ADMIN_EMAILS = only admin).
- DB: SQLite `backend/sdg_analyzer.db`. Startup auto-migrates missing columns (idempotent ALTER TABLE).

## Edge Cases & Error Handling

- Upload wrong-council file as officer → `403` with the assigned council named.
- Registered user hits `/upload` (URL or nav) → `403` backend; frontend shows an "officers only" notice with pending-request state.
- Officer request before approval → account works for browse/export; upload stays `403` until admin approves.
- PDF with a text layer but no activity sentences (genuinely sparse prose, e.g. some councils) → still "No activities found"; OCR won't help (it has text). Not a bug.
- Re-ingesting a council-year: default skips if completed, re-runs if failed (deleting the stale failed row first); `--replace` re-runs + overwrites completed.

## Warnings

- **Do not "fix" the JWT_SECRET warning in logs** — server uses the real secret from `.env`; the warning is from CLI processes. (See Failed Approaches.)
- **Do not stage `backend/*.db.bak-*` or `backend/sdg_analyzer.db`** — gitignored; the .bak is 400+ MB.
- **`effective_role` result must never be written back to `user.role`** — a flush would persist `admin` into the DB. `/me` builds `UserResponse` explicitly to avoid this.
- **OCR is expensive but cached** — first pass on a 100-page scan is minutes; re-runs are seconds (SHA-keyed `.cache/ocr/`). Cache is gitignored.
- **exit 138 on extraction scripts is normal** teardown noise, not a failure.
- Public data endpoints filter `status='completed'`; failed/duplicate rows never leak publicly.
