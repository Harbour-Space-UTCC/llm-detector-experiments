"""generate(): Direct and, when `style_template` is set, Style-prompted Samples, with a fake client."""
import pytest

from modules import common, generate as gen
from modules.common import read_csv
from modules.humanize import humanize
from modules.metrics import metrics
import pandas as pd


class FakeClient:
    prompts = []

    def __init__(self, **_):
        self.chat = self
        self.completions = self

    def create(self, model, messages, **_):
        FakeClient.prompts.append(messages[0]["content"])
        text = "```python\nprint(1)\n```"
        msg = type("M", (), {"content": text})
        return type("R", (), {"choices": [type("C", (), {"message": msg})]})


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(gen, "ROOT", tmp_path)
    monkeypatch.setattr(gen, "OpenAI", FakeClient)
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    FakeClient.prompts = []
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/problems.csv").write_text(
        "problem_id,statement,human_code,post_type,site\np1,Sum it,print(2),answer,github\np2,Add it,print(3),question,github\n")
    (tmp_path / "inputs/template.txt").write_text("PLAIN {problem}")
    (tmp_path / "inputs/style_template.txt").write_text("STYLE {problem}")
    return {"experiment": "t", "template": "inputs/template.txt", "problems": "inputs/problems.csv",
            "fpr_fallback": 0.05, "generators": [{"name": "g", "model_id": "m"}],
            "detectors": {"fake": {"threshold": 0.5}}}


def test_without_key_nothing_changes(cfg):
    gen.generate(cfg)
    d = common.results_dir(cfg)
    assert not (d / "style_prompted.csv").exists()
    assert set(read_csv(d / "samples.csv")["category"]) == {"Human", "Direct"}


def test_style_samples_use_style_template_and_id(cfg):
    cfg["style_template"] = "inputs/style_template.txt"
    gen.generate(cfg)
    d = common.results_dir(cfg)
    style = read_csv(d / "style_prompted.csv")
    assert list(style["sample_id"]) == ["g:p1:style", "g:p2:style"]
    assert set(style["category"]) == {"Style-prompted"} and set(style["label"]) == {"llm"}
    assert sorted(FakeClient.prompts) == ["PLAIN Add it", "PLAIN Sum it", "STYLE Add it", "STYLE Sum it"]
    assert set(read_csv(d / "direct.csv")["sample_id"]) == {"g:p1", "g:p2"}


def test_rerun_skips_and_force_clears(cfg):
    cfg["style_template"] = "inputs/style_template.txt"
    gen.generate(cfg)
    n = len(FakeClient.prompts)
    gen.generate(cfg)
    assert len(FakeClient.prompts) == n  # nothing regenerated
    d = common.results_dir(cfg)
    pd.DataFrame({"sample_id": ["g:p1:style"], "score": [0.5]}).to_csv(d / "scores" / "fake.csv", index=False)
    gen.generate(cfg, force=True)
    assert len(FakeClient.prompts) == 2 * n
    assert not (d / "scores" / "fake.csv").exists()


def test_human_fixed_only_from_direct_and_summary_has_style_rows(cfg):
    cfg["style_template"] = "inputs/style_template.txt"
    gen.generate(cfg)
    humanize(cfg)
    d = common.results_dir(cfg)
    s = read_csv(d / "samples.csv")
    hf = s[s["category"] == "Human-fixed"]
    assert not hf["source_id"].str.endswith(":style").any()
    pd.DataFrame({"sample_id": s["sample_id"], "score": 0.5}).to_csv(d / "scores" / "fake.csv", index=False)
    assert "Style-prompted" in set(metrics(cfg)["category"])
