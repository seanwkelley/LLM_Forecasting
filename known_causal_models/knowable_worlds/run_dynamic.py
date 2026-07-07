"""Runner for the dynamic (regime-shift) arm (KNOWABLE_WORLDS_DESIGN §15).

Scenario grid = change_types x seeds. For each scenario: simulate the series
once, then at each checkpoint ask (1) affected-node forecast, (2) control-node
forecast, (3) the current structure. Writes results.jsonl, one row per
elicitation, resume-safe (failed rows are retried on --resume).

v2 modes (design doc §15.3 controls + §16 addenda):
  --change-types none        control world: nothing ever changes (C-c)
  --temperature 0            deterministic decoding (C-b)
  --resample N               ask each structure item N times, identical
                             prompt (C-a: same-prompt reliability)
  --kinds structure          run a subset of item kinds
  --structure-format probs   per-edge probabilities instead of an edge list
                             (I2: structure as true calibration)
  --carry-belief true-prior  hand the model its current causal model (as
                             per-edge probabilities) at every checkpoint,
                             seeded with the TRUE regime-1 graph; its revised
                             probabilities become the next checkpoint's
                             belief (P2: maintenance/revision isolated)

Usage (original pilot):
    python -m knowable_worlds.run_dynamic --model gpt-oss \
        --seeds 300 301 302 --out-dir knowable_worlds/outputs/dynamic_gptoss
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

KCM = Path(__file__).parent.parent
REPO = KCM.parent
sys.path.insert(0, str(KCM))
sys.path.insert(0, str(REPO))

from knowable_worlds.dyn_engine import DynSCM, CHANGE_TYPES               # noqa: E402
from knowable_worlds.dyn_battery import generate_dyn_battery, CHECKPOINTS  # noqa: E402
from knowable_worlds.dyn_prompts import build_dyn_prompt, all_pairs       # noqa: E402
from forecast_bench.llm_client import LLMClient, parse_json_response  # noqa: E402
from forecast_bench.run_sensitivity import MODEL_MAP                  # noqa: E402

EDGE_RE = re.compile(r"^X(\d+)\s*->\s*X(\d+)\s*:?\s*([+-])?$")


def ask_probability(client: LLMClient, system: str, user: str,
                    retries: int = 6) -> float | None:
    for _ in range(retries):
        text, ok = client.call_single(system, user)
        client.rate_limit_wait()
        if not ok:
            continue
        data = parse_json_response(text)
        if data and "probability" in data:
            try:
                p = float(data["probability"])
            except (TypeError, ValueError):
                continue
            if not 0.0 <= p <= 1.0:            # percent-style garbage: retry
                continue
            return min(0.999, max(0.001, p))
    return None


def ask_edges(client: LLMClient, system: str, user: str, n_nodes: int,
              retries: int = 6) -> list[str] | None:
    for _ in range(retries):
        text, ok = client.call_single(system, user)
        client.rate_limit_wait()
        if not ok:
            continue
        data = parse_json_response(text)
        if not data or not isinstance(data.get("edges"), list):
            continue
        edges, valid = [], True
        for e in data["edges"]:
            m = EDGE_RE.match(str(e).strip())
            if not m or not (1 <= int(m.group(1)) <= n_nodes
                             and 1 <= int(m.group(2)) <= n_nodes):
                valid = False
                break
            if int(m.group(1)) != int(m.group(2)):     # drop stray self-links
                sign = m.group(3) or "+"               # unsigned -> assume +
                edges.append(f"X{m.group(1)}->X{m.group(2)}:{sign}")
        if valid:
            return sorted(set(edges))
    return None


def ask_edge_probs(client: LLMClient, system: str, user: str,
                   pairs: list[str], retries: int = 6) -> dict | None:
    """All 56 ordered-pair probabilities, validated for completeness."""
    want = set(pairs)
    for _ in range(retries):
        text, ok = client.call_single(system, user)
        client.rate_limit_wait()
        if not ok:
            continue
        data = parse_json_response(text)
        got = data.get("edge_probabilities") if isinstance(data, dict) else None
        if not isinstance(got, dict):
            continue
        clean = {}
        for k, v in got.items():
            k = str(k).replace(" ", "")
            if k in want:
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    continue
                if 0.0 <= v <= 1.0:            # out-of-range: leave missing
                    clean[k] = v
        if set(clean) == want:                 # every pair, exactly once
            return {k: clean[k] for k in pairs}
    return None


def true_prior_belief(dyn: DynSCM) -> dict:
    """The correct regime-1 graph as soft edge probabilities (P2 seed)."""
    present = {f"X{i+1}->X{j+1}" for i, j in dyn.cross_edges(1)}
    return {p: (0.9 if p in present else 0.05) for p in all_pairs(dyn)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--change-types", nargs="+", default=[
        "edge_add", "edge_remove", "sign_flip", "weight_double"],
        choices=list(CHANGE_TYPES))
    ap.add_argument("--seeds", nargs="+", type=int, default=[300, 301, 302])
    ap.add_argument("--n-changes", type=int, default=1,
                    help="edges that change simultaneously at t* "
                         "(change-magnitude axis; 1/3/6)")
    ap.add_argument("--n-nodes", type=int, default=8)
    ap.add_argument("--edge-prob", type=float, default=0.2)
    ap.add_argument("--info-level", default="none",
                    choices=["none", "possible", "occurred", "when", "what"])
    ap.add_argument("--kinds", nargs="+", default=["forecast", "structure"],
                    choices=["forecast", "structure"])
    ap.add_argument("--resample", type=int, default=1,
                    help="ask each STRUCTURE item this many times (C-a)")
    ap.add_argument("--structure-format", default="list",
                    choices=["list", "probs"])
    ap.add_argument("--carry-belief", default="none",
                    choices=["none", "true-prior", "self"],
                    help="hand the model its current causal model each "
                         "checkpoint (requires --structure-format probs)")
    ap.add_argument("--stakes", action="store_true",
                    help="I1: scoring-rule language on structure items")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=4000,
                    help="raise for reasoning models: thinking tokens count "
                         "against this cap on OpenRouter")
    ap.add_argument("--timeout", type=int, default=120,
                    help="per-call timeout in seconds")
    ap.add_argument("--out-dir", default="knowable_worlds/outputs/dynamic_pilot")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    if args.carry_belief != "none":
        assert args.structure_format == "probs", \
            "belief carryover uses per-edge probabilities"
        assert args.resample == 1 and set(args.kinds) == {"forecast",
                                                          "structure"}

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        sys.exit("[ERROR] OPENROUTER_API_KEY not set")
    client = LLMClient(api_key=api_key, model=MODEL_MAP.get(args.model, args.model),
                       temperature=args.temperature, max_tokens=args.max_tokens,
                       timeout=args.timeout)

    out_dir = KCM / args.out_dir if not Path(args.out_dir).is_absolute() \
        else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.jsonl"

    # resume keys carry the CONDITION fields, not just the cell: resuming a
    # different condition (info level, format, carried belief, stakes, model)
    # into the same directory must re-run every cell, not silently skip it
    # (audit 2026-07-07)
    def cond_key(scenario, item_id, rep, src):
        get = src.get if isinstance(src, dict) else \
            lambda k, d=None: getattr(src, k, d)
        return (scenario, item_id, rep, get("model"),
                get("info_level", "none"), get("structure_format", "list"),
                get("carry_belief", "none"), bool(get("stakes", False)))

    done, old_rows = set(), []
    if args.resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            old_rows.append(r)
            if (r.get("p") is None and r.get("edges") is None
                    and r.get("edge_probs") is None):
                continue                       # failed call -> retry
            done.add(cond_key(r["scenario"], r["item_id"], r.get("rep", 0), r))
        print(f"[resume] {len(done)} elicitations already recorded")

    fh = out_path.open("a", encoding="utf-8")
    made = 0
    for ct in args.change_types:
        for seed in args.seeds:
            dyn = DynSCM(n_nodes=args.n_nodes, edge_prob=args.edge_prob,
                         seed=seed, change_type=ct, n_changes=args.n_changes)
            X = dyn.simulate()
            scenario = f"{ct}_{seed}" if args.n_changes == 1 \
                else f"{ct}x{args.n_changes}_{seed}"
            pairs = all_pairs(dyn)

            belief = None                      # "self": starts empty — the
            if args.carry_belief == "true-prior":  # first structure answer
                belief = true_prior_belief(dyn)    # becomes the first belief
            # resume: replay this scenario's stored revisions (same condition
            # only) in checkpoint order so the carried belief is reconstructed
            if args.carry_belief != "none":
                revs = sorted((r for r in old_rows
                               if r["scenario"] == scenario
                               and r.get("edge_probs") is not None
                               and r.get("carry_belief") == args.carry_belief
                               and r.get("model") == args.model),
                              key=lambda r: r["checkpoint"])
                for r in revs:
                    belief = r["edge_probs"]

            for item in generate_dyn_battery(dyn, X):
                if item["kind"] not in args.kinds:
                    continue
                reps = args.resample if item["kind"] == "structure" else 1
                for rep in range(reps):
                    if cond_key(scenario, item["item_id"], rep, args) in done:
                        continue
                    system, user = build_dyn_prompt(
                        dyn, X, item, info=args.info_level,
                        structure_format=args.structure_format,
                        belief=belief, stakes=args.stakes)
                    row = {"scenario": scenario, "change_type": ct,
                           "seed": seed, "n_nodes": args.n_nodes,
                           "edge_prob": args.edge_prob,
                           "n_changes": args.n_changes, "model": args.model,
                           "info_level": args.info_level, "rep": rep,
                           "structure_format": args.structure_format,
                           "carry_belief": args.carry_belief,
                           "stakes": args.stakes,
                           "temperature": args.temperature, **item}
                    if item["kind"] == "structure":
                        if args.structure_format == "probs":
                            got = ask_edge_probs(client, system, user, pairs)
                            row["edge_probs"] = got
                            # in ANY carry mode the answer becomes the belief;
                            # in "self" mode the FIRST answer seeds it (the
                            # old `belief is not None` guard made fresh self
                            # runs a silent no-op — audit 2026-07-07)
                            if got is not None and args.carry_belief != "none":
                                belief = got   # revised belief carries on
                        else:
                            row["edges"] = ask_edges(client, system, user,
                                                     dyn.n)
                    else:
                        row["p"] = ask_probability(client, system, user)
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()
                    made += 1
                    if made % 10 == 0:
                        got = row.get("p", row.get("edges"))
                        if got is None and row.get("edge_probs") is not None:
                            ep = row["edge_probs"]
                            got = f"56 edge probs, mean {sum(ep.values())/len(ep):.2f}"
                        print(f"  [{made}] {scenario} {item['item_id']} "
                              f"rep{rep} -> {got}", flush=True)
    fh.close()
    print(f"\nAPI stats: {json.dumps(client.stats.to_dict())}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
