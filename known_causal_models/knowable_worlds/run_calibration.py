"""True-calibration runner (KNOWABLE_WORLDS_DESIGN §§5-7): direct mode.

For each SCM seed: generate the p*-stratified battery, then for each item x rung
ask the model for a probability. Writes results.jsonl (one row per forecast)
and prints the headline metrics per rung:

    true calibration error   mean |p - p*|
    discrimination slope     OLS slope of p on p*   (1 = perfect)
    optimality gap           mean (p - p*)^2        (excess Brier, exact)

Usage (sanity pilot, ~180 calls, <$0.50):
    python -m knowable_worlds.run_calibration --model gpt-oss \
        --n-scms 5 --rungs L0 L3 --out-dir knowable_worlds/outputs/pilot_gptoss
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent          # known_causal_models/
REPO = KCM.parent                            # repo root
sys.path.insert(0, str(KCM))
sys.path.insert(0, str(REPO))

from scm.engine import SCM                                        # noqa: E402
from knowable_worlds.battery import generate_battery                  # noqa: E402
from knowable_worlds.prompts import build_prompt, RUNGS               # noqa: E402
from forecast_bench.llm_client import LLMClient, parse_json_response  # noqa: E402
from forecast_bench.run_sensitivity import MODEL_MAP              # noqa: E402


def get_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "")


def ask(client: LLMClient, system: str, user: str, retries: int = 6) -> float | None:
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


def summarize(rows: list[dict]):
    print(f"\n{'rung':<6}{'n':>5}{'mean|p-p*|':>12}{'slope':>8}{'opt gap':>10}{'bias':>8}")
    for rung in RUNGS:
        r = [x for x in rows if x["rung"] == rung and x["p"] is not None]
        if not r:
            continue
        p = np.array([x["p"] for x in r])
        ps = np.array([x["p_star"] for x in r])
        slope = float(np.polyfit(ps, p, 1)[0]) if len(r) > 2 else float("nan")
        print(f"{rung:<6}{len(r):>5}{np.mean(np.abs(p-ps)):>12.4f}{slope:>8.3f}"
              f"{np.mean((p-ps)**2):>10.4f}{np.mean(p-ps):>+8.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--n-scms", type=int, default=5)
    ap.add_argument("--seed-base", type=int, default=100)
    ap.add_argument("--n-nodes", type=int, default=8)
    ap.add_argument("--edge-prob", type=float, default=0.35)
    ap.add_argument("--noise-scale", type=float, default=1.0)
    ap.add_argument("--rungs", nargs="+", default=["L0", "L3"], choices=list(RUNGS))
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--out-dir", default="knowable_worlds/outputs/pilot")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--noise-sweep", nargs="+", type=float, default=None,
                    help="RQ4: run each SCM's battery at several noise scales; "
                         "events (tau, do) stay FIXED from the sigma=1 reference "
                         "battery, true p* is recomputed per sigma.")
    args = ap.parse_args()

    api_key = get_api_key()
    if not api_key:
        sys.exit("[ERROR] OPENROUTER_API_KEY not set")
    client = LLMClient(api_key=api_key, model=MODEL_MAP.get(args.model, args.model),
                       temperature=args.temperature, max_tokens=4000)

    out_dir = KCM / args.out_dir if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.jsonl"

    done = set()
    rows = []
    if args.resume and out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("p") is None:
                continue          # failed call (e.g. credit outage) -> retry on resume
            rows.append(r)
            # keys carry model + noise scale so a different condition resumed
            # into the same directory re-runs instead of silently skipping
            base = (r["scm_seed"], r["item_id"], r["rung"],
                    r.get("model"), r.get("noise_scale", 1.0))
            done.add(base + ((r["sweep_sigma"],) if "sweep_sigma" in r else ()))
        print(f"[resume] {len(done)} forecasts already recorded")

    fh = out_path.open("a", encoding="utf-8")
    total = args.n_scms * 18 * len(args.rungs)   # approx
    made = 0
    from knowable_worlds.analytic import event_prob
    sweep = args.noise_sweep or [args.noise_scale]
    for s in range(args.n_scms):
        seed = args.seed_base + s
        ref = SCM(n_nodes=args.n_nodes, edge_prob=args.edge_prob, seed=seed,
                  noise_scale=1.0)
        battery = generate_battery(ref, seed=seed)   # events fixed at sigma=1 ref
        for sig in sweep:
            scm = SCM(n_nodes=args.n_nodes, edge_prob=args.edge_prob, seed=seed,
                      noise_scale=sig)
            for item in battery:
                # whenever the shown world's sigma differs from the sigma=1
                # reference battery, the truth must be recomputed on the shown
                # world — this used to happen only on the --noise-sweep path,
                # so a plain --noise-scale 2.0 run was scored against sigma=1
                # ground truth (audit 2026-07-07)
                if sig != 1.0 and item.get("kind") == "counterfactual":
                    continue   # truth-recompute is interventional; invalid for cf
                do = {int(i): v for i, v in (item.get("do_idx") or {}).items()}
                if sig != 1.0:
                    p_star_sig = round(float(event_prob(
                        scm, item["outcome_idx"], item["tau"], do=do or None)), 6)
                else:
                    p_star_sig = item["p_star"]
                item_run = dict(item); item_run["p_star"] = p_star_sig
                item = item_run
                for rung in args.rungs:
                    key = (seed, item["item_id"], rung, args.model, sig) \
                        + ((sig,) if args.noise_sweep else ())
                    if key in done:
                        continue
                    system, user = build_prompt(scm, item, rung,
                                                samples_seed=555 + seed)
                    p = ask(client, system, user)
                    row = {
                        "scm_seed": seed, "rung": rung, "p": p,
                        "model": args.model,
                        "noise_scale": sig,
                        **({"sweep_sigma": sig} if args.noise_sweep else {}),
                        **{k: item.get(k) for k in (
                            "item_id", "kind", "outcome", "tau", "p_star", "depth",
                            "aleatoric", "do", "confounded", "node_type",
                            "p_obs_analog", "ident_gap")},
                    }
                    rows.append(row)
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()
                    made += 1
                    if made % 10 == 0:
                        print(f"  [{made}/{total - len(done)}] scm={seed} "
                              f"{item['item_id']} {rung} p={p} p*={item['p_star']}",
                              flush=True)
    fh.close()

    summarize(rows)
    print(f"\nAPI stats: {json.dumps(client.stats.to_dict())}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
