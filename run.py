import click

from app import create_app, db

app = create_app()

# Ensure tables are created on startup (idempotent — does nothing if they exist).
# Without this the app fails with "no such table" on first run because the CLI
# command 'init-db' is easy to forget and the error is confusing to end users.
with app.app_context():
    db.create_all()


@app.cli.command("send-test-email")
@click.argument("recipient")
def send_test_email_command(recipient):
    """Send a test email through the configured SMTP server (use a real inbox)."""
    from flask import current_app
    from flask_mail import Message

    from app import mail
    from app.services.mail_service import log_smtp_config

    log_smtp_config()
    msg = Message(
        subject="AI-BASED WATER POINT FAILURE PREDICTION SYSTEM - SMTP test",
        recipients=[recipient],
        body="This is a test email from the AI-BASED WATER POINT FAILURE PREDICTION SYSTEM.",
    )
    mail.send(msg)
    click.echo(f"OK: email sent to {recipient}")


@app.cli.command("init-db")
def init_db():
    """Create database tables (redundant — now done automatically on startup)."""
    db.create_all()
    print("Database initialized.")


@app.cli.command("train-model")
@click.option("--data", "data_path", required=True, help="Path to a labeled CSV/XLSX (needs a current_status column).")
@click.option("--test-size", default=0.2, show_default=True, type=float, help="Fraction of data held out for evaluation.")
@click.option("--random-state", default=42, show_default=True, type=int, help="Seed for the train/test split and model fit.")
def train_model_command(data_path, test_size, random_state):
    """Train the water point failure-risk model and save it to models/."""
    from app.ml_train import train_model

    train_model(data_path, test_size=test_size, random_state=random_state)


@app.cli.command("seed")
@click.option("--water-points", "wp_path", default="data/raw/sample_water_points.csv", help="CSV with water points to seed.")
@click.option("--training-data", "train_path", default="data/raw/sample_training_data.csv", help="CSV for model training.")
@click.option("--user-id", "user_id", default=1, type=int, help="User ID to attribute uploads to.")
def seed_command(wp_path, train_path, user_id):
    """Seed the database with water points from CSV files and train the model.

    Reads water points from --water-points (uses district from each row),
    trains the failure-risk model on --training-data, then runs predictions
    on all seeded points so the Predict page works immediately.
    """
    import pandas as pd
    from pathlib import Path

    from app.dashboard import value_or_none
    from app.models import WaterPoint
    from app.rwanda_geo import BUGESERA_SECTORS
    from app.utils import utcnow

    # --- Seed water points ------------------------------------------------
    seen = set()
    bugesera_sector_list = sorted(BUGESERA_SECTORS)
    bugesera_cycle_idx = [0]

    def _real_bugesera_address(district, sector, cell):
        """Replace generic 'Sector-N' / empty cell with real Bugesera names."""
        if district != "Bugesera":
            return sector, cell

        if sector is None or sector.startswith("Sector-"):
            idx = bugesera_cycle_idx[0] % len(bugesera_sector_list)
            bugesera_cycle_idx[0] += 1
            sector = bugesera_sector_list[idx]

        if not cell:
            cells = sorted(BUGESERA_SECTORS.get(sector, {}))
            if cells:
                cell = cells[0]
            else:
                cell = None

        return sector, cell

    def _seed_csv(filepath, label):
        path = Path(filepath)
        if not path.exists():
            click.echo(f"{label} not found: {path}, skipping.")
            return 0

        df = pd.read_csv(path)
        required = {"water_point_id", "latitude", "longitude", "technology_type"}
        missing = required - set(df.columns)
        if missing:
            click.echo(f"Error: {path.name} missing columns: {', '.join(sorted(missing))}")
            raise click.Abort()

        count = 0
        for _, row in df.iterrows():
            pid = str(row["water_point_id"])
            if pid in seen:
                continue
            seen.add(pid)

            wp = WaterPoint.query.filter_by(water_point_id=pid).first()
            if wp is None:
                wp = WaterPoint(water_point_id=pid, uploaded_by_id=user_id)
                db.session.add(wp)

            wp.district = str(row.get("district", "Bugesera"))
            wp.sector = value_or_none(row.get("sector"))
            wp.cell = value_or_none(row.get("cell"))
            wp.sector, wp.cell = _real_bugesera_address(wp.district, wp.sector, wp.cell)
            wp.latitude = float(row["latitude"])
            wp.longitude = float(row["longitude"])
            wp.technology_type = str(row["technology_type"])
            wp.year_installed = int(row["year_installed"]) if pd.notna(row.get("year_installed")) else None
            wp.population_served = int(row["population_served"]) if pd.notna(row.get("population_served")) else None
            wp.depth = float(row["depth"]) if pd.notna(row.get("depth")) else None
            wp.monthly_rainfall = float(row.get("rainfall") or row.get("monthly_rainfall", 0)) if pd.notna(row.get("rainfall") or row.get("monthly_rainfall")) else None
            wp.rainfall_month = value_or_none(row.get("rainfall_month"))
            if "current_status" in df.columns and pd.notna(row.get("current_status")):
                wp.current_status = str(row["current_status"])
            wp.last_updated = utcnow()
            count += 1

        return count

    total_seeded = 0
    total_seeded += _seed_csv(wp_path, "Water points")
    total_seeded += _seed_csv(train_path, "Training data")
    db.session.commit()
    click.echo(f"Seeded {total_seeded} water points total.")

    # --- Train model on the training data --------------------------------
    train_file = Path(train_path)
    if train_file.exists():
        from app.ml_train import train_model

        try:
            metrics = train_model(train_file)
            click.echo(
                f"Model trained: accuracy={metrics['accuracy']:.3f} "
                f"f1={metrics['f1_score']:.3f} "
                f"roc_auc={metrics['roc_auc']}"
            )
        except Exception as exc:
            click.echo(f"Training skipped ({exc}). Predictions will not be run.")
            return
    else:
        click.echo(f"Training file not found: {train_file}, skipping model training.")
        return

    # --- Run predictions on all water points -----------------------------
    from app.ml_inference import is_model_available, predict_single
    from app.settings import ensure_defaults
    from sqlalchemy import func

    from app.models import WaterSource

    ensure_defaults()

    catchment_pressures = dict(
        db.session.query(WaterSource.catchment, func.sum(WaterSource.industrial_pressure_score))
        .filter(WaterSource.catchment.isnot(None))
        .group_by(WaterSource.catchment)
        .all()
    )

    water_points = WaterPoint.query.all()
    predicted = 0
    for wp in water_points:
        catchment_pressure = 0.0
        if wp.water_source and wp.water_source.catchment:
            catchment_pressure = catchment_pressures.get(wp.water_source.catchment, 0.0)

        prediction = predict_single(wp, catchment_pressure=catchment_pressure)
        if prediction:
            wp.risk_probability = prediction.probability
            wp.current_status = prediction.status
            wp.prediction_confidence = prediction.confidence
            wp.last_prediction_date = utcnow()
            predicted += 1

    db.session.commit()
    click.echo(f"Predicted risk for {predicted} water points.")


@app.cli.command("dedupe-water-points")
@click.option("--preview", is_flag=True, help="List duplicate groups without deleting anything.")
@click.option("--user-id", "user_id", default=1, type=int, help="User ID to attribute the audit log entry to.")
def dedupe_water_points(preview, user_id):
    """Find and merge duplicate water points (same ID variant or same location)."""
    from app.models import AuditLog, User, WaterPoint

    from app.services.water_point_service import find_duplicate_groups, merge_all_duplicates

    groups = find_duplicate_groups()
    if not groups:
        click.echo("No duplicate water points found.")
        return

    for group in groups:
        points = group["points"]
        reason = "same ID" if group["reason"] == "id" else "same location"
        click.echo(
            f"[{reason}] {len(points)} points -> keep #{points[0].id} ({points[0].water_point_id}), "
            f"merge {', '.join(f'#{wp.id} ({wp.water_point_id})' for wp in points[1:])}"
        )

    if preview:
        click.echo(f"{len(groups)} duplicate group(s) found; nothing deleted (--preview).")
        return

    actor = User.query.get(user_id) if user_id else None
    summary = merge_all_duplicates()
    db.session.add(
        AuditLog(
            user_id=actor.id if actor else None,
            action="dedupe_water_points",
            details=(
                f"Merged {summary['removed']} duplicate water point(s) "
                f"across {summary['groups']} group(s), keeping {summary['kept']}."
            ),
        )
    )
    db.session.commit()
    click.echo(
        f"Merged {summary['removed']} duplicate(s) across {summary['groups']} group(s). "
        f"Total water points now: {WaterPoint.query.count()}."
    )


@app.cli.command("reset-password")
@click.option("--email", required=True, help="Email of the user whose password to reset.")
@click.option("--password", default=None, help="New password. Auto-generated if omitted.")
@click.option("--force-change/--no-force-change", default=True, help="Force the user to change the password on next login (default: on).")
def reset_password_command(email, password, force_change):
    """Reset a user's password from the command line."""
    import secrets

    import bcrypt
    from sqlalchemy import func

    from app.models import AuditLog, User

    user = User.query.filter(func.lower(User.email) == email.strip().lower()).first()
    if user is None:
        raise click.ClickException(f"No user found with email {email}")

    new_password = password or secrets.token_urlsafe(12)
    user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.must_change_password = bool(force_change)
    db.session.add(
        AuditLog(
            user_id=user.id,
            action="password_reset_cli",
            details=f"Password reset for {user.email} via CLI",
        )
    )
    db.session.commit()
    click.echo(f"Password reset for {user.email} ({user.full_name}).")
    if not password:
        click.echo(f"New password: {new_password}")
    if force_change:
        click.echo("User must change this password on next login.")


if __name__ == "__main__":
    app.run(debug=True)
