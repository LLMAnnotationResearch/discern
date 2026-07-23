"""All-null FDR simulation test (code-review P0-1 acceptance test).

Certifies that the CORRECTED selection path (no screen: measure every candidate, Stage 5
same-sign permutation + BH-FDR 5%) controls false discoveries under the global null, using the
ACTUAL measure_lib.stage5/bh_pass implementations. Also runs the OLD path (screen on 120
observations that overlap the confirmatory 300, |diff| >= 0.08, then Stage 5 + BH on survivors)
on identical data, to quantify the miscalibration that motivated the fix.

Global null: K binary features, prevalence ~ U(0.05, 0.5), independent of group labels.
Geometry mirrors the real runs: 300 units, 150/150 groups, SCREEN = first 60 of each group.
Under the global null every discovery is false, so FDR = P(any discovery).

Offline: no API calls. Run:  python3 tests/test_null_fdr.py
Writes tests/null_fdr_results.json + prints a pass/fail verdict (corrected path <= 5% + MC margin).
"""
import os, sys, json, numpy as np
from pathlib import Path
from multiprocessing import Pool

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from discern.core import stage5, bh_pass  # the code under test (canonical impl)

# env-overridable so a fast smoke test is possible (Pool workers re-import this module,
# so overrides must travel through the environment, not monkeypatching)
N = 300                                     # measurement units (mirrors real runs)
K = int(os.environ.get("NULLSIM_K", 40))    # null candidate features per replication
B = int(os.environ.get("NULLSIM_B", 2000))  # permutations (matches production)
Q = 0.05                                    # BH level (matches production)
REPS = int(os.environ.get("NULLSIM_REPS", 200))  # simulation replications per path
SCREEN_THRESH = 0.08
LABELS = np.array([1]*150 + [0]*150)          # fixed 150/150, group-1 rows first (as in MEAS)
SCREEN = list(range(0, 60)) + list(range(150, 210))  # exact old-path screen indices

def _one_rep(seed):
    """Simulate one replication of BOTH paths on the same null data. Returns dict of counts."""
    rng = np.random.default_rng(seed)
    msplit = rng.integers(1, 3, N)
    # global null: features independent of labels
    C_all = {}
    for k in range(K):
        p = rng.uniform(0.05, 0.5)
        C_all[f"f{k:02d}"] = (rng.random(N) < p).astype(int)

    # --- corrected path: no screen, Stage 5 + BH over ALL candidates ---
    r5 = stage5(LABELS.copy(), msplit, C_all, B=B, seed=int(seed) + 1)
    pv = {f: v[2] for f, v in r5.items()}
    v_fixed = len(bh_pass(pv, q=Q))

    # --- old path: screen on 120 obs INSIDE the confirmatory 300, then Stage 5 + BH on survivors ---
    gg = LABELS[SCREEN]
    surv = {}
    for f, y in C_all.items():
        ys = y[SCREEN]
        d = ys[gg == 1].mean() - ys[gg == 0].mean()
        if abs(d) >= SCREEN_THRESH:
            surv[f] = y
    if surv:
        r5o = stage5(LABELS.copy(), msplit, surv, B=B, seed=int(seed) + 1)
        pvo = {f: v[2] for f, v in r5o.items()}
        v_old = len(bh_pass(pvo, q=Q))
    else:
        v_old = 0
    return {"v_fixed": v_fixed, "v_old": v_old, "n_surv": len(surv)}

def main():
    with Pool() as pool:
        rows = pool.map(_one_rep, range(10_000, 10_000 + REPS))
    vf = np.array([r["v_fixed"] for r in rows]); vo = np.array([r["v_old"] for r in rows])
    ns = np.array([r["n_surv"] for r in rows])
    # under the global null every discovery is false: FDR == P(any discovery)
    res = {
        "config": {"N": N, "K": K, "B": B, "q": Q, "reps": REPS, "screen_thresh": SCREEN_THRESH},
        "corrected_no_screen": {
            "P_any_false_discovery": float((vf > 0).mean()),
            "mean_false_discoveries": float(vf.mean()),
            "max_false_discoveries": int(vf.max()),
        },
        "old_screened_path": {
            "P_any_false_discovery": float((vo > 0).mean()),
            "mean_false_discoveries": float(vo.mean()),
            "max_false_discoveries": int(vo.max()),
            "mean_screen_survivors": float(ns.mean()),
        },
    }
    # Monte Carlo 95% margin on a 5% proportion with REPS reps
    mc = 1.96 * np.sqrt(Q * (1 - Q) / REPS)
    res["verdict"] = {
        "threshold": Q + mc,
        "corrected_path_controls_FDR": bool((vf > 0).mean() <= Q + mc),
    }
    (HERE / "null_fdr_results.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"\nVERDICT: corrected path P(any FD)={(vf>0).mean():.3f} "
          f"{'<=' if res['verdict']['corrected_path_controls_FDR'] else '>'} {Q+mc:.3f} "
          f"-> {'PASS' if res['verdict']['corrected_path_controls_FDR'] else 'FAIL'}")
    print(f"old screened path P(any FD)={(vo>0).mean():.3f}, "
          f"mean screen survivors under null = {ns.mean():.1f}/{K}")
    if not res["verdict"]["corrected_path_controls_FDR"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
