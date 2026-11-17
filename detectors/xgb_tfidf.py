"""XGB + TF-IDF (trained classifier, XGBoost on TF-IDF of tiktoken cl100k_base token ids, 1536 features).

Paper: Oedingen, Engelhardt, Denz, Hammer & Konen (2024), AI (MDPI) 5(3):1066-1094, DOI 10.3390/ai5030053.
Code: https://github.com/MarcOedingen/ChatGPT-Code-Detection (CC-BY-4.0), pin commit 4aa771d.
  Ships a fitted model: app/models/XGB_TFIDF.json (xgboost 2.1.0) + Models/Vectorizer_TFIDF.pkl.
  The vectorizer pickle cannot transform as shipped (analyzer None / dill lambda): rebuild TF-IDF from its
  vocabulary_ and idf_. Features must stay dense (trained on .toarray(); sparse zeros would read as missing).
  The shipped model was fit on all 40,158 released rows, so it has no held-out split of its own.
Access: download weights (~0.5 MB); CPU.
Generators: gpt-3.5-turbo only, snapshot not named (paper 3.1, 4.1); references accessed mid-2023, so 0301 or 0613 (inference).
Data: APPS, CodeChef, CodeContests, HackerEarth, HumanEval, MBPP, MTrajK. Drop any Problem that is in the
  released jsonl, or the Score is in-sample.
Paper headline: XGB + TF-IDF, unformatted code, 10 seeds (Table 3): accuracy 98.28, recall 98.70, AUC 99.84.
  Positive class = GPT (same as ours). Threshold 0.5 (XGBClassifier.predict). Paper miss rate 1 - 0.9870 = 0.013.
Status: score() is cell 2 of prototypes/xgb_tfidf.ipynb; move it here once that Colab run reproduces Table 3.
"""


def score(codes):
    raise NotImplementedError("xgb_tfidf: placeholder, see docstring")
