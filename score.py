"""Stage 2: one Run per Detector -> results/<experiment>/scores/<detector>.csv."""
import importlib

import pandas as pd

from common import append_csv, read_csv, results_dir

CHUNK = 64  # Scores appended per chunk, so a crash mid-Run resumes


def score(cfg, only=None, force=False):
    d = results_dir(cfg)
    samples = read_csv(d / "samples.csv")
    samples = samples[samples["code"].str.strip() != ""]
    names = [only] if only else list(cfg.get("detectors", {}))
    for name in names:
        out = d / "scores" / f"{name}.csv"
        if force and out.exists():
            out.unlink()
        done = set(read_csv(out)["sample_id"]) if out.exists() else set()
        todo = samples[~samples["sample_id"].isin(done)]
        detector = importlib.import_module(f"detectors.{name}")
        for i in range(0, len(todo), CHUNK):
            chunk = todo.iloc[i:i + CHUNK]
            scores = detector.score(chunk["code"].tolist())
            assert len(scores) == len(chunk), f"{name}.score returned {len(scores)} scores for {len(chunk)} codes"
            append_csv(pd.DataFrame({"sample_id": chunk["sample_id"], "score": scores}), out)
        print(f"{name}: scored {len(todo)} new Samples")
