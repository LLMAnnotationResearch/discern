"""Dataset loading, stable unit IDs, stratified held-out reservation, and the discovery/measurement
split — with the guarantees the reviewer asked for: save row IDs BEFORE any index reset, stratify
explicitly, check minimum group sizes, and keep discovery strictly disjoint from measurement.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RunConfig, dataset_fingerprint


class Dataset:
    """Loaded dataset + a reproducible partition into a held-out measurement sample and a disjoint
    discovery pool. Every unit carries a stable `uid` that survives index resets."""

    def __init__(self, cfg: RunConfig):
        self.cfg = cfg
        self.fingerprint = dataset_fingerprint(cfg.dataset)
        self.df, self.excluded = _load_and_filter(cfg)

        # --- stratified held-out reservation (fixed by reservation_seed) ---
        n = cfg.n_per_group
        focal = self.df[self.df.group == 1]
        ref = self.df[self.df.group == 0]
        for nm, grp in (("focal", focal), ("reference", ref)):
            if len(grp) < n:
                raise ValueError(f"{nm} group has {len(grp)} usable rows < n_per_group={n}")
        mf = focal.sample(n, random_state=cfg.reservation_seed)
        mr = ref.sample(n, random_state=cfg.reservation_seed + 1)
        meas = pd.concat([mf, mr])
        self.meas_uids = set(meas["uid"])
        self.meas = meas.reset_index(drop=True)
        self.pool = self.df[~self.df["uid"].isin(self.meas_uids)].reset_index(drop=True)

        # preflight the DISCOVERY halves: the pool is split ~50/50 per group into two splits, and each
        # split must supply items_per_group per group for a discovery call. Catch infeasibility now
        # (e.g. in --dry-run) instead of only when discovery actually runs.
        half_focal = int((self.pool.group == 1).sum()) // 2
        half_ref = int((self.pool.group == 0).sum()) // 2
        if min(half_focal, half_ref) < cfg.items_per_group:
            raise ValueError(
                f"after reserving {n}/group for measurement, the discovery pool halves have "
                f"~{half_focal} focal / ~{half_ref} reference units each < items_per_group="
                f"{cfg.items_per_group}. Lower n_per_group or items_per_group, or add data per group "
                f"(need roughly n_per_group + 2*items_per_group per group).")

        # --- measurement arrays ---
        self.m_uid = self.meas["uid"].tolist()
        self.m_text = self.meas["text"].tolist()
        self.m_group = self.meas["group"].values.astype(int)          # canonical (real) labels
        # PLACEBO null = permute labels WITHIN each disjoint set (Terra 2026-07-15): within the
        # measurement sample this preserves its 250/250 balance (so placebo power/cells match the
        # real run), and within the discovery pool it preserves the pool's balance. The two sets
        # share no units, so this is still one coherent, recorded null relabeling.
        self.m_placebo = np.random.default_rng(cfg.placebo_seed + cfg.run_index).permutation(
            self.m_group.copy())
        self._pool_placebo = np.random.default_rng(cfg.placebo_seed + 10_000 + cfg.run_index).permutation(
            self.pool["group"].values.astype(int))
        # STRATIFIED 1/2 split on the labels ACTUALLY TESTED, so both real and placebo halves are
        # balanced (125/125 per active label per half).
        active = self.m_placebo if cfg.condition == "placebo" else self.m_group
        self.m_split = self._stratified_split(active, cfg.split_seed)

    @staticmethod
    def _stratified_split(labels, seed):
        rng = np.random.default_rng(seed)
        split = np.empty(len(labels), dtype=int)
        for g in np.unique(labels):
            idx = np.where(labels == g)[0]
            idx = idx[rng.permutation(len(idx))]
            half = len(idx) // 2
            split[idx[:half]] = 1
            split[idx[half:]] = 2
        return split

    def measurement_labels(self):
        """Group labels used for MEASUREMENT under the configured condition (coherent w/ discovery)."""
        return self.m_placebo if self.cfg.condition == "placebo" else self.m_group

    def pool_labels(self):
        """Group labels used for DISCOVERY under the configured condition (within-pool null shuffle)."""
        if self.cfg.condition == "placebo":
            return self._pool_placebo
        return self.pool["group"].values.astype(int)

    def group_min_sizes(self) -> dict:
        # cell counts by the ACTIVE label (the one tested) — these are what must be ~n/2 per half
        active = self.measurement_labels()
        return {"pool_focal": int((self.pool.group == 1).sum()),
                "pool_reference": int((self.pool.group == 0).sum()),
                "meas_per_group": self.cfg.n_per_group,
                "active_label": "placebo" if self.cfg.condition == "placebo" else "real",
                "split1_by_active_label": {int(g): int(((active == g) & (self.m_split == 1)).sum())
                                           for g in (0, 1)},
                "split2_by_active_label": {int(g): int(((active == g) & (self.m_split == 2)).sum())
                                           for g in (0, 1)}}


def read_table(path):
    """Load a tabular dataset into a DataFrame by extension: .xlsx/.xls via Excel, .tsv/.tab as
    tab-separated, everything else as CSV. Lets researchers point discern straight at survey exports."""
    p = str(path).lower()
    if p.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(path)
        except ImportError as e:  # openpyxl (.xlsx) / xlrd (.xls) not installed
            raise SystemExit(f"reading {path} needs an Excel engine: pip install openpyxl "
                             f"(.xlsx) or xlrd (.xls). [{e}]")
    if p.endswith((".tsv", ".tab")):
        return pd.read_csv(path, sep="\t")
    return pd.read_csv(path)


def _load_and_filter(cfg: RunConfig):
    """Read the dataset and apply the shared row filtering (missing/blank text, third-group exclusion,
    stable uid, canonical binary group). Returns (df_with_group_and_uid, excluded_report)."""
    df = read_table(cfg.dataset)
    for role, col in (("text_col", cfg.text_col), ("group_col", cfg.group_col), ("id_col", cfg.id_col)):
        if col is not None and col not in df.columns:
            raise ValueError(f"{role}={col!r} is not a column in {cfg.dataset!r}. "
                             f"Available columns: {list(df.columns)}")
    n_raw = len(df)
    df = df.dropna(subset=[cfg.group_col, cfg.text_col]).copy()
    n_dropped_missing = n_raw - len(df)
    df["text"] = df[cfg.text_col].astype(str)          # exclude blank / whitespace-only text
    blank = df["text"].str.strip() == ""
    n_dropped_blank = int(blank.sum())
    df = df[~blank].copy()
    if cfg.id_col:                                       # stable unit id BEFORE any reset_index
        uid = df[cfg.id_col].astype(str)
        if uid.duplicated().any():
            raise ValueError(f"id_col {cfg.id_col!r} has duplicate values")
        df["uid"] = uid.values
    else:
        df["uid"] = df.index.astype(str)
    # canonical binary group on normalized string form (numeric-vs-string safe)
    g = df[cfg.group_col].astype(str).str.strip()
    fv, rv = str(cfg.focal_value).strip(), str(cfg.reference_value).strip()
    keep = g.isin([fv, rv])
    n_excluded_other = int((~keep).sum())               # third-group rows, reported not silently dropped
    if not keep.any():
        raise ValueError(f"no rows match focal/reference values "
                         f"{cfg.focal_value!r}/{cfg.reference_value!r} in {cfg.group_col!r} "
                         f"(values seen: {sorted(df[cfg.group_col].astype(str).unique())[:8]})")
    df = df[keep].copy()
    df["group"] = (g[keep] == fv).astype(int)
    df = df.reset_index(drop=True)
    excluded = {"rows_in_csv": n_raw, "dropped_missing": n_dropped_missing,
                "dropped_blank_text": n_dropped_blank, "excluded_other_group": n_excluded_other,
                "kept": len(df)}
    return df, excluded
