import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent


def load_config(path="config.toml"):
    with open(ROOT / path, "rb") as f:
        return tomllib.load(f)


def results_dir(cfg):
    d = ROOT / "results" / cfg["experiment"]
    (d / "scores").mkdir(parents=True, exist_ok=True)
    return d


def read_csv(path):
    # dtype=str + no NA parsing: empty code stays "", IDs like "0001" stay strings.
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def append_csv(rows, path):
    pd.DataFrame(rows).to_csv(path, mode="a", header=not path.exists(), index=False)


def done_ids(path):
    """sample_ids already written to `path`; stages skip these so a rerun resumes."""
    return set(read_csv(path)["sample_id"]) if path.exists() else set()


# One file per Category in results/<experiment>/; samples.csv combines them for the Detectors.
CATEGORY_FILES = {"Human": "human.csv", "Direct": "direct.csv",
                  "Style-prompted": "style_prompted.csv", "Human-fixed": "human_fixed.csv"}
FORMATTED_FILE = "formatted.csv"  # black-formatted copies of every Sample (not a Category)
SAMPLE_COLUMNS = ["sample_id", "problem_id", "label", "category", "generator", "model_id",
                  "edit_count", "source_id", "post_type", "site", "formatted", "code"]


def combine(d):
    """Rebuild samples.csv from the Category files and the formatted copies. Rows whose status is not "kept" are left out."""
    parts = []
    for f in [*CATEGORY_FILES.values(), FORMATTED_FILE]:
        if (d / f).exists():
            df = read_csv(d / f)
            if "status" in df:
                df = df[df["status"] == "kept"]
            df = df.reindex(columns=SAMPLE_COLUMNS, fill_value="")
            df["formatted"] = df["formatted"].replace("", "False")
            parts.append(df)
    if parts:
        pd.concat(parts).to_csv(d / "samples.csv", index=False)
