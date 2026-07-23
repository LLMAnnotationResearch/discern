"""discern — find and validate the features that distinguish two groups of text.

Blinded LLM discovery proposes candidate features from a Group A / Group B contrast; independent,
held-out, multi-model measurement decides which ones survive (same-sign replication + permutation
null + Benjamini-Hochberg FDR). Nothing in the method is specific to any dataset: you supply a CSV, a
text column, and a binary group column.

Typical use:
    from discern import RunConfig, run_pipeline
    cfg = RunConfig(dataset="data.csv", text_col="text", group_col="group")
    run_pipeline(cfg, base_dir=".")
or via the CLI:
    discern run --dataset data.csv --text-col text --group-col group

Results are valid from a single real run; the label-permuted "placebo" pass is a recommended,
label-free confidence check (it should validate ~nothing on your data), not a required step:
    discern run --dataset data.csv --text-col text --group-col group --condition placebo --fresh-reservation
"""
__version__ = "0.1.0"

from .config import RunConfig, PROMPT_VERSION, dataset_fingerprint
from .pipeline import run_pipeline

__all__ = ["RunConfig", "PROMPT_VERSION", "dataset_fingerprint", "run_pipeline", "__version__"]
