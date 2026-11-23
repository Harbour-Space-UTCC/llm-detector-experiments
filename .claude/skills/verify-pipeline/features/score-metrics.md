# Score and Metrics

Score runs each Detector in `config.toml` over the code of every Sample in `samples.csv`, writing `scores/<detector>.csv`. Metrics turns the Scores into `summary.csv`: per Detector, Generator, Category, Edit count and human split, the threshold, AUROC, miss rate and the comparison with the paper.

## Sub-features

- `score-run`: one Score per Sample with non-empty code, in `scores/<detector>.csv`.
- `score-resume`: a rerun scores only new Samples.
- `score-only-force`: `score(cfg, only="<name>", force=True)` rescores one Detector from scratch.
- `metrics-summary`: `summary.csv` has one row per Detector × Generator × Category × Edit count × human split × formatted.

## How to get to it (user POV)

- Run the notebook cells `score(cfg)` and then `metrics(cfg)` in `colab.ipynb`.
- Run `score(cfg, only="<name>", force=True)` and then `metrics(cfg)` after changing a Detector.

## Driving it with verify.sh

Preconditions:

- `samples.csv` exists in this BASE: Generate `gen-1` passed (Humanize and the Formatter check add more Categories).
- The copy's only Detector is `random_baseline`, which needs no GPU and no download.

- **Score.** Run `$V stage "$BASE" score-1 'score(cfg)'`. The log shows `random_baseline: scored <n> new Samples`, where `<n>` equals the number of `samples.csv` rows with non-empty `code`. `score-1.results/scores/random_baseline.csv` has the columns `sample_id` and `score`, one row per scored Sample.
- **Resume.** Run `$V stage "$BASE" score-2 'score(cfg)'`. The log shows `scored 0 new Samples`.
- **Rescore one.** Run `$V stage "$BASE" score-force 'score(cfg, only="random_baseline", force=True)'`. The row count matches `score-1`.
- **Metrics.** Run `$V stage "$BASE" metrics-1 'metrics(cfg)'`. `metrics-1.results/summary.csv` exists, with rows for `random_baseline` and each Category present in `samples.csv`.

## Gotchas

- The real Detectors (`xgb_tfidf`, `droiddetect`, `atc`, `whodunit`, `llm_judge`) are placeholders or need a GPU (CLAUDE.md: run them only on Colab). Enabling one in the copy is a GPU journey. Report it as not run, rather than scoring with `random_baseline` and calling it done.
- With 3 Problems, AUROC and miss rates are noise. Prove the shape of `summary.csv`, not its numbers.
- Detectors see only the `code` column (ADR 0002). An empty-code Sample is not scored, so it never appears in `scores/`.
