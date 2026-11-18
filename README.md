# llm-detector-results

How well do published detectors of LLM-written code catch it in each of four Categories: Human, Direct, Style-prompted and Human-fixed? For Direct code, has their miss rate gone up since their papers were written?

This repo is where the team's pieces come together and get run. One teammate supplies the Problems and the Prompt Template. Others add Detectors. Everyone runs the same notebook, and the Results are committed here. Terms such as Sample, Run and Miss rate are defined in [GLOSSARY.md](GLOSSARY.md).

## Categories

Every Sample belongs to one of four Categories. The names in the first column are the ones used in code and Results. The second column gives the names used in earlier notes.

| Category | Also called | What it is |
| --- | --- | --- |
| Human | Human only | Code written by a person |
| Direct | AI only (prompt) | LLM code from `inputs/template.txt`, which only asks for a solution |
| Style-prompted | AI + refine prompt | LLM code from `inputs/style_template.txt`, which also asks for code that looks human-written |
| Human-fixed | AI + Human fix | A Direct Sample after a script applies a set number of Edit rules (the Edit count) |

## How it works

Three stages run in order. Each one reads files and writes files, so you can rerun any stage on its own.

1. **Generate**: for every Generator in `config.toml`, fill the Prompt Template with each Problem, ask the model, and keep the first Python code block. Human solutions from `problems.csv` become human Samples. Output: `results/<experiment>/samples.csv`.
2. **Score**: run each Detector over every Sample. Output: `results/<experiment>/scores/<detector>.csv`.
3. **Metrics**: per Detector and Generator, compute AUROC and the miss rate at a threshold, and compare with the paper's miss rate. Output: `results/<experiment>/summary.csv`.

Each stage skips work that is already on disk, so a crash or a rerun picks up where it stopped.

## Repository layout

```
config.toml              what to run: experiment name, Generators, Detectors, paper numbers
inputs/template.txt      Prompt Template, must contain {problem}
inputs/problems.csv      problem_id, statement, human_code (one row per human solution)
detectors/<name>.py      one file per Detector
modules/                 pipeline code (generate, humanize, score, metrics)
colab.ipynb              the notebook everyone runs
results/<experiment>/    samples.csv, human_fixed.csv, scores/, summary.csv
GLOSSARY.md              shared vocabulary
```

Teammates normally edit only `config.toml`, `inputs/` and their own `detectors/<name>.py`.

## Running an experiment in Colab

### One-time setup

1. Create two Colab Secrets (key icon in the left sidebar) and give the notebook access to both:
   - `GITHUB_TOKEN`: a fine-grained GitHub token for this repo only, with **Contents: read and write** and nothing else. The notebook uses it to clone and to push Results.
   - `OPENROUTER_API_KEY`: an [OpenRouter](https://openrouter.ai) key. All Generators are called through it.
2. In the first code cell of `colab.ipynb`, set `REPO = "<owner>/llm-detector-results"`.
3. Pick a GPU runtime (Runtime → Change runtime type → T4).

### Each run

1. Edit `config.toml` in the repo: set `experiment` to a new name, and list the Generators and Detectors you want.
2. Open `colab.ipynb` in Colab and run the cells top to bottom:
   - **Setup** clones (or pulls) the repo and loads the secrets.
   - **Generate**, **Score** and **Metrics** run the three stages.
   - **Push Results** commits `results/<experiment>/` and pushes it.
3. Read `results/<experiment>/summary.csv`.

### Rerunning part of it

| You want to | Run |
| --- | --- |
| Rescore one Detector after changing its code | `score(cfg, only="<name>", force=True)` then `metrics(cfg)` |
| Score a newly added Detector | `score(cfg, only="<name>")` then `metrics(cfg)` |
| Add a Generator to an existing experiment | add it to `config.toml`, then `generate(cfg)`, `score(cfg)`, `metrics(cfg)`. Only the new Samples are generated and scored |
| Redo Human-fixed Samples after changing `modules/humanize.py` | `humanize(cfg, force=True)`. Each row records the `script_version` that made it |
| Regenerate everything after changing the template or problems | `generate(cfg, force=True)`. This re-bills the API and deletes all Scores of that experiment |

Stages skip work by `sample_id`. Editing `template.txt`, a Generator's `model_id` or `problems.csv` has no effect until you regenerate with `force=True`. A different `experiment` name is usually the better choice, because it keeps the old Results.

## Inputs

**`inputs/problems.csv`**: one row per human solution.

| column | meaning |
| --- | --- |
| `problem_id` | stable ID, repeated on every row of the same Problem |
| `statement` | the problem text put into the template |
| `human_code` | one human Python solution, or empty if there is none |

Human Sample IDs follow row order, so append new solutions at the end of a Problem's rows rather than inserting them.

**`inputs/template.txt`**: the full prompt sent to every Generator. `{problem}` is replaced with the statement. Ask for a single ```` ```python ```` block, because the code is extracted from the first one.

**Generators** live in `config.toml`:

```toml
[[generators]]
name = "claude-opus-5-5"              # short name, used in sample_id
model_id = "anthropic/claude-opus-5-5" # exact OpenRouter model ID
temperature = 0.0                      # optional; omit for the provider default
```

## Adding a Detector

1. Copy `detectors/random_baseline.py` to `detectors/<name>.py`. Placeholder files already exist for the starter set (`xgb_tfidf`, `whodunit`, `atc`, `droiddetect`, `llm_judge`). Their docstrings list the paper, the checkpoint or code link, the hardware needed and the paper's numbers. `prototypes/<name>.ipynb` reproduces each paper's own number in Colab before its `score()` moves into `detectors/`.
2. Implement `score(codes: list[str]) -> list[float]`: one Score per code, higher means more likely LLM-written. `score` is called once per chunk of 64 Samples, so load models once at module level, never inside `score`.
3. Add a block to `config.toml`:
   ```toml
   [detectors.<name>]
   threshold = 0.5          # the paper's own threshold; omit to use fpr or fpr_fallback
   fpr = 0.10               # the paper's FPR operating point, when it has no fixed threshold
   paper_miss_rate = 0.16   # the paper's miss rate, for the Outdated verdict
   ```
4. Run it on the `toy` experiment, then open a PR.

Watch the positive class when copying numbers from a paper. Here, LLM-written is positive. Some papers treat human code as positive, so their "FPR" is our miss rate.

## Reading the summary

One row per Detector and Generator.

| column | meaning |
| --- | --- |
| `auroc` | how well Scores separate this Generator's code from human code (0.5 = chance) |
| `threshold`, `threshold_source` | the cut-off used, from the paper or from `fpr_fallback` |
| `achieved_fpr` | share of human Samples flagged at that threshold |
| `miss_rate` | share of this Generator's Samples scored as human |
| `paper_miss_rate`, `outdated` | the paper's figure, and whether ours is higher |

## Open decisions

Several controls are not settled yet: samples per Problem, temperature policy, per-detector FPR, the Outdated rule for papers that report only AUROC, and more. They are listed at the bottom of `config.toml`, with what the code does today and the options. Decide one, implement it, and move its key into the live part of the config.

## Checks

Run these after changing anything in `modules/`:

```bash
python -m modules.metrics    # threshold, AUROC and miss-rate logic
python -m modules.generate   # code-block extraction
python -m modules.humanize   # each Edit rule keeps output the same; Edit count 5 includes Edit count 2
```
