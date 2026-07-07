"""Figures for the single-edge results (design doc 16.2).

(1) formation_discrimination: Qwen-thinking vs GPT-OSS stated probabilities
    on the SAME ten candidate influences (5 real, 5 absent), one pair per
    call, single pre-change snapshot — the decision-rule result.
(2) tracking_trajectories: P(present) for the changed edge vs its matched
    control edges across the eight checkpoints, per certified scenario
    (v2-prompt runs in outputs/single_edge/).

    python -m knowable_worlds.gen_single_edge_figures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

OUT = Path(__file__).parent / "outputs" / "single_edge"

INK, MUTED = "#1b1b1f", "#5c5c66"
BLUE, GREEN, ORANGE, GRAY = "#3a6ea5", "#2f7d4f", "#b5652f", "#b9b9c0"


def rows(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if json.loads(l).get("p") is not None]


def fig_formation():
    qwen = rows(OUT / "qwen_qwen3-235b-a22b-thinking-2507_edge_add_300_ck55.jsonl")
    goss = rows(OUT / "gpt-oss_edge_add_300_ck55.jsonl")
    by_pair = {r["pair"]: {"truth": r["truth"]} for r in qwen}
    for r in qwen:
        by_pair[r["pair"]]["qwen"] = r["p"]
    for r in goss:
        by_pair.setdefault(r["pair"], {"truth": r["truth"]})["goss"] = r["p"]
    pairs = sorted(by_pair.items(), key=lambda kv: (-kv[1]["truth"], kv[0]))

    fig, ax = plt.subplots(figsize=(8.6, 3.6), dpi=200)
    xs = np.arange(len(pairs))
    for x, (name, d) in zip(xs, pairs):
        ax.plot([x, x], [d.get("goss", np.nan), d.get("qwen", np.nan)],
                color="#dddde2", lw=1, zorder=1)
    ax.scatter(xs, [d.get("qwen") for _, d in pairs], s=52, color=BLUE,
               zorder=3, label="Qwen3-235B thinking")
    ax.scatter(xs, [d.get("goss") for _, d in pairs], s=46, color=ORANGE,
               marker="s", zorder=3, label="GPT-OSS 120B")
    n_true = sum(1 for _, d in pairs if d["truth"])
    ax.axvspan(-0.5, n_true - 0.5, color=GREEN, alpha=0.06)
    ax.axvline(n_true - 0.5, color=MUTED, lw=0.8, ls=":")
    ax.text(n_true / 2 - 0.5, 1.06, "influence is real", ha="center",
            fontsize=10, color=GREEN)
    ax.text(n_true + (len(pairs) - n_true) / 2 - 0.5, 1.06,
            "influence is absent", ha="center", fontsize=10, color=MUTED)
    # per-model group means
    for model, col in (("qwen", BLUE), ("goss", ORANGE)):
        for lo, hi, t in ((0, n_true, 1), (n_true, len(pairs), 0)):
            vals = [d.get(model) for _, d in pairs[lo:hi] if d.get(model) is not None]
            ax.hlines(np.mean(vals), lo - 0.4, hi - 0.6, color=col, lw=1.4,
                      ls="--", alpha=0.7)
    ax.set_xticks(xs)
    ax.set_xticklabels([n.replace("->", "→") for n, _ in pairs],
                       fontsize=8.5)
    ax.set_ylabel("stated P(influence is present)")
    ax.set_ylim(0, 1.12)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(0.99, 0.02,
            "each pair asked one at a time, single pre-change snapshot "
            "(seed 300, checkpoint 55);\ndashed lines = per-group means. "
            "Discrimination: Qwen +0.45, GPT-OSS +0.09.",
            transform=ax.transAxes, ha="right", fontsize=8, color=MUTED)
    fig.tight_layout()
    p = OUT / "formation_discrimination.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig_tracking():
    scens = [("edge_add", 301), ("edge_add", 302),
             ("edge_remove", 301), ("edge_remove", 302)]
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 5.6), dpi=200,
                             sharex=True, sharey=True)
    for ax, (ct, seed) in zip(axes.flat, scens):
        rs = rows(OUT / f"gpt-oss_track_{ct}_{seed}.jsonl")
        by_pair = {}
        for r in rs:
            by_pair.setdefault((r["pair"], r["role"]), []).append(
                (r["checkpoint"], r["p"]))
        for (pair, role), pts in sorted(by_pair.items()):
            pts.sort()
            ck, p = zip(*pts)
            if role == "changed":
                ax.plot(ck, p, color=BLUE, lw=2.2, marker="o", ms=4.5,
                        zorder=3, label="changed edge")
            else:
                ax.plot(ck, p, color=GRAY, lw=1.2,
                        ls="--" if role == "ctrl_false" else "-",
                        marker="o", ms=3, zorder=2)
        ax.axvline(60, color=INK, ls="--", lw=1)
        pre = [p for (pr, ro), pts in by_pair.items() if ro == "changed"
               for c, p in pts if c <= 60]
        post = [p for (pr, ro), pts in by_pair.items() if ro == "changed"
                for c, p in pts if c > 60]
        word = "added" if ct == "edge_add" else "removed"
        ax.set_title(f"edge {word} · world {seed}   "
                     f"(changed edge: {np.mean(pre):.2f} → "
                     f"{np.mean(post):.2f})", fontsize=10)
        ax.set_ylim(0, 1)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].text(60.8, 0.05, "t* = 60", fontsize=8.5, color=INK)
    for ax in axes[1]:
        ax.set_xlabel("checkpoint (period)")
    for ax in axes[:, 0]:
        ax.set_ylabel("stated P(present)")
    handles = [plt.Line2D([], [], color=BLUE, lw=2.2, marker="o", ms=4.5,
                          label="changed edge"),
               plt.Line2D([], [], color=GRAY, lw=1.2, marker="o", ms=3,
                          label="control edge (exists in both regimes)"),
               plt.Line2D([], [], color=GRAY, lw=1.2, ls="--", marker="o",
                          ms=3, label="control edge (exists in neither)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9,
               frameon=False)
    fig.suptitle("GPT-OSS, one pair per question: does the belief about the "
                 "changed edge move across the change?", fontsize=11.5)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    p = OUT / "tracking_trajectories.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print("wrote", fig_formation())
    print("wrote", fig_tracking())
