# Generate

Generate turns each Problem's human solution into a Human Sample and sends every line of each Prompt file in `prompts` to every Generator through OpenRouter, keeping the first Python code block as a Direct or Style-prompted Sample. It writes one row per call, skips `sample_id`s already on disk, and with `force=True` clears the experiment first.

## Sub-features

- `gen-human`: one Human Sample per Problem with human code, `sample_id` `human:<problem_id>:<n>`.
- `gen-direct`: `direct` gives rows in `direct.csv` with `sample_id` `<generator>:<problem_id>`.
- `gen-style`: every other name gives rows in `style_prompted.csv` with `sample_id` `<generator>:<problem_id>:<name>`.
- `gen-resume`: a rerun makes no new calls and adds no rows.
- `gen-force`: `force=True` deletes the Category files, `formatted.csv`, `samples.csv` and all Scores, then regenerates.
- `gen-guards`: a `prompts` list without `direct`, or a name with no Prompt file, stops before any call or deletion.

## How to get to it (user POV)

- Run the notebook cell `generate(cfg)` in `colab.ipynb`.
- Run `generate(cfg, force=True)` to regenerate.

## Driving it with verify.sh

Preconditions:

- Baseline from [README.md](./README.md), with `OPENROUTER_API_KEY` exported. Doctor shows the key `set` and the call count (3 Problems × Generators × 2 Prompt files).
- `R=$BASE/app/results/verify`.

- **First run.** Run `$V stage "$BASE" gen-1 'generate(cfg)'`. The log shows `exit: 0`, `human: 3 new Samples`, and one `<generator> Direct: 3 new` and `<generator> Style-prompted: 3 new` line per Generator. `$BASE/evidence/gen-1.results/` has `human.csv`, `direct.csv`, `style_prompted.csv` and `samples.csv`. The `sample_id`s in `style_prompted.csv` end `:style`, and the `code` column is non-empty for rows whose `raw_response` contains a code block.
- **Resume.** Run `$V stage "$BASE" gen-2 'generate(cfg)'`. Every count in the log is `0 new`, and the row counts of the Category files equal those in `gen-1.results`.
- **Guard: no direct.** Run `$V stage "$BASE" gen-nodirect 'cfg["prompts"] = ["style"]; generate(cfg)'`. The log shows `exit: 1` and `ValueError: prompts = ['style'] has no "direct"`, and `$R` still matches `gen-2.results` (`diff -r`).
- **Guard: missing file.** Run `$V stage "$BASE" gen-missing 'cfg["prompts"] = ["direct", "nope"]; generate(cfg)'`. The log shows `FileNotFoundError: inputs/templates/nope.jsonl not found`, and `$R` is unchanged.
- **Force.** Score once first (`$V stage "$BASE" gen-score 'score(cfg)'`), then run `$V stage "$BASE" gen-force 'generate(cfg, force=True)'`. The log shows `force: cleared every Category file, formatted.csv, samples.csv and all scores`, `scores/` is empty in `gen-force.results`, and the Category files are rebuilt. This bills a second full set of calls.

## Gotchas

- Without `OPENROUTER_API_KEY`, `generate` writes `human.csv` (`human: 3 new Samples`), then fails with `KeyError: 'OPENROUTER_API_KEY'` and no `samples.csv`. Report this as a failed journey with the unmet precondition. Do not fake the client.
- A failed call writes no row and prints `<sample_id> failed: ...`. The next run retries it. A model that replies without a code block gives a row with `code = ""`, counted as `with no code block`.
- The Generators come from the repo's `config.toml`. More Generators means more calls, so check doctor's count before you run.
- `cfg` is reloaded from `config.toml` on every `stage`, so changes like `cfg["prompts"] = ...` last for that step only.
