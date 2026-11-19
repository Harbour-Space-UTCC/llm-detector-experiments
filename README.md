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

Four stages run in order. Each one reads files and writes files, so you can rerun any stage on its own.

1. **Generate**: for every Generator in `config.toml`, fill the Prompt Template with each Problem, ask the model, and keep the first Python code block. Human solutions from `problems.csv` become human Samples. Output: `human.csv` and `direct.csv` in `results/<experiment>/`.
2. **Humanize**: edit every Direct Sample with Edit rules at Edit count 2 and 5. Output: `human_fixed.csv`, with the rules, seed and script version of each row.
3. **Score**: run each Detector over every Sample. Output: `results/<experiment>/scores/<detector>.csv`.
4. **Metrics**: per Detector, Generator, Category, Edit count and human split, compute AUROC and the miss rate at a threshold, and compare with the paper's miss rate. Output: `results/<experiment>/summary.csv`.

Generate and Humanize rebuild `samples.csv`, which combines the Category files and is the only file the Detectors read. Human-fixed rows that were dropped are left out.

Each stage skips work that is already on disk, so a crash or a rerun picks up where it stopped.

## Repository layout

```
config.toml              what to run: experiment name, Generators, Detectors, paper numbers
inputs/template.txt      Prompt Template, must contain {problem}
inputs/datasets.csv      scraped forum posts, as delivered (never edit)
inputs/problems.csv      problem_id, statement, human_code, post_type, site (made by modules/problems.py)
detectors/<name>.py      one file per Detector
modules/                 pipeline code (generate, humanize, score, metrics)
colab.ipynb              the notebook everyone runs
results/<experiment>/    human.csv, direct.csv, human_fixed.csv (one per Category), samples.csv (all combined), scores/, summary.csv
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
| Add a Generator to an existing experiment | add it to `config.toml`, then `generate(cfg)`, `humanize(cfg)`, `score(cfg)`, `metrics(cfg)`. Only the new Samples are generated, edited and scored |
| Redo Human-fixed Samples after changing `modules/humanize.py` | `humanize(cfg, force=True)`, then `score(cfg)` and `metrics(cfg)`. Deletes only the Human-fixed Scores. Each row records the `script_version` that made it |
| Regenerate everything after changing the template or problems | `generate(cfg, force=True)`. This re-bills the API and deletes every Category file and all Scores of that experiment |

Stages skip work by `sample_id`. Editing `template.txt`, a Generator's `model_id` or `problems.csv` has no effect until you regenerate with `force=True`. A different `experiment` name is usually the better choice, because it keeps the old Results.

## Inputs

**`inputs/datasets.csv`**: 1,071 forum posts scraped by the team (Stack Overflow, Code Review, GitHub), kept byte-for-byte as delivered. It is the provenance reference: join it to anything by `problem_id` = `sample_id`.

| column | meaning |
| --- | --- |
| `sample_id` | unique row ID (the H/N/F prefix only says which teammate scraped it) |
| `site` | `stackoverflow`, `codereview` or `github` |
| `code_source` | Post type: `question` (asker's own code) or `answer` |
| `question_id`, `answer_id` | IDs on the site. `question_id` is not unique across sites |
| `question_title`, `question_text` | the post's title and text, with the code already stripped out |
| `code` | the code taken from the post |
| `code_lines`, `code_parses` | line count, and whether the code parses as Python 3 |
| `post_created_utc`, `post_last_edited_utc`, `post_score`, `tags` | post metadata |
| `author`, `author_link`, `link`, `question_link`, `license` | attribution |

**`inputs/problems.csv`**: one Problem per kept post, with its one human solution. Generated, so do not edit it by hand. Run `python -m modules.problems` to rebuild it (this overwrites the file) whenever a rule changes. It keeps only rows with `code_parses=True` (687 of 1,071), because unparseable human code would give the label away and AST-based Detectors cannot read it. Both Post types are kept.

| column | meaning |
| --- | --- |
| `problem_id` | the row's `sample_id` |
| `statement` | post title, a blank line, then the post text (code is not put back) |
| `human_code` | the post's code |
| `post_type` | `question` or `answer`, copied to the human Sample |
| `site` | copied to the human Sample |

Human Samples carry `post_type` and `site` in `human.csv` and `samples.csv`, so the summary splits the Human side by them.

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

One row per Detector, Generator, Category, Edit count and human split. Every row is measured at the same threshold, set from all the Human Samples.

| column | meaning |
| --- | --- |
| `category`, `edit_count` | which LLM-written Samples this row covers. `edit_count` is the number of Edit rules applied, and is empty except for Human-fixed |
| `human_split` | which Human Samples the row compares against: `all`, `post_type=question`, `post_type=answer`, or `site=<site>`. If a Detector does much better on `question` than on `answer`, it may be spotting broken code, not LLM code |
| `median_lines`, `human_median_lines` | median line count of this row's Samples and of the Human Samples in its split, so a length gap is visible (length is not filtered) |
| `auroc` | how well Scores separate these Samples from human code (0.5 = chance) |
| `threshold`, `threshold_source` | the cut-off used, from the paper or from `fpr_fallback` |
| `achieved_fpr` | share of human Samples flagged at that threshold |
| `miss_rate` | share of these Samples scored as human |
| `paper_miss_rate`, `outdated` | the paper's figure, and whether ours is higher. Direct rows with `human_split` = `all` only, because papers measured plain LLM output |

## Open decisions

Several controls are not settled yet: samples per Problem, temperature policy, per-detector FPR, the Outdated rule for papers that report only AUROC, and more. They are listed at the bottom of `config.toml`, with what the code does today and the options. Decide one, implement it, and move its key into the live part of the config.

## Checks

Run these after changing anything in `modules/`:

```bash
python -m modules.metrics    # threshold, AUROC and miss-rate logic
python -m modules.generate   # code-block extraction
python -m pytest tests/      # Edit rules keep output the same; Edit count 5 includes Edit count 2
```
