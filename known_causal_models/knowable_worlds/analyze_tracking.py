"""Committed analysis for changed-edge tracking runs (design doc 16.2 add.3).

Reads one or more *_track_*.jsonl files produced by run_single_edge.py
--mode tracking. Per scenario: pre/post means per role on the field the
change type moves (p_positive for sign_flip, p otherwise), the
difference-in-differences (changed minus mean control), and — for
weight_double — the detectability certification (the reference
statistician's rolling-20 |t| gap across t*, admission bar 1.5). Pooled
summaries are reported per change type across scenarios (the scenario is
the replication unit). Writes track_master.csv beside the inputs for R.

    python -m knowable_worlds.analyze_tracking
    python -m knowable_worlds.analyze_tracking --dir knowable_worlds/outputs/single_edge
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

T_CHANGE = 60
CERT_BAR = 1.5          # weight_double admission: post-pre rolling-|t| gap
CERT_POST_FROM = 70     # cert uses checkpoints whose 20-row window is
                        # majority post-change (62/66 are still mostly pre)


def load(track_dir: Path) -> dict:
    """Scenario key -> deduped rows (last successful row per pair x ck)."""
    scenarios = defaultdict(dict)
    for f in sorted(track_dir.glob("*_track_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("p") is None:
                continue
            key = (r.get("model"), r["change_type"], r.get("n_changes", 1),
                   r["seed"])
            scenarios[key][(r["pair"], r["checkpoint"])] = r
    return {k: list(v.values()) for k, v in scenarios.items()}


def read_field(rows, change_type):
    """The elicited field this change type moves."""
    return "p_positive" if change_type == "sign_flip" else "p"


def scenario_summary(key, rows):
    model, ct, k, seed = key
    field = read_field(rows, ct)
    out = {"model": model, "change_type": ct, "n_changes": k, "seed": seed,
           "field": field, "n_rows": len(rows)}
    ch_rows = [r for r in rows if r["role"] == "changed"]
    if ch_rows and ct == "sign_flip":
        # P(positive) falls if the original weight was positive, rises if not
        out["expected"] = "-" if ch_rows[0].get("weight1", 0) > 0 else "+"
    else:
        out["expected"] = {"edge_add": "+", "edge_remove": "-",
                           "weight_double": "+", "none": "0"}.get(ct, "?")
    deltas = {}
    for role in ("changed", "ctrl_true", "ctrl_false"):
        pre = [r[field] for r in rows if r["role"] == role
               and r["checkpoint"] <= T_CHANGE and r.get(field) is not None]
        post = [r[field] for r in rows if r["role"] == role
                and r["checkpoint"] > T_CHANGE and r.get(field) is not None]
        if pre and post:
            out[f"{role}_pre"] = float(np.mean(pre))
            out[f"{role}_post"] = float(np.mean(post))
            deltas[role] = float(np.mean(post) - np.mean(pre))
    ctrl = [deltas[r] for r in ("ctrl_true", "ctrl_false") if r in deltas]
    if "changed" in deltas and ctrl:
        out["did"] = deltas["changed"] - float(np.mean(ctrl))
    # Brier on P(present) against exact truth, per role (descriptive)
    for role in ("changed", "ctrl_true", "ctrl_false"):
        rs = [r for r in rows if r["role"] == role and r.get("p") is not None]
        if rs:
            out[f"{role}_brier"] = float(np.mean(
                [(r["p"] - r["truth"]) ** 2 for r in rs]))
    # sign-omission rate (a non-compliant model returns p_positive = None)
    n_missing = sum(1 for r in rows if r.get("p_positive") is None)
    out["sign_missing_frac"] = n_missing / len(rows) if rows else 0.0
    # weight_double certification from the recorded statistician confidence
    if ct == "weight_double":
        pre_t = [r["t_roll20"] for r in rows if r["role"] == "changed"
                 and r["checkpoint"] <= T_CHANGE and "t_roll20" in r]
        post_t = [r["t_roll20"] for r in rows if r["role"] == "changed"
                  and r["checkpoint"] >= CERT_POST_FROM and "t_roll20" in r]
        if pre_t and post_t:
            out["cert_gap"] = float(np.mean(post_t) - np.mean(pre_t))
            out["admitted"] = out["cert_gap"] >= CERT_BAR
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="knowable_worlds/outputs/single_edge")
    args = ap.parse_args()
    track_dir = KCM / args.dir if not Path(args.dir).is_absolute() \
        else Path(args.dir)
    scenarios = load(track_dir)
    if not scenarios:
        sys.exit(f"no *_track_*.jsonl under {track_dir}")

    summaries = [scenario_summary(k, v) for k, v in sorted(scenarios.items())]

    print(f"\n=== changed-edge tracking: {len(summaries)} scenario(s) ===")
    hdr = (f"{'change type':<14}{'seed':>5}{'k':>3}{'field':>11}"
           f"{'chg delta':>11}{'ctl delta':>10}{'DiD':>8}{'note':>14}")
    print(hdr)
    for s in summaries:
        ch_d = s.get("changed_post", np.nan) - s.get("changed_pre", np.nan)
        ct_d = np.mean([s.get("ctrl_true_post", np.nan)
                        - s.get("ctrl_true_pre", np.nan),
                        s.get("ctrl_false_post", np.nan)
                        - s.get("ctrl_false_pre", np.nan)])
        note = ""
        if s["change_type"] == "weight_double" and "cert_gap" in s:
            note = (f"|t| gap {s['cert_gap']:+.1f} "
                    + ("ADMIT" if s["admitted"] else "EXCLUDE"))
        if s["sign_missing_frac"] > 0.1:
            note += f" sign-miss {s['sign_missing_frac']:.0%}"
        print(f"{s['change_type']:<14}{s['seed']:>5}{s['n_changes']:>3}"
              f"{s['field']:>11}{ch_d:>+11.2f}{ct_d:>+10.2f}"
              f"{s.get('did', float('nan')):>+8.2f}{note:>14}")

    # pooled per model x change type, over ADMITTED scenarios only
    print("\npooled DiD per model x change type (admitted scenarios; "
          "scenario = replication unit)")
    for model in sorted({s["model"] for s in summaries}):
        for ct in ("edge_add", "edge_remove", "sign_flip", "weight_double",
                   "none"):
            sel = [s for s in summaries if s["model"] == model
                   and s["change_type"] == ct and "did" in s
                   and s.get("admitted", True)]
            if sel:
                ds = [s["did"] for s in sel]
                want = "/".join(sorted({s["expected"] for s in sel}))
                print(f"  {str(model):<10}{ct:<14} n={len(ds)}  "
                      f"mean DiD {np.mean(ds):+.2f}  "
                      f"per-scenario {['%+.2f' % d for d in ds]}  "
                      f"[expected sign: {want}]")

    # long CSV for R (one row per pair x checkpoint)
    out = track_dir / "track_master.csv"
    fields = ["model", "change_type", "n_changes", "seed", "pair", "role",
              "checkpoint", "phase", "p", "p_positive", "truth",
              "truth_positive", "t_roll20"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for key, rows in sorted(scenarios.items()):
            for r in rows:
                r = dict(r)
                r["phase"] = "pre" if r["checkpoint"] <= T_CHANGE else "post"
                w.writerow(r)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
