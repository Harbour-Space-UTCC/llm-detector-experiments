"""ATC, approximated task conditioning (zero-shot, proxy LLM logits).

Paper: Ashkenazi et al. (2025), ECML PKDD.
Code: https://github.com/maorash/ATC (MIT).
Access: local CodeLlama-7B-Instruct (default); 4-bit or fp16 on T4.
Paper headline: mean AUROC 94.22 (MBPP), 93.82 (APPS) (Tables 1-2).
  Recall 83.92% (MBPP) / 84.08% (APPS) at fixed 10% FPR (Table 6) -> paper miss rate 0.1608 / 0.1592.
  Note: the paper's operating point is FPR 10%, not the config's fpr_fallback.
"""


def score(codes):
    raise NotImplementedError("atc: placeholder, see docstring")
