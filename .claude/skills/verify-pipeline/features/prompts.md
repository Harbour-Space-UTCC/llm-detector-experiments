# Prompts stage

The prompts stage fills every Prompt Template in `inputs/templates/` with every Problem and writes `<name>.jsonl` beside it: one `{"problem_id", "prompt"}` line per Problem, sorted by `problem_id`. A teammate reruns it after editing a template or the Problems.

## Sub-features

- `prompts-rerun`: rerunning with no input change leaves every Prompt file byte-identical.
- `prompts-edit`: a template edit shows up in every line of that template's Prompt file, and only there.
- `prompts-new`: a new `<name>.txt` gets its own `<name>.jsonl`.
- `prompts-no-placeholder`: a template without `{problem}` stops the stage, names the file, and writes nothing.

## How to get to it (user POV)

- Run `python -m modules.prompts` in a terminal at the repo root.

## Driving it with verify.sh

Preconditions:

- Baseline from [README.md](./README.md). No key is needed.
- `T=$BASE/app/inputs/templates`.

- **Rerun.** Run `sha256sum $T/*.jsonl > $BASE/evidence/prompts-before.sha`, then `$V cli "$BASE" prompts-rerun modules.prompts`, then `sha256sum -c $BASE/evidence/prompts-before.sha`. Exit `0`, and both files report `OK`.
- **Edit.** Append a marker with `printf '\nVERIFY-MARKER\n' >> $T/style.txt`, then run `$V cli "$BASE" prompts-edit modules.prompts`. `grep -c VERIFY-MARKER $T/style.jsonl` equals the Problem count (3), and `grep -c VERIFY-MARKER $T/direct.jsonl` is `0`.
- **New template.** Run `printf 'Solve:\n{problem}\n' > $T/style_v2.txt`, then `$V cli "$BASE" prompts-new modules.prompts`. `$T/style_v2.jsonl` has 3 lines, each starting `{"problem_id": "`.
- **No placeholder.** Run `printf 'Solve it.\n' > $T/bad.txt`, copy `$T/style.jsonl` to the evidence folder, then run `$V cli "$BASE" prompts-bad modules.prompts`. The log shows `exit: 1` and `ValueError: inputs/templates/bad.txt has no {problem} placeholder`. No `bad.jsonl` exists, and `cmp` shows `style.jsonl` unchanged. Remove `bad.txt` afterwards.

## Gotchas

- `python -m modules.problems` in the copy rebuilds all 687 Problems from `datasets.csv` and undoes the cut to N. After it, the next prompts run writes 687 lines per file, and Generate would bill for all of them. Relaunch instead.
- A leftover `bad.txt` makes every later prompts run fail. Remove it after the negative check.
- `style_v2.jsonl` is not sent until `"style_v2"` is added to `prompts` in the copy's `config.toml`.
