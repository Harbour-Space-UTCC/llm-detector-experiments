"""DetectCodeGPT (zero-shot, perturbation + proxy LLM logits).

Paper: Shi et al. (2025).
Code: https://github.com/YerbaPage/DetectCodeGPT (MIT).
Access: local open model logits; default scorer CodeLlama-7B (fp16 on T4, not bf16).
  Defaults use 50 perturbations per Sample (~100k 7B forward passes for 2k Samples): cut perturbations or use a smaller scorer.
Paper headline: original paper uses CodeSearchNet / The Stack, not coding problems.
  Mean AUROC 0.594 on Pan et al.'s education set (Yao et al. 2026, Table 1). Djire (2026): accuracy 0.50, F1 0.00.
"""


def score(codes):
    raise NotImplementedError("detectcodegpt: placeholder, see docstring")
