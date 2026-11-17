"""Copy-me example Detector. Random Scores: AUROC should land near 0.5 on a real Dataset.

Contract: score(codes: list[str]) -> list[float], one Score per code, higher = more likely LLM-written.
score() is called once per chunk of Samples, so load models once at module level, or cache them
with functools.cache, never inside score().
"""
import random

_rng = random.Random(0)


def score(codes):
    return [_rng.random() for _ in codes]
