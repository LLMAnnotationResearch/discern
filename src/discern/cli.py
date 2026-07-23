"""discern — command-line interface.

    discern init                 # write a starter config.json + show API-key setup
    discern setup-help           # how/where to store your API keys
    discern run   --config my.json
    discern run   --dataset data.csv --text-col text --group-col group   # or all-flags
    discern run   --dataset data.csv --text-col text --group-col group --condition placebo --fresh-reservation
    discern check --dataset data.csv --group-col group --from-run runs/real_r0   # optional classifier check

Point it at a CSV, name the text column and the binary group column, and go. Paths resolve relative to
your current directory. Nothing in the method is specific to any dataset.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .config import RunConfig
from .core import DEFAULT_POOL
from .keys import DEFAULT_ENV, check_or_raise, load_env, setup_help
from .pipeline import run_pipeline

TEMPLATE_FIELDS = [  # (field, example/default) — the knobs a user commonly sets, written by `init`
    ("dataset", "path/to/your.csv"),
    ("text_col", "text"),
    ("group_col", "group"),
    ("focal_value", 1),
    ("reference_value", 0),
    ("focal_label", "focal group"),
    ("reference_label", "reference group"),
    ("unit_label", "item"),
    ("discovery_models", list(DEFAULT_POOL)),
    ("rotation_pool", list(DEFAULT_POOL)),
    ("n_per_group", 250),
    ("fdr_q", 0.05),
    ("fdr_q_exploratory", 0.10),
    ("condition", "real"),
    ("output_dir", "runs"),
]


def cmd_setup_help(args) -> None:
    print(setup_help())


def cmd_models(args) -> None:
    """List every model + provider available to put in a rotation (`discovery_models` / `rotation_pool`
    / `--models`). Pass --config to include the custom providers/models defined in that config."""
    from .core import MODELS, PROVIDERS, DEFAULT_POOL, FLOATING
    if args.config:
        cfg, _ = RunConfig.from_file(args.config)
        from .core import register_models
        register_models(cfg.models, cfg.providers)
    print("MODELS  (use the key on the left in discovery_models / rotation_pool / --models):\n")
    for k, (prov, mid) in MODELS.items():
        tag = "pinned" if k not in FLOATING else "float."
        pool = "  <- default pool" if k in DEFAULT_POOL else ""
        print(f"  {k:16s} {tag}  {prov:11s} {mid}{pool}")
    used = {prov for prov, _ in MODELS.values()}
    print("\nPROVIDERS  (endpoint  ·  api-key env var):\n")
    for name, sp in PROVIDERS.items():
        jm = "" if sp.json_mode == "json_object" else f" json_mode={sp.json_mode}"
        # a provider with no built-in model key is an endpoint TEMPLATE: usable only via a custom model
        tmpl = "" if name in used else "  <- endpoint template: add a \"models\" entry to use it"
        print(f"  {name:11s} {sp.kind:9s} {sp.base_url or '(SDK default)':58s} "
              f"[{sp.api_key_env or 'keyless'}]{jm}{tmpl}")
    print("\nAdd your own in a config (any OpenAI-compatible gateway or a local server):\n"
          '  "providers": {"myhost": {"base_url": "http://localhost:8000/v1", "api_key_env": null}},\n'
          '  "models":    {"my-model": {"provider": "myhost", "model_id": "org/name"}}\n'
          "then list the model key in discovery_models / rotation_pool. `discern models --config x.json`"
          " shows a config's full registry.")


def cmd_init(args) -> None:
    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} already exists (use --force to overwrite)")
    tmpl = {k: v for k, v in TEMPLATE_FIELDS}
    if args.dataset:
        tmpl["dataset"] = args.dataset
    if args.text_col:
        tmpl["text_col"] = args.text_col
    if args.group_col:
        tmpl["group_col"] = args.group_col
    out.write_text(json.dumps(tmpl, indent=2))
    print(f"wrote {out}\n\nEdit the three required fields (dataset, text_col, group_col) and any "
          f"optional ones, then:\n    discern run --config {out}\n")
    # data-aware echo: if pointed at a real CSV, show group sizes and a scale-up tip at setup time
    if args.dataset and args.group_col and Path(args.dataset).exists():
        try:
            from .data import read_table
            df = read_table(args.dataset)
            if args.group_col in df.columns:
                counts = df[args.group_col].astype(str).str.strip().value_counts()
                print(f"Data: {args.group_col!r} groups -> {counts.head(6).to_dict()} "
                      f"(set focal_value/reference_value to two of these).")
        except Exception:  # noqa: BLE001
            pass
    print("\nModels default to the shipped pool (OpenAI + Anthropic + DeepSeek). Set `discovery_models`"
          " and `rotation_pool` to any subset you have keys for — including open-weight models via"
          " OpenRouter (llama-3.3-70b, qwen-2.5-72b), Gemini, or a local server. Run `discern models`"
          " to see them all and how to add your own.\n")
    print(f"API keys: keep them in {DEFAULT_ENV} — run `discern setup-help` for the how-to.")


def _config_from_flags(args) -> RunConfig:
    for req in ("dataset", "text_col", "group_col"):
        if getattr(args, req) is None:
            raise SystemExit(f"--{req.replace('_', '-')} is required (or pass --config)")
    over = dict(dataset=args.dataset, text_col=args.text_col, group_col=args.group_col,
                condition=args.condition)
    if args.focal_value is not None:
        over["focal_value"] = args.focal_value
    if args.reference_value is not None:
        over["reference_value"] = args.reference_value
    if args.focal_label is not None:
        over["focal_label"] = args.focal_label
    if args.reference_label is not None:
        over["reference_label"] = args.reference_label
    if args.unit_label is not None:
        over["unit_label"] = args.unit_label
    if args.n_per_group is not None:
        over["n_per_group"] = args.n_per_group
    if args.classify_workers is not None:
        over["classify_workers"] = args.classify_workers
    if args.discovery_variant is not None:
        over["discovery_prompt_variant"] = args.discovery_variant
    if args.organize_themes:
        over["organize_themes"] = True
    if args.output_dir is not None:
        over["output_dir"] = args.output_dir
    if args.models:
        pool = [m.strip() for m in args.models.split(",") if m.strip()]
        over["discovery_models"] = pool
        over["rotation_pool"] = pool
    return RunConfig(**over)


_CONFIG_CONFLICT_FLAGS = ("dataset", "text_col", "group_col", "focal_value", "reference_value",
                          "focal_label", "reference_label", "unit_label", "models", "n_per_group",
                          "classify_workers", "discovery_variant", "output_dir")


def cmd_run(args) -> None:
    load_env()
    if args.config:
        conflicts = ["--" + n.replace("_", "-") for n in _CONFIG_CONFLICT_FLAGS
                     if getattr(args, n) is not None]
        if args.organize_themes:
            conflicts.append("--organize-themes")
        if args.fresh_reservation:
            conflicts.append("--fresh-reservation")
        if args.n_runs != 1:
            conflicts.append("--n-runs")
        if args.run_index != 0:
            conflicts.append("--run-index")
        if conflicts:
            raise SystemExit(f"--config cannot be combined with {', '.join(conflicts)} — put all run "
                             f"settings in the config file, or use flags without --config. "
                             f"(--dry-run and --no-resume may be used with --config.)")
        cfg0, base = RunConfig.from_file(args.config)
        cfgs = [(cfg0, base)]
    else:
        base = Path.cwd()
        cfgs = []
        for k in range(args.n_runs):
            cfg = replace(_config_from_flags(args), run_index=args.run_index + k)
            if args.fresh_reservation:
                idx = args.run_index + k
                cfg = replace(cfg, reservation_seed=2027 + 1000 * idx, split_seed=2027 + 1000 * idx)
            cfgs.append((cfg, base))

    for cfg, base in cfgs:
        cfg_r = cfg.resolve(base) if cfg.base_dir is None or not Path(cfg.dataset).is_absolute() else cfg
        cfg_r.validate()
        if args.dry_run:
            from .data import Dataset
            d = Dataset(cfg_r)
            print(f"[dry-run] {cfg.condition} r{cfg.run_index}: OK — pool={len(d.pool)} "
                  f"meas={len(d.m_uid)} sizes={d.group_min_sizes()} fingerprint={d.fingerprint}")
            print(f"[dry-run] rows: {d.excluded}")
            note = cfg_r.unpinned_pool_note()
            if note:
                print(f"[dry-run] note: {note}")
            continue
        check_or_raise(cfg_r)
        run_pipeline(cfg, base, resume=not args.no_resume)


def cmd_check(args) -> None:
    from . import classifier_check
    classifier_check.run_check(args)


def _add_run_args(pr) -> None:
    pr.add_argument("--config", help="path to a JSON config (overrides the flags below)")
    pr.add_argument("--dataset")
    pr.add_argument("--text-col", dest="text_col")
    pr.add_argument("--group-col", dest="group_col")
    pr.add_argument("--focal-value", dest="focal_value")
    pr.add_argument("--reference-value", dest="reference_value")
    pr.add_argument("--focal-label", dest="focal_label")
    pr.add_argument("--reference-label", dest="reference_label")
    pr.add_argument("--unit-label", dest="unit_label",
                    help="what one row is, e.g. 'product review' (appears in every prompt)")
    pr.add_argument("--models", help="comma-separated model keys for discovery + rotation "
                    "(default: the shipped pool)")
    pr.add_argument("--n-per-group", dest="n_per_group", type=int,
                    help="held-out measurement units per group (default 250)")
    pr.add_argument("--classify-workers", dest="classify_workers", type=int,
                    help="concurrent classification requests (default 24); lower it if you hit "
                         "provider rate limits")
    pr.add_argument("--condition", choices=["real", "placebo"], default="real")
    pr.add_argument("--discovery-variant", dest="discovery_variant",
                    choices=["grounded", "relaxed"])
    pr.add_argument("--organize-themes", action="store_true")
    pr.add_argument("--fresh-reservation", action="store_true",
                    help="draw a fresh held-out sample per run (for stability batches)")
    pr.add_argument("--run-index", dest="run_index", type=int, default=0)
    pr.add_argument("--n-runs", dest="n_runs", type=int, default=1)
    pr.add_argument("--output-dir", dest="output_dir")
    pr.add_argument("--dry-run", action="store_true", help="validate config + partition, no API calls")
    pr.add_argument("--no-resume", action="store_true")


def main() -> None:
    p = argparse.ArgumentParser(prog="discern", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="write a starter config.json")
    pi.add_argument("--out", default="discern.config.json")
    pi.add_argument("--force", action="store_true")
    pi.add_argument("--dataset")
    pi.add_argument("--text-col", dest="text_col")
    pi.add_argument("--group-col", dest="group_col")
    pi.set_defaults(func=cmd_init)

    ps = sub.add_parser("setup-help", help="how/where to store your API keys")
    ps.set_defaults(func=cmd_setup_help)

    pm = sub.add_parser("models", help="list available models + providers (and how to add your own)")
    pm.add_argument("--config", help="also include custom providers/models from this config")
    pm.set_defaults(func=cmd_models)

    pr = sub.add_parser("run", help="run the pipeline (discovery -> measurement -> selection)")
    _add_run_args(pr)
    pr.set_defaults(func=cmd_run)

    pc = sub.add_parser("check", help="optional label-free cross-model agreement check")
    from .classifier_check import add_check_args
    add_check_args(pc)
    pc.set_defaults(func=cmd_check)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
