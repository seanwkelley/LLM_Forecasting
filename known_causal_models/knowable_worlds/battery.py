"""Event battery generator (KNOWABLE_WORLDS_DESIGN §5).

Produces threshold events P(X_k > τ) — observational and interventional —
with τ chosen ANALYTICALLY so that true p* hits pre-specified strata exactly.
Full calibration-curve coverage is guaranteed by construction, which no
real-world benchmark can do.

Each item carries: outcome var, τ, the do() spec (if any), exact p*,
propagation depth (min #hops from any intervened node to the outcome),
and the aleatoric level p*(1−p*).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from scm.engine import SCM                                     # noqa: E402
from knowable_worlds.analytic import (                             # noqa: E402
    gaussian_moments, event_prob, tau_for_target, cond_prob,
    counterfactual_value,
)

P_STRATA = (0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.95)


def _descendants(scm: SCM, src: int) -> set[int]:
    out, frontier = set(), {src}
    while frontier:
        nxt = set()
        for i in frontier:
            for j in range(scm.n):
                if scm.A[i, j] == 1 and j not in out:
                    out.add(j)
                    nxt.add(j)
        frontier = nxt
    return out


def _depth(scm: SCM, src: int, dst: int) -> int:
    """Min #edges from src to dst (BFS); -1 if unreachable."""
    from collections import deque
    q, seen = deque([(src, 0)]), {src}
    while q:
        v, d = q.popleft()
        if v == dst:
            return d
        for j in range(scm.n):
            if scm.A[v, j] == 1 and j not in seen:
                seen.add(j)
                q.append((j, d + 1))
    return -1


def generate_battery(scm: SCM, strata=P_STRATA, seed: int = 0,
                     interventional: bool = True) -> list[dict]:
    """One battery for one SCM: |strata| observational + |strata| interventional
    items (when a usable intervention exists), τ inverted analytically per item.
    """
    rng = np.random.default_rng(seed)
    mu, Sigma = gaussian_moments(scm)
    items = []

    # outcome pool: prefer nodes with at least one parent (non-roots respond to
    # the system); fall back to all nodes.
    non_roots = [j for j in range(scm.n) if scm.A[:, j].sum() > 0]
    outcome_pool = non_roots or list(range(scm.n))

    # --- observational items: cycle outcomes across strata ---
    for si, p_star in enumerate(strata):
        k = outcome_pool[si % len(outcome_pool)]
        tau = tau_for_target(scm, k, p_star)
        items.append({
            "item_id": f"obs_{si}",
            "kind": "observational",
            "do": {},
            "outcome": scm.var_names[k],
            "outcome_idx": k,
            "tau": round(float(tau), 4),
            "p_star": p_star,
            "depth": 0,
            "aleatoric": round(p_star * (1 - p_star), 4),
        })

    # --- interventional items ---
    if interventional:
        # pick the intervention node with the most descendants (max usable outcomes)
        cand = sorted(range(scm.n), key=lambda i: len(_descendants(scm, i)),
                      reverse=True)
        src = cand[0]
        desc = sorted(_descendants(scm, src))
        if desc:
            sd_src = float(np.sqrt(Sigma[src, src])) or 1.0
            v = float(mu[src] + rng.choice([-2.0, 2.0]) * sd_src)
            do = {src: v}
            for si, p_star in enumerate(strata):
                k = desc[si % len(desc)]
                try:
                    tau = tau_for_target(scm, k, p_star, do=do)
                except ValueError:
                    continue
                p_check = event_prob(scm, k, tau, do=do)
                items.append({
                    "item_id": f"do_{si}",
                    "kind": "interventional",
                    "do": {scm.var_names[src]: round(v, 4)},
                    "do_idx": {src: v},
                    "outcome": scm.var_names[k],
                    "outcome_idx": k,
                    "tau": round(float(tau), 4),
                    "p_star": round(float(p_check), 6),
                    "depth": _depth(scm, src, k),
                    "aleatoric": round(p_star * (1 - p_star), 4),
                })
    # --- confounded interventional items (dc_*): causal knowledge NECESSARY ---
    # Non-root intervention with a certified identification gap: the observational
    # (conditioning) answer differs from the do() answer by >= min_gap, so a
    # correlational strategy is provably wrong. At L3 these also test do-SEMANTICS
    # (the model must sever the intervened node's own equation, not condition).
    if interventional:
        min_gap = 0.15
        nonroots = [j for j in range(scm.n)
                    if scm.A[:, j].sum() > 0 and len(_descendants(scm, j)) > 0]
        cand = []
        for j in nonroots:
            sd_j = float(np.sqrt(Sigma[j, j])) or 1.0
            for direction in (+2.0, -2.0):
                v = float(mu[j] + direction * sd_j)
                for k in sorted(_descendants(scm, j)):
                    for p_target in strata:
                        try:
                            tau = tau_for_target(scm, k, p_target, do={j: v})
                        except ValueError:
                            continue
                        p_do = event_prob(scm, k, tau, do={j: v})
                        p_c = cond_prob(scm, k, tau, j, v)
                        gap = abs(p_c - p_do)
                        if gap >= min_gap:
                            cand.append((gap, p_target, j, k, v, tau, p_do, p_c))
        # fill strata greedily with the largest-gap candidate per stratum
        used = set()
        ci = 0
        for p_target in strata:
            pool = [c for c in cand if c[1] == p_target
                    and (c[2], c[3]) not in used]
            if not pool:
                continue
            gap, _, j, k, v, tau, p_do, p_c = max(pool)
            used.add((j, k))
            items.append({
                "item_id": f"dc_{ci}",
                "kind": "interventional",
                "confounded": True,
                "node_type": "nonroot",
                "do": {scm.var_names[j]: round(v, 4)},
                "do_idx": {j: v},
                "outcome": scm.var_names[k],
                "outcome_idx": k,
                "tau": round(float(tau), 4),
                "p_star": round(float(p_do), 6),
                "p_obs_analog": round(float(p_c), 6),
                "ident_gap": round(float(gap), 4),
                "depth": _depth(scm, j, k),
                "aleatoric": round(p_do * (1 - p_do), 4),
            })
            ci += 1
    # --- counterfactual items (cf_*): Pearl rung 3 ---
    # One factual realization is shown; the query is what WOULD have happened had
    # a node been set differently ON THAT OCCASION (same background noise). With
    # full factual evidence the answer is DETERMINISTIC (p* in {0,1}) — computed
    # by abduct->act->predict. tau is placed at the midpoint of the factual and
    # counterfactual outcome values, so neither "reuse the factual" nor "ignore
    # the intervention" scores; only actual noise-replay does.
    if interventional:
        x_fact = scm.sample(1, seed=777 + scm.seed)[0]
        cf_srcs = []
        root_cands = [j for j in range(scm.n)
                      if scm.A[:, j].sum() == 0 and len(_descendants(scm, j)) > 0]
        nonroot_cands = [j for j in range(scm.n)
                         if scm.A[:, j].sum() > 0 and len(_descendants(scm, j)) > 0]
        cf_srcs = root_cands[:2] + nonroot_cands[:2]
        ci = 0
        for j in cf_srcs:
            sd_j = float(np.sqrt(Sigma[j, j])) or 1.0
            v = float(x_fact[j] - np.sign(x_fact[j] - mu[j] + 1e-9) * 2.5 * sd_j)
            xc = counterfactual_value(scm, x_fact, {j: v})
            for k in sorted(_descendants(scm, j)):
                y_f, y_c = float(x_fact[k]), float(xc[k])
                if abs(y_c - y_f) < 0.3:      # too-small shifts are uninformative
                    continue
                tau = round((y_f + y_c) / 2, 4)
                items.append({
                    "item_id": f"cf_{ci}",
                    "kind": "counterfactual",
                    "confounded": bool(scm.A[:, j].sum() > 0),
                    "node_type": "root" if scm.A[:, j].sum() == 0 else "nonroot",
                    "do": {scm.var_names[j]: round(v, 4)},
                    "do_idx": {j: v},
                    "outcome": scm.var_names[k],
                    "outcome_idx": k,
                    "tau": tau,
                    "p_star": 1.0 if y_c > tau else 0.0,
                    "cf_factual_outcome": round(y_f, 4),
                    "cf_outcome": round(y_c, 4),
                    "factual": {scm.var_names[m]: round(float(x_fact[m]), 3)
                                for m in range(scm.n)},
                    "depth": _depth(scm, j, k),
                    "aleatoric": 0.0,
                })
                ci += 1
                break                          # one outcome per source node
    # tag the root-do items with their (zero-gap) analog for uniform analysis
    for it in items:
        if it["kind"] == "interventional" and "p_obs_analog" not in it:
            (i, v), = it["do_idx"].items()
            it["confounded"] = False
            it["node_type"] = "root" if scm.A[:, int(i)].sum() == 0 else "nonroot"
            it["p_obs_analog"] = round(float(cond_prob(scm, it["outcome_idx"],
                                                       it["tau"], int(i), v)), 6)
            it["ident_gap"] = round(abs(it["p_obs_analog"] - it["p_star"]), 4)
    return items


if __name__ == "__main__":
    scm = SCM(n_nodes=8, edge_prob=0.35, seed=7)
    b = generate_battery(scm, seed=7)
    print(f"{len(b)} items")
    for it in b:
        print(f"  {it['item_id']:<7} {it['kind']:<15} {it['outcome']:<4} "
              f"tau={it['tau']:<9} p*={it['p_star']:<8} depth={it['depth']} "
              f"do={it['do']}")
