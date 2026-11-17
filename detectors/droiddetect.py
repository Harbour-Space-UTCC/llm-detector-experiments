"""DroidDetect-Large-Binary (trained classifier, ModernBERT-large 396M + triplet loss + resampling).

Paper: Orel, Paul, Gurevych & Nakov (2025), EMNLP, DOI 10.18653/v1/2025.emnlp-main.1593.
Checkpoint: https://huggingface.co/project-droid/DroidDetect-Large-Binary (Apache-2.0), pin revision 44c45cbf.
  Base alternative: project-droid/DroidDetect-Base-Binary rev 4328ba94. Large vs Base is settled in prototypes/droiddetect.ipynb.
  Not a standard AutoModel. Rebuild TLModel: encoder -> Linear(1024, 256) -> ReLU -> Linear(256, 2).
  The card's projection_dim 128 is wrong (checkpoint is 256); drop the duplicate additional_loss.* encoder keys.
  Pooling is an unmasked mean over 512 padded positions; its value depends on the attention backend (sdpa on T4
  vs FlashAttention-2), so the prototype picks the pooling that reproduces the paper.
Training code: https://github.com/DaniilOr/project-droid (MIT, not linked from the paper).
Access: download weights (1.6 GB fp32); GPU (T4 fine).
Score: P(MACHINE_GENERATED), softmax index 1.
Generators: 43 models from 11 families (Table 7); newest Mistral-Small-24B-Instruct-2501, Jan 2025 (inference from
  the name). Reasoning models excluded (Limitations). Held-out data: DroidCollection test split (HF, rev 9a42843b).
Paper headline: released DroidDetect 2-class weighted F1 99.25 Large / 99.18 Base (Table 6). Table 3's 97.00 is the
  older DroidDetectCLS model. Positive class = machine (same as ours). Threshold 0.5 (argmax).
  No miss rate stated: ~0.014 inferred from F1 and the 34% false-positive share of errors (E.1). Use the prototype's measured value.
"""


def score(codes):
    raise NotImplementedError("droiddetect: placeholder, see docstring")
