"""Committed descriptives for the v2 runs (design doc §16 addenda).

Covers:
  I2   per-edge probabilities, no prior (dynamic_gptoss_eprobs)
  P2   true-prior belief carryover     (dynamic_gptoss_p2)
  C-c  no-change control worlds        (dynamic_gptoss_nochange)
  C-b  temperature-0 structure answers (dynamic_gptoss_t0)
  C-a  same-prompt resampling          (dynamic_gptoss_resample)

For probability-format runs, per checkpoint:
  Brier vs the exact 0/1 edge truth (current regime), the base-rate
  reference Brier (always answer 18/56), discrimination (mean p on true
  edges minus mean p on non-edges), and the changed slot's stated
  probability — the sharp change-tracking measure.
For P2 additionally: |p-seed| = cumulative drift from the original seed
prior, and |p-carried| = movement from the belief actually handed to this
call (the previous checkpoint's answer) — the per-step revision magnitude.

Usage:
    python -m knowable_worlds.analyze_v2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

from knowable_worlds.dyn_engine import DynSCM                 # noqa: E402
from knowable_worlds.dyn_battery import CHECKPOINTS           # noqa: E402
from knowable_worlds.dyn_prompts import all_pairs             # noqa: E402

OUT = KCM / "knowable_worlds" / "outputs"


def load(run):
    f = OUT / run / "results.jsonl"
    if not f.exists():
        return []
    rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
    dedup = {}
    for r in rows:
        if (r.get("p") is not None or r.get("edges") is not None
                or r.get("edge_probs") is not None):
            dedup[(r["scenario"], r["item_id"], r.get("rep", 0))] = r
    return list(dedup.values())


def scen_world(r):
    return DynSCM(n_nodes=r.get("n_nodes", 8), edge_prob=r.get("edge_prob", .2),
                  seed=r["seed"], change_type=r["change_type"],
                  n_changes=r.get("n_changes", 1))


def truth_sets(d, ck):
    regime = 2 if ck >= d.t_change else 1
    present = {f"X{i+1}->X{j+1}" for i, j in d.cross_edges(regime)}
    return present


def eprob_table(rows, title, with_prior=False):
    # |p-seed| = drift from the ORIGINAL seed prior (cumulative);
    # |p-carried| = movement from the belief actually handed to THIS call —
    # the previous checkpoint's revised answer (the seed at checkpoint 1).
    # The old single column was labeled "movement from the carried prior"
    # while computing drift-from-seed (audit 2026-07-07).
    print(f"\n--- {title} ---")
    hdr = f"{'t-t*':>5}{'n':>4}{'Brier':>8}{'base':>7}{'discrim':>9}{'P(slot)':>9}"
    if with_prior:
        hdr += f"{'|p-seed|':>10}{'|p-carried|':>12}"
    print(hdr + f"{'meanP':>7}")
    worlds = {}
    prev_q = {}                       # scenario -> previous checkpoint's answer
    for ck in CHECKPOINTS:
        rs = [r for r in rows if r["kind"] == "structure"
              and r["checkpoint"] == ck and r.get("edge_probs")]
        if not rs:
            continue
        briers, bases, disc, slotp, dprior, dcarried, meanp = \
            [], [], [], [], [], [], []
        for r in rs:
            key = r["scenario"]
            if key not in worlds:
                worlds[key] = scen_world(r)
            d = worlds[key]
            present = truth_sets(d, ck)
            pairs = all_pairs(d)
            base = len(present) / len(pairs)
            ep = r["edge_probs"]
            y = np.array([1.0 if p in present else 0.0 for p in pairs])
            q = np.array([ep[p] for p in pairs])
            briers.append(float(np.mean((q - y) ** 2)))
            bases.append(float(np.mean((base - y) ** 2)))
            disc.append(float(q[y == 1].mean() - q[y == 0].mean()))
            ce = d.changed_edge
            slot = f"X{ce['i']+1}->X{ce['j']+1}"
            slotp.append(ep[slot])
            meanp.append(float(q.mean()))
            if with_prior:
                seed_prior = np.array(
                    [0.9 if p in
                     {f"X{i+1}->X{j+1}" for i, j in d.cross_edges(1)}
                     else 0.05 for p in pairs])
                dprior.append(float(np.mean(np.abs(q - seed_prior))))
                carried = prev_q.get(key, seed_prior)
                dcarried.append(float(np.mean(np.abs(q - carried))))
                prev_q[key] = q
        line = (f"{ck-60:>+5}{len(rs):>4}{np.mean(briers):>8.3f}"
                f"{np.mean(bases):>7.3f}{np.mean(disc):>+9.3f}"
                f"{np.mean(slotp):>9.2f}")
        if with_prior:
            line += f"{np.mean(dprior):>10.3f}{np.mean(dcarried):>12.3f}"
        print(line + f"{np.mean(meanp):>7.2f}")


def main():
    # ---- I2: probabilities, no prior ----
    i2 = load("dynamic_gptoss_eprobs")
    if i2:
        eprob_table(i2, "I2  per-edge probabilities, NO prior "
                        "(P(slot) = stated prob of the changed slot; "
                        "true post-change: add=high, remove=low)")

    # ---- P2: carryover with true prior ----
    p2 = load("dynamic_gptoss_p2")
    st2 = [r for r in p2 if r["kind"] == "structure"]
    if st2:
        eprob_table(st2, "P2  TRUE-PRIOR carryover (prior: true edges 0.9, "
                         "others 0.05; revised belief carried forward)",
                    with_prior=True)
        # slot trajectory split by whether truth says high or low post-change
        print("\n    P2 changed-slot P by change direction (post-change truth in brackets):")
        worlds = {}
        for direction, cts in (("should RISE  [1]", ("edge_add",)),
                               ("should FALL  [0]", ("edge_remove",)),
                               ("sign flip    [1]", ("sign_flip", "weight_double"))):
            vals = {ck: [] for ck in CHECKPOINTS}
            for r in st2:
                if r["change_type"] not in cts or not r.get("edge_probs"):
                    continue
                key = r["scenario"]
                if key not in worlds:
                    worlds[key] = scen_world(r)
                d = worlds[key]
                ce = d.changed_edge
                vals[r["checkpoint"]].append(
                    r["edge_probs"][f"X{ce['i']+1}->X{ce['j']+1}"])
            s = "  ".join(f"{ck-60:+d}:{np.mean(v):.2f}"
                          for ck, v in vals.items() if v)
            print(f"      {direction}: {s}")

    # ---- P2 forecasts: does the true prior fix forecast clinging? ----
    fc2 = [r for r in p2 if r["kind"] == "forecast" and r.get("p") is not None]
    if fc2:
        print("\n--- P2 forecasts (with carried true prior) vs original pilot ---")
        pilot = load("dynamic_gptoss")
        for name, rows in (("P2 (true prior)", fc2),
                           ("pilot (no prior)",
                            [r for r in pilot if r["kind"] == "forecast"
                             and r.get("p") is not None])):
            post = [r for r in rows if r["phase"] == "post" and r["affected"]
                    and r.get("regime_gap", 0) >= 0.5]
            if not post:
                continue
            p = np.array([r["p"] for r in post])
            dt = np.mean(np.abs(p - [r["p_star"] for r in post]))
            ds = np.mean(np.abs(p - [r["p_stale"] for r in post]))
            print(f"  {name:<18} post-change affected: d(truth)={dt:.3f} "
                  f"d(old rules)={ds:.3f}  n={len(post)}")

    # ---- C-c: no-change worlds ----
    cc = load("dynamic_gptoss_nochange")
    if cc:
        print("\n--- C-c  no-change worlds (95 stable periods) ---")
        st = [r for r in cc if r["kind"] == "structure" and r.get("edges")]
        worlds = {}
        for ck in CHECKPOINTS:
            rs = [r for r in st if r["checkpoint"] == ck]
            if not rs:
                continue
            f1s, nass = [], []
            for r in rs:
                key = r["scenario"]
                if key not in worlds:
                    worlds[key] = scen_world(r)
                d = worlds[key]
                truth = d.signed_edges(1)
                got = set(r["edges"])
                tp = len(got & truth)
                pr = tp / len(got) if got else 0
                rc = tp / len(truth) if truth else 0
                f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
                nass.append(len(got))
            print(f"  t={ck:>2}: signed F1={np.mean(f1s):.3f}  "
                  f"edges asserted={np.mean(nass):.1f}")
        fc = [r for r in cc if r["kind"] == "forecast" and r.get("p") is not None]
        if fc:
            err = np.mean([abs(r["p"] - r["p_star"]) for r in fc])
            print(f"  forecast error in a quiet world: {err:.3f} (n={len(fc)})")

    # ---- C-b: temperature 0 consistency ----
    cb = load("dynamic_gptoss_t0")
    st = [r for r in cb if r.get("edges") is not None]
    if st:
        by = {}
        for r in st:
            by.setdefault(r["scenario"], {})[r["checkpoint"]] = set(r["edges"])
        jacs = []
        for sc, d_ in by.items():
            cks = sorted(d_)
            for a, b in zip(cks, cks[1:]):
                jacs.append(len(d_[a] & d_[b]) / max(len(d_[a] | d_[b]), 1))
        print(f"\n--- C-b  T=0: consecutive-checkpoint Jaccard = "
              f"{np.mean(jacs):.2f} (T=0.7 pilot was 0.09; n={len(jacs)} pairs, "
              f"{len(st)}/{96} rows in) ---")

    # ---- C-a: same-prompt resampling ----
    ca = load("dynamic_gptoss_resample")
    st = [r for r in ca if r.get("edges") is not None]
    if st:
        by = {}
        for r in st:
            by.setdefault((r["scenario"], r["checkpoint"]), []).append(
                set(r["edges"]))
        jacs = []
        for reps in by.values():
            for i in range(len(reps)):
                for j in range(i + 1, len(reps)):
                    jacs.append(len(reps[i] & reps[j])
                                / max(len(reps[i] | reps[j]), 1))
        if jacs:
            print(f"\n--- C-a  same-prompt resampling: within-prompt Jaccard = "
                  f"{np.mean(jacs):.2f} ({len(st)}/160 rows in) ---")


if __name__ == "__main__":
    main()
