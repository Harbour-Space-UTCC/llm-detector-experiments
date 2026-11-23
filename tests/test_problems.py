"""datasets.csv -> problems.csv on a few hand-made rows."""
import pandas as pd

from modules.generate import human_samples
from modules.problems import convert

COLS = ["sample_id", "site", "code_source", "question_title", "question_text", "code", "code_parses"]


def test_convert_keeps_parsing_rows_only(tmp_path):
    rows = [
        ["H1", "stackoverflow", "answer", "Sum a list", "How do I sum?", "print(sum(x))", "True"],
        ["N2", "codereview", "question", "Review my loop", "Is this ok?\n\nThanks", "for i in x:\n    pass", "True"],
        ["F3", "github", "answer", "Broken", "Why?", "def (:", "False"],
    ]
    src, dst = tmp_path / "datasets.csv", tmp_path / "problems.csv"
    pd.DataFrame(rows, columns=COLS).to_csv(src, index=False, encoding="utf-8-sig")  # BOM, as delivered
    p = convert(src, dst)
    assert list(p["problem_id"]) == ["H1", "N2"]
    assert p["statement"][1] == "Review my loop\n\nIs this ok?\n\nThanks"
    assert list(p["post_type"]) == ["answer", "question"] and list(p["site"]) == ["stackoverflow", "codereview"]
    assert (pd.read_csv(dst, dtype=str, keep_default_na=False) == p.astype(str)).all().all()
    h = human_samples(p)
    assert [(s["post_type"], s["site"]) for s in h] == [("answer", "stackoverflow"), ("question", "codereview")]


def test_config_names_inputs_in_data_and_templates_folders():
    from modules.common import ROOT, load_config
    cfg = load_config(ROOT / "config.toml")
    assert "direct" in cfg["prompts"] and cfg["problems"] == "inputs/data/problems.csv"
    prompt_files = [f"inputs/templates/{n}.jsonl" for n in cfg["prompts"]]
    for p in [*prompt_files, cfg["problems"], "inputs/templates/style.txt", "inputs/data/datasets.csv"]:
        assert (ROOT / p).is_file(), p
