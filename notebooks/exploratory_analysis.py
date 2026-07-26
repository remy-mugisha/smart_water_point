"""Exploratory data analysis for the water point failure-risk dataset.

Standalone script (not a notebook) so it needs no Jupyter dependency — run
it directly and it writes every plot to static/images/eda/ plus a short
console summary. Intended to be referenced in the final report's "Data
Understanding" section alongside its output plots.

Usage:
    python -m notebooks.exploratory_analysis --data data/raw/sample_training_data.csv
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from app.ml_features import normalize_columns

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("static/images/eda")


def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    df = pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_excel(p)
    df = normalize_columns(df)
    if "year_installed" in df.columns:
        df["age"] = pd.Timestamp.now().year - df["year_installed"]
    return df


def summarize(df: pd.DataFrame) -> None:
    print("=== Dataset summary ===")
    print(f"Rows: {len(df)}  Columns: {list(df.columns)}")
    numeric_cols = [c for c in ("age", "population_served", "monthly_rainfall") if c in df.columns]
    if numeric_cols:
        print(df[numeric_cols].describe().round(1))
    if "current_status" in df.columns:
        print("\nStatus distribution:")
        print(df["current_status"].value_counts())


def plot_distributions(df: pd.DataFrame, output_dir: Path) -> None:
    numeric_cols = [c for c in ("age", "population_served", "monthly_rainfall") if c in df.columns]
    for col in numeric_cols:
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.histplot(df[col].dropna(), kde=True, ax=ax, color="#2563eb")
        ax.set_title(f"Distribution of {col}")
        fig.tight_layout()
        fig.savefig(output_dir / f"distribution_{col}.png", dpi=120)
        plt.close(fig)


def plot_technology_counts(df: pd.DataFrame, output_dir: Path) -> None:
    if "technology_type" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    df["technology_type"].value_counts().plot(kind="bar", ax=ax, color="#16a34a")
    ax.set_title("Technology Type Counts")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(output_dir / "technology_type_counts.png", dpi=120)
    plt.close(fig)


def plot_status_pie(df: pd.DataFrame, output_dir: Path) -> None:
    if "current_status" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    df["current_status"].value_counts().plot(
        kind="pie", ax=ax, autopct="%1.0f%%", colors=["#16a34a", "#dc2626"], ylabel=""
    )
    ax.set_title("Functional vs Non-Functional")
    fig.tight_layout()
    fig.savefig(output_dir / "status_pie.png", dpi=120)
    plt.close(fig)


def plot_correlation_heatmap(df: pd.DataFrame, output_dir: Path) -> None:
    numeric_cols = [c for c in ("age", "population_served", "monthly_rainfall") if c in df.columns]
    if "current_status" in df.columns:
        df = df.copy()
        df["target"] = (df["current_status"] == "Non-Functional").astype(int)
        numeric_cols = numeric_cols + ["target"]
    if len(numeric_cols) < 2:
        return
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlation Matrix")
    fig.tight_layout()
    fig.savefig(output_dir / "correlation_heatmap.png", dpi=120)
    plt.close(fig)

    if "target" in df.columns:
        correlations = df[numeric_cols].corr()["target"].drop("target").sort_values(key=abs, ascending=False)
        print("\nFeatures most correlated with failure (Non-Functional):")
        print(correlations.round(3))


def plot_box_by_status(df: pd.DataFrame, output_dir: Path) -> None:
    if "current_status" not in df.columns:
        return
    for col in ("age", "population_served"):
        if col not in df.columns:
            continue
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.boxplot(
            data=df, x="current_status", y=col, hue="current_status", ax=ax,
            palette={"Functional": "#16a34a", "Non-Functional": "#dc2626"}, legend=False,
        )
        ax.set_title(f"{col} by Status")
        fig.tight_layout()
        fig.savefig(output_dir / f"boxplot_{col}_by_status.png", dpi=120)
        plt.close(fig)


def plot_scatter_age_population(df: pd.DataFrame, output_dir: Path) -> None:
    if not {"age", "population_served", "current_status"}.issubset(df.columns):
        return
    fig, ax = plt.subplots(figsize=(6, 4.5))
    sns.scatterplot(
        data=df, x="age", y="population_served", hue="current_status",
        palette={"Functional": "#16a34a", "Non-Functional": "#dc2626"}, ax=ax,
    )
    ax.set_title("Age vs Population Served, by Status")
    fig.tight_layout()
    fig.savefig(output_dir / "scatter_age_population.png", dpi=120)
    plt.close(fig)


def plot_rainfall_distribution(df: pd.DataFrame, output_dir: Path) -> None:
    if "monthly_rainfall" not in df.columns:
        return
    fig, ax = plt.subplots(figsize=(5, 4))
    seasons = pd.cut(df["monthly_rainfall"], bins=[-1, 50, 1000], labels=["Dry (<=50mm)", "Rainy (>50mm)"])
    sns.histplot(x=df["monthly_rainfall"], hue=seasons, ax=ax, multiple="stack")
    ax.set_title("Rainfall Distribution by Season")
    fig.tight_layout()
    fig.savefig(output_dir / "rainfall_by_season.png", dpi=120)
    plt.close(fig)


def run(data_path: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(data_path)
    summarize(df)
    plot_distributions(df, OUTPUT_DIR)
    plot_technology_counts(df, OUTPUT_DIR)
    plot_status_pie(df, OUTPUT_DIR)
    plot_correlation_heatmap(df, OUTPUT_DIR)
    plot_box_by_status(df, OUTPUT_DIR)
    plot_scatter_age_population(df, OUTPUT_DIR)
    plot_rainfall_distribution(df, OUTPUT_DIR)
    print(f"\nSaved plots to {OUTPUT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exploratory analysis of water point data.")
    parser.add_argument("--data", required=True, help="Path to CSV/XLSX water point data.")
    args = parser.parse_args()
    run(args.data)
