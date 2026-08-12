# Amazi — RWB Water Intelligence — System Explanation

**Case Study:** Bugesera District, Rwanda (generalizes to 5 districts: Nyagatare, Bugesera, Gatsibo, Kayonza, Rwamagana)
**Audience:** WASAC technicians and district water officers
**Type:** Final-year academic software engineering project

This document explains what the system does, how it's built, and — as a senior developer would assess it — where it's strong and where it still has gaps. It's written for your defense: to help you explain design decisions confidently and to be upfront about trade-offs an examiner might probe.

---

## 1. What the system does

Rural water points (boreholes, wells, tap stands) break down, and district offices historically tracked their status on paper or scattered spreadsheets. Amazi ("water" in Kinyarwanda) replaces that with a web application where:

- **Field data** (GPS location, technology type, install year, population served, rainfall, water source) gets uploaded per district via CSV/XLSX.
- Every water point has a **live status**: **Functional**, **At Risk**, **Under Repair**, or **Non-Functional**.
- A trained **Logistic Regression** model scores each water point's failure risk from age, population load, rainfall, technology type, and catchment pressure, bucketing it into Functional / At Risk / Non-Functional with a High/Medium AI-confidence badge.
- When something breaks, a manager creates a **maintenance task**, assigns it to a technician, and the system tracks it through a full repair lifecycle (**pending → assigned → accepted → in progress → completed → verified**), with every transition recorded.
- District officers get **reports and dashboards** (status breakdowns, technician performance, maintenance history, predictive risk, district/sector summaries) exportable as PDF/Excel, with Chart.js visualizations and print support.
- Everything is scoped by **district** — a Bugesera manager cannot see or act on Nyagatare's data, except admins, who see everything.
- **Admin tooling**: user approval and role management, technician creation with email-invited temporary credentials, audit-log and report-log viewers with filter/sort/export, and a model-performance dashboard.
- A **data pipeline** preprocesses real WPDx (Water Point Data Exchange) and Rwanda Water Board source data to seed the system and score catchment-level industrial water pressure.

---

## 2. Architecture

**Stack:** Flask (application factory pattern) + SQLAlchemy 2.0 (ORM) + Flask-Migrate (Alembic) + Flask-Login (sessions) + Flask-WTF (forms/CSRF) + Flask-Mail (SMTP) + bcrypt + Bootstrap 5 + Leaflet.js (map) + Chart.js (dashboards) + pandas/scikit-learn/joblib (ML) + ReportLab/openpyxl (exports). SQLite for development; config is environment-driven so PostgreSQL is a one-line `DATABASE_URL` swap for production.

**Process model:** Gunicorn in production, Flask's built-in server with auto-reload in development. The app starts idempotently — `run.py` calls `db.create_all()` on startup so a fresh clone runs immediately without remembering to init the database first.

```
run.py                          entrypoint + CLI: init-db, train-model, seed,
                                dedupe-water-points, reset-password, send-test-email
config.py                       Config base class + DevelopmentConfig/TestingConfig/
                                ProductionConfig subclasses; reads from .env
app/
  __init__.py                   create_app() factory — extension wiring, blueprint
                                registration, before_request settings sync,
                                after_request cache-prevention, context processors
                                (unread notifications, system district),
                                hidden /create-admin-now route + decoy URLs
  models.py                     SQLAlchemy models + Enums (UserRole, WaterPointStatus,
                                 TaskPriority, TaskStatus) — 9 active tables
  auth.py                        register / login / logout / profile / settings /
                                change-password / temp-password flow
  admin.py                       admin dashboard, user approval/role/toggle/delete,
                                technician CRUD, password reset, audit-log viewer,
                                report-log viewer, model-performance page
  dashboard.py                   home dashboard, map, water-point list/detail,
                                CSV/XLSX upload, AI prediction glue, district view,
                                prediction center (single-point predict)
  ml_features.py                 shared feature engineering (train + inference)
  ml_train.py                    training pipeline: clean → engineer → fit → evaluate →
                                save artifacts + plots (CLI: flask train-model)
  ml_inference.py                singleton model cache (mtime-reload), predict_single/
                                predict_batch, graceful degradation
  tasks.py                       maintenance-task state machine + helpers
  notifications.py               in-app notification inbox + mark-read
  reports.py                     6 report routes × (view + PDF + Excel)
  report_queries.py              pure data-builder functions (no Flask request cycle)
  report_export.py               shared ReportLab/openpyxl PDF & Excel builders
  settings.py                    runtime key/value system settings, persisted + cached
  rwanda_geo.py                  Bugesera administrative hierarchy (15 sectors,
                                72 cells, 581 villages) from ngabovictor/Rwanda
  forms.py                       all WTForms definitions (auth, tasks, reports, upload)
  utils.py                       utcnow() helper, role_required/api_role_required,
                                scoped_by_district(), user_can_access_district(),
                                home_for(), notify(), allowed_file()
  services/
    water_point_service.py       duplicate detection + merge (union-find by ID/location)
    technician_service.py        technician creation with bcrypt temp-password + email
    mail_service.py              SMTP config logging, welcome emails, error hints
migrations/                     Alembic — full migration chain from baseline onward
notebooks/                      exploratory_analysis.py — standalone EDA script
scripts/                        seed_rwb_sources.py — imports RWB water-source data
waterpoints/                    process_bugesera.py — WPDx extraction & cleaning
data/raw/                       sample_training_data.csv, sample_water_points.csv
models/                         water_point_model.pkl (+scaler, +feature_names — gitignored),
                                training_metrics.json (tracked)
templates/                      Jinja2 + Bootstrap 5 (landing, base shell, auth,
                                dashboard, tasks, reports, admin, notifications, emails)
static/css/, static/js/         Bootstrap theme overrides, Leaflet map, Chart.js
tests/                          pytest suite — 70 tests across 7 files
```

This is a textbook Flask **application-factory + blueprints** structure — a defensible architectural choice for an academic project because it's the officially recommended Flask pattern, keeps concerns separated by domain (auth vs. tasks vs. reports), and each blueprint is independently testable.

A notable evolution: business logic that was originally inline in blueprint route handlers (user creation, water-point deduplication, email sending) has been factored into a **`services/` layer** — pure functions that are independently testable and don't depend on Flask request state. The ML pipeline was split the same way: `ml_features.py` holds the single source of truth for feature engineering (imported by both training and inference), and `ml_inference.py` is deliberately Flask- and database-agnostic, receiving plain dicts/DataFrames from `dashboard.py` as a glue layer.

---

## 3. Data model

| Table | Purpose |
|---|---|
| `users` | Accounts. Role is one of `admin`, `district_manager`, `district_technician`, `viewer` (stored as a plain string, backed by the `UserRole` Enum in code). Scoped to one `district`, with optional `sector`/`cell`/`village`. New registrations need admin approval; `must_change_password` forces a password change on next login (used for admin-reset passwords and CLI resets). First-run bootstrapping uses the hidden `/create-admin-now` URL — there's no "first user" DB logic, anyone who knows the URL can create an admin at any time, and decoy URLs (`/admin-register`, `/create-admin`, etc.) block guessed paths. |
| `water_points` | The core asset. Location, technology type, current status, ML risk probability + confidence + timestamp, rainfall, and a `water_source_id` FK to `water_sources`. |
| `water_sources` | Catchments and their industrial usage pressure scores, imported from RWB's national water-user registry (`raw data/rwanda_water_users.xlsx`). The `industrial_pressure_score` is a feature in the ML model — a point drawing water from a catchment with heavy industrial demand carries higher failure risk. |
| `maintenance_tasks` + `task_status_history` | The repair workflow and its full audit trail. Every status transition is a row in `task_status_history` with who changed it, when, and a note. The task also records granular timestamps (`assigned_at`, `accepted_at`, `started_at`, `completed_at`, `verified_at`) and the `resulting_status` so a completed repair's outcome is permanently captured. |
| `notifications` | In-app inbox. Respects a per-user `notifications_enabled` preference — if disabled, the `notify()` helper silently skips the row. |
| `audit_logs` | System-wide security/action log (logins, logouts, approvals, uploads, task actions, password changes, admin creation). Used by the admin Audit Log viewer with filter/sort/export. |
| `report_logs` | Who generated which report/export, when, with what filters and row count — an audit trail for the reporting module, surfaced via the admin Report Activity Log viewer. |
| `system_settings` | Admin-editable key/value config (`app_name`, `admin_email`, `risk_threshold`, `session_cookie_secure`, `max_upload_mb`, `default_district`). Applied to Flask's config per-request via a `before_request` hook. |
| ~~`maintenance_visits`~~ | **Dropped.** Was dead code in the original scaffold — zero write call-sites, superseded by `maintenance_tasks`. Removed via an Alembic migration (`drop_maintenance_visits`) that also deletes the orphan table from any existing databases. |

### The migration chain

The original project had a gap: `users`, `water_points`, `notifications`, and `audit_logs` existed only via `db.create_all()`, not migrations, so `flask db upgrade` on a fresh database would miss them. That's been closed with a baseline migration (`87ca337431cf`, `down_revision = None`) inserted as the new root of the chain. The full migration history, in order, is:

1. `87ca337431cf` — **baseline schema** (users, water_points, notifications, audit_logs)
2. `90489408fe07` — maintenance_tasks + task_status_history
3. `a1b2c3d4e5f6` — report_logs
4. `c158a8bdc832` — sector/cell/village columns on users
5. `236b669f40e4` — water_sources table + water_source_id FK on water_points
6. `b2c3d4e5f6a7` — system_settings table
7. `d3e4f5a6b7c8` — user preferences (theme_preference, notifications_enabled)
8. `drop_maintenance_visits` — removes the orphan maintenance_visits table
9. `e4f5a6b7c8d9` — prediction_confidence on water_points

A fresh `flask db upgrade` now produces the complete, FK-ordered schema on an empty database.

### Why a task state machine instead of just editing `current_status`

A naive design would let a technician just flip a water point's status directly. Amazi instead models the *repair process itself* as a state machine (`pending → assigned → accepted → in_progress → completed → verified`), with every transition recorded. That's a genuinely good design choice for a system whose whole value proposition is accountability — you get built-in answers to "how long did this repair take," "who verified it," "which technician has the best completion rate" for free, because the data was captured at each step rather than reconstructed after the fact. The Technician Performance report is a direct beneficiary: it doesn't need any special instrumentation, it just aggregates `task_status_history` and the task timestamps.

---

## 4. Feature walkthrough

### Auth & RBAC

Registration is self-service; new accounts sit in "pending" until an admin approves them. Passwords are hashed with **bcrypt**. Four roles gate access via decorators in `utils.py`:
- `role_required(*roles)` — HTML redirects (flash + route to home)
- `api_role_required(*roles)` — JSON 401/403 (API callers can't act on an HTML redirect)
- `admin_required`, `technician_required`, `manager_required` — convenience wrappers

The **first administrator** is created via the hidden `/create-admin-now` URL (mounted at the app level, not under `/auth`, so it's not discoverable from the login page). It stays available even after admins exist, so new admins can be provisioned anytime by anyone who knows the URL — and decoy routes (`/admin-register`, `/create-admin`, `/register-admin`, `/setup-admin`) intercept guessed paths and redirect to login. The `/api/predict` endpoint was previously missing its role decorator (any logged-in user, including viewer, could trigger predictions) — now gated like the other write endpoints.

**Security hardening:**
- The post-login `?next=` parameter only honors same-origin relative paths (`urlsplit` checks both `netloc` and `scheme`), closing the classic open-redirect vector (CWE-601).
- An `after_request` hook sets `Cache-Control: no-store` on every non-static response, so authenticated pages aren't cached in shared browsers.
- Passwords require 8–72 chars with at least one uppercase, one lowercase, and one digit — enforced via WTForms `Regexp` validators on every password form.

### District scoping

`scoped_by_district()` in `utils.py` is the single source of truth: it returns the query unfiltered for admins, or filters to `current_user.district` for everyone else. It's used by `scoped_water_points()` (dashboard), `scoped_tasks()` (tasks), the maintenance-report query in `report_queries.py`, and the API. Cross-district access is independently tested (`test_cannot_assign_technician_from_other_district`, `test_maintenance_report_is_district_scoped_for_non_admin`, etc.). Technicians are additionally scoped to their own assigned tasks in the task worklist and the technician-performance report.

### Data ingestion & deduplication

CSV/XLSX upload (`dashboard.py: upload_data`) reads rows via `pandas`, saves the file to `data/uploaded/`, then processes via `process_water_point_data()`:
- **Upsert by water-point ID** (case/whitespace-normalized via `normalize_point_id`), so re-uploading the same file updates existing records rather than duplicating them.
- **Location fallback matching** — if the ID doesn't match an existing point, the system checks for a point at the same coordinates (within ~11 m) in the same district, so GPS drift doesn't create duplicates.
- **Water-source linking** — if the upload contains a `water_source_name` column, it's matched to `WaterSource` records and the FK is set, which feeds the catchment-pressure feature in ML.
- **AI prediction** — if a trained model exists, `predict_batch()` runs over all rows and sets `risk_probability`, `current_status`, `prediction_confidence`, and `last_prediction_date` in one vectorized pass. If no model is present, uploads still work — they just skip the prediction step. This graceful degradation matters for demos: you can show the full pipeline without a trained model.

If processing fails after the file is saved, the file is deleted (`filepath.unlink(missing_ok=True)`) — no orphaned upload files left behind.

The `flask seed` command does a bulk bootstrap: seeds water points from CSV, trains the model, and runs predictions on all points in one shot. `flask dedupe-water-points [--preview]` finds and merges duplicate groups using a union-find algorithm over shared normalized IDs or shared rounded coordinates.

### ML prediction (full training + inference pipeline)

The system predicts each water point's failure risk with a **Logistic Regression** model (`StandardScaler` + `LogisticRegression(class_weight="balanced")`). The pipeline is fully real, not a stub:

**Training** (`app/ml_train.py`, run via `flask train-model --data <file>` or the admin retrain):
1. Loads a labeled CSV/XLSX (requires `year_installed`, `population_served`, and `current_status` columns).
2. Filters to binary labels (`Functional`/`Non-Functional` only — "At Risk" has no verified historical label to train on).
3. Drops rows missing >30% of numeric fields; median-imputes the rest (medians computed once at training time and persisted for inference).
4. Removes age/population outliers via 1.5×IQR (training only — inference never rejects real data).
5. Engineers **9 features** via `app/ml_features.py` (the shared module): `age`, `population_served`, `monthly_rainfall`, `tech_encoded` (normalized technology → integer code), `catchment_pressure`, `interaction_age_pop`, `interaction_age_rain`, `rainy_season_flag`, `population_density_category`.
6. Stratified 80/20 train/test split, fits the pipeline, evaluates accuracy/precision/recall/F1/ROC-AUC.
7. Saves `models/water_point_model.pkl`, `models/scaler.pkl`, `models/feature_names.pkl` (all gitignored) and `models/training_metrics.json` (tracked), plus evaluation plots (confusion matrix, ROC curve, feature importance) to `static/images/`.

**Inference** (`app/ml_inference.py`): a module-level singleton reloads the model whenever the pickle's mtime changes, so a retraining is picked up by a running app without a restart. Exposes `predict_single()` (used by the single-point `/dashboard/predict` page) and `predict_batch()` (used by CSV upload and the admin "Re-run Predictions" button). Degrades gracefully — returns `None` and logs a warning if no model is available; uploads and the rest of the app work identically either way.

**Same features, never drift:** `ml_features.py` is imported by both training and inference, so the two can never compute features differently. Unseen technology types fall back to the most frequent training category rather than erroring.

**Risk bucketing:** probability below 33% → Functional, 33–66% → At Risk, above 66% → Non-Functional. Confidence is "High" when the probability is ≤0.2 or ≥0.8 (far from the boundaries), "Medium" otherwise. These thresholds are shared with the reporting module (`RISK_LOW_MAX`/`RISK_MEDIUM_MAX`) so the dashboard status and the Predictive Risk report's Low/Medium/High buckets are always describing the same probability.

**Explainability:** the `risk_factors_for()` function in `dashboard.py` decomposes a single water point's prediction into its top contributing factors using the model's coefficients — so a technician doesn't just see "82% risk," they see "age +24y (↑ risk), population 1,200 (↑), rainfall 20mm (↓)." This addresses the "black box" concern head-on.

**Honest limitations:** the pipeline is real and fully tested (`tests/test_ml.py`, 15 tests covering feature engineering, training, inference, cache reload-on-mtime-change, and 1000-row batch performance), but training currently runs on a small synthetic sample (`data/raw/sample_training_data.csv`, 220 rows) rather than verified WASAC field records. The full methodology, results, and limitations are documented in `ML_REPORT_SECTION.md`.

### Maintenance task workflow

Covered in §3. Managers create and verify tasks; technicians accept, start, update progress, and complete them; every transition fires an in-app notification to the relevant party and writes to both `task_status_history` (workflow audit) and `audit_logs` (system audit). Starting a task automatically flips the water point to "Under Repair," and completing one applies the technician's chosen `resulting_status` — a nice touch that keeps the map/dashboard in sync with real repair activity without a separate manual step. The full lifecycle is tested end-to-end (`test_full_task_lifecycle`).

### Reporting & Analytics

Six report types, each with filters, pagination, Chart.js visualizations, and PDF (ReportLab) / Excel (openpyxl) / print export:

1. **Water Point Status** — counts per status (pie chart), with district/sector filters.
2. **Technician Performance** — assigned/completed/in-progress counts, completion rate, average resolution time per technician, with district/technician/date filters and pagination.
3. **Maintenance** — task list with water point, district, technician, repair date, status, remarks, plus a monthly-activity trend chart.
4. **Predictive Risk** — risk-bucketed list of water points with predictions, risk-distribution pie chart, filters by district/sector/technology/risk-level.
5. **District/Sector Summary** — aggregate health by district (drill-down to sector), showing total/functional/at-risk/maintenance-case counts with a district risk-ranked bar chart.
6. **Source Validation** — water points with no linked water source, surfaced for data-quality remediation.

All the data-builder logic (`report_queries.py`) is separated from the Flask routes — these are pure functions that take a `filters` dict and return a plain dict, so they're testable as Python with no request/response cycle involved. The 22 report tests exercise them through the Flask test client, while the 15 ML tests directly import `ml_features` and `ml_inference` as plain Python modules. The shared `SimplePagination` class duck-types to Flask-SQLAlchemy's `Pagination` so the same template partial works for both DB-paginated admin lists and in-memory-paginated report lists.

**Report audit trail:** every view, PDF export, or Excel export writes a `ReportLog` row (who, what, when, filters, row count), surfaced via the admin "Report Activity Log" page with the same filter/sort/export machinery as the audit-log viewer.

### Notifications & Audit

Every significant action writes an `AuditLog` row (login, logout, registration, admin creation, user approval/rejection, role change, toggle-active, deletion, password change/reset, task create/assign/accept/start/complete/verify, data upload, prediction re-run, email failure). Admins view these via a paginated, filterable, sortable, exportable Audit Log page. In-app notifications (not email — see §5) alert users to task assignments, completions, and verifications. Notification rendering respects the per-user `notifications_enabled` preference.

### Admin panel

The admin experience (`/admin/`) includes:
- **Dashboard** — user counts, pending approvals, water-point status counts, recent audit activity.
- **Users** — approve/reject pending, change roles, toggle active, reset passwords, delete (with safety checks: can't delete yourself, can't delete the only admin, can't delete a user who created/verified tasks/reports/history).
- **Technicians** — create (generates a temp password, sends a welcome email), resend credentials, view by district with the real Bugesera sector/cell/village hierarchy.
- **Model Performance** — accuracy/precision/recall/F1/ROC-AUC, confusion matrix image, feature-importance coefficients (sorted by absolute weight), and the system settings form.
- **Report Activity Log** — filter/sort/export report-generation audit trail.
- **Audit Log** — filter/sort/export system-wide action log.

### Runtime system settings

`app/settings.py` implements an admin-editable key/value table (`SystemSetting` model) with six typed settings and defaults declared in code. A `before_request` hook calls `apply_settings_to_config()` to sync persisted settings into Flask's config every request, so the rest of the app (report titles, upload limits, session cookie security, default district, risk threshold) picks them up automatically. Settings can also be updated programmatically (`set_setting()`), which is how the ML pipeline and tests interact with them.

### Data pipeline (`waterpoints/`, `scripts/`)

- `waterpoints/process_bugesera.py` — extracts and cleans WPDx data for Bugesera District: filters by district, maps WPDx technology/source fields onto the app's four technology categories (Borehole, Handpump, Piped Kiosk, Protected Spring), standardizes status, computes age, and outputs a cleaned CSV plus summary report, map, and charts. It also flags a data-quality warning: the WPDx point-level file labels all Bugesera points as "Non-Functional," which disagrees with the grid-level HDX aggregate file.
- `scripts/seed_rwb_sources.py` — imports water sources from the RWB registry (`raw data/rwanda_water_users.xlsx`), infers catchment from usage types, assigns an `industrial_pressure_score` from a hand-weighted usage lookup, and persists them to the `water_sources` table. These pressure scores feed the catchment-pressure feature in the ML model.
- `notebooks/exploratory_analysis.py` — standalone EDA script (no Jupyter dependency) that generates distribution, correlation, box-plot, and scatter visualizations.

---

## 5. Areas for improvement (senior-developer assessment)

I've grouped these by how much they actually matter for an academic project.

### Worth fixing (small, contained, likely already worth mentioning in defense)

- **`datetime.utcnow()` deprecation.** The codebase now uses a `utcnow()` helper in `utils.py` that wraps `datetime.now(timezone.utc).replace(tzinfo=None)` — this keeps naive timestamps (matching SQLite's storage) while avoiding the deprecation warning. However, a few `datetime.utcnow()` call-sites may still linger; the test suite currently emits 55 warnings, mostly `LegacyAPIWarning` for `Query.get()` (the pre-SQLAlchemy-2.0 query API). Migrating `query.get()` → `db.session.get()` is a mechanical find-replace across `admin.py` (5 call-sites), `tasks.py` (7 call-sites), `notifications.py` (1 call-site), and `app/services/technician_service.py` (1 call-site).
- **Duplicate `predict_batch`/legacy inference paths.** `dashboard.py` still defines `load_prediction_model()` and `predict_risk()` (the old single-model-load + threshold-based binary label path), used only by the `/api/predict` endpoint. The newer `ml_inference.py` module is the canonical path for everything else. Consolidating `/api/predict` to use `ml_inference.predict_batch` would remove redundant code — worth noting if asked about consistency.
- **`_index_context` `dict()` bug.** The dashboard's district health aggregation once did `dict()` on 3-tuples from a `GROUP BY` query, which silently dropped data. This has been fixed — the current version uses a dict comprehension that correctly maps `(district, status)` pairs to counts without losing data.

### Worth mentioning as known, deliberate scope boundaries

- **The trained model is a synthetic-data stub, not a validated classifier.** The training *pipeline* is real, fully working, and tested. The model it produces is only as good as the labeled data it's trained on — and the repo currently trains on a small synthetic sample (`data/raw/sample_training_data.csv`, 220 rows) rather than verified WASAC maintenance records. State this proactively: the pipeline is production-ready in structure, the data is not yet production-quality. Full methodology and limitations in `ML_REPORT_SECTION.md` §3.
- **No email in production.** Flask-Mail is integrated and the welcome-email path works (technician creation sends credentials, with SMTP-config logging and error hints for common Brevo setup mistakes), but SMTP credentials live in `.env` (gitignored) and must be configured by the deployer. `flask send-test-email` is the verification tool. In-app notifications are the reliable delivery channel — emails are best-effort.
- **Training data quality.** The WPDx extraction for Bugesera labels all 223 points as "Non-Functional," which disagrees with the grid-level HDX aggregate. This is flagged in the cleaning script and summary report and should be called out explicitly in any methodology discussion.

### Worth doing if you have time before submission

- **Consolidate the remaining inline district checks.** `scoped_by_district()` is the shared helper, but `dashboard.py:water_point_detail` still does an inline `current_user.district != water_point.district` check. `api.py:update_status` was already consolidated to use `user_can_access_district()`. A single `user_can_access_district()` call (already in `utils.py`) for the remaining inline check would be cleaner and more defensible if asked "how do you extend this to a 6th district."
- **Migrate off `Query.get()`.** 14 deprecated usages across `admin.py` (5 `get_or_404` call-sites), `tasks.py` (7 `get_or_404` call-sites), `notifications.py` (1 `get_or_404` call-site), and `app/services/technician_service.py` (1 plain `.get()` call-site). Switching to `db.session.get()` removes the `LegacyAPIWarning` noise — an easy demonstration of keeping the codebase actively maintained.
- **Single-point predict page vs. `/api/predict` duplication.** The `/dashboard/predict` route (single-point, uses `ml_inference.predict_single`) and the `/api/predict` endpoint (loops point-by-point calling the legacy `predict_risk`) overlap in purpose. Neither uses the vectorized `ml_inference.predict_batch` path that upload and the admin "Re-run Predictions" button already use. If the API is consumed by an external integration, consider unifying both to `ml_inference.predict_batch` so there's one prediction interface.

### Not worth doing for this project

- Adding rate limiting, a caching layer, or migrating off SQLite — reasonable production hardening, but disproportionate effort for a system that will be demoed and graded. If asked "is this production-ready," the honest answer is "the architecture and security patterns are sound, but the ML model needs real labeled data and the deployment needs SMTP/PostgreSQL config — here's specifically what's missing."

---

## 6. Suggested defense talking points

If asked to justify design decisions, these are the strongest ones in the codebase:

1. **The task state machine over direct status edits** (§3) — captures the *process*, not just the *outcome*, which is what makes Technician Performance and Maintenance reports possible without extra instrumentation. The granular timestamps (`accepted_at`, `started_at`, `completed_at`) give resolution-time metrics for free.

2. **Pure, request-independent report-builder functions** (`report_queries.py`) — a deliberate testability decision, proven by 16 tests that never touch Flask's request/response cycle. Data aggregation happens in SQL (`GROUP BY`/`func.count`), not Python loops, which is the pattern the original audit flagged as an improvement over `dashboard.py`'s Python-level aggregation.

3. **Shared feature-engineering module** (`ml_features.py`) — the single source of truth that both training and inference import, so the two can never silently drift apart. The model cache in `ml_inference.py` reloads on file mtime change, so a retraining takes effect without an app restart.

4. **Graceful ML degradation** — the system is fully functional with zero trained model present (uploads, dashboard, reports all work); prediction is additive, not load-bearing. The same `flask train-model` pipeline powers both the CSV-upload predictions and the admin Model Performance page.

5. **Consolidated district scoping** (`scoped_by_district()` in `utils.py`) — one helper for "is this user allowed to see this district's data," used by dashboard, tasks, API, and reports. Cross-district access is independently tested.

6. **Service layer isolation** (`app/services/`) — business logic (user creation, water-point dedup, email sending) lives in pure functions that don't depend on Flask request state, making them testable outside the web app and reusable from CLI commands.

7. **Defense-in-depth on auth** — open-redirect fix on `?next=`, CSRF protection on all forms (with a dedicated CSRF-enabled test app), cache-prevention headers on authenticated responses, bcrypt password hashing, role-based decorators that return JSON (not redirects) for API callers.

8. **Consistent audit trail** — `audit_logs` + `task_status_history` + `report_logs` together mean almost every consequential action in the system is independently reconstructable after the fact.

### Project artifacts

| Document | Purpose |
|---|---|
| `README.md` | Setup, upload format, ML training/inference, EDA, test commands |
| `explanation.md` | This file — system explanation for defense |
| `AUDIT_REPORT.md` | Pre-reporting-module codebase audit (dated 2026-07-06, now historical) |
| `FINAL_DELIVERY_REPORT.md` | Reporting module delivery report (dated 2026-07-06, documents what was added) |
| `DESIGN_SYSTEM.md` | Full visual design system (AMAZI branding, watershed interface, tokens, components, IA/wireframes) |
| `ML_REPORT_SECTION.md` | ML methodology, results, limitations, and future work for the thesis report |
*(No AGENTS.md present in this project.)*

### Test coverage

The pytest suite has **70 tests** across 7 files, all passing:

| Test file | Focus |
|---|---|
| `tests/test_security.py` | CSRF, API role enforcement, login routing, `/create-admin-now` flow, admin password reset |
| `tests/test_reports.py` | RBAC per role, district-scoping, status counts, risk thresholds, technician completion rates, pagination, PDF/Excel validity, ReportLog audit trail |
| `tests/test_ml.py` | Feature engineering, training pipeline, inference, cache reload-on-mtime-change, 1000-row batch performance |
| `tests/test_tasks.py` | Full task lifecycle, cross-district assignment blocking, out-of-order transition rejection, viewer access denial |
| `tests/test_water_point_dedup.py` | ID normalization, location-based matching, upload dedup (same ID variant, same location different ID), duplicate-group detection and merge with task repointing |
| `tests/test_user_delete.py` | Self-deletion blocking, only-admin safety, foreign-key reassignment on delete |
| `tests/test_settings.py` | Settings defaults, programmatic updates, risk-threshold driving prediction behavior, default-district on upload form |

If asked "what would you do with another month," the moderate-effort list in §5 (consolidated inline scoping, `Query.get()` cleanup, unifying the legacy `/api/predict` path) is a good, honest answer that shows awareness without overselling the current state.
