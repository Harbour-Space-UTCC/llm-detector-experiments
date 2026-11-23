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
    (tmp_path / "inputs/data").mkdir(parents=True)
    (tmp_path / "inputs/templates").mkdir()
    (tmp_path / "inputs/data/problems.csv").write_text(
        "problem_id,statement,human_code,post_type,site\np1,Sum it,print(2),answer,github\np2,Add it,print(3),question,github\n")
    for name, word in [("direct", "PLAIN"), ("style", "STYLE"), ("style_v2", "V2")]:
        (tmp_path / f"inputs/templates/{name}.jsonl").write_text(
            f'{{"problem_id": "p1", "prompt": "{word} Sum it"}}\n{{"problem_id": "p2", "prompt": "{word} Add it"}}\n')
    return {"experiment": "t", "prompts": ["direct"], "problems": "inputs/data/problems.csv",
            "fpr_fallback": 0.05, "generators": [{"name": "g", "model_id": "m"}],
            "detectors": {"fake": {"threshold": 0.5}}}


def test_name_left_out_of_prompts_is_skipped(cfg):
    gen.generate(cfg)
    d = common.results_dir(cfg)
    assert not (d / "style_prompted.csv").exists()
    assert set(read_csv(d / "samples.csv")["category"]) == {"Human", "Direct"}


def test_prompts_sent_are_the_jsonl_lines_and_style_id_ends_with_name(cfg):
    cfg["prompts"] = ["direct", "style"]
    gen.generate(cfg)
    d = common.results_dir(cfg)
    style = read_csv(d / "style_prompted.csv")
    assert list(style["sample_id"]) == ["g:p1:style", "g:p2:style"]
    assert set(style["category"]) == {"Style-prompted"} and set(style["label"]) == {"llm"}
    assert sorted(FakeClient.prompts) == ["PLAIN Add it", "PLAIN Sum it", "STYLE Add it", "STYLE Sum it"]
    assert set(read_csv(d / "direct.csv")["sample_id"]) == {"g:p1", "g:p2"}


def test_rerun_skips_and_force_clears(cfg):
    cfg["prompts"] = ["direct", "style"]
    gen.generate(cfg)
    calls_after_first_run = len(FakeClient.prompts)
    gen.generate(cfg)
    assert len(FakeClient.prompts) == calls_after_first_run
    d = common.results_dir(cfg)
    pd.DataFrame({"sample_id": ["g:p1:style"], "score": [0.5]}).to_csv(d / "scores" / "fake.csv", index=False)
    gen.generate(cfg, force=True)
    assert len(FakeClient.prompts) == 2 * calls_after_first_run
    assert not (d / "scores" / "fake.csv").exists()


def test_adding_style_later_generates_only_style(cfg):
    gen.generate(cfg)
    FakeClient.prompts = []
    cfg["prompts"] = ["direct", "style"]
    gen.generate(cfg)
    assert sorted(FakeClient.prompts) == ["STYLE Add it", "STYLE Sum it"]


def test_missing_prompt_file_fails_before_any_call(cfg):
    cfg["prompts"] = ["direct", "nope"]
    with pytest.raises(FileNotFoundError, match="python -m modules.prompts"):
        gen.generate(cfg)
    assert FakeClient.prompts == []


def test_prompts_without_direct_fails_before_any_call(cfg):
    cfg["prompts"] = ["style"]
    with pytest.raises(ValueError, match="direct"):
        gen.generate(cfg)
    assert FakeClient.prompts == []


def test_other_names_are_style_prompted_with_their_own_id(cfg):
    cfg["prompts"] = ["direct", "style", "style_v2"]
    gen.generate(cfg)
    style = read_csv(common.results_dir(cfg) / "style_prompted.csv")
    assert sorted(style["sample_id"]) == ["g:p1:style", "g:p1:style_v2", "g:p2:style", "g:p2:style_v2"]
    assert set(style["category"]) == {"Style-prompted"}
    assert "V2 Add it" in FakeClient.prompts


def test_human_fixed_only_from_direct(cfg):
    cfg["prompts"] = ["direct", "style"]
    gen.generate(cfg)
    humanize(cfg)
    s = read_csv(common.results_dir(cfg) / "samples.csv")
    hf = s[s["category"] == "Human-fixed"]
    assert len(hf) and not hf["source_id"].str.endswith(":style").any()


def test_summary_has_style_rows_for_each_generator(cfg):
    cfg["prompts"] = ["direct", "style"]
    cfg["generators"].append({"name": "g2", "model_id": "m2"})
    gen.generate(cfg)
    d = common.results_dir(cfg)
    s = read_csv(d / "samples.csv")
    pd.DataFrame({"sample_id": s["sample_id"], "score": 0.5}).to_csv(d / "scores" / "fake.csv", index=False)
    out = metrics(cfg)
    assert set(out.loc[out["category"] == "Style-prompted", "generator"]) == {"g", "g2"}
