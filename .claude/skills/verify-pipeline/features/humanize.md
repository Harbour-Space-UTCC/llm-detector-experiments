# Humanize

Humanize applies Edit rules to every Direct Sample with code, at Edit count 2 and 5. It writes Human-fixed Samples to `human_fixed.csv`, recording the rules, seed and script version of each row, and rebuilds `samples.csv`.

## Sub-features

- `hum-fixed`: each Direct Sample with code gives two rows, `<direct sample_id>:hf2` and `:hf5`, with `source_id` set to the Direct `sample_id`.
- `hum-dropped`: a Direct Sample that does not parse, or whose edited code does not parse, gets rows with a `status` starting `dropped:`. Those rows are left out of `samples.csv`.
- `hum-resume`: a rerun adds no rows.
- `hum-force`: `humanize(cfg, force=True)` redoes the Human-fixed rows and deletes only their Scores and formatted copies.

## How to get to it (user POV)

- Run the notebook cell `humanize(cfg)` in `colab.ipynb`, after Generate.

## Driving it with verify.sh

Preconditions:

- [Generate](./generate.md) `gen-1` passed in this BASE, so `direct.csv` holds Direct Samples.

- **Edit.** Run `$V stage "$BASE" hum-1 'humanize(cfg)'`. The log shows `exit: 0` and `human-fixed: <n> new rows`, where `<n>` is 2 × the number of Direct Samples with code. In `hum-1.results/human_fixed.csv`, `sample_id`s end in `:hf2` or `:hf5`, every `source_id` is in `direct.csv`, and kept rows have `status` `kept` and non-empty `code`. In `samples.csv`, `category` now includes `Human-fixed`, and no row has a `dropped:` status.
- **Resume.** Run `$V stage "$BASE" hum-2 'humanize(cfg)'`. The log shows `0 new rows`, and `human_fixed.csv` has the same row count as in `hum-1.results`.
- **Force.** Run `$V stage "$BASE" hum-force 'humanize(cfg, force=True)'`. `human_fixed.csv` is rebuilt. Scores and `:fmt` rows of the other Categories are still present when they existed before.

## Gotchas

- `edit_count` is the number of rules actually applied, so it can be less than 2 or 5 when a Sample offers few edits (the log counts these as short). Check the `:hf2` / `:hf5` suffix for the target, not `edit_count`.
- Humanize reads Direct Samples only. Style-prompted Samples never get Human-fixed versions.
- A Direct Sample with `code = ""` (no code block) is skipped and gets no row at all.
- Different LLM output gives different Human-fixed code. Assert on row shape and `source_id`, not on the exact code.
