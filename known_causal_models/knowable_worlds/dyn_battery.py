"""Item battery for the dynamic (regime-shift) arm (KNOWABLE_WORLDS_DESIGN §15).

One SCENARIO = one DynSCM (seed x change_type) + one simulated series. At each
CHECKPOINT t the model sees periods 1..t and answers three items:

    forecast, affected node   P(X_j at t+1 > tau) where j = changed edge's child.
        Post-change: tau = midpoint of the stale (regime-1) and true (regime-2)
        conditional means — maximally separates "still using the old model"
        from "updated" (same trick as the counterfactual midpoint-tau design).
        Pre-change: stratified tau for graded truth.
    forecast, control node    a node != j. One-step-ahead, given the fully
        observed current state, ONLY the changed edge's child differs across
        regimes — so controls certify that any post-change error jump is the
        change, not general confusion.
    structure                 elicit the cross-lag edge list (scored against
        both regimes' graphs at analysis time -> detection latency).

Every forecast item carries the exact truth p_star (current regime) AND the
exact stale answer p_stale (regime-1 mechanism applied to the same state) —
the perseveration oracle. regime_gap = |mu2 - mu1|/sigma tags detectability;
the perseveration analysis filters regime_gap >= 0.5.
"""

from __future__ import annotations

import numpy as np

from knowable_worlds.dyn_engine import DynSCM

# three PRE-change checkpoints = a pure regime-1 learning curve (30/40/55 rows
# of single-regime data): establishes whether structure beliefs CONVERGED
# before the change — perseveration is only interpretable for a formed belief
CHECKPOINTS = (30, 40, 55, 62, 66, 70, 80, 95)   # t_change = 60
Z_STRATA = (-1.28, -0.52, 0.0, 0.52, 1.28)   # p* in {.90,.70,.50,.30,.10}


def generate_dyn_battery(dyn: DynSCM, X: np.ndarray,
                         checkpoints=CHECKPOINTS) -> list[dict]:
    rng = np.random.default_rng(dyn.seed * 31 + 5)
    # affected = every child whose incoming edge changed (one node when a
    # single edge changes; the union across the changed set for multi-edge)
    affected_nodes = sorted({ce["j"] for ce in dyn.changed_edges})
    controls = [k for k in range(dyn.n) if k not in affected_nodes]
    items = []
    for ci, ck in enumerate(checkpoints):
        assert ck + 1 <= dyn.T
        x_prev = X[ck - 1]                       # last row the model sees
        regime = 1 if ck + 1 <= dyn.t_change else 2
        phase = "pre" if regime == 1 else "post"
        mu1 = dyn.cond_mean(x_prev, 1)
        mu2 = dyn.cond_mean(x_prev, 2)

        def forecast(k: int, tau: float, affected: bool) -> dict:
            mu_true = mu1 if regime == 1 else mu2
            p_star = dyn.prob_exceed(x_prev, k, tau, regime)
            p_stale = dyn.prob_exceed(x_prev, k, tau, 1)
            gap = abs(float(mu2[k] - mu1[k])) / dyn.noise_scale
            return {
                "item_id": f"ck{ck}_{'aff' if affected else 'ctl'}_X{k+1}",
                "kind": "forecast", "checkpoint": ck, "phase": phase,
                "outcome": dyn.var_names[k], "outcome_idx": k,
                "tau": round(float(tau), 4),
                "p_star": round(float(p_star), 6),
                "p_stale": round(float(p_stale), 6),
                "affected": affected,
                "regime_gap": round(gap, 4),
                "mu_true": round(float(mu_true[k]), 4),
            }

        # affected node(s): midpoint tau post-change, stratified pre-change
        # (and stratified whenever the regimes agree there, e.g. the
        # no-change control world — a midpoint of equal means is degenerate).
        # one item per changed child, so multi-edge scenarios price every
        # affected relationship.
        for j in affected_nodes:
            if phase == "post" and abs(float(mu2[j] - mu1[j])) > 1e-9:
                tau_aff = float((mu1[j] + mu2[j]) / 2.0)
            else:
                tau_aff = float(mu1[j] + rng.choice(Z_STRATA) * dyn.noise_scale)
            items.append(forecast(j, tau_aff, affected=True))

        # control node: cycle through non-affected nodes, stratified tau
        if controls:
            k = controls[ci % len(controls)]
            mu_now = mu1 if regime == 1 else mu2
            tau_ctl = float(mu_now[k] + rng.choice(Z_STRATA) * dyn.noise_scale)
            items.append(forecast(k, tau_ctl, affected=False))

        items.append({
            "item_id": f"ck{ck}_structure",
            "kind": "structure", "checkpoint": ck, "phase": phase,
        })
    return items


if __name__ == "__main__":
    import json
    from knowable_worlds.dyn_engine import CHANGE_TYPES
    for ct in CHANGE_TYPES:
        d = DynSCM(seed=300, change_type=ct)
        X = d.simulate()
        bat = generate_dyn_battery(d, X)
        f = [i for i in bat if i["kind"] == "forecast"]
        post_aff = [i for i in f if i["affected"] and i["phase"] == "post"]
        print(f"{ct:>14}: {len(bat)} items | post-affected p*: "
              + " ".join(f"{i['p_star']:.2f}" for i in post_aff)
              + " | gaps: " + " ".join(f"{i['regime_gap']:.2f}" for i in post_aff))
        json.dumps(bat)  # serializability guard (np.bool_ lesson)
