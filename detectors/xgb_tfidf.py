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
Reproduced (prototypes/xgb_tfidf.ipynb, Colab CPU, Python 3.13, xgboost 2.1.0, scikit-learn 1.5.2, tiktoken 0.8.0):
  repo recipe, 80/20 split by problem id, seeds 0-9: accuracy 98.36 +- 0.19, recall 98.78 +- 0.29,
  AUC 99.87 +- 0.03; miss rate 1.22%, FPR 2.05% (paper ~2.14% implied). All within 1 pp of Table 3.
  The shipped artifact is that recipe fit on all rows: the vectorizer's idf matches a fit on all 40,158 rows
  exactly on the 1533/1536 shared tokens (the other 3 are ties at the cut-off), and a default XGBClassifier
  refit on those features gives the shipped JSON booster's predictions (max |dp| 0.0, label agreement 1.0).
  This module's TF-IDF matches sklearn's to 2.8e-16.
"""
import functools, hashlib, importlib, io, os, pickle, urllib.request
import numpy as np, tiktoken, xgboost as xgb

_RAW = ("https://raw.githubusercontent.com/MarcOedingen/ChatGPT-Code-Detection/"
        "4aa771dc59a08b2233f75486235374f81b0a5bb4/")
_SHA256 = {
    "Models/Vectorizer_TFIDF.pkl": "62c9cc09caa85a4e82f74293993c63f9dbd046164834addedca09f9aa45ac8b2",
    "app/models/XGB_TFIDF.json": "b3ba52bd67849cc90588c65003059fbd6775672e1d4f39c036506075cac215c0",
}
_CACHE = os.path.expanduser("~/.cache/xgb_tfidf")


def _fetch(rel):
    path = os.path.join(_CACHE, rel)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(_RAW + rel, path)
    data = open(path, "rb").read()
    if hashlib.sha256(data).hexdigest() != _SHA256[rel]:
        raise RuntimeError(f"checksum mismatch: {path}")
    return path, data


class _State:
    def __setstate__(self, state):
        self.__dict__.update(state)


class _SafeUnpickler(pickle.Unpickler):
    _NUMPY = {("numpy", "dtype"), ("numpy", "float64"), ("numpy", "ndarray"),
              ("numpy.core.multiarray", "_reconstruct"), ("numpy.core.multiarray", "scalar")}

    def find_class(self, module, name):
        if module == "sklearn.feature_extraction.text":
            return _State
        if (module, name) in self._NUMPY:
            return getattr(importlib.import_module(module), name)
        raise pickle.UnpicklingError(f"blocked global {module}.{name}")


@functools.cache
def _model():
    vec = _SafeUnpickler(io.BytesIO(_fetch("Models/Vectorizer_TFIDF.pkl")[1])).load()
    vocab = {int(tok): int(col) for tok, col in vec.vocabulary_.items()}
    idf = np.asarray(vec._tfidf.idf_, dtype=np.float64)
    booster = xgb.Booster()
    booster.load_model(_fetch("app/models/XGB_TFIDF.json")[0])
    return tiktoken.get_encoding("cl100k_base"), vocab, idf, booster


def _tfidf(codes, enc, vocab, idf):
    X = np.zeros((len(codes), len(idf)))
    for i, code in enumerate(codes):
        for tok in enc.encode(code, disallowed_special=()):
            col = vocab.get(tok)
            if col is not None:
                X[i, col] += 1
    X *= idf
    norm = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.where(norm == 0, 1, norm)


def score(codes):
    enc, vocab, idf, booster = _model()
    # Dense on purpose: the model was trained on .toarray() features, so zeros are values, not missing.
    return booster.predict(xgb.DMatrix(_tfidf(codes, enc, vocab, idf))).tolist()
