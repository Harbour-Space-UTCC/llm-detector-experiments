"""Whodunit (stylometric-AST, XGBoost on 136 stylometry features).

Paper: Idialu, Mathews, Maipradit, Atlee & Nagappan (2024), MSR, DOI 10.1145/3643991.3644926.
Replication package: Zenodo record 18834715 (2026 v2; concept DOI 10.5281/zenodo.10152237 redirects there), CC-BY-4.0.
  Ships feature CSVs, raw code, remove_all_comments and CodeMetricsExtractor (runs on new code strings).
  No model file: retrain XGBoost on all 1596 rows; CPU, seconds. Needs radon==6.0.1.
  Run remove_all_comments before extraction: 323/798 human training files have CRLF line endings, 0 AI files do;
  the stripper normalises them. It also breaks some valid code: score those as 0.5 and count them.
Generator: GPT-4-0613 only (Jun 2023), temperature 0 (3.1). Data: 399 CodeChef problems, 798 human + 798 GPT-4, Python 3.
Paper headline, Table 4 "All" (136 features; the 140-feature Halstead variant is a side result):
  accuracy, precision, recall, F1 0.91; Non-Gameable (134) 0.89. Positive class = GPT-4 (same as ours).
  Its "AUC-ROC" is a per-fold mean on hard 0/1 predictions (balanced accuracy), not a probability AUROC.
  Threshold 0.5 (XGBClassifier.predict). Paper miss rate 1 - recall = 0.09 (shipped counts: FN 70/798 = 0.088).
"""


def score(codes):
    raise NotImplementedError("whodunit: placeholder, see docstring")
