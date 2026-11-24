"""detectors/xgb_tfidf.py with a fake tokenizer and booster: no download, no real model."""
import numpy as np
import pytest

pytest.importorskip("xgboost")
pytest.importorskip("tiktoken")

from detectors import xgb_tfidf  # noqa: E402


class FakeEnc:
    def encode(self, code, disallowed_special=()):
        return [int(t) for t in code.split()]


class FakeBooster:
    def predict(self, dmatrix):
        return np.full(dmatrix.num_row(), 0.7, dtype=np.float32)


VOCAB = {10: 0, 20: 1}  # token id -> column
IDF = np.array([1.0, 2.0])


@pytest.fixture
def fake_model(monkeypatch):
    monkeypatch.setattr(xgb_tfidf, "_model", lambda: (FakeEnc(), VOCAB, IDF, FakeBooster()))


def test_tfidf_drops_unknown_tokens_and_l2_normalizes():
    X = xgb_tfidf._tfidf(["10 10 20 99", "99", ""], FakeEnc(), VOCAB, IDF)
    np.testing.assert_allclose(X[0], np.array([2.0, 2.0]) / np.sqrt(8))  # counts [2, 1] * idf [1, 2]
    assert not X[1:].any() and np.isfinite(X).all()  # no known token: zero row, not NaN


def test_score_one_float_per_code(fake_model):
    scores = xgb_tfidf.score(["10 20", "99", ""])
    assert len(scores) == 3 and all(isinstance(s, float) for s in scores)
