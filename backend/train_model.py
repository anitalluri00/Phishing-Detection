from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


FEATURE_COLUMNS = [
    "Have_IP",
    "Have_At",
    "URL_Length",
    "URL_Depth",
    "Redirection",
    "https_Domain",
    "TinyURL",
    "Prefix/Suffix",
    "DNS_Record",
    "Web_Traffic",
    "Domain_Age",
    "Domain_End",
    "iFrame",
    "Mouse_Over",
    "Right_Click",
    "Web_Forwards",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _load_frame(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = _normalize_columns(df)

    if "Label" not in df.columns:
        raise ValueError(f"{csv_path} is missing 'Label' column")

    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_features:
        raise ValueError(f"{csv_path} missing feature columns: {missing_features}")

    df = df[FEATURE_COLUMNS + ["Label"]].copy()

    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Label"] = pd.to_numeric(df["Label"], errors="coerce")
    # Some phishing datasets use {-1, 1}; normalize to {0, 1}.
    df["Label"] = df["Label"].replace({-1: 0, 2: 1})

    df = df.dropna(subset=FEATURE_COLUMNS + ["Label"])
    df["Label"] = df["Label"].astype(int)
    df = df[df["Label"].isin([0, 1])]
    return df


def train(input_csv: Path, output_model: Path, output_metrics: Path | None) -> None:
    df = _load_frame(input_csv)
    if df.empty:
        raise RuntimeError("Training dataset is empty after cleaning.")

    x = df[FEATURE_COLUMNS].astype(float).values
    y = df["Label"].astype(int).values

    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        raise RuntimeError(
            "Training dataset must include both classes (safe=0 and phishing=1)."
        )

    stratify_target = y if counts.min() >= 2 else None
    if stratify_target is None:
        print(
            "warning=Insufficient samples per class for stratified split; using non-stratified split."
        )

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=stratify_target
    )

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    report = classification_report(y_test, y_pred, output_dict=True)

    output_model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_columns": FEATURE_COLUMNS, "accuracy": accuracy},
        output_model,
    )

    if output_metrics:
        output_metrics.parent.mkdir(parents=True, exist_ok=True)
        output_metrics.write_text(
            json.dumps(
                {
                    "accuracy": accuracy,
                    "rows": int(len(df)),
                    "features": FEATURE_COLUMNS,
                    "classification_report": report,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"trained_rows={len(df)}")
    print(f"accuracy={accuracy:.4f}")
    print(f"model_saved={output_model}")
    if output_metrics:
        print(f"metrics_saved={output_metrics}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train phishing URL model.")
    parser.add_argument(
        "--input-csv",
        default="data/urldata.csv",
        help="Path to engineered training CSV containing feature columns + Label.",
    )
    parser.add_argument(
        "--output-model",
        default="backend/model/model.pkl",
        help="Path to save trained model.",
    )
    parser.add_argument(
        "--output-metrics",
        default="backend/model/metrics.json",
        help="Path to save training metrics JSON.",
    )
    args = parser.parse_args()

    train(
        input_csv=Path(args.input_csv),
        output_model=Path(args.output_model),
        output_metrics=Path(args.output_metrics) if args.output_metrics else None,
    )


if __name__ == "__main__":
    main()
