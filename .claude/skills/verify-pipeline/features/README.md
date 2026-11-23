# Pipeline verification map

This directory is the maintained source for verifying what a teammate does with the pipeline. Read this index before you drive it, then use the matching feature file as the recipe.

## Baseline preconditions

- `V=.claude/skills/verify-pipeline/verify.sh`, run from the repo root.
- `$V launch 3` gave `READY BASE=...`, and `$V doctor "$BASE"` exits 0.
- The copy has `experiment = "verify"`, `prompts = ["direct", "style"]`, 3 Problems, the repo's Generators and the Detector `random_baseline`.
- Journeys from Generate on need `OPENROUTER_API_KEY` exported, and they bill it (doctor prints the call count).
- Never drive the real checkout or its `results/`. Drive only a BASE this run launched.

## Driving conventions

- Run stages in pipeline order. Each one reads what the previous one wrote.
- A teammate's action is either a notebook cell (`$V stage "$BASE" <label> '<code>'`) or a terminal command (`$V cli "$BASE" <label> <module>`). Use the same form the user would.
- Edit inputs inside `$BASE/app`, never in the repo.
- Give every step a distinct label, because a label's log and snapshot are overwritten.

## Proof and skip reporting

- Proof is the step's `$BASE/evidence/<label>.log` (with its `exit:` line) plus the state it produced: the `<label>.results/` snapshot, or files under `$BASE/app/inputs/`.
- Assert on rows and files (`sample_id`s, row counts, columns), not only on printed counts.
- A journey that cannot run (no key, no GPU for a real Detector) is reported as failed, with the command and the unmet precondition. Never swap in a fake client or skip ahead with hand-written rows.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behaviour. Four H2 sections follow, in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with verify.sh`, `Gotchas`.

## Features

- [Prompts stage](./prompts.md): rebuild Prompt files, pick up template edits, reject a template without `{problem}`. No API cost.
- [Generate](./generate.md): Human, Direct and Style-prompted Samples, resume, and `force`. Bills OpenRouter.
- [Humanize](./humanize.md): Human-fixed Samples at Edit count 2 and 5 from Direct Samples.
- [Formatter check](./formatcheck.md): black-formatted `:fmt` copies of every Sample.
- [Score and Metrics](./score-metrics.md): Scores per Detector and `summary.csv`.
