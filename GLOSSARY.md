# Glossary

**Question**: The one thing an Experiment sets out to answer (e.g. "How well do published detectors catch LLM-written code in each Category?").

**Experiment**: A fixed design that answers one Question: a set of Detectors, Datasets and Metrics.

**Run**: One Detector scored on one Dataset under one config and seed. Produces a Score for every Sample.

**Detector**: A method that maps a code Sample to a Score of how likely it is to be LLM-written (zero-shot, trained classifier, stylometric).

**Problem**: One coding task (statement and ID) put into the Prompt Template to make a Generator write code. A forum post (its title and text, without its code) is one Problem, and the code from that post is its Human Sample. _Avoid_: question (that is the research Question).

**Prompt Template**: Text with a placeholder that a Problem fills in.

**Prompt**: One Prompt Template filled with one Problem: the exact text sent to a Generator. Every Generator gets the same Prompt for the same Problem and Prompt Template. _Avoid_: filled template, rendered prompt.

**Generator**: One LLM, pinned by exact model ID, that writes LLM-written Samples.

**Dataset**: A collection of labelled Samples with known provenance.

**Sample**: One piece of code with its label (human or LLM-written) and, if LLM-written, the Generator that wrote it.

**Score**: A Detector's output for one Sample. Higher means more likely LLM-written.

**Result**: Metrics computed from a Run's Scores.

**Miss rate**: Share of LLM-written Samples a Detector scores as human at a given threshold. The threshold is the paper's own. When the paper gives none, it is the one that flags the paper's FPR share of human Samples, or 5% if the paper states no FPR either.

**Outdated**: A Detector whose miss rate on Direct Samples from frontier Generators is higher than the miss rate its paper reported. Only Direct is compared, because papers measured plain LLM output.

**Category**: How a Sample came to be written. Every Sample has exactly one: Human, Direct, Style-prompted or Human-fixed. _Avoid_: condition, type, source.

**Human**: Category of Samples written by a person. The only Category labelled human.

**Post type**: Where in a forum post a Human Sample's code came from: `question` (the asker's own attempt, often broken) or `answer` (a reply that solves the Problem). _Avoid_: code source, origin.

**Human split**: A subset of the Human Samples (all of them, one Post type, or one site) that a summary row's LLM-written Samples are compared against. Shows whether a Detector separates human from LLM code or only one kind of human code from another.

**Direct**: Category of LLM-written Samples from the plain Prompt Template, which asks only for a solution to the Problem. _Avoid_: AI only, pure AI.

**Style-prompted**: Category of LLM-written Samples from a Style Prompt Template. _Avoid_: AI + refine prompt, humanized prompt.

**Style Prompt Template**: A Prompt Template that also asks the Generator to write code that looks human-written.

**Human-fixed**: Category of LLM-written Samples made by applying Edit rules to a Direct Sample, the way a student might touch up code before handing it in. Still labelled LLM-written, and keeps the Generator of the Sample it was made from. _Avoid_: AI + human fix, humanized, perturbed.

**Formatted copy**: A Sample run through black at a pinned version, made for every Sample in every Category, Human included. Not a Category, because it never changes who wrote the code. Used to check whether a Detector reacts only to spacing. _Avoid_: normalized, cleaned.

**Formatter check**: The stage that makes Formatted copies, and the summary rows that compare formatted with unformatted Samples to show whether a Detector reacts only to spacing.

**Edit rule**: One fixed, mechanical change used to make a Human-fixed Sample (e.g. rename variables to short names, remove comments).

**Edit count**: How many Edit rules were applied to a Human-fixed Sample (e.g. 2 or 5). _Avoid_: light, heavy, edit level.

**Positive class**: LLM-written. Every rate (TPR, FPR) counts LLM-written code as positive. _Avoid_: papers' "FPR" when they made human code positive.
