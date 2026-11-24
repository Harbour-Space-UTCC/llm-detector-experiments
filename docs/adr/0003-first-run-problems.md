# The first full run uses all 687 parseable Problems

Superseded by ADR 0004: Problems are now competitive-programming tasks, not forum posts.

The first full run uses every row of `datasets.csv` whose delivered `code_parses` is True: 687 Problems, no subset. The evidence is in `analysis/eda_posts.ipynb` (#31). It is cheap at this size: about $17 to generate and $6 for the LLM judge, for 2 Generators and 2 Prompt files at the placeholder prices in the notebook. The full set also gives the tightest Results: the 95% half-width of a miss rate is at most 3.7 points at N=687, against 5.7 at N=300. The smallest Human split (GitHub, 48 Samples) is noisy at any N.

## Considered Options

- **A stratified random subset (e.g. 300 by site x Post type).** Saves about $10. That is not worth the lost precision: up to 2 points of half-width (at a rate near 0.5). The notebook keeps a preview cell in case real Generator prices come in far higher.
- **Re-check parsing with `ast.parse` instead of the delivered column.** The count depends on the Python version: 8 rows marked False parse on 3.13, and more parse on 3.14, which accepts `except A, B:` (PEP 758). The delivered column keeps the set fixed.

## Consequences

- No post-ChatGPT rule is needed: every post is from 2010–2018. Their age makes memorization the risk instead (#33).
- No length or line-ending rule is needed either. Every main-set snippet has 10 or more lines, and no code has CRLF line endings.
- GitHub stays in the main set. All 48 of its Problems come from one author (`kamyu104`). Every one has a class and comments, and the statements are short (median 115 characters). Its Human split is reported with that caveat, not as "GitHub code" in general.
- The 384 unparseable rows are scored as a separate Human group by every Detector except `whodunit`, in their own Result tables (#46).
