"""inputs/templates/<name>.txt + inputs/data/problems.csv -> inputs/templates/<name>.jsonl, one Prompt per Problem.
Rerun after editing a Prompt Template or the Problems, and commit the .jsonl files:
    python -m modules.prompts
"""
import json

from .common import ROOT, read_csv

TEMPLATES = "inputs/templates"
PROBLEMS = "inputs/data/problems.csv"


def fill(template, problems):
    """JSONL text: one {"problem_id", "prompt"} line per unique Problem, sorted by problem_id, non-ASCII kept."""
    unique = problems.drop_duplicates("problem_id").sort_values("problem_id")
    return "".join(json.dumps({"problem_id": pid, "prompt": template.replace("{problem}", statement)},
                              ensure_ascii=False) + "\n"
                   for pid, statement in zip(unique["problem_id"], unique["statement"]))


def write_prompts():
    problems = read_csv(ROOT / PROBLEMS)
    templates = {p: p.read_text(encoding="utf-8") for p in sorted((ROOT / TEMPLATES).glob("*.txt"))}
    for path, text in templates.items():  # check all before writing any, so a bad template changes nothing
        if "{problem}" not in text:
            name = path.relative_to(ROOT).as_posix()
            raise ValueError(f"{name} has no {{problem}} placeholder, so every prompt would omit the Problem")
    for path, text in templates.items():
        # write_bytes: no newline translation, so the file is byte-identical on every OS.
        path.with_suffix(".jsonl").write_bytes(fill(text, problems).encode("utf-8"))


if __name__ == "__main__":
    write_prompts()
    print(f"Prompt files written to {TEMPLATES}/")
