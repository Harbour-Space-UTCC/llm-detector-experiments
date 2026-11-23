---
name: verify-pipeline
description: Drive the llm-detector pipeline (prompts stage, Generate, Humanize, Formatter check, Score, Metrics) for real in a disposable copy of this checkout cut to a few Problems, and capture evidence. Use to prove a change to modules/, detectors/, inputs/ or config.toml works the way a teammate runs it, beyond the unit tests.
---

# Verify the pipeline

The app has no server or UI. A teammate edits `config.toml` and `inputs/`, runs `python -m modules.problems` / `python -m modules.prompts`, then runs the stage functions from `colab.ipynb` in order: `generate(cfg)`, `humanize(cfg)`, `format_copies(cfg)`, `score(cfg)`, `metrics(cfg)`. Each stage reads and writes files under `results/<experiment>/`. The harness reproduces exactly that, in a copy.

All commands run from the repo root. `V=.claude/skills/verify-pipeline/verify.sh`.

## Launch

```bash
V=.claude/skills/verify-pipeline/verify.sh
$V launch 3        # N Problems to keep, default 3
```

It copies the working tree as it is now (tracked and untracked files, uncommitted edits included; never `.env`, `results/` or `.claude/`) to `BASE/app`, cuts the Problems file to the first N `problem_id`s, sets `experiment = "verify"` and `prompts = ["direct", "style"]` in the copy's `config.toml`, and runs the prompts stage there. Ready is the last line, `READY BASE=/tmp/verify-pipeline.XXXXXX`. Keep that path: every other command takes it.

Code in the copy runs from the copy (`ROOT` is the folder holding `modules/`), with the repo's `.venv` interpreter. Your checkout and its `results/` are never touched. Each launch gets its own BASE, so runs can go side by side.

## Doctor

```bash
$V doctor "$BASE"
```

Read-only. Exit 0 means every `ok` line held: code runs from the copy, `experiment = verify`, black matches `BLACK_VERSION`, and each listed Prompt file has one line per Problem. `info` lines show how many OpenRouter calls `generate` would make, whether `OPENROUTER_API_KEY` is set (never its value), and the Detectors in the config. Run it first, and again whenever a result looks off.

## Drive

```bash
$V stage "$BASE" <label> '<python>'    # notebook cell: cfg and generate/humanize/format_copies/score/metrics/results_dir in scope
$V cli   "$BASE" <label> <module>      # python -m <module>, e.g. modules.prompts
```

Both print and save the command, output and exit code, return the stage's exit code, and snapshot `results/verify/` after the step. Edit inputs in `$BASE/app` (templates, `config.toml`) the way a teammate edits them in the repo. The feature recipes are in [features/README.md](features/README.md).

`generate` calls OpenRouter for real and bills the key: export `OPENROUTER_API_KEY` first (for example `set -a; . ./.env; set +a`), and read doctor's call count before you run it. Without the key every journey from Generate on fails. Report that, do not fake the client.

## Evidence

Everything goes to `$BASE/evidence/`: `<label>.log` (command, output, `exit: <code>`) and `<label>.results/` (the experiment's files right after that step). Add your own checks there too (checksums, `grep` counts). A proof shows the action and the state it produced: the stage log plus the rows or files it wrote, not just "exit: 0". Check side effects such as rows appended and files deleted by `force=True`, not only printed counts.

## Cleanup

```bash
$V cleanup "$BASE"
```

It deletes `$BASE/app` only and refuses any path that is not a `verify-pipeline.*` folder with an `app/`. `$BASE/evidence/` stays; quote its path in your report. It starts no processes, so there is nothing to kill.
