"""DroidDetect-Large-Binary (trained classifier, ModernBERT 395M).

Paper: Orel, Paul, et al. (2025), Droid resource suite.
Checkpoint: https://huggingface.co/project-droid/DroidDetect-Large-Binary
  (collection: https://huggingface.co/collections/project-droid/droid-683360d8b008214a4273099a)
  Not a standard AutoModel: copy the TLModel class from the model card and load pytorch_model.bin.
  The card hardcodes hidden dim 768; Large needs 1024.
Access: download weights; GPU (T4 fine).
Score: P(LLM-written) from the Binary head.
Paper headline: DroidDetectCLS-Large average weighted F1 97.00 (2-class) (Table 3). No threshold or miss rate stated.
"""


def score(codes):
    raise NotImplementedError("droiddetect: placeholder, see docstring")
