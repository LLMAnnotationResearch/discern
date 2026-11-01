"""Execute independent compact validation runs with separate caches and usage totals.

All statistical/generation/measurement behavior uses the production pipeline.
Credentials load from the existing local configuration and are never saved here.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern import core, keys
from discern.config import RunConfig
from discern.pipeline import run_pipeline
from discern.validation import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True, help="compact-layout manifest with planned_jobs")
    parser.add_argument("--out", required=True, help="new directory for orchestration metadata")
    parser.add_argument("--workers", type=int, default=5, help="concurrent independent runs")
    parser.add_argument("--classify-timeout", type=float, default=45, help="seconds per short classification request")
    parser.add_argument("--malformed-retry-delay", type=float, default=None,
                        help="optional delay for local schema/parse errors only; keeps six attempts and provider-error backoff")
    args = parser.parse_args()
    if args.malformed_retry_delay is not None:
        if args.malformed_retry_delay < 0:raise ValueError('retry delay must be nonnegative')
        normal_retry_wait=core._retry_wait
        core._retry_wait=lambda ex,attempt: args.malformed_retry_delay if isinstance(ex,ValueError) else normal_retry_wait(ex,attempt)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    keys.load_env()
    jobs = json.loads(Path(args.batch).read_text())["planned_jobs"]
    configs = []
    for job in jobs:
        cfg, base = RunConfig.from_file(job["config_path"])
        cfg.validate()
        keys.check_or_raise(cfg)
        configs.append((job["run_id"], cfg, base))
    if len({cfg.output_dir for _, cfg, _ in configs}) != len(configs):
        raise ValueError("parallel runs require separate output/cache directories")
    state = {"started_utc": datetime.now(timezone.utc).isoformat(), "status": "running",
             "script_sha256": sha256(__file__), "batch_sha256": sha256(args.batch),
             "classification_request_timeout_seconds": args.classify_timeout,
             "generation_request_timeout_seconds": 300,
             "malformed_answer_retry_delay_seconds": args.malformed_retry_delay,
             "sdk_retries": 0, "retry_policy": "production core retry/fallback loops; no nested SDK retries",
             "source_sha256": {p.name: sha256(p) for p in (Path(__file__).resolve().parents[1] / "src/discern").glob("*.py")},
             "package_versions": {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "openai", "anthropic"]},
             "usage_by_model": {}, "runs": {rid: {"status": "queued", "condition": cfg.condition,
              "config_sha256": sha256(next(j["config_path"] for j in jobs if j["run_id"] == rid)),
              "artifact_path": str(Path(cfg.output_dir) / rid)} for rid, cfg, _ in configs}}
    lock = threading.RLock()

    def save():
        with lock:
            tmp = out / "status.json.tmp"
            tmp.write_text(json.dumps(state, indent=2) + "\n")
            tmp.replace(out / "status.json")

    def sanitize(message):
        message = str(message)
        for name in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"]:
            value = os.environ.get(name)
            if value:
                message = message.replace(value, "[redacted]")
        return re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", message)

    def track(method, provider):
        def create(*pos, **kw):
            kw.setdefault("timeout", args.classify_timeout if kw.get("max_tokens", 0) <= 30 else 300)
            response = method(*pos, **kw)
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0)) or 0
            output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0)) or 0
            model = f"{provider}:{getattr(response, 'model', kw.get('model', 'unknown'))}"
            with lock:
                totals = state["usage_by_model"].setdefault(model, {"successful_calls": 0, "input_tokens": 0, "output_tokens": 0})
                totals["successful_calls"] += 1
                totals["input_tokens"] += int(input_tokens)
                totals["output_tokens"] += int(output_tokens)
                if totals["successful_calls"] % 100 == 0:
                    save()
            return response
        return create

    providers = {core.MODELS[m][0] for _, cfg, _ in configs for m in cfg.active_models()}
    for provider in providers:
        client = core._client(provider).with_options(max_retries=0)
        core._clients[provider] = client
        if core.PROVIDERS[provider].kind == "openai":
            client.chat.completions.create = track(client.chat.completions.create, provider)
        else:
            client.messages.create = track(client.messages.create, provider)
    save()

    def execute(job):
        rid, cfg, base = job
        start = time.monotonic()
        with lock:
            state["runs"][rid]["status"] = "running"
            state["runs"][rid]["started_utc"] = datetime.now(timezone.utc).isoformat()
            save()

        def log(message):
            clean = sanitize(message)
            print(clean, flush=True)
            with lock:
                state["runs"][rid]["latest_progress"] = clean
                save()
        try:
            result = run_pipeline(cfg, base, run_name=rid, resume=True, log=log)
            summary = {"status": "complete", "n_candidates": result["n_candidates"],
                       "n_tested": result["n_tested"], "n_validated": result["n_validated"],
                       "n_suggestive": result["n_suggestive"],
                       "n_uncorrected": result.get("n_uncorrected", 0),
                       "n_skipped_unmeasurable": result.get("n_skipped_unmeasurable", 0)}
        except Exception as exc:
            summary = {"status": "failed", "error_type": type(exc).__name__, "message": sanitize(exc)[:1000]}
            print(f"[{rid}] FAILED: {summary['error_type']}: {summary['message']}", flush=True)
        summary["wall_seconds"] = round(time.monotonic() - start, 2)
        with lock:
            state["runs"][rid].update(summary)
            save()
        return summary

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(execute, job) for job in configs]):
            future.result()
    state["status"] = "complete" if all(r["status"] == "complete" for r in state["runs"].values()) else "complete_with_failures"
    state["finished_utc"] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps({"status": state["status"], "runs": state["runs"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
