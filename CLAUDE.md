## Inference

Run model inference (Generators, Detector `score()`, prototype notebooks) only when one of these holds:

1. The model sits behind an API (OpenRouter).
2. A GPU is present (`torch.cuda.is_available()`, i.e. Colab).
3. The user says to run it here.

Otherwise verify with tests that fake the model, as `tests/test_generate.py` does, and leave the real run to Colab.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for Harbour-Space-UTCC/llm-detector-experiments, managed with `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
