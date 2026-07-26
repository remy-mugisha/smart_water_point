# Smart Water Point Monitoring System — System Explanation

**Case Study:** Bugesera District, Rwanda (generalizes to 5 districts: Nyagatare, Bugesera, Gatsibo, Kayonza, Rwamagana)
**Audience:** WASAC technicians and district water officers
**Type:** Final-year academic software engineering project

This document explains what the system does, how it's built, and — as a senior developer would assess it — where it's strong and where it still has gaps. It's written for your defense: to help you explain design decisions confidently and to be upfront about trade-offs an examiner might probe.

---

## 1. What the system does

Rural water points (boreholes, wells, tap stands) break down, and district offices historically tracked their status on paper or scattered spreadsheets. This system replaces that with a web app where:

- Field data (GPS location, technology type, install year, population served) gets uploaded per district.
- Every water point has a live status: **Functional**, **At Risk**, **Under Repair**, or **Non-Functional**.
- A trained Logistic Regression model scores each water point's failure risk from age, population load, rainfall, technology type, and catchment pressure, bucketing it into Functional / At Risk / Non-Functional with a High/Medium AI-confidence badge.
- When something breaks, a manager creates a **maintenance task**, assigns it to a technician, and the system tracks it through a full repair lifecycle (assigned → accepted → in progress → completed → verified).
- District officers get **reports and dashboards** (status breakdowns, technician performance, maintenance history, predictive risk, district/sector summaries) exportable as PDF/Excel or printable.
- Everything is scoped by **district** — a Bugesera manager cannot see or act on Nyagatare's data, except admins, who see everything.

---

## 2. Architecture

**Stack:** Flask (application factory pattern) + SQLAlchemy (ORM) + Flask-Migrate (Alembic) + Flask-Login (sessions) + Flask-WTF (forms/CSRF) + Bootstrap 5 + Leaflet.js (map) + Chart.js (dashboards) + pandas/scikit-learn (ML) + ReportLab/openpyxl (exports). SQLite for development; the config is environment-driven so it's a one-line swap to PostgreSQL for production.

```
run.py                  entrypoint, CLI (`flask init-db`, `flask train-model`)
config.py               single Config class, reads from .env
app/
  __init__.py           create_app() factory, extension wiring, blueprint registration
  models.py             SQLAlchemy models + enums (roles, statuses, task states)
  auth.py                register / login / logout / profile
  admin.py                user approval, audit log viewer, report-log viewer, model performance/retrain
  dashboard.py            home dashboard, map, water point list, CSV/XLSX upload + AI prediction glue
  ml_features.py            shared feature engineering (train + inference use the same code)
  ml_train.py               training pipeline: clean data, engineer features, fit, evaluate, save artifacts
  ml_inference.py           singleton model loader + predict_single/predict_batch
  tasks.py                 maintenance task state machine
  notifications.py          in-app notification inbox
  api.py                     JSON endpoints (used by the Leaflet map, and for programmatic access)
  reports.py + report_queries.py + report_export.py   reporting & analytics module
  forms.py                    all WTForms definitions
  utils.py                     decorators (role_required, api_role_required, etc.), notify() helper
migrations/               Alembic migration scripts
notebooks/                exploratory_analysis.py — standalone EDA script
templates/, static/       Jinja2 + Bootstrap + vanilla JS
tests/                     pytest suite (52 tests)
```

This is a textbook Flask **application-factory + blueprints** structure — a good, defensible architectural choice for an academic project because it's the officially recommended Flask pattern, keeps concerns separated by domain (auth vs. tasks vs. reports), and each blueprint is independently testable.

---

## 3. Data model

| Table | Purpose |
|---|---|
| `users` | Accounts. Role is a plain string (`admin`, `district_manager`, `district_technician`, `viewer`), scoped to one `district`. New registrations need admin approval — except the very first user ever created, who is auto-approved as admin (bootstrap problem, solved simply). |
| `water_points` | The core asset. Location, technology type, current status, ML risk probability, and AI-confidence level. |
| `maintenance_tasks` + `task_status_history` | The repair workflow and its full audit trail — every status transition is a row, with who changed it, when, and a note. |
| `notifications` | In-app inbox, one row per (user, event). |
| `audit_logs` | System-wide security/action log (logins, approvals, uploads, task actions). |
| `report_logs` | Who generated which report/export, when, with what filters — an audit trail for the reporting module. |
| `maintenance_visits` | **Dead** — defined in the model but nothing in the app writes to it. Superseded by `maintenance_tasks`. Left in place from an earlier scaffold; see §5. |

### Why a task state machine instead of just editing `current_status`
A naive design would let a technician just flip a water point's status directly. This project instead models the *repair process itself* as a state machine (`pending → assigned → accepted → in_progress → completed → verified`), with every transition recorded. That's a genuinely good design choice for a system whose whole value proposition is accountability — you get built-in answers to "how long did this repair take," "who verified it," "which technician has the best completion rate" for free, because the data was captured at each step rather than reconstructed after the fact. The Technician Performance report is a direct beneficiary of this: it doesn't need any special instrumentation, it just aggregates `task_status_history`.

---

## 4. Feature walkthrough

### Auth & RBAC
Registration is self-service; new accounts sit in "pending" until an admin approves them (`auth.py`, `admin.py`). Passwords are hashed with `bcrypt`. Four roles gate access via decorators in `utils.py` (`admin_required`, `manager_required`, `technician_required`, and a JSON-returning `api_role_required` for the API blueprint, since redirecting an AJAX/API caller to a login page doesn't make sense).

### District scoping
Every query that returns water points, tasks, or reports is filtered by `current_user.district` unless the caller is an admin. This isn't one shared helper (a legitimate area for improvement — see §5) but the pattern is applied consistently everywhere it needs to be, and it's independently tested for cross-district access (`test_cannot_assign_technician_from_other_district`, etc.).

### Data ingestion
CSV/XLSX upload (`dashboard.py: upload_data`) reads rows via `pandas`, upserts by `water_point_id` (so re-uploading the same file updates existing records rather than duplicating them), and — if a trained model file exists at `models/water_point_model.pkl` — runs it against each row to set an initial risk status. If no model is present, uploads still work; they just skip the prediction step. This graceful-degradation choice matters for a student project: you can demo the full pipeline without ever having trained a real model.

### ML prediction
A full training pipeline now exists (`app/ml_train.py`, run via `flask train-model --data <file>` or the admin retrain button): it cleans a labeled CSV (median-imputes missing values, drops rows >30% incomplete, strips age/population outliers via IQR), engineers nine features (age, population served, rainfall, technology encoding, catchment pressure, two interaction terms, a rainy-season flag, and a population-density category), trains a `StandardScaler` + `LogisticRegression(class_weight="balanced")` pipeline with a stratified 80/20 split, and saves the model, scaler, feature metadata, metrics, and confusion-matrix/ROC/feature-importance plots.

`app/ml_inference.py` is the deployed side: a module-level singleton reloads the model whenever the pickle's mtime changes, exposes `predict_single()` (used by the legacy `/api/predict` endpoint) and a vectorized `predict_batch()` (used by CSV upload and the admin "Re-run Predictions" button), and degrades gracefully to "no prediction" if no model has been trained yet — uploads and the rest of the app work identically either way. `app/ml_features.py` is the shared feature-engineering module both training and inference import, so the two can never compute features differently. The admin "Model Performance" page (`/admin/model-performance`) surfaces accuracy/precision/recall/F1/ROC-AUC, the confusion matrix, and feature-importance coefficients read straight from the training run's metrics file.

The model file (`models/*.pkl`) is still gitignored and not shipped — a fresh clone has no model until someone runs `flask train-model`, consistent with the project's existing graceful-degradation philosophy. Training currently runs on a small synthetic labeled dataset (`data/raw/sample_training_data.csv`); see `ML_REPORT_SECTION.md` for full methodology, results, and the honest limitations (synthetic training data, binary ground truth, no live retraining) worth stating proactively in a defense.

### Maintenance task workflow
Covered in §3. Managers create and verify tasks; technicians accept, work, and complete them; every transition fires an in-app notification to the relevant party and writes to both `task_status_history` (workflow audit) and `audit_logs` (system audit). Starting a task automatically flips the water point to "Under Repair," and completing one applies the technician's chosen resulting status — a nice touch that keeps the map/dashboard in sync with real repair activity without a separate manual step.

### Reporting & Analytics
Five report types (Status, Technician Performance, Maintenance, Predictive Risk, District/Sector Summary), each with filters, pagination, PDF export (ReportLab), Excel export (openpyxl), and print support (`@media print` CSS). All the data-builder logic (`report_queries.py`) is separated from the Flask routes on purpose, so it's testable as plain Python functions with no request/response involved — worth calling out in a defense as a deliberate testability decision, not an accident.

### Notifications & Audit
Every significant action (login, logout, approval, task transition, upload) writes an `AuditLog` row, visible to admins. In-app notifications (not email — see §5) alert users to task assignments, completions, and verifications relevant to them.

---

## 5. Areas for improvement (senior-developer assessment)

I've grouped these by how much they actually matter for an academic project, since "everything a senior engineer would flag in a production system" and "what's worth fixing or at least mentioning in your defense" are different lists.

### Worth fixing (small, contained, already done)
- **Open redirect in login** (`auth.py`): the post-login `?next=` parameter was redirected to unvalidated, which is a textbook phishing vector (CWE-601). Fixed by only honoring same-origin relative paths.
- **Test-fixture context leak** (`tests/conftest.py`): the pytest fixtures held a Flask app context open across an entire test, which let Flask-Login's per-request user cache (`flask.g`) leak between two different logged-in test clients within the same test. This never affected the *app* (production requests always get a fresh context per request), but it meant any future test written the natural way — "log in as manager A on one client, manager B on another, assert A can't see B's district" — would have silently produced a false result. Worth mentioning in a defense as an example of distinguishing an application bug from a test-infrastructure bug, since a professor may probe whether you understand the difference.
- **Alembic migration history was incomplete** — `users`/`water_points`/`notifications`/`audit_logs` only existed via `db.create_all()`, not migrations. Closed with a baseline migration (`87ca337431cf`) inserted as the new root of the chain, so `flask db upgrade` alone now produces the full schema on an empty database.
- **ML pipeline was inference-only** — closed by adding a full training pipeline (`app/ml_train.py`, `flask train-model` CLI), a shared feature-engineering module (`app/ml_features.py`), and a caching inference module (`app/ml_inference.py`); see §4 and `ML_REPORT_SECTION.md`.

### Worth mentioning as known, deliberate scope boundaries
- **`MaintenanceVisit` model is dead code.** It was part of the original scaffold, superseded by the `MaintenanceTask` workflow, and nothing writes to it anymore. Safe to delete; kept for now only because it doesn't hurt anything. If asked, the honest answer is "superseded during the task-workflow redesign, not yet cleaned up."
- **`district_match_required` decorator is defined but unused** — same story, dead code from an earlier iteration before scoping was folded into each blueprint's own query helpers.
- **The trained model is a synthetic-data stub, not a validated classifier.** The training *pipeline* is real and fully working; the shipped model (once trained) is only as good as the labeled data it's trained on, and the repo currently trains on a small synthetic sample rather than verified WASAC maintenance records. State this proactively — see `ML_REPORT_SECTION.md` §3 Limitations.
- **No email** — notifications are in-app only, despite Gmail SMTP being an earlier stated plan. Also a defensible cut given time constraints; in-app notifications demo just as well.

### Worth doing if you have time before submission (moderate effort, real payoff)
- **Consolidate district-scoping logic.** Right now `scoped_water_points()` (dashboard.py), `scoped_tasks()` (tasks.py), `_scoped_maintenance_tasks_query()` (report_queries.py), and inline role checks in `api.py` all implement "is this user allowed to see this district's data" slightly differently. They're each individually correct and tested, but a single shared helper would be easier to defend as "one source of truth for access control" if an examiner asks how you'd extend the system to a 6th district or a new resource type.
- **Deprecation cleanup.** `datetime.utcnow()` is used in ~10 places and is deprecated in current Python (fires 600+ warnings in the test run); `Query.get()` is SQLAlchemy's deprecated legacy API. Neither breaks anything today, but both are one-line-per-call-site fixes and make the codebase look actively maintained rather than starting to rot — an easy thing to point to if asked "how would you keep this maintainable."
- **Orphaned upload files.** If a CSV/XLSX upload is saved to disk successfully but then fails during row processing (bad data in a later row), the file stays on disk uncleaned. Low risk (it's just disk usage in a folder only admins/technicians can populate), but a `finally`-block cleanup would be a clean 10-minute fix if you want to demonstrate defensive error handling.

### Not worth doing for this project
- Splitting `Config` into Dev/Test/Prod subclasses, adding rate limiting, or migrating off SQLite — all reasonable production hardening steps, but disproportionate effort for a system that will be demoed and graded rather than deployed to real WASAC infrastructure. If an examiner asks "is this production-ready," the honest and correct answer is "not yet, and here's specifically what's missing" (this list) — that's a stronger answer than pretending it's deployment-ready.

---

## 6. Suggested defense talking points

If asked to justify design decisions, these are the strongest ones in the codebase:
1. **The task state machine over direct status edits** — captures the process, not just the outcome, which is what makes the reporting module possible without extra instrumentation.
2. **Pure, request-independent report-builder functions** (`report_queries.py`) — a deliberate testability decision, proven out by 16 tests that never touch Flask's request/response cycle.
3. **Graceful ML degradation** — the system is fully functional with zero trained model present (uploads, dashboard, and reports all work); prediction is additive, not load-bearing, and the same `flask train-model` pipeline is what powers both the CSV-upload predictions and the admin Model Performance page.
4. **Consistent audit trail** — `audit_logs` + `task_status_history` + `report_logs` together mean almost every consequential action in the system is independently reconstructable after the fact.

If asked "what would you do with another month," the moderate-effort list in §5 (consolidated scoping helper, deprecation cleanup, migration baseline) is a good, honest answer that shows awareness without overselling the current state.
