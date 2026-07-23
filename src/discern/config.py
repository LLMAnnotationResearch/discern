"""RunConfig — every knob of a discern run, explicit and reproducible.

You must supply three things: the `dataset` CSV, the `text_col` holding the text, and the binary
`group_col`. Everything else has a sensible default:
  * NO screen on the inference path (measure every candidate, Stage 5 on all).
  * BALANCED ROTATION confirmatory measurement over the model pool.
  * Held-out reservation of 250 per group (n=500) by default — see docs/GUIDANCE for smaller samples.
  * Default rotation pool = 3 providers (gpt-4o-mini, claude-haiku, gpt-4.1-mini + DeepSeek) for
    cross-provider variance; fully user-configurable. MAIN_POOL is the pinned-snapshot reference pool
    (a fixed model version — not byte-identical outputs); unpinned models (DeepSeek) have their runtime
    version recorded per run.
Paths resolve relative to the config file (or an explicit base_dir), never the caller's CWD.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .core import MODELS, MAIN_POOL, DEFAULT_POOL, FLOATING

PROMPT_VERSION = "discern-1"  # part of the classification cache key: bump on ANY prompt-text change
#   so a changed prompt never silently reuses an answer computed under the old wording.


@dataclass
class RunConfig:
    # --- input dataset (the three REQUIRED fields — no defaults) ---
    dataset: str                              # path to your CSV (resolved relative to base_dir)
    text_col: str                             # column holding the text to analyze
    group_col: str                            # binary group column (the contrast to explain)
    # --- optional dataset settings ---
    id_col: str | None = None                 # stable unit ID column; None -> use CSV row index
    focal_value: object = 1                   # value of group_col treated as the "focal" group (-> group 1)
    reference_value: object = 0               # value treated as the reference group (-> group 0)
    focal_label: str | None = None            # human name for the focal group in output legends;
    reference_label: str | None = None        #   None -> "<group_col>=<value>". Set for readable output.
    unit_label: str = "item"                  # what one row IS ("product review", "job posting", ...);
    #                                           appears in every prompt in place of any domain term.

    # --- experiment condition ---
    condition: str = "real"                   # "real" | "placebo" (placebo permutes labels)
    run_index: int = 0                        # distinguishes runs in a batch (seeds derive from it)

    # --- discovery (Stage 1-2) ---
    discovery_models: list = field(default_factory=lambda: list(DEFAULT_POOL))
    discovery_prompt_variant: str = "relaxed"  # "relaxed" permits one level of text-supported
    #   abstraction (recovers abstract mechanisms, not just concrete labels); "grounded" is
    #   concrete/observable only. Both are validated by the same held-out measurement rule.
    n_iterations: int = 15                    # discovery calls per split. Default from a saturation
    #   diagnostic (10->15 still adds real narrow concepts; 15->20 adds only re-wordings). Raise it if
    #   your domain is broad; a cycling/no-reuse sampler shows fresh examples each call.
    items_per_group: int = 15                 # units shown per group per discovery call
    discovery_temperature: float = 0.7
    discovery_max_tokens: int = 4000          # per discovery call; too low -> truncated JSON (a
    #   verbose model enumerating many hypotheses can exceed a stingy cap). On a truncation the call
    #   grows this automatically (see core.llm_json_call), but a sane floor avoids needless retries.

    # --- consolidation (Stage 3) ---
    consolidation_model: str = "gpt-4.1"      # capable generation model — gpt-4o-mini under-merged
    consolidation_temperature: float = 0.0    # deterministic; retry-jitter still fires on malformed JSON
    consolidation_max_tokens: int = 16000     # P2/P3 output can be long; too low -> truncated JSON
    residual_dedup: bool = True               # extra temp-0 pass merging P3's own exact-equivalent twins

    # --- measurement reservation + design (Stage 4) ---
    n_per_group: int = 250                    # held-out confirmatory units per group (n=500 total)
    measurement_design: str = "rotate"        # "rotate" (main spec) | "ensemble" (sensitivity)
    rotation_pool: list = field(default_factory=lambda: list(DEFAULT_POOL))
    ensemble_pool: list = field(default_factory=lambda: list(MAIN_POOL))
    max_candidates: int = 400                 # hard guard: raise (not silently truncate) before measuring
    classify_workers: int = 24

    # --- selection (Stage 5) ---
    permutations: int = 2000
    fdr_q: float = 0.05                        # primary ("confirmed") FDR level — the headline table
    fdr_q_exploratory: float | None = 0.10    # secondary ("suggestive") tier reported ALONGSIDE the
    #   primary set (None disables). Surfaces real-but-marginal effects instead of hiding them below a
    #   single line — important for small-effect field studies. False-positive control still rests on
    #   the same-sign replication gate; optionally sanity-check this tier on your data with a placebo run.
    effect_floor: float | None = None         # optional, explicitly domain-specific; reported separately

    # --- optional post-validation theme grouping (Stage 6; navigation-only, non-selective) ---
    organize_themes: bool = False             # off by default (navigation-only grouping)
    theme_model: str = "gpt-4.1"

    # --- reproducibility ---
    reservation_seed: int = 2027              # fixes the held-out sample; override for fresh-per-run
    split_seed: int = 2027                    # fixes the 1/2 split within the measurement sample
    assignment_seed: int = 11                 # balanced rotation assignment
    placebo_seed: int = 500                   # coherent null relabeling (per-run: +run_index)
    discovery_seed: int = 100                 # discovery pool halving + example sampling (per-run: +run_index)
    prompt_version: str = PROMPT_VERSION

    # --- custom model registry (extend the built-ins; select from them via the pools above) ---
    providers: dict = field(default_factory=dict)  # name -> {kind?, base_url?, api_key_env?}; register an
    #   OpenAI-compatible endpoint (a gateway like OpenRouter/Together/Groq, or a localhost server) or an
    #   anthropic-kind one. kind defaults to "openai"; api_key_env=null means keyless (e.g. local Ollama).
    models: dict = field(default_factory=dict)      # key -> {provider, model_id}; then put the key in
    #   discovery_models / rotation_pool. Extends the shipped registry (see discern.core.register_models).
    model_revision: dict = field(default_factory=dict)  # model_key -> revision string. Folded into the
    #   classification cache key AND recorded as provenance. For a model whose backend can change under a
    #   stable id (a local/Ollama tag re-pulled with new weights, or a floating hosted alias), bump this to
    #   force fresh classification instead of silently reusing cached answers from the old model.

    # --- io ---
    base_dir: str | None = None               # resolves relative paths; None -> config file dir / CWD
    output_dir: str = "runs"

    # -------------------------------------------------------------------------------------------
    def resolve(self, base: Path) -> "RunConfig":
        """Return a copy with dataset/output_dir resolved to absolute paths under `base`."""
        b = Path(base)
        d = asdict(self)
        d["dataset"] = str((b / self.dataset).resolve()) if not Path(self.dataset).is_absolute() else self.dataset
        d["output_dir"] = str((b / self.output_dir).resolve()) if not Path(self.output_dir).is_absolute() else self.output_dir
        d["base_dir"] = str(b)
        return RunConfig(**d)

    def validate(self) -> None:
        errs = []
        # Register any custom providers/models FIRST so the pool checks below see them. A malformed
        # custom entry (bad shape, unknown provider) becomes a clear validation error, not a crash.
        from .core import register_models
        try:
            register_models(self.models, self.providers)
        except Exception as e:  # noqa: BLE001
            errs.append(f"invalid custom providers/models: {e}")
        if self.condition not in ("real", "placebo"):
            errs.append(f"condition must be real|placebo, got {self.condition!r}")
        if self.measurement_design not in ("rotate", "ensemble"):
            errs.append(f"measurement_design must be rotate|ensemble, got {self.measurement_design!r}")
        if self.focal_value == self.reference_value:
            errs.append("focal_value and reference_value must differ")
        for name, pool in (("discovery_models", self.discovery_models),
                           ("rotation_pool", self.rotation_pool),
                           ("ensemble_pool", self.ensemble_pool)):
            if not pool:
                errs.append(f"{name} is empty")
            for m in pool:
                if m not in MODELS:
                    errs.append(f"{name}: unknown model {m!r} (known: {sorted(MODELS)})")
        if self.consolidation_model not in MODELS:
            errs.append(f"unknown consolidation_model {self.consolidation_model!r}")
        if self.organize_themes and self.theme_model not in MODELS:
            errs.append(f"unknown theme_model {self.theme_model!r}")
        # rotate needs >= 2 distinct models — balanced rotation across a pool is the whole point; a
        # one-model "rotation" silently degrades to a single-model design (use 'ensemble' for that).
        if self.measurement_design == "rotate" and len(set(self.rotation_pool)) < 2:
            errs.append(f"measurement_design 'rotate' needs >= 2 distinct models in rotation_pool "
                        f"(got {self.rotation_pool}); for a single model use measurement_design 'ensemble'")
        # model_revision: a dict of ACTIVE model key -> non-empty string. Validate here so a typo, a
        # null, or a revision for an unused model fails now — not at Stage 4, after discovery and
        # consolidation calls have already cost money.
        if not isinstance(self.model_revision, dict):
            errs.append(f"model_revision must be a dict of model_key -> revision string, got "
                        f"{type(self.model_revision).__name__}")
        else:
            active = self.active_models()
            for k, v in self.model_revision.items():
                if k not in active:
                    errs.append(f"model_revision key {k!r} is not a model used by this run "
                                f"(active models: {sorted(active)})")
                if not isinstance(v, str) or not v.strip():
                    errs.append(f"model_revision[{k!r}] must be a non-empty string, got {v!r}")
        if self.discovery_prompt_variant not in ("grounded", "relaxed"):
            errs.append(f"discovery_prompt_variant must be grounded|relaxed, got "
                        f"{self.discovery_prompt_variant!r}")
        for name, v in (("n_per_group", self.n_per_group), ("n_iterations", self.n_iterations),
                        ("items_per_group", self.items_per_group), ("permutations", self.permutations),
                        ("max_candidates", self.max_candidates), ("classify_workers", self.classify_workers)):
            if not isinstance(v, int) or v <= 0:
                errs.append(f"{name} must be a positive int, got {v!r}")
        if not (0 < self.fdr_q < 1):
            errs.append(f"fdr_q must be in (0,1), got {self.fdr_q}")
        if self.fdr_q_exploratory is not None and not (0 < self.fdr_q_exploratory < 1):
            errs.append(f"fdr_q_exploratory must be in (0,1) or None, got {self.fdr_q_exploratory}")
        if errs:
            raise ValueError("invalid RunConfig:\n  - " + "\n  - ".join(errs))

    def active_models(self) -> set:
        """Every model key this run will actually call: discovery + consolidation + the measurement
        pool in force (rotate|ensemble) + the theme model iff theming is on. Single source of truth
        for key requirements (keys.py), the unpinned-alias note, and run provenance (pipeline.py)."""
        used = set(self.discovery_models) | {self.consolidation_model}
        used |= set(self.rotation_pool if self.measurement_design == "rotate" else self.ensemble_pool)
        if self.organize_themes:
            used.add(self.theme_model)
        return used

    def unpinned_pool_note(self) -> str | None:
        """Informational note (not a warning) if ANY active model — discovery, consolidation,
        measurement, or theme — is an unpinned alias. These are fine to use: a completed run is
        reproducible from its stored intermediates, and each unpinned model's runtime-resolved version
        is recorded in 00_runspec. Only the pinned reference pool (MAIN_POOL) names a fixed model
        version (and even a pinned snapshot does not guarantee byte-identical API outputs)."""
        unpinned = self.active_models() & FLOATING
        if unpinned:
            return (f"pool includes unpinned alias(es) {sorted(unpinned)} — their runtime-resolved "
                    f"version is recorded in 00_runspec; only the pinned reference pool names a fixed "
                    f"model version (identical API outputs are still not guaranteed)")
        return None

    def focal_name(self) -> str:
        return self.focal_label or f"{self.group_col}={self.focal_value}"

    def reference_name(self) -> str:
        return self.reference_label or f"{self.group_col}={self.reference_value}"

    def direction_legend(self) -> str:
        """One-line key so a reader never has to guess what a + / - sign means."""
        return (f"+ (focal_higher) = more prevalent among {self.focal_name()!r}; "
                f"- (focal_lower) = more prevalent among {self.reference_name()!r}")

    def to_json(self) -> dict:
        return asdict(self)

    def spec_hash(self, dataset_fp: str) -> str:
        """Canonical hash of everything that defines a run's IDENTITY (all config except output
        location + the dataset fingerprint). Persisted in the manifest; on resume a mismatch means
        the run name was reused under a changed configuration -> raise instead of blending artifacts."""
        d = asdict(self)
        # exclude output location + cosmetic-only fields (they don't affect any result, so changing
        # a display label must not force a re-run or block a resume)
        for k in ("base_dir", "output_dir", "focal_label", "reference_label"):
            d.pop(k, None)
        payload = json.dumps({"cfg": d, "dataset_fp": dataset_fp}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @classmethod
    def from_file(cls, path: str | Path) -> tuple["RunConfig", Path]:
        """Load a JSON config; returns (resolved_config, base_dir). Paths resolve to the config's dir."""
        p = Path(path).resolve()
        d = json.loads(p.read_text())
        cfg = cls(**d)
        # a base_dir in the config resolves relative to the CONFIG FILE (not the caller's CWD), so the
        # same config behaves identically no matter where `discern run --config ...` is invoked from.
        bd = d.get("base_dir")
        if bd:
            bd = Path(bd)
            base = bd if bd.is_absolute() else (p.parent / bd)
        else:
            base = p.parent
        return cfg.resolve(base), base


def dataset_fingerprint(path: str | Path) -> str:
    """Content hash of the dataset file — part of the cache key, so a changed dataset never
    silently reuses stale classifications."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]
