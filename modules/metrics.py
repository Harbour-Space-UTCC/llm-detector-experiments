"""Stage 3: Scores -> results/<experiment>/summary.csv (one row per Detector x Generator x Category x Edit count x formatted x human split)."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .common import read_csv, results_dir


def fallback_threshold(human, fpr):
    """Smallest observed human Score with at most `fpr` of human Scores above it. Flag rule: score > threshold."""
    return float(np.quantile(human, 1 - fpr, method="higher"))


def summarize(human, llm, threshold):
    """human, llm: arrays of Scores. Positive class = LLM-written."""
    human, llm = np.asarray(human, float), np.asarray(llm, float)
    y = np.r_[np.zeros(len(human)), np.ones(len(llm))]
    return {
        "n_human": len(human),
        "n_llm": len(llm),
        "auroc": roc_auc_score(y, np.r_[human, llm]),
        "threshold": threshold,
        "achieved_fpr": float(np.mean(human > threshold)),
        "miss_rate": float(np.mean(llm <= threshold)),
    }


def median_lines(codes):
    return float(np.median([len(c.splitlines()) for c in codes]))


ALL = "all"  # human_split of the row that uses every Human Sample


def human_splits(human):
    """("all", all Human rows), then one subset per Post type and per site. Blank values (non-forum Problems) are skipped."""
    yield ALL, human
    for col in ("post_type", "site"):
        for value, g in human.groupby(col):
            if value:
                yield f"{col}={value}", g


def metrics(cfg):
    d = results_dir(cfg)
    samples = read_csv(d / "samples.csv")[
        ["sample_id", "category", "generator", "edit_count", "post_type", "site", "formatted", "code"]]
    rows = []
    for name, dcfg in cfg.get("detectors", {}).items():
        path = d / "scores" / f"{name}.csv"
        if not path.exists():
            print(f"{name}: no scores, skipped")
            continue
        s = read_csv(path).merge(samples, on="sample_id")
        s["score"] = s["score"].astype(float)
        # Formatted copies are measured on their own. A Detector with no paper threshold takes its threshold from
        # the formatted Human Samples; one with a paper threshold keeps it, and achieved_fpr shows any shift.
        for formatted, sf in s.groupby("formatted"):
            human_rows = sf[sf["category"] == "Human"]
            human = human_rows["score"].to_numpy()  # one threshold for every Category and human split of this `formatted` value
            if len(human) == 0:
                if formatted == "True":  # e.g. black could not format a single Human Sample
                    print(f"{name}: no formatted Human Samples scored, formatted rows skipped")
                    continue
                raise ValueError(f"{name}: no human Samples scored; FPR and AUROC need them")
            if "threshold" in dcfg:
                threshold, source = dcfg["threshold"], "paper"
            else:
                fpr = dcfg.get("fpr", cfg["fpr_fallback"])
                threshold, source = fallback_threshold(human, fpr), f"fpr={fpr}"
            llm = sf[sf["category"] != "Human"]
            splits = [(name_, h, median_lines(h["code"])) for name_, h in human_splits(human_rows)]
            for (gen, cat, ec), g in llm.groupby(["generator", "category", "edit_count"]):
                for split, h, h_lines in splits:
                    r = {"detector": name, "generator": gen, "category": cat, "edit_count": ec,
                         "formatted": formatted, "human_split": split, "threshold_source": source,
                         **summarize(h["score"], g["score"], threshold),
                         "median_lines": median_lines(g["code"]), "human_median_lines": h_lines}
                    # papers measured plain, unformatted LLM output
                    if "paper_miss_rate" in dcfg and cat == "Direct" and split == ALL and formatted == "False":
                        r["paper_miss_rate"] = dcfg["paper_miss_rate"]
                        r["outdated"] = r["miss_rate"] > dcfg["paper_miss_rate"]
                    rows.append(r)
    summary = pd.DataFrame(rows)
    summary.to_csv(d / "summary.csv", index=False)
    return summary


if __name__ == "__main__":
    h = np.linspace(0, 0.49, 100)            # human Scores all below every LLM Score
    l = np.linspace(0.5, 1, 100)
    r = summarize(h, l, fallback_threshold(h, 0.05))
    assert r["auroc"] == 1 and r["miss_rate"] == 0 and r["achieved_fpr"] <= 0.05, r
    assert summarize(l, h, 0.5)["auroc"] == 0                    # inverted Detector
    t = fallback_threshold(np.arange(100), 0.05)                 # Scores 0..99
    assert t == 95 and np.mean(np.arange(100) > t) == 0.04, t    # flags 96..99: 4% <= 5%
    assert summarize([0, 1], [0.5, 2], 0.5)["miss_rate"] == 0.5  # score == threshold counts as a miss
    print("metrics self-check ok")
