import click

from app import create_app, db

app = create_app()


@app.cli.command("init-db")
def init_db():
    """Create database tables."""
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


if __name__ == "__main__":
    app.run(debug=True)
