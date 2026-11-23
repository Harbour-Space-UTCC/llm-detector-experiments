# Detectors see only the code of a Sample

A Sample row in the Category files keeps both `code` (the first Python code block of the reply) and `raw_response` (the whole reply), but `samples.csv` carries only `code`, and every Detector, the LLM judge included, scores `code` alone. We chose this because the experiment asks whether a Detector can tell LLM-written code from human code: the prose around a code block, or the Prompt that asked for it, would give the label away and measure something else. `raw_response` is kept so a missing or wrong code block can be checked by hand.

## Considered Options

- **Give Detectors the whole reply.** Closer to what a reader sees, but the prose ("Here is a solution…") is a near-certain LLM tell that human Samples never have.
- **Store the Prompt text in each Sample row.** Not needed: `sample_id` names the Prompt file and `problem_id` the line, and the Prompt files are committed (ADR 0001).

## Consequences

- A Sample whose reply has no code block gets `code = ""` and is not scored.
