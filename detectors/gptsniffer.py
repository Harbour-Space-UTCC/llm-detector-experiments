"""GPTSniffer (trained classifier, CodeBERT 125M).

Paper: Nguyen et al. (2024).
Code: https://github.com/MDEGroup/GPTSniffer (code only, train yourself).
  Re-implementation: Pordanesh et al. OSF package https://osf.io/jahxs/?view_only=dff479fdad8c4b9cb2060e6a3c2c5e5a
Access: retrain on its data (original is Java; Python in re-runs); GPU.
Paper headline: in-domain F1 0.97 (CSN, GPT-4o) and 0.99 (CodeNet) (Pordanesh et al. 2025, Tables 2-3).
  Djire (2026, Table 1): accuracy 0.50, F1 0.00 with HUMAN as positive class (it flags almost all human code).
"""


def score(codes):
    raise NotImplementedError("gptsniffer: placeholder, see docstring")
