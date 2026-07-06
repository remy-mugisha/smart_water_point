# System Audit — Smart Water Point Monitoring System (Rwanda)
**Date:** 2026-07-06 | **Branch:** main | **Scope:** Full codebase review prior to building the Reporting & Analytics module

---

## 1. Application Structure

| Item | Status |
|---|---|
| Factory pattern (`app/__init__.py`) | ✓ EXISTS — `create_app()`, extensions: SQLAlchemy, Migrate, Login, CSRFProtect |
| Blueprints | ✓ EXISTS — `auth`, `admin`, `dashboard`, `api`, `tasks`, `notifications` (6 total) |
| Config | ⚠ PARTIAL — single `Config` class, no Dev/Test/Prod split; only `SECRET_KEY`/`DATABASE_URL`/`SESSION_COOKIE_SECURE` from env |
| Static assets | ⚠ MINIMAL — one CSS file (147 lines), one JS file (38 lines, actually map code mislabeled "dashboard.js") |

**No `.env` mail config exists** — relevant since reports may want to be emailed.

---

## 2. Database Models (`app/models.py`, 205 lines)

**7 tables exist today:** `User`, `WaterPoint`, `MaintenanceVisit`, `MaintenanceTask`, `TaskStatusHistory`, `Notification`, `AuditLog`.

| Requested table | Status |
|---|---|
| `maintenance_records` | ✗ MISSING (closest analogs: `maintenance_visits` — **dead/unused**, and `maintenance_tasks` — active) |
| `report_logs` | ✗ MISSING |
| `technician_performance` | ✗ MISSING (derivable from `maintenance_tasks` + `task_status_history`, no dedicated table) |
| `system_settings` | ✗ MISSING (template stub exists, zero backing data) |
| `validation_logs` | ✗ MISSING |

**Key finding:** `MaintenanceVisit` (models.py:103-121) has **zero write call-sites anywhere** in the app — it's dead legacy data from the original scaffold. All real maintenance activity now flows through `MaintenanceTask` + `TaskStatusHistory`, which is a good audit trail for resolution-time metrics.

**Migration gap:** Only one Alembic revision exists (`90489408fe07`, creates `maintenance_tasks`/`task_status_history` only). `users`, `water_points`, `maintenance_visits`, `notifications`, `audit_logs` were never migrated — they exist only via `db.create_all()` in `run.py`. New reporting tables need real migrations, and this pre-existing gap should eventually be backfilled.

---

## 3. API Endpoints (`app/api.py`, 93 lines)

| Route | Method | Auth | Purpose |
|---|---|---|---|
| `/api/water-points` | GET | login_required | List, district-scoped |
| `/api/water-points/<id>/status` | PUT | role: admin/technician/manager | Direct status edit (bypasses task workflow) |
| `/api/upload` | POST | role-gated | CSV/XLSX ingestion |
| `/api/predict` | POST | **login_required only — no role check** ⚠ | ML prediction |

**No aggregation/stats/reporting endpoint exists at all.**

---

## 4. Dashboard (`app/dashboard.py`, 161 lines)

- Status counts computed **in Python** over fully-fetched rows (lines 22-28), not SQL `GROUP BY` — fine at current scale, won't scale for cross-district reports.
- Template renders 5 stat-cards only. **No chart, no canvas, no charting library anywhere in the repo** (confirmed via full-text grep for "chart" — zero hits).
- `static/js/dashboard.js` is actually Leaflet map-rendering code, not dashboard logic.

---

## 5. Task Assignment & Notifications

✓ **Fully built, well-tested state machine** — `tasks.py` (299 lines): pending → assigned → accepted → in_progress → completed → verified, each transition recorded to `TaskStatusHistory` + `AuditLog` + in-app `Notification`. District-scoped. Covered by `tests/test_tasks.py` (9 passing tests, full lifecycle + negative cases).

This is the best raw material for the **Technician Performance** and **Maintenance** reports — no new instrumentation needed, just aggregation queries.

---

## 6. Reporting / Export Functionality

**100% MISSING.** Exhaustive repo-wide grep confirms:
- No `reportlab`, `weasyprint`, `pdfkit`, `xlsxwriter`, `to_excel`, `to_csv`, `send_file` anywhere.
- No route, template, or model with "report" in the name.
- `openpyxl` is a dependency but only used for **reading** uploads, never writing.

This is a fully greenfield build — nothing to avoid duplicating.

---

## 7. Auth & RBAC

**Roles:** `admin`, `district_technician`, `district_manager`, `viewer` (default).

**Gaps found:**
1. `/api/predict` has no role decorator (any logged-in user, including viewer, can trigger ML runs).
2. `district_match_required` decorator (utils.py:57) is defined but **never called anywhere** — dead code.
3. District-scoping logic (`scoped_water_points`, `scoped_tasks`, inline API ternaries) is duplicated 3+ times with no shared helper — a reporting module needs a 4th scoped-query pattern; worth consolidating into one helper instead.
4. No distinct "can export raw data" permission — only 4 roles total.

---

## 8. Frontend/UI

- CSS custom properties define a teal-blue theme (`--primary:#0f6f8f`). `.stat-card`/`.stats-grid` is a reusable KPI-tile pattern already in use on 2 pages.
- Bootstrap 5.3 + Font Awesome + Leaflet all loaded from **CDN only** — no local vendoring. This matters for server-side PDF generation, which can't reach a CDN mid-render.
- `templates/admin/users.html` and most tables have **no search, sort, filter, or pagination** — only `audit_logs.html` paginates (the one precedent to copy).
- Single-block nav in `base.html`, one-line addition needed for a "Reports" menu item.

---

## 9. Tests

208 lines total. Solid coverage of the task lifecycle and CSRF/API security. **Zero coverage** of `auth.py`, `admin.py`, `dashboard.py`, or most of `api.py`.

---

## 10. Dependencies (`requirements.txt`)

Present: Flask stack, pandas/numpy/scikit-learn/joblib (ML), openpyxl (read-only today), gunicorn, pytest.
**Missing for this task:** any PDF library, `xlsxwriter` (openpyxl can write too, so not strictly required), any caching layer for aggregation-heavy report queries.

---

## Bottom line

| Capability | Verdict |
|---|---|
| Reporting module (5 report types) | Build from scratch — nothing to reuse but the underlying data model |
| Charts | Build from scratch — introduce Chart.js (fits the existing Bootstrap/CDN pattern) |
| PDF/Excel/Print export | Build from scratch — pick a PDF lib, reuse `openpyxl` for Excel |
| Data sources | **Good news:** `MaintenanceTask` + `TaskStatusHistory` + `WaterPoint` + `User` already carry everything needed for reports #1-4. Only report #5 (District/Sector Summary) is a straightforward `GROUP BY` on existing `WaterPoint` fields. No new "performance" or "report_logs" tables are strictly required — they can be computed on the fly from existing tables, though a `report_logs` audit table (who generated what report, when) is worth adding for the "Generated By" requirement. |
| UI baseline | Usable design tokens exist; needs pagination/search/sort added consistently and a real charting layer |
