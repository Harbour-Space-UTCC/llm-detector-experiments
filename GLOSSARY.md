# Glossary

**Question**: The one thing an Experiment sets out to answer (e.g. "Do published detectors still catch code written by frontier LLMs?").

**Experiment**: A fixed design that answers one Question: a set of Detectors, Datasets and Metrics.

**Run**: One Detector scored on one Dataset under one config and seed. Produces a Score for every Sample.

**Detector**: A method that maps a code Sample to a Score of how likely it is to be LLM-written (zero-shot, trained classifier, stylometric).

**Problem**: One coding task (statement and ID) put into the Prompt Template to make a Generator write code. _Avoid_: question (that is the research Question).

**Prompt Template**: Text with a placeholder that a Problem fills in; the full prompt sent to a Generator.

**Generator**: One LLM, pinned by exact model ID, that writes LLM-written Samples.

**Dataset**: A collection of labelled Samples with known provenance.

**Sample**: One piece of code with its label (human or LLM-written) and, if LLM-written, the Generator that wrote it.

**Score**: A Detector's output for one Sample. Higher means more likely LLM-written.

**Result**: Metrics computed from a Run's Scores.

**Miss rate**: Share of LLM-written Samples a Detector scores as human at a given threshold. The threshold is the paper's own. When the paper gives none, it is the one that flags the paper's FPR share of human Samples, or 5% if the paper states no FPR either.

**Outdated**: A Detector whose miss rate on frontier Generators is higher than the miss rate its paper reported.

**Positive class**: LLM-written. Every rate (TPR, FPR) counts LLM-written code as positive. _Avoid_: papers' "FPR" when they made human code positive.
