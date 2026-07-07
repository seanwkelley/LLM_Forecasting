"""Noise-sensitivity figure (RQ4): does the model's confidence track how random
the world actually is?

Left: error vs the noise dial, per rung — shows the L3 calculator is exact at
sigma=1 and degrades away from it. Right: for each event, how much the model's
answer moved vs how much the TRUE answer moved when sigma changed (slope 1 =
perfect tracking) — split by rung.

Counterfactual items excluded (sweep truth-recompute is undefined for them).

Usage:
    python -m knowable_worlds.gen_noise_sensitivity \
        --run-dir knowable_worlds/outputs/noise_gptoss
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, MUTED = "#1b1b1f", "#5c5c66"
COL = {"L0": "#3a6ea5", "L3": "#2f7d4f"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    rows = [json.loads(l) for l in
            (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    ok = [r for r in rows if r["p"] is not None and r["kind"] != "counterfactual"
          and "sweep_sigma" in r]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.9))

    # left: mean error vs sigma
    sigmas = sorted({r["sweep_sigma"] for r in ok})
    for rung in ("L0", "L3"):
        ys = []
        for sig in sigmas:
            r = [x for x in ok if x["rung"] == rung and x["sweep_sigma"] == sig]
            ys.append(np.mean([abs(x["p"] - x["p_star"]) for x in r]))
        ax1.plot(sigmas, ys, "o-", color=COL[rung], lw=2, ms=6, label=rung)
        for sx, sy in zip(sigmas, ys):
            ax1.annotate(f"{sy:.3f}", (sx, sy), textcoords="offset points",
                         xytext=(0, 7), fontsize=7, color=COL[rung], ha="center")
    ax1.set_xlabel("how random the world is (noise scale σ)")
    ax1.set_ylabel("mean error  |p − p*|")
    ax1.set_title("Error vs the noise dial\n(the L3 calculator is exact at σ=1 only)",
                  fontsize=9.5)
    ax1.axvline(1.0, color=MUTED, ls=":", lw=1)
    ax1.legend(frameon=False, fontsize=9)

    # right: per-event tracking — model's move vs the true move across sigma
    for rung in ("L0", "L3"):
        groups = defaultdict(list)
        for r in ok:
            if r["rung"] == rung:
                groups[(r["scm_seed"], r["item_id"])].append(r)
        dx, dy = [], []
        for g in groups.values():
            if len(g) < 3:
                continue
            g = sorted(g, key=lambda x: x["sweep_sigma"])
            ps = [x["p_star"] for x in g]
            p = [x["p"] for x in g]
            if max(ps) - min(ps) < 0.02:
                continue
            dx.append(ps[-1] - ps[0])      # how much the truth moved
            dy.append(p[-1] - p[0])        # how much the model moved
        ax2.scatter(dx, dy, s=26, alpha=0.65, color=COL[rung], label=rung,
                    edgecolors="none")
    lim = 0.85
    ax2.plot([-lim, lim], [-lim, lim], "--", color=MUTED, lw=1.2)
    ax2.axhline(0, color=MUTED, lw=0.6)
    ax2.axvline(0, color=MUTED, lw=0.6)
    ax2.set_xlabel("how much the TRUE answer moved (σ 0.25 → 2)")
    ax2.set_ylabel("how much the model's answer moved")
    ax2.set_title("Tracking, event by event\n(dashed = perfect; flat cloud = deaf to randomness)",
                  fontsize=9.5)
    ax2.legend(frameon=False, fontsize=9)

    fig.suptitle("Does the model's confidence respond to true randomness? "
                 "(GPT-OSS, noise sweep)", fontsize=11)
    fig.tight_layout()
    out = run_dir / "noise_sensitivity.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
