# Amazi — RWB Water Intelligence

**Amazi** ("water" in Kinyarwanda) is a Flask application for water point
failure-risk monitoring in rural Rwanda. It combines AI risk prediction, GIS
mapping, and maintenance operations in a single watershed interface for the
Rwanda Water Board, with authentication, role-based access control, admin
approval, uploads, and JSON API endpoints.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app run.py init-db
python run.py
```

If `python` is not available on PATH, install Python from python.org or enable the Windows Python launcher, then rerun the commands above.

Open `http://127.0.0.1:5000`.

Administrator accounts are provisioned via the hidden `/create-admin-now`
URL, which works even after admins already exist (anyone who knows the URL can
create a new administrator). Later users must be approved from the admin user
management page.

## Upload Format

CSV/XLSX uploads require these columns:

- `water_point_id`
- `latitude`
- `longitude`
- `technology_type`

Optional columns include `sector`, `cell`, `year_installed`, `population_served`, `depth`, `rainfall`, and `rainfall_month`.

## AI Risk Prediction

The system predicts each water point's failure risk with a Logistic Regression
model (see `ML_REPORT_SECTION.md` for full methodology).

**Training** (produces `models/water_point_model.pkl`, `scaler.pkl`,
`feature_names.pkl`, `training_metrics.json`, and evaluation plots under
`static/images/`):

```powershell
flask --app run.py train-model --data data/raw/sample_training_data.csv
```

The training CSV needs a `current_status` column of `Functional`/`Non-Functional`
plus `year_installed`, `population_served`, and `monthly_rainfall` (or
`rainfall`). Admins can also retrain from the UI at **Admin → Model
Performance**, which also shows accuracy/precision/recall/F1/ROC-AUC,
confusion matrix, and feature importance for the currently deployed model.

**Inference** runs automatically on every CSV/XLSX upload and via the
admin "Re-run Predictions" button. With no trained model present, uploads
still work — water points just keep their existing status. A water
point's predicted status is bucketed from its risk probability: below 33%
Functional, 33-66% At Risk, above 66% Non-Functional, each shown with a
High/Medium AI-confidence badge.

**Exploratory data analysis** (writes plots to `static/images/eda/`):

```powershell
python -m notebooks.exploratory_analysis --data data/raw/sample_training_data.csv
```

## Tests

```powershell
pytest
```
