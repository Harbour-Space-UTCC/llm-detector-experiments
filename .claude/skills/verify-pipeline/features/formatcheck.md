# Formatter check

The optional Formatter check makes a black-formatted copy of every Sample in every Category, Human included, at the pinned black version. Copies land in `formatted.csv` with `sample_id` `<sample_id>:fmt`, and `samples.csv` marks them `formatted = True`.

## Sub-features

- `fmt-copies`: every Sample with code gets one `:fmt` row.
- `fmt-failed`: a Sample black cannot format gets a `status` of `failed: ...` and is left out of `samples.csv`.
- `fmt-skip-empty`: Samples with no code are skipped.
- `fmt-version`: a black version other than `BLACK_VERSION` stops the stage.

## How to get to it (user POV)

- Run the notebook cell `format_copies(cfg)` in `colab.ipynb`, after Humanize. Skipping the cell skips the check.

## Driving it with verify.sh

Preconditions:

- Generate (`gen-1`) and Humanize (`hum-1`) passed in this BASE. Doctor shows black matching the pin.

- **Copies.** Run `$V stage "$BASE" fmt-1 'format_copies(cfg)'`. The log shows `exit: 0`. In `fmt-1.results/formatted.csv`, each `sample_id` ends `:fmt` and names a Sample from the Category files with non-empty code. `samples.csv` has rows with `formatted` `True`.
- **Resume.** Run `$V stage "$BASE" fmt-2 'format_copies(cfg)'`. `formatted.csv` keeps the same row count.

## Gotchas

- The Human Samples come from real forum posts. Some fail to format, and the `failed: ...` rows are the expected outcome, not a harness error.
- The black version is pinned in `modules/formatcheck.py` and in `colab.ipynb`. A `.venv` with another version fails doctor. Fix the environment, not the pin.
