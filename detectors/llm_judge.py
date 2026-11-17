"""LLM judge, Djire's LLM4GCD zero-shot prompt (LLM judge, API).

Paper: Djire (2026), ASE, DOI 10.1145/3832783.3844566.
Replication package: https://doi.org/10.5281/zenodo.22248135 (src.zip, MIT inside; Zenodo says CC-BY-4.0).
  llm4gcd.py holds the 4 prompts verbatim, plus all raw verdicts and the Table 1 confusion matrices.
Strategy: zero-shot ("classification"). On the shipped verdicts it beats the other three for GPT-5-mini
  (LLM-positive F1 0.85 vs 0.66-0.80; AUROC 0.89 vs 0.56-0.74).
Call: prompt as system message, bare code as user message; 3 votes at temperature 0.1 (not applied by
  Claude Sonnet 5 or GPT-5-mini endpoints). Score = share of "yes" (AI) votes in {0, 1/3, 2/3, 1}; threshold 0.5.
  Parse with a regex fallback: Mistral replies hold raw newlines inside the JSON string.
  Use max_tokens 8192 + retries: at the paper's 1024, GPT-5-mini gave no valid vote on 8/18 human snippets.
Access: OpenRouter key. Put the judge's exact model ID in config so vendor overlap with Generators shows.
Eval data: 18 problems (C++, Java, Python), 18 human + 126 AI snippets, generators up to Code Llama (Aug 2023, inference).
Paper headline: Table 1 reports F1 with HUMAN as positive class. Converted to LLM-written positive (exact,
  from the shipped confusion matrices): GPT-5-mini zero-shot F1 0.76-0.97, pooled miss rate 0.25.
  Pooled zero-shot miss rate by judge: Llama-3.1-70B 0.07, Mistral Large 0.13, GPT-5-mini 0.25, Gemini-3 0.54,
  Claude Sonnet 5 0.60, Ministral 0.67, Gemini-2.5 0.96, GPT-3.5 0.98 (valid replies only).
  Only GPT-5-mini beats chance (AUROC 0.89); the rest sit at 0.26-0.53. openai/gpt-5-mini expires on OpenRouter 2026-12-11.
"""


def score(codes):
    raise NotImplementedError("llm_judge: placeholder, see docstring")
