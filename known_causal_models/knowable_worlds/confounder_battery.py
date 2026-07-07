"""Battery for the hidden-confounder dynamic world (§16.3).

At each checkpoint the model has seen periods 1..ck (some of them labeled
interventions on A). It is asked to forecast B in the next period under five
readings of the same situation:

  obs     baseline: no information about A next period            (ability)
  see_A   "you OBSERVE A = a next period"   -> correct: USE a     (uses confound)
  do_A    "A is SET to a by intervention"   -> correct: IGNORE a  (causal core)
  see_C   "you OBSERVE C = c next period"   -> correct: USE c
  do_C    "C is SET to c by intervention"   -> correct: USE c     (necessity control)

The pair {see_A, do_A} on the SAME value a is the causal probe: their correct
answers diverge only if the model distinguishes seeing from doing. do_C blocks
the "ignore every intervention" shortcut (C is a real cause). Each item carries
the exactly-correct p_star and the confounded-forecaster p_spurious; the
confound gap |p_star(do_A) - p_spurious(do_A)| is certified >= a threshold by
choosing an extreme intervention value a.
"""

from __future__ import annotations

import numpy as np

from knowable_worlds.dyn_confounder import ConfoundedDynSCM

CHECKPOINTS = (30, 40, 55, 62, 66, 70, 80, 95)   # t_change = 60 (shared)
GAP_MIN = 0.15                                    # certified causal necessity


def _extreme_value(mu: float, sd: float, rng) -> float:
    """An intervention value far enough out to make the confound gap large."""
    sign = 1.0 if rng.random() < 0.5 else -1.0
    return float(mu + sign * rng.uniform(1.8, 2.6) * sd)


def generate_confounder_battery(scm: ConfoundedDynSCM, X: np.ndarray,
                                checkpoints=CHECKPOINTS) -> list[dict]:
    rng = np.random.default_rng(scm.seed * 37 + 3)
    items = []
    for ck in checkpoints:
        assert ck + 1 <= scm.T
        x_ck = X[ck - 1]
        mean_B, var_B, mu_A, mu_C, beta = scm._forecast_moments(x_ck)
        sd_B = float(np.sqrt(var_B))
        var_A = scm.lam_a ** 2 * scm.sigma_u ** 2 + scm.noise_scale ** 2
        sd_A = float(np.sqrt(var_A))
        sd_C = scm.noise_scale
        regime = 1 if ck + 1 <= scm.t_change else 2
        phase = "pre" if regime == 1 else "post"

        # a shared threshold near the baseline mean so p is informative
        tau = round(float(mean_B + rng.choice([-0.4, 0.0, 0.4]) * sd_B), 4)
        # one extreme A value used by BOTH see_A and do_A (the causal pair)
        a_val = _extreme_value(mu_A, sd_A, rng)
        c_val = _extreme_value(mu_C, sd_C, rng)

        specs = [
            ("obs", None), ("see_A", a_val), ("do_A", a_val),
            ("see_C", c_val), ("do_C", c_val),
        ]
        for query, value in specs:
            v = 0.0 if value is None else float(value)
            p_star = scm.p_star(x_ck, query, tau, v)
            p_spur = scm.p_spurious(x_ck, query, tau, v)
            item = {
                "item_id": f"ck{ck}_{query}",
                "kind": "forecast", "query": query,
                "checkpoint": ck, "phase": phase,
                "outcome": scm.var_names[scm.B], "outcome_idx": scm.B,
                "intervened": query.startswith("do_"),
                "intervened_var": (scm.var_names[scm.A] if query in ("see_A", "do_A")
                                   else scm.var_names[scm.C] if query in ("see_C", "do_C")
                                   else None),
                "intervened_value": None if value is None else round(v, 4),
                "tau": tau,
                "p_star": round(float(p_star), 6),
                "p_spurious": round(float(p_spur), 6),
            }
            if query == "do_A":
                gap = abs(p_star - p_spur)
                if gap < GAP_MIN:
                    raise ValueError(
                        f"seed {scm.seed}, ck{ck}: confound gap {gap:.3f} < "
                        f"GAP_MIN={GAP_MIN} — this world/checkpoint does not "
                        "certify causal necessity; pick another seed")
                item["confound_gap"] = round(float(gap), 6)
            items.append(item)

        # structure item: does the model assert the SPURIOUS A->B edge?
        items.append({
            "item_id": f"ck{ck}_structure", "kind": "structure",
            "checkpoint": ck, "phase": phase,
        })
    return items


if __name__ == "__main__":
    import json
    for seed in (300, 301, 302):
        scm = ConfoundedDynSCM(seed=seed)
        X = scm.simulate()
        bat = generate_confounder_battery(scm, X)
        json.dumps(bat)                              # serializability guard
        gaps = [i["confound_gap"] for i in bat if i.get("query") == "do_A"]
        n_interv = int(np.sum(~np.isnan(scm.interv_val)))
        # sanity: do_A p_star must equal obs p_star (a is causally irrelevant)
        by = {}
        for i in bat:
            if i["kind"] == "forecast":
                by.setdefault(i["checkpoint"], {})[i["query"]] = i["p_star"]
        ok = all(abs(d["do_A"] - d["obs"]) < 1e-9 for d in by.values())
        print(f"seed{seed}: {len(bat)} items | {n_interv} intervention rows | "
              f"do_A==obs: {ok} | confound gaps: "
              + " ".join(f"{g:.2f}" for g in gaps))
        # see_A vs do_A divergence (the causal signal)
        div = [abs(by[ck]["see_A"] - by[ck]["do_A"]) for ck in by]
        print(f"          mean |see_A - do_A| divergence = {np.mean(div):.2f}")
