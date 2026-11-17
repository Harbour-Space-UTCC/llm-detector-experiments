"""Stage 2: one Run per Detector -> results/<experiment>/scores/<detector>.csv."""
import importlib

from .common import append_csv, done_ids, read_csv, results_dir

CHUNK = 64  # Scores are appended per chunk, so a crash mid-Run resumes


def score(cfg, only=None, force=False):
    d = results_dir(cfg)
    samples = read_csv(d / "samples.csv")
    samples = samples[samples["code"].str.strip() != ""]
    for name in [only] if only else cfg.get("detectors", {}):
        out = d / "scores" / f"{name}.csv"
        if force:
            out.unlink(missing_ok=True)
        todo = samples[~samples["sample_id"].isin(done_ids(out))]
        detector = importlib.import_module(f"detectors.{name}")
        for i in range(0, len(todo), CHUNK):
            chunk = todo.iloc[i:i + CHUNK]
            scores = detector.score(chunk["code"].tolist())
            if len(scores) != len(chunk):
                raise ValueError(f"{name}.score returned {len(scores)} Scores for {len(chunk)} codes")
            append_csv({"sample_id": chunk["sample_id"], "score": scores}, out)
        print(f"{name}: scored {len(todo)} new Samples")
