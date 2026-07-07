"""Elicitation prompts for the information ladder (KNOWABLE_WORLDS_DESIGN §6).

Rungs (what the model sees about the mechanism):
    L0  observational samples only
    L1  L0 + DAG structure
    L2  L1 + edge signs
    L3  full structural equations + noise scales (p* computable in principle)

Deliberately NEUTRAL: no calibration coaching, no anti-anchoring language —
the study measures the model's DEFAULT probabilistic behavior (the ensemble
pilot's v2 lesson: coaching shifts anchors without adding discrimination, and
would contaminate the measurement).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from scm.engine import SCM  # noqa: E402

# Factorial rungs: mechanism level x observational-data presence.
#   data present : L0 (samples only), L1 (+structure), L2 (+signs), L3 (+equations)
#   data absent  : Lnull (nothing but the event), L1p, L2p, L3p ("pure theory")
# Lnull measures the pure prior (anchoring floor); L3p vs L3 isolates whether
# data aids, distracts, or is inert once the mechanism is fully known.
# Quality rungs (data always present; the STRUCTURE is manipulated):
#   L1w — WRONG structure: every edge reversed (still a DAG; certified false)
#   L1r — PARTIAL, query-RELEVANT: only edges on paths from the do-node (or
#         ancestors, for obs items) to the outcome
#   L1i — PARTIAL, query-IRRELEVANT: an equal COUNT of edges not on such paths
#   L1b — PARTIAL, relevant + BACK-DOOR: the forward subgraph PLUS the
#         confounding pathway (edges into the do-node and from its ancestors
#         to the outcome). Tests whether SEEING the back-door explicitly
#         triggers severing where the full graph did not (attentional vs
#         conceptual failure).
# Masked-outcome rungs (the outcome's COLUMN is hidden from the table):
#   Lm  — masked data + the OUTCOME's equation only: forced composition — the
#         answer requires combining parent data with the given mechanism
#         (counting is impossible; truth still exact)
#   Lms — masked data + structure only: unanswerable-in-principle control
#         (no outcome observations AND no outcome mechanism)
RUNGS = ("Lnull", "L0", "L1", "L2", "L3", "L1p", "L2p", "L3p",
         "L1w", "L1r", "L1i", "L1b", "Lm", "Lms")
_LEVEL = {"Lnull": 0, "L0": 0, "L1": 1, "L1p": 1, "L2": 2, "L2p": 2,
          "L3": 3, "L3p": 3, "L1w": 1, "L1r": 1, "L1i": 1, "L1b": 1,
          "Lm": -1, "Lms": 1}
_HAS_DATA = {"L0": True, "L1": True, "L2": True, "L3": True,
             "Lnull": False, "L1p": False, "L2p": False, "L3p": False,
             "L1w": True, "L1r": True, "L1i": True, "L1b": True,
             "Lm": True, "Lms": True}
_MASK_OUTCOME = {"Lm", "Lms"}


def _reach(edges, n, srcs):
    """nodes reachable from srcs via directed edges (incl. srcs)."""
    out = set(srcs)
    changed = True
    while changed:
        changed = False
        for a, b in edges:
            if a in out and b not in out:
                out.add(b)
                changed = True
    return out


def select_edges(scm: SCM, rung: str, item: dict | None):
    """Edge list (as (i,j) index pairs) to SHOW for structure rungs."""
    all_edges = [(i, j) for i in range(scm.n) for j in range(scm.n)
                 if scm.A[i, j] == 1]
    if rung == "L1w":
        return [(j, i) for i, j in all_edges]            # reverse all: still a DAG
    if rung in ("L1r", "L1i", "L1b") and item is not None:
        k = item["outcome_idx"]
        if item.get("do_idx"):
            srcs = [int(i) for i in item["do_idx"]]
        else:  # observational: ancestors of the outcome
            rev = [(b, a) for a, b in all_edges]
            srcs = list(_reach(rev, scm.n, {k}))
        fwd_reach = _reach(all_edges, scm.n, set(srcs))
        relevant = []
        for a, b in all_edges:
            into_k = _reach(all_edges, scm.n, {b})
            if (a in fwd_reach) and (k in into_k or b == k):
                relevant.append((a, b))
        if rung == "L1r":
            return relevant
        if rung == "L1b":
            # forward subgraph PLUS the confounding pathway: edges among the
            # do-node's ancestors (incl. into the do-node itself), and edges on
            # paths from those ancestors to the outcome.
            rev = [(b, a) for a, b in all_edges]
            anc = _reach(rev, scm.n, set(srcs)) - set(srcs)
            bd = set(relevant)
            anc_reach = _reach(all_edges, scm.n, anc) if anc else set()
            for a, b in all_edges:
                if a in anc and (b in anc or b in srcs):
                    bd.add((a, b))                       # ancestral edges into do-node
                elif a in anc_reach and b not in srcs:
                    into_k = _reach(all_edges, scm.n, {b})
                    if k in into_k or b == k:
                        bd.add((a, b))                   # ancestor -> outcome route
            return [e for e in all_edges if e in bd]     # stable order
        others = [e for e in all_edges if e not in relevant]
        # seeded random draw (NOT index-order truncation, which would bias
        # toward low-index nodes); seed ties selection to the SCM+item so it
        # is reproducible and stable across resume runs
        rng = np.random.default_rng(scm.seed * 1000 + item["outcome_idx"])
        n_pick = min(len(relevant) if relevant else 2, len(others))
        idx = rng.choice(len(others), size=n_pick, replace=False)
        picked = [others[i] for i in sorted(idx)]
        if len(picked) < len(relevant):
            # cannot match count in this graph — flag via shortfall marker
            pass
        return picked
    return all_edges

SYSTEM = """\
You are an expert probability estimator. You will be shown information about a \
system of numeric variables, then asked for the probability of one event. \
Respond with ONLY valid JSON: {"probability": <float strictly between 0 and 1>}"""


def render_samples(scm: SCM, n: int = 50, seed: int = 555,
                   exclude_idx: int | None = None) -> str:
    X = scm.sample(n, seed=seed)
    cols = [k for k in range(scm.n) if k != exclude_idx]
    header = "   ".join(f"{scm.var_names[k]:>6}" for k in cols)
    rows = "\n".join("   ".join(f"{row[k]:6.2f}" for k in cols) for row in X)
    note = ("" if exclude_idx is None else
            f" ({scm.var_names[exclude_idx]} was NOT recorded in this data)")
    return (f"Observational data: {n} independent joint draws of the system"
            f"{note}\n{header}\n{rows}")


def render_outcome_equation(scm: SCM, k: int) -> str:
    terms = [f"{scm.intercept[k]:.3f}"]
    for i in range(scm.n):
        if scm.A[i, k] == 1:
            g = f"tanh({scm.var_names[i]})" if scm.functional == "tanh" \
                else scm.var_names[i]
            terms.append(f"({scm.W[i, k]:+.3f})*{g}")
    return (f"The mechanism that generates {scm.var_names[k]} is known exactly:\n"
            f"{scm.var_names[k]} = " + " + ".join(terms)
            + f" + Normal(0, {scm.noise_scale:.2f})\n"
            "(The mechanisms generating the other variables are not provided.)")


def render_structure(scm: SCM, edge_idx: list | None = None,
                     partial: bool = False) -> str:
    if edge_idx is None:
        edge_idx = [(i, j) for i in range(scm.n) for j in range(scm.n)
                    if scm.A[i, j] == 1]
    edges = ", ".join(f"{scm.var_names[a]}->{scm.var_names[b]}"
                      for a, b in edge_idx)
    head = ("Known causal relationships (this may be only part of the full "
            "structure; A->B means A directly influences B)"
            if partial else
            "Causal structure (directed acyclic graph; A->B means A directly "
            "influences B)")
    return f"{head}:\n{edges}"


def render_signs(scm: SCM) -> str:
    lines = []
    for i in range(scm.n):
        for j in range(scm.n):
            if scm.A[i, j] == 1:
                s = "increases" if scm.W[i, j] > 0 else "decreases"
                lines.append(f"{scm.var_names[i]} {s} {scm.var_names[j]}")
    return "Direction of each influence:\n" + "\n".join(lines)


def render_equations(scm: SCM) -> str:
    lines = []
    for j in range(scm.n):
        terms = [f"{scm.intercept[j]:.3f}"]
        for i in range(scm.n):
            if scm.A[i, j] == 1:
                g = f"tanh({scm.var_names[i]})" if scm.functional == "tanh" else scm.var_names[i]
                terms.append(f"({scm.W[i, j]:+.3f})*{g}")
        lines.append(f"{scm.var_names[j]} = " + " + ".join(terms)
                     + f" + Normal(0, {scm.noise_scale:.2f})")
    return ("The system's exact generating equations (noise terms are independent "
            "Gaussians; a fresh draw of every noise term produces one joint "
            "realization):\n" + "\n".join(lines))


def render_context(scm: SCM, rung: str, samples_seed: int = 555,
                   item: dict | None = None) -> str:
    level, has_data = _LEVEL[rung], _HAS_DATA[rung]
    if rung in _MASK_OUTCOME and item is not None:
        k = item["outcome_idx"]
        parts = [render_samples(scm, seed=samples_seed, exclude_idx=k)]
        if rung == "Lm":
            parts.append(render_outcome_equation(scm, k))
        else:                                  # Lms: structure only
            parts.append(render_structure(scm))
        return "\n\n".join(parts)
    parts = []
    if has_data:
        parts.append(render_samples(scm, seed=samples_seed))
    else:
        parts.append("The system consists of the numeric variables "
                     + ", ".join(scm.var_names)
                     + ". No observational data is available.")
    if level in (1, 2):
        edge_idx = select_edges(scm, rung, item)
        parts.append(render_structure(scm, edge_idx,
                                      partial=rung in ("L1r", "L1i", "L1b")))
    if level == 2:
        parts.append(render_signs(scm))
    if level == 3:
        parts.append(render_equations(scm))
    return "\n\n".join(parts)


def render_event(item: dict) -> str:
    if item["kind"] == "counterfactual":
        (var, val), = item["do"].items()
        fact = ", ".join(f"{k} = {v}" for k, v in item["factual"].items())
        return (f"The system was observed running once, and produced exactly:\n"
                f"{fact}\n\n"
                f"Counterfactual question: if, ON THAT SAME OCCASION, {var} had "
                f"instead been SET to {val} by external control (all background "
                f"random influences exactly as they were; {var}'s usual causes "
                f"severed), what is the probability that {item['outcome']} would "
                f"have exceeded {item['tau']}?")
    if item["kind"] == "interventional":
        (var, val), = item["do"].items()
        return (f"Now consider an intervention: {var} is SET to {val} by external "
                f"control (its usual causes are severed; all other variables "
                f"respond as usual).\n\nIn one new realization of the system under "
                f"this intervention, what is the probability that "
                f"{item['outcome']} > {item['tau']}?")
    return (f"In one new independent realization of the system, what is the "
            f"probability that {item['outcome']} > {item['tau']}?")


def build_prompt(scm: SCM, item: dict, rung: str, samples_seed: int = 555) -> tuple[str, str]:
    user = (render_context(scm, rung, samples_seed, item=item) + "\n\n" + render_event(item)
            + '\n\nRespond as JSON: {"probability": <float>}')
    return SYSTEM, user
