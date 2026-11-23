# Memorization of scraped Human Samples

The scraped Human Samples (`inputs/data/datasets.csv`) are Stack Overflow, Code Review and GitHub posts from 2010–2018. Public code of that age is almost certainly in the pretraining data of every Generator, and may be in the training data of some Detectors.

## Why it matters

- **Perplexity Detectors may flag human code.** A model that has seen a post finds it unsurprising, so zero-shot Detectors (e.g. ATC) can score memorized Human Samples as LLM-written. That raises the false positive rate and moves any threshold set from the human Samples (the FPR fallback).
- **Trained Detectors may be flattered.** A classifier trained on the same posts has seen these exact Human Samples, so it calls them human more easily than it would fresh human code.
- **Generators may copy the accepted answer.** Asked the same question, a Generator can reproduce the human answer almost verbatim, so a Direct Sample may be near-identical to its Human Sample.

## What we do about it

- State this limitation wherever Results on this data are reported.
- Later: flag Direct Samples that are near-copies of the Human Sample for the same Problem, and report Results with and without them.
- Later, if feasible: compare against human code written after the Generators' training cutoff.
