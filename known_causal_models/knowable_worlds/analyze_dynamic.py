"""Committed analysis for the dynamic (regime-shift) arm.

Loads results.jsonl, dedupes (last successful row per scenario x item),
regenerates each scenario to attach exact quantities and the three rational
baselines, prints the study tables, writes dyn_master.csv (forecast rows) and
dyn_structure.csv (structure rows) for analyze_dynamic.R.

Baselines (every forecast row gets all three; sigma estimated from residuals,
as a real agent would have to):
    p_never    OLS lag-1 fit on periods 1..30 (first checkpoint), never refit
               -> the pure perseverer
    p_window   OLS on the last 20 periods before the checkpoint
               -> forgets fast, adapts fast (the recency strategy)
    p_full     OLS on all periods so far
               -> the change-blind statistician (contaminated after t*)
    p_stale    exact regime-1 mechanism (from the battery) -> perseveration
               oracle; p_star = exact current-regime truth

Structure scoring: F1 of the reported cross-lag edge list against BOTH
regimes' true edge sets -> tracking = F1(regime 2) - F1(regime 1) over time.

Usage:
    python -m knowable_worlds.analyze_dynamic \
        --run-dir knowable_worlds/outputs/dynamic_gptoss
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

from knowable_worlds.dyn_engine import (DynSCM, fit_var_ols,       # noqa: E402
                                    ols_prob_exceed)
from knowable_worlds.dyn_battery import CHECKPOINTS                # noqa: E402

GAP_MIN = 0.5      # regime_gap filter for the perseveration analysis


def _resid_sigma(X: np.ndarray, B: np.ndarray, c: np.ndarray, k: int) -> float:
    r = X[1:, k] - (c[k] + X[:-1] @ B[:, k])
    return max(float(r.std(ddof=X.shape[1] + 1)), 1e-6)


def _stat_edges(X: np.ndarray, ck: int, window: int = 20) -> set[str]:
    """The statistical yardstick's STATED structure: OLS on the rolling
    window, assert edge i->j when |t| = |b/SE(b)| > 2 (sign from b).
    Computed from the series alone — the LLM never sees a t-statistic."""
    W = X[max(0, ck - window):ck]
    n = W.shape[1]
    D = np.column_stack([W[:-1], np.ones(len(W) - 1)])
    XtX_inv = np.linalg.inv(D.T @ D + 1e-9 * np.eye(n + 1))
    out = set()
    for j in range(n):
        coef = XtX_inv @ D.T @ W[1:, j]
        r = W[1:, j] - D @ coef
        sd = max(float(np.sqrt((r @ r) / max(len(r) - n - 1, 1))), 1e-6)
        se = sd * np.sqrt(np.maximum(np.diag(XtX_inv), 1e-12))
        for i in range(n):
            if i != j and abs(coef[i] / se[i]) > 2:
                out.add(f"X{i+1}->X{j+1}:{'+' if coef[i] > 0 else '-'}")
    return out


def load(run_dir: Path):
    raw = [json.loads(l) for l in
           (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    dedup = {}
    for r in raw:
        if r.get("p") is not None or r.get("edges") is not None:
            # rep in the key: without it, a --resample run collapses to the
            # last repetition per item (audit 2026-07-07)
            dedup[(r["scenario"], r["item_id"], r.get("rep", 0))] = r
    rows = list(dedup.values())

    scen = {}
    for r in rows:
        key = r["scenario"]
        if key not in scen:
            d = DynSCM(n_nodes=r.get("n_nodes", 8),
                       edge_prob=r.get("edge_prob", 0.2),
                       seed=r["seed"], change_type=r["change_type"],
                       n_changes=r.get("n_changes", 1))
            scen[key] = (d, d.simulate())
        d, X = scen[key]
        r["rel_time"] = r["checkpoint"] - d.t_change
        if r["kind"] == "forecast":
            ck, k, tau = r["checkpoint"], r["outcome_idx"], r["tau"]
            x_prev = X[ck - 1]
            fits = {"p_never": X[:CHECKPOINTS[0]],
                    "p_window": X[max(0, ck - 20):ck],
                    "p_full": X[:ck]}
            for name, W_ in fits.items():
                B, c = fit_var_ols(W_)
                sig = _resid_sigma(W_, B, c, k)
                r[name] = round(ols_prob_exceed(B, c, x_prev, k, tau, sig), 6)
        else:
            got = set(r["edges"] or [])
            got_u = {e.split(":")[0] for e in got}
            # changed-slot state: whole-graph F1 is dominated by the ~17
            # shared edges (old/new separation is bounded at ~1 edge in 18),
            # so track the changed slot directly: old / new / neither
            ce = d.changed_edge
            slot = f"X{ce['i']+1}->X{ce['j']+1}"
            state = lambda es: ("+" if slot + ":+" in es else
                                "-" if slot + ":-" in es else None)
            s1, s2 = state(d.signed_edges(1)), state(d.signed_edges(2))
            sg = state(got)
            r["changed_state"] = ("old" if sg == s1 else
                                  "new" if sg == s2 else "neither")
            # over-assertion, explicitly: correct vs false edges relative to
            # the CURRENT regime's graph (false-alarm churn around t* is
            # itself a detection signature — mixed-regime windows fit blends)
            truth_now = d.signed_edges(2 if r["phase"] == "post" else 1)
            r["n_correct_now"] = len(got & truth_now)
            r["n_false_now"] = len(got) - r["n_correct_now"]
            # statistical yardstick for the structure channel (same series,
            # rolling OLS, |t|>2): F1 + changed-slot state, for comparison
            se_est = _stat_edges(X, r["checkpoint"])
            for tag, regime in (("r1", 1), ("r2", 2)):
                truth = d.signed_edges(regime)
                tp = len(se_est & truth)
                prec = tp / len(se_est) if se_est else 0.0
                rec = tp / len(truth) if truth else 0.0
                r[f"stat_f1_{tag}"] = round(2 * prec * rec / (prec + rec), 4) \
                    if prec + rec > 0 else 0.0
            sg_s = state(se_est)
            r["stat_changed_state"] = ("old" if sg_s == s1 else
                                       "new" if sg_s == s2 else "neither")
            for tag, regime in (("r1", 1), ("r2", 2)):
                truth = d.signed_edges(regime)          # signed (primary)
                truth_u = {e.split(":")[0] for e in truth}
                for suff, g, t in (("", got, truth), ("u", got_u, truth_u)):
                    tp = len(g & t)
                    prec = tp / len(g) if g else 0.0
                    rec = tp / len(t) if t else 0.0
                    r[f"f1{suff}_{tag}"] = round(
                        2 * prec * rec / (prec + rec), 4) if prec + rec > 0 \
                        else 0.0
            r["n_edges_reported"] = len(got)
    return rows, scen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = KCM / args.run_dir if not Path(args.run_dir).is_absolute() \
        else Path(args.run_dir)
    rows, scen = load(run_dir)
    fc = [r for r in rows if r["kind"] == "forecast"]
    st = [r for r in rows if r["kind"] == "structure"]
    n_scen = len({r['scenario'] for r in rows})
    print(f"forecast rows: {len(fc)} | structure rows: {len(st)} "
          f"| scenarios: {n_scen} (scenario = replication unit)")

    # 1. recovery curve: error vs time-from-change, model + baselines
    print("\n--- RECOVERY CURVE: mean |p - p*| by checkpoint (affected node) ---")
    print(f"{'t-t*':>5}{'n':>4}{'model':>8}{'stale':>8}{'never':>8}"
          f"{'window':>8}{'full':>8}")
    for ck in CHECKPOINTS:
        r = [x for x in fc if x["checkpoint"] == ck and x["affected"]]
        if not r:
            continue
        cols = [np.mean([abs(x["p"] - x["p_star"]) for x in r])]
        for o in ("p_stale", "p_never", "p_window", "p_full"):
            cols.append(np.mean([abs(x[o] - x["p_star"]) for x in r]))
        print(f"{ck - 60:>+5}{len(r):>4}" + "".join(f"{c:>8.3f}" for c in cols))

    print("\n--- CONTROL NODES (should stay flat across the change) ---")
    for phase in ("pre", "post"):
        r = [x for x in fc if not x["affected"] and x["phase"] == phase]
        if r:
            print(f"  {phase:<5} n={len(r):>3}  model |p-p*| = "
                  f"{np.mean([abs(x['p'] - x['p_star']) for x in r]):.3f}")

    # 2. perseveration triangulation (post, affected, detectable)
    print(f"\n--- PERSEVERATION: post-change affected items, gap >= {GAP_MIN} ---")
    r = [x for x in fc if x["affected"] and x["phase"] == "post"
         and x["regime_gap"] >= GAP_MIN]
    if r:
        p = np.array([x["p"] for x in r])
        dt = np.abs(p - [x["p_star"] for x in r])
        ds = np.abs(p - [x["p_stale"] for x in r])
        closer = "STALE model" if ds.mean() < dt.mean() else "truth"
        print(f"  n={len(r)}  d(truth)={dt.mean():.3f}  d(stale)={ds.mean():.3f}"
              f"  -> closer to {closer}")
        for ck in CHECKPOINTS:
            rr = [x for x in r if x["checkpoint"] == ck]
            if rr:
                pp = np.array([x["p"] for x in rr])
                print(f"    t-t*={ck-60:+3d}: d(truth)="
                      f"{np.mean(np.abs(pp-[x['p_star'] for x in rr])):.3f} "
                      f"d(stale)={np.mean(np.abs(pp-[x['p_stale'] for x in rr])):.3f}"
                      f" (n={len(rr)})")

    # 3. structure tracking (signed F1 primary; unsigned dissociates
    #    edge-detection from sign errors; weight_double is invisible here
    #    by design — forecast channel only)
    print("\n--- STRUCTURE TRACKING: signed F1 vs old (r1) / new (r2) graph ---")
    print(f"{'t-t*':>5}{'n':>4}{'F1 old':>8}{'F1 new':>8}"
          f"{'F1u old':>9}{'F1u new':>9}{'edges':>7}{'ok':>6}{'false':>7}")
    for ck in CHECKPOINTS:
        r = [x for x in st if x["checkpoint"] == ck and x.get("f1_r1") is not None]
        if not r:
            continue
        print(f"{ck - 60:>+5}{len(r):>4}"
              f"{np.mean([x['f1_r1'] for x in r]):>8.3f}"
              f"{np.mean([x['f1_r2'] for x in r]):>8.3f}"
              f"{np.mean([x['f1u_r1'] for x in r]):>9.3f}"
              f"{np.mean([x['f1u_r2'] for x in r]):>9.3f}"
              f"{np.mean([x['n_edges_reported'] for x in r]):>7.1f}"
              f"{np.mean([x['n_correct_now'] for x in r]):>6.1f}"
              f"{np.mean([x['n_false_now'] for x in r]):>7.1f}")

    # 3b. the changed slot itself (the sharp detection metric), model vs the
    #     |t|>2 rolling-OLS statistician on the same series
    print("\n--- CHANGED-EDGE SLOT: stated as in the OLD or NEW graph? ---")
    print(f"{'':>9}{'--- model ---':>21}{'--- statistician ---':>27}")
    print(f"{'t-t*':>5}{'n':>4}{'old':>7}{'new':>7}{'neither':>8}"
          f"{'old':>9}{'new':>7}{'neither':>8}")
    for ck in CHECKPOINTS:
        r = [x for x in st if x["checkpoint"] == ck and "changed_state" in x]
        if not r:
            continue
        frac = lambda s, f: sum(1 for x in r if x[f] == s) / len(r)
        print(f"{ck - 60:>+5}{len(r):>4}"
              f"{frac('old', 'changed_state'):>7.2f}"
              f"{frac('new', 'changed_state'):>7.2f}"
              f"{frac('neither', 'changed_state'):>8.2f}"
              f"{frac('old', 'stat_changed_state'):>9.2f}"
              f"{frac('new', 'stat_changed_state'):>7.2f}"
              f"{frac('neither', 'stat_changed_state'):>8.2f}")

    # CSVs for R
    f_fields = ["scenario", "change_type", "seed", "checkpoint", "rel_time",
                "phase", "affected", "outcome", "regime_gap", "tau",
                "p", "p_star", "p_stale", "p_never", "p_window", "p_full"]
    with (run_dir / "dyn_master.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=f_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(fc)
    s_fields = ["scenario", "change_type", "seed", "checkpoint", "rel_time",
                "phase", "f1_r1", "f1_r2", "f1u_r1", "f1u_r2",
                "changed_state", "n_edges_reported",
                "n_correct_now", "n_false_now",
                "stat_f1_r1", "stat_f1_r2", "stat_changed_state"]
    with (run_dir / "dyn_structure.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=s_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(st)
    print(f"\nwrote dyn_master.csv ({len(fc)}) and dyn_structure.csv ({len(st)}) "
          f"-> analyze_dynamic.R")


if __name__ == "__main__":
    main()
