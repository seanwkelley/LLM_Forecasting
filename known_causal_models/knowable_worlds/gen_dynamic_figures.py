"""Figure for the dynamic (regime-shift) arm — three panels:

    (a) recovery curve: forecast error on the AFFECTED node vs time from the
        change, model against the stale oracle and the refit baselines
        (controls overlaid as the flat reference)
    (b) perseveration: x = distance to the stale mechanism, y = distance to
        truth, post-change (ABOVE the diagonal = closer to the old world —
        matches the in-plot title; the docstring used to say below)
    (c) structure tracking: reported-graph F1 against the old and new regime
        graphs across checkpoints

Usage:
    python -m knowable_worlds.gen_dynamic_figures \
        --run-dir knowable_worlds/outputs/dynamic_gptoss
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

from knowable_worlds.analyze_dynamic import load          # noqa: E402
from knowable_worlds.dyn_battery import CHECKPOINTS       # noqa: E402

INK, MUTED = "#1b1b1f", "#5c5c66"
BLUE, ORANGE, RED, GREEN = "#3a6ea5", "#d17a22", "#b03a3a", "#2f7d4f"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    run_dir = KCM / args.run_dir if not Path(args.run_dir).is_absolute() \
        else Path(args.run_dir)
    rows, _ = load(run_dir)
    fc = [r for r in rows if r["kind"] == "forecast"]
    st = [r for r in rows if r["kind"] == "structure"]
    rel = [ck - 60 for ck in CHECKPOINTS]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.2, 4.0))

    # (a) recovery curve
    series = {"model": (BLUE, "o", "-"), "p_stale": (RED, "x", "--"),
              "p_window": (GREEN, "s", ":"), "p_full": (MUTED, "d", ":")}
    for name, (col, mk, ls) in series.items():
        ys = []
        for ck in CHECKPOINTS:
            r = [x for x in fc if x["checkpoint"] == ck and x["affected"]]
            if not r:
                ys.append(np.nan); continue
            src = [x["p"] if name == "model" else x[name] for x in r]
            ys.append(np.mean([abs(a - x["p_star"]) for a, x in zip(src, r)]))
        lab = {"model": "model", "p_stale": "old regime",
               "p_window": "recent 20 periods only",
               "p_full": "all history"}[name]
        ax1.plot(rel, ys, ls, marker=mk, color=col, lw=1.8, ms=5, label=lab)
    ctl = []
    for ck in CHECKPOINTS:
        r = [x for x in fc if x["checkpoint"] == ck and not x["affected"]]
        ctl.append(np.mean([abs(x["p"] - x["p_star"]) for x in r])
                   if r else np.nan)
    ax1.plot(rel, ctl, "-", color=BLUE, lw=1.0, alpha=0.35,
             label="model, control nodes")
    ax1.axvline(0, color=INK, ls=":", lw=1.2)
    ax1.text(0.5, ax1.get_ylim()[1] * 0.97, "structure\nchanges",
             fontsize=7.5, color=INK, va="top")
    ax1.set_xlabel("checkpoints, periods from the change")
    ax1.set_ylabel("mean error  |p − p*|")
    ax1.set_title("(a) Forecast error on the affected node", fontsize=10)
    ax1.legend(frameon=False, fontsize=7.5)

    # (b) perseveration scatter (post, affected, detectable)
    pv = [x for x in fc if x["affected"] and x["phase"] == "post"
          and x["regime_gap"] >= 0.5]
    dt = [abs(x["p"] - x["p_star"]) for x in pv]
    ds = [abs(x["p"] - x["p_stale"]) for x in pv]
    t = [x["rel_time"] for x in pv]
    sc = ax2.scatter(ds, dt, c=t, cmap="viridis", s=34, edgecolors="none")
    lim = max(dt + ds + [0.5]) * 1.06
    ax2.plot([0, lim], [0, lim], "--", color=MUTED, lw=1.2)
    ax2.set_xlim(0, lim); ax2.set_ylim(0, lim)
    ax2.set_xlabel("distance to Old Regime")
    ax2.set_ylabel("distance to Current Regime")
    ax2.set_title("(b) Which regime is it answering from?\n(above diagonal = closer to Old Regime)",
                  fontsize=10)
    fig.colorbar(sc, ax=ax2, label="periods since change", shrink=0.85)

    # (c) structure tracking
    for tag, col, lab in (("f1_r1", RED, "old regime"),
                          ("f1_r2", GREEN, "current regime")):
        ys = []
        for ck in CHECKPOINTS:
            r = [x for x in st if x["checkpoint"] == ck
                 and x.get(tag) is not None]
            ys.append(np.mean([x[tag] for x in r]) if r else np.nan)
        ax3.plot(rel, ys, "o-", color=col, lw=1.8, ms=5, label=lab)
    ax3.axvline(0, color=INK, ls=":", lw=1.2)
    ax3.set_ylim(0, 1)
    ax3.set_xlabel("checkpoints, periods from the change")
    ax3.set_ylabel("edge-list F1")
    ax3.set_title("(c) Stated structure: which regime\ndoes the model describe?",
                  fontsize=10)
    ax3.legend(frameon=False, fontsize=8)

    fig.suptitle("Tracking a changing causal world (dynamic arm)", fontsize=12)
    fig.tight_layout()
    out = run_dir / "dynamic_tracking.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
