# Problems are competitive-programming tasks

Supersedes ADR 0003.

Problems come from competitive programming, not from forum posts. Each Problem is one task statement, and its Human Sample is one accepted human solution in Python. The project asks about education: a competitive-programming task is like a programming assignment. It gives a stated task and a complete program that passes the judge, and that is what a student hands in. The Detectors' papers also measured their miss rates on competitive-programming data (APPS, CodeChef, MBPP, CodeContests). The Outdated comparison holds only when our data is the same kind.

The source must meet four rules:

- **Not in any Detector's training data.** This rules out APPS, CodeChef, CodeContests, HackerEarth, HumanEval, MBPP and MTrajK (`xgb_tfidf`), CodeChef (`whodunit`), and whatever DroidCollection draws on (`droiddetect`).
- **Accepted Python 3 solutions submitted before 2022-11-30**, so the Human label is clean.
- **All difficulty levels.**
- **One human solution per Problem.** The teammate who collects the data picks it and writes the selection rule down.

## Source: Google Code Jam and Kick Start, 2018–2022

Problems and Human Samples come from Google Code Jam and Google Kick Start rounds held from 2018 to 2022 (#47).

- **Problem statements:** Google's official archive, [google/coding-competitions-archive](https://github.com/google/coding-competitions-archive) (Apache-2.0).
- **Human Samples:** contestants' submitted code from the [GCJ Archive](https://zibada.guru/gcj/), which has every submission for GCJ 2018 and all of 2019–2023. The site states that under Google's Coding Competitions Terms all submitted code is published under the MIT License, so the code can be kept in this repo with credit. A mirror of the same data is on Zenodo ([10.5281/zenodo.18901762](https://zenodo.org/records/18901762)).
- **Python 3 and accepted:** from 2018 Google's judge ran the code and stored the language. The archive's file extensions `.py3` and `.pypy3` mark Python 3; other Python files are left out. Accepted means the scoreboard counts the submission as correct on at least Test Set 1. Before 2018 contestants uploaded code beside their own output, so nothing proves the code ran, and the archive has no code for 2010–2017 anyway.
- **Dates:** the last round used is Kick Start 2022 Round H, 2022-11-12. The 2023 Farewell Rounds are left out.
- **Difficulty:** the source has no difficulty label. Each Problem keeps its round (Qualification, 1A–1C, 2, 3, World Finals, I/O for Women, Kick Start A–H and Practice), its letter in the round, and the solve rate of each Test Set from the scoreboard. Rounds run easy to hard, and problems inside a round mostly do too.

### Check against each Detector's training data

No Detector was trained on Code Jam or Kick Start:

| Detector | Training or tuning data | Code Jam or Kick Start in it? |
|-|-|-|
| `xgb_tfidf` | APPS, CodeChef, CodeContests, HackerEarth, HumanEval, MBPP, MTrajK ([repo readme](https://github.com/MarcOedingen/ChatGPT-Code-Detection#data)) | No. [APPS](https://github.com/hendrycks/apps) is Codewars, AtCoder, Kattis and Codeforces. [CodeContests](https://github.com/google-deepmind/code_contests) is Aizu, AtCoder, CodeChef, Codeforces and HackerEarth. [MTrajK/coding-problems](https://github.com/MTrajK/coding-problems) lists Google's competitions as a training site, but none of its 132 solutions is from Code Jam or Kick Start (grep for `codejam`, `kickstart`, `withgoogle` on its main branch). |
| `droiddetect` | DroidCollection: StarcoderData and The Vault (GitHub), research code, and competitive programming from TACO, CodeNet (AtCoder, Aizu), LeetCode and Codeforces ([dataset card](https://huggingface.co/datasets/project-droid/DroidCollection), [paper 3.1](https://aclanthology.org/2025.emnlp-main.1593.pdf)) | No. [TACO](https://huggingface.co/datasets/BAAI/TACO) is Aizu, AtCoder, CodeChef, Codeforces, Codewars, GeeksforGeeks, HackerEarth, HackerRank, Kattis and LeetCode. |
| `whodunit` | 399 CodeChef problems ([Zenodo](https://doi.org/10.5281/zenodo.10152237)) | No. |
| `atc` | No training. Zero-shot on CodeLlama-7B-Instruct; evaluated on MBPP, APPS and CodeContests ([repo](https://github.com/maorash/ATC)) | No. |
| `llm_judge` | No training. Zero-shot prompt ([replication package](https://doi.org/10.5281/zenodo.22248135)) | No. |

Two risks are left. Some contestants pushed their Code Jam code to GitHub, so a few Human Samples may sit in StarcoderData or The Vault inside DroidCollection, and in the Generators' pretraining. The same is true of every judge's code. Problems whose Human Sample a Generator copies are flagged by #33. The collection step (#48) also searches the `xgb_tfidf` jsonl for the `Case #` output format and drops any match.

### How many Problems

The archive has **281 Problems** with code from 2018 to 2022: 158 from Code Jam (34 in 2018, then 31 a year) and 123 from Kick Start (27 in 2019, then 32 a year). The count with at least one accepted Python 3 solution is a little lower, because World Finals rounds had about 25 contestants. #48 writes down the exact number.

That is fewer than the 700 aimed for. At 281 the 95% half-width of a miss rate near 0.5 is about ±6 points (it is ±3.7 at 700). No other source meets the training-data and licence rules at a larger size (see below).

## Considered Options

- **AtCoder contests after CodeNet (mid-2020 to 2022-11).** More than 1,000 Problems, an official difficulty (letter and points), and many Python 3 submissions with dates. Rejected for the licence: the [AtCoder Terms of Use](https://atcoder.jp/tos) say "the ownership and copyright of any program posted on our Website ... shall belong to the User who created it", and grant no licence to copy it. AtCoder contests up to 2020 are also in CodeNet, so in CodeContests and DroidCollection.
- **Codeforces, LeetCode, CodeChef, HackerEarth, Aizu, Kattis, Codewars, HackerRank, GeeksforGeeks.** Each is in at least one Detector's training data (table above).
- **Code Jam 2008–2009.** The archive has the code, but submissions were not run by the judge and are mostly Python 2.
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
