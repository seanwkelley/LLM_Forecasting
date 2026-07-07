"""Runner for the hidden-confounder dynamic world (§16.3).

For each scenario (seed): simulate once, then at each checkpoint ask the five
forecast queries (obs / see_A / do_A / see_C / do_C) plus the structure item.
Writes results.jsonl, resume-safe. The headline read is the see_A-vs-do_A
divergence: a model with the causal structure right answers the do differently
from the see; a confounded model answers them the same (and its do_A error is
the confound gap). Scoring is done in analyze_confounder.py.

Usage:
    python -m knowable_worlds.run_confounder --model gpt-oss \
        --seeds 300 301 302 --out-dir knowable_worlds/outputs/confounder_gptoss
    python -m knowable_worlds.run_confounder --model gpt-oss --kinds forecast \
        --seeds 300 --out-dir knowable_worlds/outputs/confounder_smoke
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

from knowable_worlds.dyn_confounder import ConfoundedDynSCM                # noqa: E402
from knowable_worlds.confounder_battery import generate_confounder_battery  # noqa: E402
from knowable_worlds.confounder_prompts import build_confounder_prompt     # noqa: E402
from forecast_bench.llm_client import LLMClient, parse_json_response   # noqa: E402
from forecast_bench.run_sensitivity import MODEL_MAP                   # noqa: E402

EDGE_RE = re.compile(r"^X(\d+)\s*->\s*X(\d+)\s*:?\s*([+-])?$")


def ask_probability(client, system, user, retries=6):
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


def ask_edges(client, system, user, n_nodes, retries=6):
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
            if int(m.group(1)) != int(m.group(2)):
                edges.append(f"X{m.group(1)}->X{m.group(2)}:{m.group(3) or '+'}")
        if valid:
            return sorted(set(edges))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--seeds", nargs="+", type=int, default=[300, 301, 302])
    ap.add_argument("--n-nodes", type=int, default=8)
    ap.add_argument("--kinds", nargs="+", default=["forecast", "structure"],
                    choices=["forecast", "structure"])
    ap.add_argument("--intervene-from", type=int, default=None,
                    help="period interventions on A begin (default 1; set to "
                         "60 for the policy-rule-change / Lucas framing)")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--out-dir", default="knowable_worlds/outputs/confounder_pilot")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

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

    # resume keys carry the condition (model, intervene_from), so resuming a
    # different condition into the same directory re-runs instead of skipping
    iv_from = 1 if args.intervene_from is None else args.intervene_from
    done = set()
    if args.resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("p") is not None or r.get("edges") is not None:
                done.add((r["scenario"], r["item_id"], r.get("model"),
                          r.get("intervene_from", 1)))
        print(f"[resume] {len(done)} elicitations already recorded")

    fh = out_path.open("a", encoding="utf-8")
    made = 0
    for seed in args.seeds:
        scm = ConfoundedDynSCM(n_nodes=args.n_nodes, seed=seed,
                               intervene_from=args.intervene_from)
        X = scm.simulate()
        scenario = f"conf_{seed}"
        for item in generate_confounder_battery(scm, X):
            if item["kind"] not in args.kinds:
                continue
            if (scenario, item["item_id"], args.model, iv_from) in done:
                continue
            system, user = build_confounder_prompt(scm, X, item)
            row = {"scenario": scenario, "seed": seed, "n_nodes": args.n_nodes,
                   "model": args.model, "intervene_from": scm.intervene_from,
                   "temperature": args.temperature, **item}
            if item["kind"] == "structure":
                row["edges"] = ask_edges(client, system, user, scm.n)
            else:
                row["p"] = ask_probability(client, system, user)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            made += 1
            got = row.get("p", row.get("edges"))
            print(f"  [{made}] {scenario} {item['item_id']} -> {got}",
                  flush=True)
    fh.close()
    print(f"\nAPI stats: {json.dumps(client.stats.to_dict())}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
