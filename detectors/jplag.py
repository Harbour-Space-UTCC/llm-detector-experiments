"""JPlag (plagiarism tool, similarity to reference LLM solutions).

Paper: Saglam & Schmid (2025). Tool: https://github.com/jplag/JPlag (Java CLI).
  Replication package: https://github.com/tsaglam/EMSE25-SM
Access: text only, but needs reference LLM solutions per Problem.
  Does NOT fit score(codes): needs problem_ids too. Extend the contract in modules/score.py when building this.
Score: max similarity to that Problem's reference solutions.
Paper headline: median similarity gap, GPT-4 pairs vs human pairs, baseline vs Subsequence Match Merging:
  15.04 vs 23.58 (PROGpedia-19) (Table 10). No fixed threshold: the paper rejects one.
"""


def score(codes):
    raise NotImplementedError("jplag: placeholder, see docstring")
