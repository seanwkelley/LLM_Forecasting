"""Committed analysis for the Knowable Worlds study (audit item C6).

Loads a run's results.jsonl, dedupes (last successful row per (scm, item, rung)),
attaches the FOUR normative oracles, prints the study tables, and writes
master_long.csv for the R inference layer (analyze_calibration.R).

Oracles (every model error becomes attributable):
    p_table   counting oracle — exceedance frequency in the SAME 50-row table
              the model saw (observational items)
    p_cond    conditioning oracle — exact observational P(Y>tau | X=v)
              (the "trap"; equals truth for root interventions)
    p_ols     rational-statistician floor — OLS along the TRUE graph on the same
              50 rows, then exact propagation under do()
    p_wrong   wrong-model oracle — OLS along the REVERSED graph on the same rows,
              then do() computed faithfully under that wrong model (what a
              rational agent who BELIEVES the L1w graph would answer)

Usage:
    python -m knowable_worlds.analyze_calibration \
        --run-dir knowable_worlds/outputs/pilot_gptoss
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

from scm.engine import SCM                                     # noqa: E402
from knowable_worlds.battery import generate_battery               # noqa: E402
from knowable_worlds.analytic import cond_prob                     # noqa: E402
from knowable_worlds.prompts import RUNGS                          # noqa: E402

Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))         # noqa: E731

QUANTITY = ["Lnull", "L0", "L1", "L2", "L3"]
PURE = ["L1p", "L2p", "L3p"]
QUALITY = ["L1w", "L1r", "L1i", "L1b"]
KINDS = ["observational", "interventional", "counterfactual"]


def _fit_and_do(A: np.ndarray, X: np.ndarray, do: dict, k: int, tau: float) -> float | None:
    """OLS-fit a linear SCM with adjacency A on data X, then exact P(Xk>tau | do)."""
    n = A.shape[0]
    W = np.zeros((n, n)); c = np.zeros(n); s2 = np.zeros(n)
    for j in range(n):
        pa = [i for i in range(n) if A[i, j] == 1]
        if pa:
            D = np.column_stack([X[:, pa], np.ones(len(X))])
            coef, *_ = np.linalg.lstsq(D, X[:, j], rcond=None)
            for cf, i in zip(coef[:-1], pa):
                W[i, j] = cf
            c[j] = coef[-1]
            r = X[:, j] - D @ coef
            s2[j] = max(float(r.var(ddof=len(pa) + 1)), 1e-9)
        else:
            c[j] = X[:, j].mean(); s2[j] = max(float(X[:, j].var(ddof=1)), 1e-9)
    for j, v in do.items():
        W[:, j] = 0.0; c[j] = float(v); s2[j] = 0.0
    try:
        M = np.linalg.inv(np.eye(n) - W.T)
    except np.linalg.LinAlgError:
        return None
    mu = M @ c
    var = float((M @ np.diag(s2) @ M.T)[k, k])
    if var <= 1e-12:
        return 1.0 if mu[k] > tau else 0.0
    return 1.0 - Phi((tau - float(mu[k])) / math.sqrt(var))


def load(run_dir: Path, era1_cutoff: int = 180):
    raw = [json.loads(l) for l in
           (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    era1_keys = {(r["scm_seed"], r["item_id"], r["rung"])
                 for r in raw[:era1_cutoff] if r.get("p") is not None}
    dedup = {}
    for r in raw:
        if r.get("p") is not None and "sweep_sigma" not in r:
            dedup[(r["scm_seed"], r["item_id"], r["rung"])] = r
    rows = list(dedup.values())

    # attach oracles for exactly the SCM seeds present in the data — a
    # hardcoded seed range (100..104) silently attached no oracles to the
    # scale-up run (seeds 200+) and then crashed (audit 2026-07-07)
    seeds = sorted({r["scm_seed"] for r in rows})
    for seed in seeds:
        scm = SCM(n_nodes=8, edge_prob=0.35, seed=seed)
        bat = {it["item_id"]: it for it in generate_battery(scm, seed=seed)}
        X = scm.sample(50, seed=555 + seed)
        A_rev = scm.A.T.copy()
        for r in rows:
            if r["scm_seed"] != seed:
                continue
            it = bat.get(r["item_id"])
            if it is None:
                r["_orphan"] = True
                continue
            k = it["outcome_idx"]; tau = it["tau"]
            do = {int(i): v for i, v in (it.get("do_idx") or {}).items()}
            r["p_table"] = float((X[:, k] > tau).mean())
            if do:
                (j, v), = do.items()
                r["p_cond"] = cond_prob(scm, k, tau, j, v)
                r["p_ols"] = _fit_and_do(scm.A, X, do, k, tau)
                r["p_wrong"] = _fit_and_do(A_rev, X, do, k, tau)
            r["depth"] = it.get("depth"); r["aleatoric"] = it.get("aleatoric")
            r["era1"] = (r["scm_seed"], r["item_id"], r["rung"]) in era1_keys
    return [r for r in rows if not r.get("_orphan")]


def table(rows, rungs, kinds=KINDS, conf_only=None, title=""):
    print(f"\n--- {title} ---")
    print(f"{'rung':<7}{'kind':<16}{'n':>4}{'|p-p*|':>8}{'gap':>8}{'slope':>7}")
    for rung in rungs:
        for kind in kinds:
            r = [x for x in rows if x["rung"] == rung and x["kind"] == kind
                 and (conf_only is None or bool(x.get("confounded")) == conf_only)]
            if len(r) < 4:
                continue
            p = np.array([x["p"] for x in r]); ps = np.array([x["p_star"] for x in r])
            slope = np.polyfit(ps, p, 1)[0] if ps.std() > 0.05 else float("nan")
            print(f"{rung:<7}{kind:<16}{len(r):>4}{np.mean(np.abs(p-ps)):>8.3f}"
                  f"{np.mean((p-ps)**2):>8.4f}{slope:>7.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = KCM / args.run_dir if not Path(args.run_dir).is_absolute() \
        else Path(args.run_dir)
    rows = load(run_dir)
    print(f"deduped successful forecasts: {len(rows)} "
          f"(era-1 rows: {sum(1 for r in rows if r.get('era1'))})")

    # PRIMARY (design doc §16): the causal-required subset — items where the
    # best data-only answer is certifiably wrong (confounded do: ident_gap
    # >= 0.15; counterfactual: factual-reuse wrong by construction).
    # Observational and root-do items are ability CONTROLS (counting works;
    # for roots conditioning == intervening).
    print("\n=== PRIMARY: CAUSAL-REQUIRED ITEMS (data-only answers certifiably wrong) ===")
    causal_req = [r for r in rows if
                  (r["kind"] == "interventional" and r.get("confounded"))
                  or r["kind"] == "counterfactual"]
    table(causal_req, QUANTITY + PURE + QUALITY,
          kinds=["interventional", "counterfactual"],
          title="causal-required subset, by rung")

    print("\n=== CONTROLS: data-only-answerable items (counting / root-do) ===")
    table(rows, QUANTITY, title="QUANTITY LADDER (all kinds)")
    table(rows, PURE, title="PURE-THEORY RUNGS (no data)")
    table(rows, QUALITY, title="QUALITY RUNGS")

    # VOI ladder: marginal reduction in optimality gap per increment, by kind
    print("\n--- VOI LADDER (marginal gap reduction; negative = knowledge hurt) ---")
    for kind in KINDS:
        gaps = {}
        for rung in QUANTITY:
            r = [x for x in rows if x["rung"] == rung and x["kind"] == kind]
            if len(r) >= 4:
                gaps[rung] = np.mean([(x["p"] - x["p_star"])**2 for x in r])
        pairs = [(a, b) for a, b in zip(QUANTITY, QUANTITY[1:])
                 if a in gaps and b in gaps]
        s = "  ".join(f"{a}->{b}: {gaps[a]-gaps[b]:+.4f}" for a, b in pairs)
        print(f"{kind:<16} {s}")

    # trap triangulation on confounded interventional items
    print("\n--- CONFOUNDED ITEMS: distance to truth / trap / wrong-model ---")
    print(f"{'rung':<7}{'n':>3}{'d(truth)':>10}{'d(trap)':>9}{'d(wrong)':>10}{'closest':>10}")
    for rung in QUANTITY[1:] + QUALITY:
        r = [x for x in rows if x["rung"] == rung and x.get("confounded")
             and x["kind"] == "interventional" and x.get("p_cond") is not None]
        if len(r) < 4:
            continue
        p = np.array([x["p"] for x in r])
        dt = np.mean(np.abs(p - [x["p_star"] for x in r]))
        dc = np.mean(np.abs(p - [x["p_cond"] for x in r]))
        dw = (np.mean(np.abs(p - [x["p_wrong"] for x in r]))
              if all(x.get("p_wrong") is not None for x in r) else float("nan"))
        best = min(("truth", dt), ("trap", dc), ("wrong", dw), key=lambda t: t[1])[0]
        print(f"{rung:<7}{len(r):>3}{dt:>10.3f}{dc:>9.3f}{dw:>10.3f}{best:>10}")

    # oracle reference errors (what the ideal strategies score against truth)
    print("\n--- ORACLE ERRORS vs truth (context for every number above) ---")
    obs = [x for x in rows if x["kind"] == "observational" and x["rung"] == "L0"
           and x.get("p_table") is not None]
    if obs:
        print(f"counting oracle (obs):      "
              f"{np.mean([abs(x['p_table']-x['p_star']) for x in obs]):.3f}")
    do_ = [x for x in rows if x["kind"] == "interventional"
           and x.get("p_ols") is not None and x["rung"] == "L1"]
    if do_:
        print(f"OLS floor (do, true graph): "
              f"{np.mean([abs(x['p_ols']-x['p_star']) for x in do_]):.3f}")
        print(f"wrong-model oracle (do):    "
              f"{np.mean([abs(x['p_wrong']-x['p_star']) for x in do_]):.3f}")

    # master CSV for R
    out = run_dir / "master_long.csv"
    fields = ["scm_seed", "item_id", "rung", "kind", "confounded", "node_type",
              "p", "p_star", "p_table", "p_cond", "p_ols", "p_wrong",
              "tau", "depth", "aleatoric", "era1"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})
    print(f"\nwrote {out} ({len(rows)} rows) -> analyze_calibration.R")


if __name__ == "__main__":
    main()
