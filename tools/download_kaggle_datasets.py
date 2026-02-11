from __future__ import annotations

import json
import os
from pathlib import Path


DATASETS = [
    "subhajournal/phishingemails",
    "shashwatwork/web-page-phishing-detection-dataset",
    "hasibur013/phishing-data",
    "naserabdullahalam/phishing-email-dataset",
    "ethancratchley/email-phishing-dataset",
    "sai10py/phishing-websites-data",
    "xblock/ethereum-phishing-transaction-network",
    "faizaniftikharjanjua/metaverse-financial-transactions-dataset",
    "zackyzac/phishing-sites-screenshot",
    "evilspirit05/phising-data",
    "phangud/spamcsv",
]


def main() -> None:
    token = os.getenv("KAGGLE_API_TOKEN")
    if not token:
        raise SystemExit(
            "KAGGLE_API_TOKEN is not set. Export it before running this script."
        )

    try:
        import kagglehub
    except Exception as exc:
        raise SystemExit(f"kagglehub import failed: {exc}")

    out_dir = Path("data/kaggle")
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_map = {}

    for dataset in DATASETS:
        try:
            path = kagglehub.dataset_download(dataset)
            dataset_map[dataset] = path
            print(f"downloaded: {dataset}")
            print(f"path: {path}")
        except Exception as exc:
            dataset_map[dataset] = f"ERROR: {exc}"
            print(f"failed: {dataset} -> {exc}")

    (out_dir / "download_map.json").write_text(
        json.dumps(dataset_map, indent=2), encoding="utf-8"
    )
    print(f"saved map: {out_dir / 'download_map.json'}")


if __name__ == "__main__":
    main()
