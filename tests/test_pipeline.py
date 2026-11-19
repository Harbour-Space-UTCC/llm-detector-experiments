"""Category files -> samples.csv -> summary.csv, without calling any Generator or real Detector."""
import pandas as pd
import pytest

from modules import common
from modules.common import append_csv, read_csv
from modules.humanize import humanize
from modules.metrics import metrics

DIRECT_CODE = '''def main():
    numbers = list(map(int, input().split()))
    result = sum([value * 2 for value in numbers])
    print(f"Total: {result}")


if __name__ == "__main__":
    main()
'''


@pytest.fixture
def exp(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    cfg = {"experiment": "t", "fpr_fallback": 0.05,
           "detectors": {"fake": {"threshold": 0.5, "paper_miss_rate": 0.1}}}
    d = common.results_dir(cfg)
    append_csv([{"sample_id": f"human:p1:{i}", "problem_id": "p1", "label": "human", "category": "Human",
                 "generator": "human", "model_id": "", "code": "print(1)", "raw_response": ""} for i in range(4)],
               d / "human.csv")
    append_csv([{"sample_id": "g:p1", "problem_id": "p1", "label": "llm", "category": "Direct",
                 "generator": "g", "model_id": "m", "code": DIRECT_CODE, "raw_response": ""},
                {"sample_id": "g:p2", "problem_id": "p2", "label": "llm", "category": "Direct",
                 "generator": "g", "model_id": "m", "code": "def (:", "raw_response": ""}],
               d / "direct.csv")
    humanize(cfg)
    return cfg, d


def test_samples_combine_every_category_and_leave_out_dropped(exp):
    _, d = exp
    s = read_csv(d / "samples.csv")
    assert s["category"].value_counts().to_dict() == {"Human": 4, "Direct": 2, "Human-fixed": 2}
    hf = s[s["category"] == "Human-fixed"]
    assert set(hf["source_id"]) == {"g:p1"}  # g:p2 does not parse, so its rows are dropped
    assert set(hf["edit_count"]) <= {"1", "2", "3", "4", "5"}
    assert (s.loc[s["category"] != "Human-fixed", ["edit_count", "source_id"]] == "").all().all()


def test_metrics_one_row_per_category_and_outdated_only_for_direct(exp):
    cfg, d = exp
    s = read_csv(d / "samples.csv")
    scores = s["category"].map({"Human": 0.1, "Direct": 0.9, "Human-fixed": 0.2})  # edits fool the Detector
    pd.DataFrame({"sample_id": s["sample_id"], "score": scores}).to_csv(d / "scores" / "fake.csv", index=False)
    out = metrics(cfg).set_index(["category", "edit_count"])
    direct = out.loc[("Direct", "")]
    assert direct["miss_rate"] == 0 and not direct["outdated"]
    hf = out.drop(index="Direct", level="category")
    assert (hf["miss_rate"] == 1).all() and hf["outdated"].isna().all()


def test_humanize_force_drops_only_human_fixed_scores(exp):
    cfg, d = exp
    ids = read_csv(d / "samples.csv")["sample_id"]
    pd.DataFrame({"sample_id": ids, "score": 0.5}).to_csv(d / "scores" / "fake.csv", index=False)
    humanize(cfg, force=True)
    left = set(read_csv(d / "scores" / "fake.csv")["sample_id"])
    assert left == {i for i in ids if ":hf" not in i}


def test_metrics_split_by_post_type_and_site_with_line_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    cfg = {"experiment": "t", "fpr_fallback": 0.05, "detectors": {"fake": {"threshold": 0.5, "paper_miss_rate": 0.1}}}
    d = common.results_dir(cfg)
    rows = [("h1", "Human", "question", "github", "a\nb\nc", 0.9), ("h2", "Human", "question", "github", "a\nb\nc", 0.8),
            ("h3", "Human", "answer", "codereview", "a", 0.1), ("h4", "Human", "answer", "codereview", "a", 0.2),
            ("l1", "Direct", "", "", "a\nb", 0.4)]
    pd.DataFrame([{"sample_id": i, "category": c, "generator": "g" if c != "Human" else "human", "edit_count": "",
                   "post_type": pt, "site": site, "code": code} for i, c, pt, site, code, _ in rows]
                 ).to_csv(d / "samples.csv", index=False)
    pd.DataFrame({"sample_id": [r[0] for r in rows], "score": [r[5] for r in rows]}).to_csv(d / "scores" / "fake.csv", index=False)
    out = metrics(cfg).set_index("human_split")
    assert set(out.index) == {"all", "post_type=question", "post_type=answer", "site=github", "site=codereview"}
    assert out.loc["post_type=question", "achieved_fpr"] == 1 and out.loc["post_type=answer", "achieved_fpr"] == 0
    assert out.loc["post_type=question", "auroc"] == 0 and out.loc["post_type=answer", "auroc"] == 1
    assert out.loc["all", "median_lines"] == 2 and out.loc["all", "human_median_lines"] == 2
    assert out.loc["post_type=answer", "human_median_lines"] == 1
    assert out["threshold"].nunique() == 1  # every split uses the threshold from all Human Samples
    assert out.loc["all", "outdated"] and out.drop(index="all")["outdated"].isna().all()
