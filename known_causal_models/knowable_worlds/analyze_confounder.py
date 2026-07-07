"""Analysis for the hidden-confounder dynamic world (§16.3).

The causal reads:
  1. see/do divergence: mean |answer(see_A) - answer(do_A)|. A model with the
     causal structure right SEPARATES them (matching the true divergence); a
     confounded model collapses them toward 0.
  2. do_A error: |answer(do_A) - p_star(do_A)| vs the confound gap
     |p_spurious - p_star|. Landing near p_spurious = the confounding error;
     near p_star = correct do-reasoning.
  3. do_C is the necessity control: the model MUST use the intervened value
     (C is a real cause). Using it (tracking p_star) while ignoring do_A =
     correct causal structure, not a blanket "ignore interventions" rule.
  4. structure: does the model assert the SPURIOUS X1->X2 (A->B) edge? It
     should not (A only co-moves with B through the hidden confounder).

Emits per-checkpoint and pooled tables; writes conf_master.csv for R.

Usage:
    python -m knowable_worlds.analyze_confounder --run confounder_gptoss
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

from knowable_worlds.dyn_confounder import ConfoundedDynSCM   # noqa: E402

OUT = KCM / "knowable_worlds" / "outputs"


def load(run):
    f = (OUT / run / "results.jsonl") if not Path(run).is_absolute() \
        else Path(run)
    if not f.exists():
        sys.exit(f"no results at {f}")
    rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
    keep = {}
    for r in rows:
        if r.get("p") is not None or r.get("edges") is not None:
            keep[(r["scenario"], r["item_id"])] = r
    return list(keep.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="confounder_gptoss")
    args = ap.parse_args()
    rows = load(args.run)

    fc = [r for r in rows if r["kind"] == "forecast"]
    st = [r for r in rows if r["kind"] == "structure"]

    # index forecasts by (scenario, checkpoint, query)
    idx = {(r["scenario"], r["checkpoint"], r["query"]): r for r in fc}
    scen_cks = sorted({(r["scenario"], r["checkpoint"]) for r in fc})

    print(f"\n=== hidden-confounder world: {args.run} "
          f"({len(scen_cks)} scenario-checkpoints) ===\n")

    # ---- 1+2: see/do on A ----
    # model divergence and true divergence are computed over the SAME items
    # (both see_A and do_A present) — mismatched guards used to crash on
    # partial data and average the two numbers over different samples
    # (audit 2026-07-07)
    see_do_div, true_div, do_err_star, do_err_spur = [], [], [], []
    rows_csv = []
    for sc, ck in scen_cks:
        see = idx.get((sc, ck, "see_A"))
        do = idx.get((sc, ck, "do_A"))
        doc = idx.get((sc, ck, "do_C"))
        if see and do and see["p"] is not None and do["p"] is not None:
            see_do_div.append(abs(see["p"] - do["p"]))
            true_div.append(abs(see["p_star"] - do["p_star"]))
            do_err_star.append(abs(do["p"] - do["p_star"]))
            do_err_spur.append(abs(do["p"] - do["p_spurious"]))
            rows_csv.append({
                "scenario": sc, "checkpoint": ck,
                "p_see_A": see["p"], "p_do_A": do["p"],
                "p_do_C": doc["p"] if doc else "",
                "star_do_A": do["p_star"], "spurious_do_A": do["p_spurious"],
                "confound_gap": do.get("confound_gap", ""),
                "star_do_C": doc["p_star"] if doc else "",
            })
    if see_do_div:
        print("1. see(A) vs do(A) divergence (model separates seeing from doing?)")
        print(f"   mean |p(see_A) - p(do_A)| = {np.mean(see_do_div):.3f}")
        print(f"   (true divergence in these items: {np.mean(true_div):.3f})")
        print("\n2. do(A) answer: is it the correct value or the confounded one?")
        print(f"   mean |p(do_A) - p*(correct)|   = {np.mean(do_err_star):.3f}")
        print(f"   mean |p(do_A) - p(confounded)| = {np.mean(do_err_spur):.3f}")
        closer = ("CORRECT (causal)" if np.mean(do_err_star) < np.mean(do_err_spur)
                  else "CONFOUNDED (spurious)")
        print(f"   -> do(A) answers land closer to: {closer}")

    # ---- 3: do_C necessity control ----
    doc_err = [abs(idx[(sc, ck, "do_C")]["p"] - idx[(sc, ck, "do_C")]["p_star"])
               for sc, ck in scen_cks
               if (sc, ck, "do_C") in idx and idx[(sc, ck, "do_C")]["p"] is not None]
    if doc_err:
        print("\n3. do(C) necessity control (must USE the intervened value)")
        print(f"   mean |p(do_C) - p*| = {np.mean(doc_err):.3f} "
              f"(low = correctly uses the real cause)")

    # ---- 4: spurious A->B edge in structure ----
    if st:
        spur = sum(1 for r in st if r.get("edges")
                   and any(e.startswith("X1->X2") for e in r["edges"]))
        n = sum(1 for r in st if r.get("edges"))
        print(f"\n4. spurious X1->X2 (A->B) edge asserted in "
              f"{spur}/{n} structure answers (should be ~0)")

    # ---- csv for R ----
    if rows_csv:
        cpath = OUT / args.run / "conf_master.csv"
        with cpath.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_csv[0].keys()))
            w.writeheader()
            w.writerows(rows_csv)
        print(f"\nwrote {cpath}")


if __name__ == "__main__":
    main()
