"""Prompts for the hidden-confounder dynamic world (§16.3).

Neutral, like the rest of the arm: the confounder is never named, and the word
"causal" is avoided. The series marks intervention periods (A externally set)
so a model CAN learn the tell — that A and B move together in normal periods
but not in intervention periods — from the data alone. The see/do wording is
the only place the seeing/doing distinction is made, and it is made plainly.
"""

from __future__ import annotations

import numpy as np

from knowable_worlds.dyn_confounder import ConfoundedDynSCM

SYSTEM_FORECAST = """\
You are an expert probability estimator. You will be shown a time series of a \
system of numeric variables, then asked for the probability of one event. \
Respond with ONLY valid JSON: {"probability": <float strictly between 0 and 1>}"""

SYSTEM_STRUCT = """\
You are an expert data analyst. You will be shown a time series of a system of \
numeric variables, then asked how the variables influence each other. \
Respond with ONLY valid JSON in the requested format."""


def render_series(scm: ConfoundedDynSCM, X: np.ndarray, ck: int) -> str:
    """Series up to period ck, with intervention periods flagged. In flagged
    periods, X1 was externally set (its usual drivers overridden) — a '*' marks
    the value."""
    names = scm.var_names
    header = "period   " + "   ".join(f"{v:>7}" for v in names) + "   note"
    lines = []
    for t in range(1, ck + 1):
        cells = []
        for k in range(scm.n):
            val = f"{X[t - 1, k]:7.2f}"
            if k == scm.A and not np.isnan(scm.interv_val[t - 1]):
                val = val + "*"
            else:
                val = val + " "
            cells.append(val)
        note = (f"{names[scm.A]} externally set"
                if not np.isnan(scm.interv_val[t - 1]) else "")
        lines.append(f"{t:>6}   " + "  ".join(cells) + f"   {note}")
    a = names[scm.A]
    intro = (
        f"Below is a recording of a system of {scm.n} numeric variables, "
        f"observed once per period for {ck} consecutive periods. In some "
        f"periods (marked '*' and noted at right) the value of {a} was set by "
        f"an outside intervention rather than arising from the system's own "
        f"dynamics; in all other periods every variable arose from the system.")
    return f"{intro}\n\n{header}\n" + "\n".join(lines)


def render_forecast_event(scm: ConfoundedDynSCM, item: dict) -> str:
    ck = item["checkpoint"]
    b = scm.var_names[scm.B]
    tau = item["tau"]
    nxt = ck + 1
    q = item["query"]
    ask = (f"\n\nWhat is the probability that {b} in period {nxt} (the next "
           f"period) will exceed {tau}?"
           '\n\nRespond as JSON: {"probability": <float>}')
    if q == "obs":
        return (f"Consider period {nxt}, the next period." + ask)
    var = item["intervened_var"]
    val = item["intervened_value"]
    if q in ("see_A", "see_C"):
        return (f"Consider period {nxt}, the next period. Suppose you will "
                f"OBSERVE that {var} in period {nxt} turns out to be {val} "
                f"(it arises from the system as usual, and you simply get to "
                f"see it in advance)." + ask)
    # do_A / do_C
    return (f"Consider period {nxt}, the next period. Suppose that in period "
            f"{nxt}, {var} is SET to {val} by an outside intervention: its "
            f"usual drivers in the system are overridden and it takes the "
            f"value {val} regardless of what the system would have produced."
            + ask)


def render_structure_event(scm: ConfoundedDynSCM) -> str:
    return (
        "Consider how this system evolves. A variable's value may be "
        "influenced by other variables. List the direct influences you "
        "believe are present.\n\n"
        'Respond as JSON: {"edges": ["XA->XB:+", "XC->XD:-", ...]} where '
        '"XA->XB:+" means a higher XA directly leads to a higher XB, and ":-" '
        "means a higher value leads to a lower one. Use only the variable "
        "names " + ", ".join(scm.var_names) + ".")


def build_confounder_prompt(scm: ConfoundedDynSCM, X: np.ndarray,
                            item: dict) -> tuple[str, str]:
    series = render_series(scm, X, item["checkpoint"])
    if item["kind"] == "structure":
        return SYSTEM_STRUCT, series + "\n\n" + render_structure_event(scm)
    return SYSTEM_FORECAST, series + "\n\n" + render_forecast_event(scm, item)


if __name__ == "__main__":
    from knowable_worlds.confounder_battery import generate_confounder_battery
    scm = ConfoundedDynSCM(seed=301)
    X = scm.simulate()
    bat = generate_confounder_battery(scm, X)
    for it in bat[:6]:
        sysp, user = build_confounder_prompt(scm, X, it)
        print("=" * 72)
        print(f"[{it['item_id']}]  ~{len(user)} chars")
        tail = user.splitlines()
        print("\n".join(tail[-4:]))
