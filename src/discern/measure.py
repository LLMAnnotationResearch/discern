"""Stage 4: measure every candidate on the full held-out sample. Main spec = BALANCED ROTATION
(one model per unit, balanced within group x split). No screen on the inference path (PI decision
2026-07-13) — the confounded screen was removed, not made optional.

The classification cache is keyed by dataset fingerprint + prompt version + model snapshot +
unit id + question + definition, so a changed dataset/prompt/model never silently reuses a stale answer.
Every unit call is wrapped in an audit request/response(/failure) event.
"""
from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .core import MODELS, PROVIDERS, classify_one, balanced_assignment


class Cache:
    """Persistent classification cache with a reproducibility-complete key."""

    def __init__(self, path, fingerprint, prompt_version, classifier_settings, revisions=None):
        self.path = Path(path)
        self.fp = fingerprint
        self.pv = prompt_version
        self.cs = classifier_settings
        self.rev = dict(revisions or {})   # model_key -> user revision (identity for mutable backends)
        self._d = json.loads(self.path.read_text()) if self.path.exists() else {}
        self._lock = threading.Lock()

    def _model_identity(self, model) -> str:
        # The cache must key on the ACTUAL model behind a key, not just its id. Two custom endpoints
        # serving 'model-x' (different provider/base_url) must not collide, and a floating/local model
        # whose backend changes under a stable id must not silently reuse old answers — so include the
        # provider, endpoint, model_id, and any user-supplied revision. (Snapshot-pinned built-ins have
        # a stable identity here; mutable backends should set model_revision to control invalidation.)
        provider, model_id = MODELS[model]
        base = PROVIDERS[provider].base_url or "" if provider in PROVIDERS else ""
        return "\x1e".join([provider, base, model_id, self.rev.get(model, "")])

    def key(self, uid, model, question, definition=""):
        # definition is part of the rendered classifier prompt, so it MUST be in the key: two
        # candidates with the same question but different definitions must not share an answer.
        raw = "\x1f".join([self.fp, self.pv, self._model_identity(model), self.cs, str(uid),
                           question.strip().lower(), (definition or "").strip().lower()])
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, uid, model, question, definition=""):
        return self._d.get(self.key(uid, model, question, definition))

    def put_many(self, items):
        with self._lock:
            for uid, model, question, definition, val in items:
                self._d[self.key(uid, model, question, definition)] = val
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._d))
            tmp.replace(self.path)


def _measure_units(question, uids, texts, models, defn, cache, audit, cid, workers,
                   unit_label="business description"):
    """Classify the given units, each with its assigned model. Returns 0/1 array. Cache-aware;
    audits every fresh call."""
    need = [(j, uids[j], models[j]) for j in range(len(uids))
            if cache.get(uids[j], models[j], question, defn) is None]
    if need:
        def one(t):
            j, uid, model = t
            audit.event("measure", "request", candidate_id=cid, uid=uid, model=model)
            try:
                v = classify_one(question, texts[j], model=model, definition=defn,
                                 unit_label=unit_label)
            except Exception as ex:  # noqa: BLE001
                audit.event("measure", "failure", candidate_id=cid, uid=uid, model=model, error=str(ex))
                raise
            audit.event("measure", "response", candidate_id=cid, uid=uid, model=model, answer=v)
            return (uid, model, question, defn, v)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(one, need))
        cache.put_many(results)
    return np.array([cache.get(uids[j], models[j], question, defn) for j in range(len(uids))])


def run_measurement(cfg, data, candidates, cache, audit) -> dict:
    """Measure all candidates on the held-out sample under the configured design.
    Returns {candidate_id -> {"y": [...], "model_assignment": [...]}}."""
    labels = data.measurement_labels()
    uids, texts = data.m_uid, data.m_text
    C = {}
    skipped = []
    if cfg.measurement_design == "rotate":
        # one balanced assignment reused for all candidates (deterministic; auditable)
        assign = balanced_assignment(labels, data.m_split, cfg.rotation_pool, seed=cfg.assignment_seed)
        assign = list(assign)
    for idx, c in enumerate(candidates):
        cid = c["candidate_id"]
        q, defn = c["classification_question"], c.get("definition", "")
        # Graceful, still fail-closed: a single unit whose answer stays malformed after retries (e.g. a
        # model that stubbornly returns a non-binary value for one question x text) drops just THAT
        # CANDIDATE, logged — not the whole run. A systematic outage (many candidates failing) still
        # raises via the guard below, so an outage never masquerades as a small result set.
        try:
            if cfg.measurement_design == "rotate":
                y = _measure_units(q, uids, texts, assign, defn, cache, audit, cid,
                                   cfg.classify_workers, unit_label=cfg.unit_label)
                C[cid] = {"y": [int(v) for v in y], "model_assignment": assign}
            else:  # ensemble: average across the pool
                cols = []
                for m in cfg.ensemble_pool:
                    models = [m] * len(uids)
                    cols.append(_measure_units(q, uids, texts, models, defn, cache, audit, cid,
                                               cfg.classify_workers, unit_label=cfg.unit_label))
                y = np.mean(cols, axis=0)
                C[cid] = {"y": [float(v) for v in y], "model_assignment": cfg.ensemble_pool}
        except Exception as ex:  # noqa: BLE001
            audit.event("measure", "candidate_skipped", candidate_id=cid,
                        feature_name=c.get("feature_name"), error=str(ex)[:200])
            skipped.append((cid, c.get("feature_name"), str(ex)[:160]))
            continue
        audit.event("measure", "note", candidate_id=cid, done=idx + 1, total=len(candidates))
    if skipped:
        frac = len(skipped) / max(1, len(candidates))
        audit.event("measure", "skipped_summary", n_skipped=len(skipped), fraction=round(frac, 3),
                    candidates=[{"candidate_id": s[0], "feature": s[1], "error": s[2]} for s in skipped])
        # systematic failure (outage) must still fail closed, not silently shrink the candidate set
        if len(skipped) > 2 and frac > 0.10:
            raise RuntimeError(f"{len(skipped)}/{len(candidates)} candidates failed measurement "
                               f"({frac:.0%}) — treating as a systematic failure. First: {skipped[:3]}")
    return C
