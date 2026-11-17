"""Stage 1: build results/<experiment>/samples.csv from human code and Generators."""
import os
import re

import pandas as pd

from common import ROOT, append_csv, read_csv, results_dir

COLUMNS = ["sample_id", "problem_id", "label", "generator", "model_id", "code", "raw_response"]
_FENCE_PY = re.compile(r"```(?:python3?|py)[ \t]*\n(.*?)```", re.DOTALL)
_FENCE_BARE = re.compile(r"```[ \t]*\n(.*?)```", re.DOTALL)


def extract_code(text):
    """First ```python block, else first untagged block, else "" (never the prose)."""
    m = _FENCE_PY.search(text) or _FENCE_BARE.search(text)
    return m.group(1).strip() if m else ""


def generate(cfg, force=False):
    out = results_dir(cfg) / "samples.csv"
    if force:
        # Regenerated Samples reuse sample_ids, so old Scores would silently attach to new code.
        out.unlink(missing_ok=True)
        for f in (out.parent / "scores").glob("*.csv"):
            f.unlink()
        print("force: cleared samples.csv and all scores")
    done = set(read_csv(out)["sample_id"]) if out.exists() else set()

    problems = read_csv(ROOT / cfg["problems"])
    template = (ROOT / cfg["template"]).read_text()

    # Human Samples: one per non-empty human_code row.
    human = problems[problems["human_code"].str.strip() != ""].copy()
    human["sample_id"] = "human:" + human["problem_id"] + ":" + human.groupby("problem_id").cumcount().astype(str)
    human = human[~human["sample_id"].isin(done)]
    if len(human):
        append_csv(pd.DataFrame({
            "sample_id": human["sample_id"], "problem_id": human["problem_id"], "label": "human",
            "generator": "human", "model_id": "", "code": human["human_code"], "raw_response": "",
        })[COLUMNS], out)
    print(f"human: {len(human)} new Samples")

    # LLM Samples: one per (Generator, unique Problem). Appended one by one so a crash resumes.
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    unique = problems.drop_duplicates("problem_id")
    for g in cfg["generators"]:
        new = failed = no_code = 0
        for pid, statement in zip(unique["problem_id"], unique["statement"]):
            sid = f"{g['name']}:{pid}"
            if sid in done:
                continue
            extra = {"temperature": g["temperature"]} if "temperature" in g else {}
            try:
                r = client.chat.completions.create(
                    model=g["model_id"],
                    messages=[{"role": "user", "content": template.replace("{problem}", statement)}],
                    **extra,
                )
                raw = r.choices[0].message.content or ""
            except Exception as e:  # not written -> retried on next call
                failed += 1
                print(f"  {sid} failed: {e}")
                continue
            code = extract_code(raw)
            no_code += code == ""
            append_csv(pd.DataFrame([[sid, pid, "llm", g["name"], g["model_id"], code, raw]], columns=COLUMNS), out)
            new += 1
        print(f"{g['name']}: {new} new, {failed} failed (rerun to retry), {no_code} with no code block")


if __name__ == "__main__":
    assert extract_code("hi\n```python\nx = 1\n```\nbye") == "x = 1"
    assert extract_code("```py\nx = 1\n```") == "x = 1"
    assert extract_code("```\nx = 1\n```") == "x = 1"
    assert extract_code("```bash\nls\n```\n```python\nx = 1\n```") == "x = 1"
    assert extract_code("no code here") == ""
    print("generate self-check ok")
