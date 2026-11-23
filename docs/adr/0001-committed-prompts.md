# Prompts are committed files, and generate() sends only those

Every Prompt (one Prompt Template filled with one Problem) is written by the prompts stage to a JSONL file beside its template and committed, and `generate()` sends those lines as-is instead of filling templates itself. We chose this so that git holds the exact text every Generator received: a template or Problem edit shows up as a Prompt diff in review, and old Samples can be traced to the Prompts that made them. A test fails when a committed Prompt file no longer matches its template and the current Problems, so the files cannot drift silently.

## Considered Options

- **Fill templates in memory (the old way).** No generated files in git, but nobody can see what a template edit does to 687 Prompts, and nothing records what earlier Samples were made from.
- **Fill in memory and also save a copy.** The copy can disagree with what was sent, e.g. after a template edit without regenerating.
- **One `.txt` file per Prompt.** Clean per-Problem diffs, but about 1,400 small files; one JSONL file per template, one line per Problem sorted by `problem_id`, keeps diffs per Problem with two files.

## Consequences

- About 2 MB of generated text is committed, and the prompts stage must be rerun after any template or Problems change (the staleness test enforces it).
- The config lists Prompt sets by name (`prompts = ["direct", "style"]`). The name `direct` alone gives the Direct Category and is required, because Humanize edits Direct Samples; every other name gives Style-prompted Samples with `sample_id` ending `:<name>`. A second Direct wording would need a new rule.
