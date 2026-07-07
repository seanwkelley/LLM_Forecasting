"""True-calibration scatter: stated p vs exact p*, per information rung.

The defining figure of the study — each point is one forecast event scored
against the analytically true probability (no bins, no proxies). Identity
line = perfect calibration; fitted line shows the observed slope.

Usage:
    python -m knowable_worlds.gen_calibration_plot \
        --run-dir knowable_worlds/outputs/pilot_gptoss
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")   # headless generator
import matplotlib.pyplot as plt

INK, MUTED = "#1b1b1f", "#5c5c66"
OBS, DO, CONF = "#3a6ea5", "#b5652f", "#b03030"
RUNGS = ["Lnull", "L0", "L1", "L2", "L3", "L1p", "L2p", "L3p"]
RUNG_LABEL = {"Lnull": "L∅ — event only", "L0": "L0 — samples only",
              "L1": "L1 — + structure", "L2": "L2 — + signs",
              "L3": "L3 — + equations", "L1p": "L1p — structure, no data",
              "L2p": "L2p — signs, no data", "L3p": "L3p — equations, no data"}

def classify(x):
    if x["kind"] == "observational":
        return "obs"
    if x["kind"] == "counterfactual":
        return "cf"
    return "conf" if x.get("confounded") else "do"

CF = "#7d4f8d"
CLASSES = [("obs", OBS, "o", "observational"),
           ("do", DO, "^", "do( · ) root"),
           ("conf", CONF, "x", "do( · ) confounded"),
           ("cf", CF, "v", "counterfactual")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    rows = [json.loads(l) for l in
            (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [r for r in rows if r.get("p") is not None]

    rungs = [r for r in RUNGS if any(x["rung"] == r for x in rows)]
    ncol = min(4, len(rungs))
    nrow = (len(rungs) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.3 * ncol, 3.8 * nrow),
                             sharey=True, squeeze=False)
    flat = axes.flatten()
    for extra in flat[len(rungs):]:
        extra.axis("off")

    for ax, rung in zip(flat, rungs):
        sub = [x for x in rows if x["rung"] == rung]
        for cls, color, marker, label in CLASSES:
            pts = [x for x in sub if classify(x) == cls]
            if not pts:
                continue
            ps = np.array([x["p_star"] for x in pts])
            p = np.array([x["p"] for x in pts])
            # jitter x slightly so stacked strata are visible
            jit = (np.random.RandomState(0).rand(len(ps)) - 0.5) * 0.012
            ax.scatter(ps + jit, p, s=30 if marker == "x" else 26, alpha=0.7,
                       color=color, marker=marker, label=label,
                       linewidths=1.6 if marker == "x" else 0,
                       edgecolors="none" if marker != "x" else color, zorder=3)
        ax.plot([0, 1], [0, 1], "--", color=MUTED, lw=1.2, zorder=2)
        # per-kind fitted slopes: the kind x rung interaction IS the finding —
        # a pooled slope would conflate counting (obs) with causal inference (do)
        yy = 0.93
        for cls, color, tag in [("obs", OBS, "obs"), ("do", DO, "do"),
                                ("conf", CONF, "conf"), ("cf", CF, "cf")]:
            pts = [x for x in sub if classify(x) == cls]
            if len(pts) < 4:
                continue
            ps = np.array([x["p_star"] for x in pts])
            p = np.array([x["p"] for x in pts])
            b, a = np.polyfit(ps, p, 1)
            xs = np.linspace(0, 1, 10)
            ax.plot(xs, a + b * xs, color=color, lw=1.7, zorder=4)
            ax.text(0.04, yy, f"{tag}: slope {b:.2f}, |err| {np.mean(np.abs(p-ps)):.3f}",
                    fontsize=8, weight="bold", color=color, transform=ax.transAxes)
            yy -= 0.075
        ax.text(0.04, yy, f"n = {len(sub)}", fontsize=7.5, color=MUTED,
                transform=ax.transAxes)
        ax.set_xlim(-0.03, 1.03); ax.set_ylim(-0.03, 1.03)
        ax.set_title(RUNG_LABEL.get(rung, rung), fontsize=10.5)
        ax.set_xlabel("true probability p*", fontsize=9.5)
        ax.tick_params(labelsize=8)
        ax.set_aspect("equal")
    for r in range(nrow):
        axes[r][0].set_ylabel("model's stated probability p", fontsize=9.5)
    flat[0].legend(fontsize=7.5, loc="lower right", frameon=False)
    model = rows[0].get("model", "?") if rows else "?"
    fig.suptitle(f"True calibration by information rung — {model} "
                 f"(dashed = perfect; each point scored against exact p*)",
                 fontsize=11, y=1.0)
    fig.tight_layout()
    out = run_dir / "calibration_scatter.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
