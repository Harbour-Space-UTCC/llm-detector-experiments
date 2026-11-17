"""LLM judge, Djire's LLM4GCD harness (LLM judge, API).

Paper: Djire (2026).
Replication package: https://doi.org/10.5281/zenodo.22248135 (README.md, src.zip): prompts for 4 strategies.
Access: API LLM key (open judges such as Llama 3.1-70B can run locally).
  Put the judge's exact model ID in config so overlap with Generator vendors shows in Results.
Score: Djire asks 3 times at temperature 0.1 and averages "yes" verdicts -> Score in {0, 1/3, 2/3, 1}.
  Coarse Scores make AUROC and the fpr_fallback threshold coarse.
Paper headline: F1 with HUMAN as positive class. GPT-5-mini zero-shot F1 0.75-0.95; lexico-semantic prompting 0.25-0.40 (Table 1).
"""


def score(codes):
    raise NotImplementedError("llm_judge: placeholder, see docstring")
