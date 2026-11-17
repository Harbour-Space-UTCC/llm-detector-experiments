"""Stage 3: Scores -> results/<experiment>/summary.csv (one row per Detector x Generator)."""
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


def metrics(cfg):
    d = results_dir(cfg)
    samples = read_csv(d / "samples.csv")[["sample_id", "label", "generator"]]
    rows = []
    for name, dcfg in cfg.get("detectors", {}).items():
        path = d / "scores" / f"{name}.csv"
        if not path.exists():
            print(f"{name}: no scores, skipped")
            continue
        s = read_csv(path).merge(samples, on="sample_id")
        s["score"] = s["score"].astype(float)
        human = s.loc[s["label"] == "human", "score"].to_numpy()
        if len(human) == 0:
            raise ValueError(f"{name}: no human Samples scored; FPR and AUROC need them")
        paper_t = "threshold" in dcfg
        t = dcfg["threshold"] if paper_t else fallback_threshold(human, cfg["fpr_fallback"])
        for gen, g in s[s["label"] == "llm"].groupby("generator"):
            r = {"detector": name, "generator": gen, "threshold_source": "paper" if paper_t else "fpr_fallback",
                 **summarize(human, g["score"], t)}
            if "paper_miss_rate" in dcfg:
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
