"""Prompts for the dynamic (regime-shift) arm (KNOWABLE_WORLDS_DESIGN §15).

Deliberately NEUTRAL, matching the static ladder's convention: no calibration
coaching, and — in the default condition — NO mention that the dynamics may
have changed. Detecting the change unprompted is the headline measurement;
`hint=True` adds one sentence flagging possible change (the informed arm).

The model sees only the raw series (L0-equivalent). Structure rungs for the
dynamic arm are a registered future knob, not built here.
"""

from __future__ import annotations

import numpy as np

from knowable_worlds.dyn_engine import DynSCM

SYSTEM_FORECAST = """\
You are an expert probability estimator. You will be shown a time series of a \
system of numeric variables, then asked for the probability of one event. \
Respond with ONLY valid JSON: {"probability": <float strictly between 0 and 1>}"""

SYSTEM_STRUCT = """\
You are an expert data analyst. You will be shown a time series of a system of \
numeric variables, then asked about how the variables influence each other. \
Respond with ONLY valid JSON in the requested format."""

# Dynamic information ladder (design doc §15): what the agent is told about
# the change. Each rung removes ONE inferential burden; adjacent-rung deltas
# price single skills (hypothesis generation / detection / temporal
# localization / structural localization) in forecast currency.
INFO_LEVELS = ("none", "possible", "occurred", "when", "what")


def info_text(dyn: DynSCM, level: str) -> str:
    if level == "none":
        return ""
    if level == "possible":
        return ("Note: the way this system works may have changed at some "
                "unknown point during the recording.")
    if level == "occurred":
        return ("Note: the way this system works changed at some unknown "
                "point during the recording.")
    when = (f"Note: the way this system works changed after period "
            f"{dyn.t_change}: periods 1-{dyn.t_change} were generated under "
            f"the old configuration, periods {dyn.t_change + 1} onward under "
            f"the new one.")
    if level == "when":
        return when
    if level == "what":
        # enumerate ALL changed edges — with n_changes > 1 the old single-edge
        # sentence was factually false about the world (audit 2026-07-07)
        parts = [f"how {dyn.var_names[ce['j']]} is influenced by "
                 f"{dyn.var_names[ce['i']]}" for ce in dyn.changed_edges]
        return (when + " The change affected " + "; and ".join(parts) +
                "; everything else is unchanged.")
    raise ValueError(f"unknown info level: {level}")


def render_series(dyn: DynSCM, X: np.ndarray, ck: int,
                  info: str = "none") -> str:
    header = "period   " + "   ".join(f"{v:>6}" for v in dyn.var_names)
    rows = "\n".join(
        f"{t + 1:>6}   " + "   ".join(f"{X[t, k]:6.2f}" for k in range(dyn.n))
        for t in range(ck))
    intro = (f"Below is a recording of a system of {dyn.n} numeric variables, "
             f"observed once per period for {ck} consecutive periods.")
    extra = info_text(dyn, info)
    if extra:
        intro += " " + extra
    return f"{intro}\n\n{header}\n{rows}"


def render_forecast_event(item: dict) -> str:
    ck = item["checkpoint"]
    return (f"What is the probability that {item['outcome']} in period {ck + 1} "
            f"(the next period) will exceed {item['tau']}?")


def render_structure_event(dyn: DynSCM) -> str:
    return (
        "Consider how this system evolves from one period to the next: a "
        "variable's value in a period may be influenced by variables' values "
        "in the PREVIOUS period.\n\n"
        "Based on the most recent behavior of the system, list the "
        "cross-variable influences you believe are CURRENTLY present. Every "
        "variable may also depend on its own previous value; do not list "
        "those self-links.\n\n"
        'Respond as JSON: {"edges": ["XA->XB:+", "XC->XD:-", ...]} where '
        '"XA->XB:+" means a HIGHER XA in one period leads to a higher XB in '
        'the next period, and ":-" means a higher value leads to a LOWER one. '
        "Use only the variable names "
        + ", ".join(dyn.var_names) + ".")


def all_pairs(dyn: DynSCM) -> list[str]:
    return [f"X{i+1}->X{j+1}" for i in range(dyn.n) for j in range(dyn.n)
            if i != j]


def render_edge_prob_event(dyn: DynSCM) -> str:
    pairs = all_pairs(dyn)
    return (
        "Consider how this system evolves from one period to the next: a "
        "variable's value in a period may be influenced by variables' values "
        "in the PREVIOUS period (every variable may also depend on its own "
        "previous value; ignore those self-links)." + "\n\n"
        + "For EVERY ordered pair listed below, state the probability (between "
        "0 and 1) that the first variable directly influences the second, in "
        "the system's CURRENT behavior. Include every pair exactly once." + "\n\n"
        + 'Respond as JSON: {"edge_probabilities": {"X1->X2": <p>, ...}}' + "\n\n"
        + "Pairs: " + ", ".join(pairs))


def render_belief(belief: dict) -> str:
    body = ", ".join(f"{k}: {belief[k]:.2f}" for k in sorted(belief))
    return ("Your current causal model of this system, as probabilities that "
            "each direct influence exists (carried over from your previous "
            "analysis; revise it only as the data warrants):" + "\n" + body)


STAKES_LIST = (
    "Your answer will be scored: +1 for each influence you list that is truly "
    "present with the right direction, -1 for each you list that is not, 0 for "
    "influences you omit. An empty list is allowed and scores 0. List an "
    "influence only if you believe it is more likely present than not.")

STAKES_PROBS = (
    "Your probabilities will be scored by squared error against the true "
    "structure: for each pair you lose (p - truth)^2, where truth is 1 if the "
    "influence is present and 0 if not. State the probabilities that minimize "
    "your expected loss.")


def build_dyn_prompt(dyn: DynSCM, X: np.ndarray, item: dict,
                     info: str = "none", structure_format: str = "list",
                     belief: dict | None = None,
                     stakes: bool = False) -> tuple[str, str]:
    series = render_series(dyn, X, item["checkpoint"], info=info)
    if belief is not None:
        series = series + "\n\n" + render_belief(belief)
    if item["kind"] == "structure":
        event = (render_edge_prob_event(dyn) if structure_format == "probs"
                 else render_structure_event(dyn))
        if stakes:
            event = event + "\n\n" + (STAKES_PROBS if structure_format
                                       == "probs" else STAKES_LIST)
        return SYSTEM_STRUCT, (series + "\n\n" + event)
    return SYSTEM_FORECAST, (series + "\n\n" + render_forecast_event(item)
                             + '\n\nRespond as JSON: {"probability": <float>}')


if __name__ == "__main__":
    from knowable_worlds.dyn_battery import generate_dyn_battery
    d = DynSCM(seed=300, change_type="sign_flip")
    X = d.simulate()
    bat = generate_dyn_battery(d, X)
    for it in (bat[0], bat[2], bat[-3]):
        sys_p, user = build_dyn_prompt(d, X, it)
        print("=" * 70)
        print(f"[{it['item_id']}]  ~{len(user)} chars")
        lines = user.splitlines()
        print("\n".join(lines[:5] + ["   ..."] + lines[-6:]))
