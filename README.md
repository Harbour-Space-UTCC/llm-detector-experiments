# llm-detector-results

Do published LLM-code detectors still catch code from frontier LLMs? Terms in [GLOSSARY.md](GLOSSARY.md).

Run: open `colab.ipynb` in Colab, run top to bottom. Results land in `results/<experiment>/` and get pushed.

- **What runs**: `config.toml` (experiment name, Generators, Detectors, paper numbers).
- **Inputs**: `inputs/template.txt` (must contain `{problem}`), `inputs/problems.csv` (`problem_id, statement, human_code`, one row per human solution).
- **Add a Detector**: copy `detectors/random_baseline.py` to `detectors/<name>.py`, implement `score(codes) -> list[float]` (higher = more likely LLM-written), add `[detectors.<name>]` to `config.toml`, open a PR.
- **Self-checks**: `python metrics.py`, `python generate.py`.
- **Stages skip by `sample_id`**: editing `template.txt`, a Generator's `model_id`, or `problems.csv` changes nothing until you run `generate(cfg, force=True)` (re-bills the API, clears all Scores). Human ids follow row order in `problems.csv`.
