"""inputs/data/datasets.csv (scraped forum posts) -> inputs/data/problems.csv. Rerun after changing a rule:
    python -m modules.problems
then rebuild the Prompts from the new Problems: python -m modules.prompts
"""
import pandas as pd

from .common import ROOT, read_csv


def convert(src=ROOT / "inputs/data/datasets.csv", dst=ROOT / "inputs/data/problems.csv"):
    """One Problem per post whose code parses: statement = title, blank line, post text as delivered."""
    d = pd.read_csv(src, dtype=str, keep_default_na=False, encoding="utf-8-sig")  # file has a BOM
    d = d[d["code_parses"] == "True"]
    p = pd.DataFrame({
        "problem_id": d["sample_id"],  # question_id is not unique across sites
        "statement": d["question_title"] + "\n\n" + d["question_text"],
        "human_code": d["code"],
        "post_type": d["code_source"],
        "site": d["site"],
    }).reset_index(drop=True)
    p.to_csv(dst, index=False)
    return p


if __name__ == "__main__":
    print(f"{len(convert())} Problems written to inputs/data/problems.csv")
