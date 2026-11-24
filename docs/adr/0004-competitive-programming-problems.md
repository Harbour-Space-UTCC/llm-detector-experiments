# Problems are competitive-programming tasks

Supersedes ADR 0003.

Problems come from competitive programming, not from forum posts. Each Problem is one task statement, and its Human Sample is one accepted human solution in Python. The project asks about education: a competitive-programming task is like a programming assignment. It gives a stated task and a complete program that passes the judge, and that is what a student hands in. The Detectors' papers also measured their miss rates on competitive-programming data (APPS, CodeChef, MBPP, CodeContests). The Outdated comparison holds only when our data is the same kind.

The source must meet four rules:

- **Not in any Detector's training data.** This rules out APPS, CodeChef, CodeContests, HackerEarth, HumanEval, MBPP and MTrajK (`xgb_tfidf`), CodeChef (`whodunit`), and whatever DroidCollection draws on (`droiddetect`).
- **Accepted Python 3 solutions submitted before 2022-11-30**, so the Human label is clean.
- **All difficulty levels.**
- **One human solution per Problem.** The teammate who collects the data picks it and writes the selection rule down.

## Considered Options

- **Forum posts (`datasets.csv`, ADR 0003).** Already collected and not in any training data. Rejected for two reasons:
  - Human and LLM-written Samples do different jobs. `question` code is the asker's broken attempt, and many `answer` snippets are fragments, while LLM code is a complete solution. A Detector could separate "fragment" from "complete" instead of human from LLM.
  - A miss rate measured on forum code cannot be compared with a paper's measured on competitive programming. Domain shift and newer Generators would be mixed together.
- **Only the 90 LeetCode rows already scraped (`F` prefix).** Too few, and all from one author.
- **Human solutions after 2022-11-30.** Fewer memorized problems, but a "human" solution may be LLM-written, and nothing in the data can catch that. Memorization is flagged instead (#33).

## Consequences

- `datasets.csv` and the forum `problems.csv` are replaced when the new data arrives. `analysis/eda_posts.ipynb` is rewritten for the new data.
- Post type and site no longer describe a Human Sample, so the Human split changes with the new data.
- The unparseable-posts group (#46) is dropped.
- The first full run covers Human, Direct and Style-prompted only. It uses 5 Detectors (`xgb_tfidf`, `droiddetect`, `atc`, `whodunit`, `llm_judge`) and no Formatter check. Generators are added to one experiment one at a time. Human-fixed and the Formatter check can be added later without regenerating.
