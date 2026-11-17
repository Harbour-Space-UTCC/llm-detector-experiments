"""ATC, approximated task conditioning (zero-shot, proxy LLM logits). Needs code only: it infers the task itself.

Paper: Ashkenazi, Brenner, Furman Shohet & Treister (2025), ECML PKDD, LNCS pp. 187-204, DOI 10.1007/978-3-032-06078-5_11.
Code: https://github.com/maorash/ATC (MIT). Ships per-task MBPP score files (13B, 4 seeds), no generated code.
Access: local CodeLlama-7B-Instruct (13.5 GB fp16); T4. fp16 vs nf4 is settled in prototypes/atc.ipynb.
  Compute entropy in fp32 (log_softmax): with transformers >= 4.46 the repo's fp16 probs*log(probs) gives NaN.
Score: -mean entropy over N=4 inferred tasks; higher = more likely LLM-written (paper 4.1, Algorithm 1).
Eval generators (4.1): GPT-3.5-Turbo, GPT-4o-mini (newest, Jul 2024), Claude3-haiku, StarChat-Alpha,
  CodeLlama-7B/13B, CodeGemma-7B. Data: MBPP test, APPS test, CodeContests.
Paper headline, 7B, N=4 (the model we run): AUROC 93.53 (MBPP), 92.51 (APPS) (Tables 1-2).
  Miss rate at 10% FPR: 0.2113 (MBPP), 0.2150 (APPS) (Appendix H). 13B: AUROC 94.22 / 93.82, miss 0.1608 / 0.1592 (Table 6).
  Operating point is 10% FPR, no fixed threshold published (4.9): config sets fpr = 0.10.
  Caveat: 99.8% of MBPP human solutions have CRLF line endings, LLM code does not; the prototype checks
  whether that inflates the paper's AUROC.
"""


def score(codes):
    raise NotImplementedError("atc: placeholder, see docstring")
