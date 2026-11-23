"""Prompts stage: every Prompt Template filled with every Problem, one JSONL file per template."""
import pytest

from modules import prompts

CFG = {"problems": "inputs/data/problems.csv"}

@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "ROOT", tmp_path)
    (tmp_path / "inputs/data").mkdir(parents=True)
    (tmp_path / "inputs/templates").mkdir()
    # Unsorted, p2 twice (two human solutions), non-ASCII statement.
    (tmp_path / "inputs/data/problems.csv").write_text(
        "problem_id,statement,human_code,post_type,site\n"
        "p2,Café über,print(3),question,github\n"
        "p1,Sum it,print(2),answer,github\n"
        "p2,Café über,print(4),answer,github\n", encoding="utf-8")
    (tmp_path / "inputs/templates/direct.txt").write_text("PLAIN {problem}")
    (tmp_path / "inputs/templates/style.txt").write_text("STYLE\n{problem}")
    return tmp_path


def test_writes_one_sorted_jsonl_per_template(root):
    prompts.write_prompts(CFG)
    t = root / "inputs/templates"
    assert (t / "direct.jsonl").read_bytes().decode("utf-8") == (
        '{"problem_id": "p1", "prompt": "PLAIN Sum it"}\n'
        '{"problem_id": "p2", "prompt": "PLAIN Café über"}\n')
    assert (t / "style.jsonl").read_bytes().decode("utf-8") == (
        '{"problem_id": "p1", "prompt": "STYLE\\nSum it"}\n'
        '{"problem_id": "p2", "prompt": "STYLE\\nCafé über"}\n')
    assert sorted(p.name for p in t.iterdir()) == ["direct.jsonl", "direct.txt", "style.jsonl", "style.txt"]


def test_problems_come_from_the_config_problems_file(root):
    # The same file generate() reads Human Samples from, so Prompts and Human Samples share Problems.
    (root / "inputs/data/subset.csv").write_text(
        "problem_id,statement,human_code,post_type,site\n"
        "p9,Only me,print(9),answer,github\n", encoding="utf-8")
    prompts.write_prompts({"problems": "inputs/data/subset.csv"})
    assert (root / "inputs/templates/direct.jsonl").read_text(encoding="utf-8") == (
        '{"problem_id": "p9", "prompt": "PLAIN Only me"}\n')


def test_template_without_placeholder_stops_the_stage_naming_the_file(root):
    (root / "inputs/templates/style.txt").write_text("STYLE with no placeholder")
    with pytest.raises(ValueError, match=r"inputs/templates/style.txt has no \{problem\} placeholder"):
        prompts.write_prompts(CFG)
    assert not list((root / "inputs/templates").glob("*.jsonl"))


def test_committed_prompt_files_match_templates_and_problems():
    """Real repo files: a template or Problems edit without rerunning the stage, or a Prompt file left after its template was removed, fails here."""
    from modules.common import ROOT, load_config, read_csv
    problems = read_csv(ROOT / load_config()["problems"])
    templates = sorted((ROOT / prompts.TEMPLATES_DIR).glob("*.txt"))
    assert templates
    for t in templates:
        out = t.with_suffix(".jsonl")
        fix = f"{out.relative_to(ROOT).as_posix()} is stale: run `python -m modules.prompts` and commit it"
        assert out.is_file(), fix
        assert out.read_bytes() == prompts.fill(t.read_text(encoding="utf-8"), problems).encode("utf-8"), fix
    for out in (ROOT / prompts.TEMPLATES_DIR).glob("*.jsonl"):
        assert out.with_suffix(".txt").is_file(), (
            f"{out.relative_to(ROOT).as_posix()} has no {out.stem}.txt template: delete it or restore the template")
