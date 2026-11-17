"""Whodunit (stylometric-AST, XGBoost on 140 stylometry features).

Paper: Idialu et al. (2024), MSR.
Replication package: https://zenodo.org/doi/10.5281/zenodo.10152237 (CC-BY-4.0): feature scripts, CSVs, notebooks; no pickled model.
Access: retrain XGBoost from their CSVs; CPU, seconds. Python only (CodeChef, GPT-4-0613).
Paper headline: F1 and AUC 0.91 with all features; 0.89 without gameable ones (Table 4).
"""


def score(codes):
    raise NotImplementedError("whodunit: placeholder, see docstring")
