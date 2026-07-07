"""Single-edge queries: one call, one candidate influence (design doc §16.1).

Two modes, both spending the whole answer budget on ONE pair — exactly the
statistician yardstick's decomposition (one t-test per pair):

FORMATION (--mode formation, default). One checkpoint. Pair selection stacked
in the model's favor: the true edges are the MOST detectable (largest OLS |t|
on the shown window), the non-edges the most cleanly absent (smallest |t|),
so an idealized analyst scores ~perfectly. Separates two readings of the
whole-graph floor:
  - single-edge discrimination > 0, whole-graph ~ 0  -> the failure is task
    management (attention over 56 hypotheses), not statistical inference;
  - single-edge discrimination ~ 0 too               -> the model cannot
    extract a lagged pairwise association from a rendered series at all.

TRACKING (--mode tracking). THE structure question of the study (collapsed
design, 2026-07-06): ask about the edge(s) that change at t*, across every
checkpoint spanning the change, alongside CONTROL edges that never change.
Each call elicits TWO probabilities for one pair: that the influence is
PRESENT, and that it is POSITIVE if present. The read is a
difference-in-differences at the single-edge level: does the changed edge's
stated probability move across t* while the controls stay flat? With the
whole budget on one pair per call, "managing 56 hypotheses" is no longer an
excuse. All four change types have a predicted signature:
  edge_add:      P(present) low -> high.
  edge_remove:   P(present) high -> low.
  sign_flip:     P(present) stays high; P(positive) crosses 0.5.
  weight_double: truth never changes, but the evidence doubles -> P(present)
                 should climb. Subtlest case: every row records the rolling-20
                 |t| on the pair, so a scenario is admitted only when the
                 statistician's own confidence gap across t* clears a bar.
  ctrl_true:     present in BOTH regimes  -> flat.
  ctrl_false:    absent  in BOTH regimes  -> flat.

Usage:
    python -m knowable_worlds.run_single_edge --model gpt-oss
    python -m knowable_worlds.run_single_edge --mode tracking --model gpt-oss \
        --change-type edge_add --seed 300
    python -m knowable_worlds.run_single_edge --mode tracking \
        --model qwen/qwen3-235b-a22b-thinking-2507 --max-tokens 49152
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent
REPO = KCM.parent
sys.path.insert(0, str(KCM))
sys.path.insert(0, str(REPO))

from knowable_worlds.dyn_engine import DynSCM                              # noqa: E402
from knowable_worlds.dyn_battery import CHECKPOINTS                       # noqa: E402
from knowable_worlds.dyn_prompts import render_series                     # noqa: E402
from knowable_worlds.run_dynamic import ask_probability                   # noqa: E402
from forecast_bench.llm_client import LLMClient                       # noqa: E402
from forecast_bench.run_sensitivity import MODEL_MAP                  # noqa: E402

SYSTEM = """\
You are an expert data analyst. You will be shown a time series of a system of \
numeric variables, then asked about one specific potential influence between \
two variables. Respond with ONLY valid JSON: \
{"probability": <float between 0 and 1>}"""

SYSTEM_TRACK = """\
You are an expert data analyst. You will be shown a time series of a system of \
numeric variables, then asked about one specific potential influence between \
two variables. Respond with ONLY valid JSON: \
{"present": <float between 0 and 1>, "positive_if_present": <float between 0 and 1>}. \
Keep any deliberation brief, and always end your reply with the JSON object — \
never send an empty reply."""


def lag1_tstats(X: np.ndarray) -> np.ndarray:
    """t-statistics for every lag-1 coefficient, OLS per target column."""
    Y, Z = X[1:], X[:-1]
    D = np.column_stack([Z, np.ones(len(Z))])
    G = np.linalg.inv(D.T @ D)
    coef = G @ D.T @ Y                              # (n+1, n)
    resid = Y - D @ coef
    dof = len(Y) - D.shape[1]
    t = np.zeros((X.shape[1], X.shape[1]))
    for j in range(X.shape[1]):
        s2 = float(resid[:, j] @ resid[:, j]) / dof
        se = np.sqrt(s2 * np.diag(G))[:-1]
        t[:, j] = coef[:-1, j] / se
    return t                                        # t[i, j]: Xi -> Xj


def select_pairs(dyn: DynSCM, X: np.ndarray, ck: int,
                 n_true: int, n_false: int) -> list[dict]:
    """Most-detectable true edges + most-cleanly-absent non-edges.

    Truth and weights come from the regime ACTIVE at ck (the question asks
    about "the system's current behavior") — a post-change checkpoint used to
    be scored against the regime-1 graph (audit 2026-07-07)."""
    t = lag1_tstats(X[:ck])
    regime = 1 if ck <= dyn.t_change else 2
    B = dyn.B1 if regime == 1 else dyn.B2
    present = set(dyn.cross_edges(regime))
    off = [(i, j) for i in range(dyn.n) for j in range(dyn.n) if i != j]
    true_ranked = sorted((p for p in off if p in present),
                         key=lambda p: -abs(t[p[0], p[1]]))
    false_ranked = sorted((p for p in off if p not in present),
                          key=lambda p: abs(t[p[0], p[1]]))
    out = []
    for i, j in true_ranked[:n_true] + false_ranked[:n_false]:
        out.append({"pair": f"X{i+1}->X{j+1}", "truth": int((i, j) in present),
                    "weight": float(B[i, j]),
                    "t_stat": float(t[i, j])})
    return out


def select_tracking_pairs(dyn: DynSCM, n_ctrl_true: int = 2,
                          n_ctrl_false: int = 1) -> list[dict]:
    """The changed edge(s) + controls that never change (strength-matched).

    Handles single- and multi-edge scenarios and all four change types: every
    edge in dyn.changed_edges becomes a 'changed' probe; controls are edges
    whose status is identical in both regimes, strength-matched to the mean
    changed magnitude."""
    changed = [(ce["i"], ce["j"]) for ce in dyn.changed_edges]
    present1 = set(dyn.cross_edges(1))
    present2 = set(dyn.cross_edges(2))
    both = present1 & present2                       # true in every regime
    neither = {(i, j) for i in range(dyn.n) for j in range(dyn.n)
               if i != j} - present1 - present2      # absent in every regime
    for e in changed:
        both.discard(e)
        neither.discard(e)
    # controls matched to the mean changed magnitude so "strong => high p"
    # cannot masquerade as tracking
    mags = [max(abs(ce["w1"]), abs(ce["w2"])) for ce in dyn.changed_edges]
    target_w = float(np.mean(mags))
    ct = sorted(both, key=lambda e: abs(abs(dyn.B1[e]) - target_w))[:n_ctrl_true]
    cf = sorted(neither, key=lambda e: -(e[0] * dyn.n + e[1]))[:n_ctrl_false]
    out = []
    for e in changed:
        out.append({"pair": f"X{e[0]+1}->X{e[1]+1}", "role": "changed",
                    "weight1": float(dyn.B1[e]), "weight2": float(dyn.B2[e])})
    for e in ct:
        out.append({"pair": f"X{e[0]+1}->X{e[1]+1}", "role": "ctrl_true",
                    "weight1": float(dyn.B1[e]), "weight2": float(dyn.B2[e])})
    for e in cf:
        out.append({"pair": f"X{e[0]+1}->X{e[1]+1}", "role": "ctrl_false",
                    "weight1": 0.0, "weight2": 0.0})
    return out


def pair_idx(pair: str) -> tuple[int, int]:
    a, b = pair.split("->")
    return int(a[1:]) - 1, int(b[1:]) - 1


def edge_present_at(dyn: DynSCM, pair: str, ck: int) -> int:
    """Ground-truth existence of `pair` in the regime active at checkpoint ck."""
    i, j = pair_idx(pair)
    B = dyn.B1 if ck <= dyn.t_change else dyn.B2
    return int(B[i, j] != 0.0)


def edge_positive_at(dyn: DynSCM, pair: str, ck: int) -> int | None:
    """Ground-truth sign of `pair` at checkpoint ck (None if absent)."""
    i, j = pair_idx(pair)
    B = dyn.B1 if ck <= dyn.t_change else dyn.B2
    w = B[i, j]
    return None if w == 0.0 else int(w > 0)


def t_roll20(X: np.ndarray, pair: str, ck: int) -> float:
    """Rolling-20-row |t| on the pair at checkpoint ck — the statistician's
    confidence, recorded with every answer so detectability (especially for
    weight_double) is certifiable per scenario without extra API calls."""
    i, j = pair_idx(pair)
    t = lag1_tstats(X[max(0, ck - 20):ck])
    return float(abs(t[i, j]))


def ask_two(client, system: str, user: str, retries: int = 6):
    """Elicit {present, positive_if_present}; returns (p_present, p_positive).

    A missing positive_if_present is retried, and after exhausting retries the
    present-only answer is kept with p_positive=None — never silently filled
    with 0.5, which would fake a flat null exactly on the sign_flip scenarios
    that read that field (audit 2026-07-07). Out-of-range values (e.g. 75)
    are rejected and retried, not clamped."""
    from forecast_bench.llm_client import parse_json_response
    clamp = lambda v: min(0.999, max(0.001, v))
    fallback = None                       # best present-only answer seen
    for _ in range(retries):
        text, ok = client.call_single(system, user)
        client.rate_limit_wait()
        if not ok:
            continue
        data = parse_json_response(text)
        if not data or "present" not in data:
            continue
        try:
            p = float(data["present"])
        except (TypeError, ValueError):
            continue
        if not 0.0 <= p <= 1.0:
            continue
        if "positive_if_present" not in data:
            fallback = (clamp(p), None)
            continue
        try:
            q = float(data["positive_if_present"])
        except (TypeError, ValueError):
            continue
        if not 0.0 <= q <= 1.0:
            continue
        return clamp(p), clamp(q)
    return fallback if fallback is not None else (None, None)


def render_question(dyn: DynSCM, pair: str) -> str:
    a, b = pair.split("->")
    return (
        "Consider how this system evolves from one period to the next: a "
        "variable's value in a period may be influenced by variables' values "
        "in the PREVIOUS period (every variable also depends on its own "
        "previous value; that self-link is not in question here).\n\n"
        f"One specific potential influence: does {a} in one period directly "
        f"influence {b} in the next period, in the system's current "
        "behavior?\n\n"
        "What is the probability that this direct influence is present? "
        'Respond as JSON: {"probability": <float between 0 and 1>}')


def render_question_track(dyn: DynSCM, pair: str) -> str:
    a, b = pair.split("->")
    return (
        "Consider how this system evolves from one period to the next: a "
        "variable's value in a period may be influenced by variables' values "
        "in the PREVIOUS period (every variable also depends on its own "
        "previous value; that self-link is not in question here).\n\n"
        f"One specific potential influence: does {a} in one period directly "
        f"influence {b} in the next period, in the system's current "
        "behavior?\n\n"
        "Give two probabilities: that this direct influence is present, and — "
        "supposing it is present — that it is positive (a higher value of "
        f"{a} leads to a higher value of {b} in the next period).\n\n"
        'Respond as JSON: {"present": <float between 0 and 1>, '
        '"positive_if_present": <float between 0 and 1>}')


def run_formation(client, args, dyn, X, out_path):
    pairs = select_pairs(dyn, X, args.checkpoint, args.n_true, args.n_false)
    series = render_series(dyn, X, args.checkpoint)
    done = set()
    if args.resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("p") is not None:
                done.add(r["pair"])
        print(f"[resume] {len(done)} pairs already recorded")

    with out_path.open("a", encoding="utf-8") as fh:
        for q in pairs:
            if q["pair"] in done:
                continue
            p = ask_probability(client, SYSTEM, series + "\n\n"
                                + render_question(dyn, q["pair"]))
            row = {"model": args.model, "seed": args.seed, "mode": "formation",
                   "change_type": args.change_type,
                   "checkpoint": args.checkpoint, **q, "p": p}
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(f"  {q['pair']}  truth={q['truth']}  |t|={abs(q['t_stat']):5.1f}"
                  f"  ->  p={p}", flush=True)

    rows = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines()
            if json.loads(l).get("p") is not None]
    ps = {0: [], 1: []}
    for r in rows:
        ps[r["truth"]].append(r["p"])
    if ps[0] and ps[1]:
        print(f"\nmean p | true edges: {np.mean(ps[1]):.2f} (n={len(ps[1])})"
              f"   mean p | non-edges: {np.mean(ps[0]):.2f} (n={len(ps[0])})"
              f"   discrimination: {np.mean(ps[1]) - np.mean(ps[0]):+.2f}")


def run_tracking(client, args, dyn, X, out_path):
    pairs = select_tracking_pairs(dyn)
    done = set()
    if args.resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("p") is not None:
                done.add((r["pair"], r["checkpoint"]))
        print(f"[resume] {len(done)} (pair, checkpoint) cells recorded")

    with out_path.open("a", encoding="utf-8") as fh:
        for ck in CHECKPOINTS:
            series = render_series(dyn, X, ck)
            for q in pairs:
                if (q["pair"], ck) in done:
                    continue
                p, p_pos = ask_two(client, SYSTEM_TRACK, series + "\n\n"
                                   + render_question_track(dyn, q["pair"]))
                row = {"model": args.model, "seed": args.seed, "mode": "tracking",
                       "change_type": args.change_type,
                       "n_changes": args.n_changes, "checkpoint": ck,
                       "truth": edge_present_at(dyn, q["pair"], ck),
                       "truth_positive": edge_positive_at(dyn, q["pair"], ck),
                       "t_roll20": round(t_roll20(X, q["pair"], ck), 2),
                       **q, "p": p, "p_positive": p_pos}
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(f"  ck{ck:>2} {q['pair']:>9} [{q['role']:>10}]  ->  "
                      f"present={p}  positive={p_pos}", flush=True)

    # difference-in-differences summary, on the field each change type moves
    rows = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines()
            if json.loads(l).get("p") is not None]
    field = "p_positive" if dyn.change_type == "sign_flip" else "p"
    print("\n  role ({}: reading {})   pre-t*   post-t*   delta   (t*={})"
          .format(dyn.change_type, field, dyn.t_change))
    deltas = {}
    for role in ("changed", "ctrl_true", "ctrl_false"):
        pre = [r[field] for r in rows if r["role"] == role
               and r["checkpoint"] <= dyn.t_change and r.get(field) is not None]
        post = [r[field] for r in rows if r["role"] == role
                and r["checkpoint"] > dyn.t_change and r.get(field) is not None]
        if pre and post:
            d = np.mean(post) - np.mean(pre)
            deltas[role] = d
            print(f"  {role:<11}{np.mean(pre):>7.2f}{np.mean(post):>9.2f}"
                  f"{d:>+8.2f}")
    if "changed" in deltas:
        ctrl = [deltas[r] for r in ("ctrl_true", "ctrl_false") if r in deltas]
        if ctrl:
            did = deltas["changed"] - np.mean(ctrl)
            want = {"edge_add": "rise (+)", "edge_remove": "fall (-)",
                    "sign_flip": "P(positive) crosses 0.5",
                    "weight_double": "rise (+): same truth, doubled evidence",
                    }.get(dyn.change_type,
                          "stay flat (control world: nothing changes)")
            print(f"\n  difference-in-differences (changed - mean control): "
                  f"{did:+.2f}   [changed edge should {want}]")
    if dyn.change_type == "weight_double":
        # detectability certification: the statistician's own confidence gap
        pre_t = [r["t_roll20"] for r in rows if r["role"] == "changed"
                 and r["checkpoint"] <= dyn.t_change and "t_roll20" in r]
        # ck >= 70: the rolling window is majority post-change (62/66 mostly pre)
        post_t = [r["t_roll20"] for r in rows if r["role"] == "changed"
                  and r["checkpoint"] >= 70 and "t_roll20" in r]
        if pre_t and post_t:
            gap = np.mean(post_t) - np.mean(pre_t)
            print(f"  certification: rolling-20 |t| on changed edge "
                  f"{np.mean(pre_t):.1f} -> {np.mean(post_t):.1f} "
                  f"(gap {gap:+.1f}; admit scenario only if the gap is "
                  f"clearly positive, e.g. >= 1.5)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="formation",
                    choices=["formation", "tracking"])
    ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--seed", type=int, default=300)
    ap.add_argument("--change-type", default="edge_add")
    ap.add_argument("--n-changes", type=int, default=1,
                    help="tracking mode: edges that change at once (1/3/6)")
    ap.add_argument("--checkpoint", type=int, default=55,
                    help="formation mode only")
    ap.add_argument("--n-true", type=int, default=5)
    ap.add_argument("--n-false", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--timeout", type=int, default=480)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--out-dir", default="knowable_worlds/outputs/single_edge")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        sys.exit("[ERROR] OPENROUTER_API_KEY not set")
    client = LLMClient(api_key=api_key,
                       model=MODEL_MAP.get(args.model, args.model),
                       temperature=args.temperature,
                       max_tokens=args.max_tokens, timeout=args.timeout)

    dyn = DynSCM(n_nodes=8, edge_prob=0.2, seed=args.seed,
                 change_type=args.change_type, n_changes=args.n_changes)
    X = dyn.simulate()

    out_dir = KCM / args.out_dir if not Path(args.out_dir).is_absolute() \
        else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = args.model.replace("/", "_").replace(":", "_")
    if args.mode == "tracking":
        kx = "" if args.n_changes == 1 else f"x{args.n_changes}"
        out_path = out_dir / f"{tag}_track_{args.change_type}{kx}_{args.seed}.jsonl"
        run_tracking(client, args, dyn, X, out_path)
    else:
        out_path = out_dir / f"{tag}_{args.change_type}_{args.seed}_ck{args.checkpoint}.jsonl"
        run_formation(client, args, dyn, X, out_path)

    print(f"API stats: {json.dumps(client.stats.to_dict())}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
