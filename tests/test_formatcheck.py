import pandas as pd
import pytest

from modules import common, formatcheck as fc
from modules.common import append_csv, combine, read_csv
from modules.metrics import metrics
from modules.score import score

MESSY = "x=1\nprint( x )\n"
NEAT = "x = 1\nprint(x)\n"


def row(sample_id, category, code, **kw):
    return {"sample_id": sample_id, "problem_id": "p1", "label": "human" if category == "Human" else "llm",
            "category": category, "generator": "human" if category == "Human" else "g", "model_id": "",
            "edit_count": "2" if category == "Human-fixed" else "", "source_id": "",
            "post_type": "answer" if category == "Human" else "", "site": "github" if category == "Human" else "",
            "code": code, **kw}


@pytest.fixture
def exp(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    cfg = {"experiment": "t", "fpr_fallback": 0.25, "detectors": {"random_baseline": {}}}
    d = common.results_dir(cfg)
    append_csv([row("human:p1:0", "Human", MESSY), row("human:p1:1", "Human", NEAT)], d / "human.csv")
    append_csv([row("g:p1", "Direct", MESSY)], d / "direct.csv")
    append_csv([row("g:p1:style", "Style-prompted", MESSY)], d / "style_prompted.csv")
    append_csv([row("g:p1:hf2", "Human-fixed", MESSY, status="kept", source_id="g:p1")], d / "human_fixed.csv")
    combine(d)
    return cfg, d


def test_every_sample_in_every_category_gets_one_formatted_copy(exp):
    cfg, d = exp
    fc.format_copies(cfg)
    s = read_csv(d / "samples.csv")
    copies = s[s["formatted"] == "True"]
    assert len(copies) == 5 and set(copies["category"]) == {"Human", "Direct", "Style-prompted", "Human-fixed"}
    assert (copies["code"] == NEAT).all()
    assert set(copies["source_id"]) == set(s.loc[s["formatted"] == "False", "sample_id"])
    assert (copies["sample_id"] == copies["source_id"] + ":fmt").all()
    originals = s[s["formatted"] == "False"].set_index("sample_id")
    assert originals.loc["human:p1:0", "code"] == MESSY  # originals untouched
    assert (copies["post_type"] == s.set_index("sample_id").loc[copies["source_id"], "post_type"].to_numpy()).all()


def test_unformattable_sample_is_counted_and_logged_not_crashed_on(exp, capsys):
    cfg, d = exp
    append_csv([row("g:p2", "Direct", "def (:")], d / "direct.csv")
    combine(d)
    fc.format_copies(cfg)
    s = read_csv(d / "samples.csv")
    assert "g:p2:fmt" not in set(s["sample_id"]) and "g:p2" in set(s["sample_id"])
    assert "1 could not be formatted" in capsys.readouterr().out
    assert read_csv(d / "formatted.csv").set_index("sample_id").loc["g:p2:fmt", "status"].startswith("failed")


def test_rerun_skips_copies_already_made_and_force_redoes(exp, monkeypatch):
    cfg, d = exp
    calls = []
    real = fc.black.format_str
    monkeypatch.setattr(fc.black, "format_str", lambda *a, **k: calls.append(1) or real(*a, **k))
    fc.format_copies(cfg)
    first = len(calls)
    fc.format_copies(cfg)
    assert len(calls) == first
    fc.format_copies(cfg, force=True)
    assert len(calls) == 2 * first


def test_empty_code_is_not_formatted(exp):
    cfg, d = exp
    append_csv([row("g:p3", "Direct", "")], d / "direct.csv")
    combine(d)
    fc.format_copies(cfg)
    assert "g:p3:fmt" not in set(read_csv(d / "samples.csv")["sample_id"])


def test_wrong_black_version_is_refused(exp, monkeypatch):
    cfg, _ = exp
    monkeypatch.setattr(fc, "BLACK_VERSION", "0.0.1")
    with pytest.raises(RuntimeError, match="black"):
        fc.format_copies(cfg)


def test_toy_run_with_random_baseline_has_formatted_and_unformatted_rows_for_every_category(exp):
    cfg, d = exp
    fc.format_copies(cfg)
    score(cfg)
    out = metrics(cfg)
    out = out[out["human_split"] == "all"]
    pairs = set(zip(out["category"], out["formatted"]))
    for cat in ("Direct", "Style-prompted", "Human-fixed"):
        assert {(cat, "False"), (cat, "True")} <= pairs


def test_formatted_rows_take_their_threshold_from_formatted_human_scores(exp):
    cfg, d = exp
    fc.format_copies(cfg)
    s = read_csv(d / "samples.csv")
    # Unformatted Humans score high, formatted Humans score low: neat formatting would be a clue
    # if one threshold were shared.
    sc = {"False": {"Human": 0.9, "Direct": 0.95}, "True": {"Human": 0.1, "Direct": 0.5}}
    scores = [sc[f].get(c, 0.5) for f, c in zip(s["formatted"], s["category"])]
    pd.DataFrame({"sample_id": s["sample_id"], "score": scores}).to_csv(d / "scores" / "random_baseline.csv", index=False)
    out = metrics(cfg)
    out = out[(out["category"] == "Direct") & (out["human_split"] == "all")].set_index("formatted")
    assert out.loc["False", "threshold"] == 0.9 and out.loc["True", "threshold"] == 0.1
    assert out.loc["False", "miss_rate"] == 0 and out.loc["True", "miss_rate"] == 0
    assert out.loc["True", "n_human"] == 2 and out.loc["False", "n_human"] == 2


def test_humanize_force_drops_formatted_copies_of_human_fixed_only(exp):
    from modules.humanize import humanize
    cfg, d = exp
    fc.format_copies(cfg)
    pd.DataFrame({"sample_id": read_csv(d / "samples.csv")["sample_id"], "score": 0.5}).to_csv(
        d / "scores" / "random_baseline.csv", index=False)
    humanize(cfg, force=True)
    s = read_csv(d / "samples.csv")
    assert not s["sample_id"].str.contains(r":hf\d+:fmt$").any()
    assert {"human:p1:0:fmt", "g:p1:fmt", "g:p1:style:fmt"} <= set(s["sample_id"])
    left = set(read_csv(d / "scores" / "random_baseline.csv")["sample_id"])
    assert not any(":hf" in i for i in left) and "g:p1:fmt" in left
