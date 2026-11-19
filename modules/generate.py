"""Stage 1: human.csv from problems.csv, direct.csv (and style_prompted.csv when `style_template` is set) from the Generators, combined into samples.csv."""
import os
import re
from typing import NamedTuple

from openai import OpenAI

from .common import CATEGORY_FILES, ROOT, append_csv, combine, done_ids, read_csv, results_dir

_FENCE_PY = re.compile(r"```(?:python3?|py)[ \t]*\n(.*?)```", re.DOTALL)
_FENCE_BARE = re.compile(r"```[ \t]*\n(.*?)```", re.DOTALL)


def extract_code(text):
    """First ```python block, else first untagged block, else "" (never the prose)."""
    m = _FENCE_PY.search(text) or _FENCE_BARE.search(text)
    return m.group(1).strip() if m else ""


class Pass(NamedTuple):
    category: str
    template: str
    id_suffix: str


def read_template(path):
    text = (ROOT / path).read_text()
    if "{problem}" not in text:
        raise ValueError(f"{path} has no {{problem}} placeholder, so every prompt would omit the Problem")
    return text


def human_samples(problems):
    human = problems[problems["human_code"].str.strip() != ""]
    nth = human.groupby("problem_id").cumcount().astype(str)
    return [
        {"sample_id": f"human:{pid}:{n}", "problem_id": pid, "label": "human", "category": "Human",
         "generator": "human", "model_id": "", "code": code, "raw_response": "",
         "post_type": post_type, "site": site}
        for pid, n, code, post_type, site in zip(human["problem_id"], nth, human["human_code"],
                                          human["post_type"], human["site"])
    ]


def generate(cfg, force=False):
    d = results_dir(cfg)
    human_out = d / CATEGORY_FILES["Human"]
    if force:
        # Regenerated Samples reuse sample_ids, so old Scores would silently attach to new code.
        # Human-fixed Samples are edits of the old Direct code, so they go too.
        for f in [*CATEGORY_FILES.values(), "samples.csv", *(d / "scores").glob("*.csv")]:
            (d / f).unlink(missing_ok=True)
        print("force: cleared every Category file, samples.csv and all scores")
    passes = [Pass("Direct", read_template(cfg["template"]), "")]
    if cfg.get("style_template"):
        passes.append(Pass("Style-prompted", read_template(cfg["style_template"]), ":style"))
    done = done_ids(human_out).union(*(done_ids(d / CATEGORY_FILES[p.category]) for p in passes))
    problems = read_csv(ROOT / cfg["problems"])

    human = [s for s in human_samples(problems) if s["sample_id"] not in done]
    if human:
        append_csv(human, human_out)
    print(f"human: {len(human)} new Samples")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    unique = problems.drop_duplicates("problem_id")
    for g in cfg["generators"]:
        options = {"temperature": g["temperature"]} if "temperature" in g else {}
        for category, template, suffix in passes:
            out = d / CATEGORY_FILES[category]
            new = failed = no_code = 0
            for pid, statement in zip(unique["problem_id"], unique["statement"]):
                sid = f"{g['name']}:{pid}{suffix}"
                if sid in done:
                    continue
                prompt = template.replace("{problem}", statement)
                try:
                    r = client.chat.completions.create(
                        model=g["model_id"], messages=[{"role": "user", "content": prompt}], **options)
                    raw = r.choices[0].message.content or ""
                except Exception as e:  # not written, so the next call retries it
                    failed += 1
                    print(f"  {sid} failed: {e}")
                    continue
                code = extract_code(raw)
                no_code += code == ""
                # One row per call: a crash loses at most the Sample in flight.
                append_csv([{"sample_id": sid, "problem_id": pid, "label": "llm", "category": category,
                             "generator": g["name"],
                             "model_id": g["model_id"], "code": code, "raw_response": raw}], out)
                new += 1
            print(f"{g['name']} {category}: {new} new, {failed} failed (rerun to retry), {no_code} with no code block")
    combine(d)


if __name__ == "__main__":
    assert extract_code("hi\n```python\nx = 1\n```\nbye") == "x = 1"
    assert extract_code("```py\nx = 1\n```") == "x = 1"
    assert extract_code("```\nx = 1\n```") == "x = 1"
    assert extract_code("```bash\nls\n```\n```python\nx = 1\n```") == "x = 1"
    assert extract_code("no code here") == ""
    print("generate self-check ok")
