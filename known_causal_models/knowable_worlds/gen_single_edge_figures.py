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


def draw_world(ax, dyn, highlights, note=None):
    """Small circular graph of the world: regime-1 edges faint; highlighted
    pairs colored. highlights: {(i,j): (color, linestyle, lw)}."""
    n = dyn.n
    pos = {k: (np.cos(2 * np.pi * k / n - np.pi / 2),
               np.sin(2 * np.pi * k / n - np.pi / 2)) for k in range(n)}
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.55, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")

    def edge(i, j, color, ls, lw, zorder):
        x0, y0 = pos[i]
        x1, y1 = pos[j]
        ax.annotate("", xy=(x1 * 0.82, y1 * 0.82),
                    xytext=(x0 * 0.82, y0 * 0.82),
                    arrowprops=dict(arrowstyle="-|>", color=color, ls=ls,
                                    lw=lw, shrinkA=0, shrinkB=0,
                                    connectionstyle="arc3,rad=0.12"),
                    zorder=zorder)

    present = set(map(tuple, np.argwhere(dyn.B1 != 0)))
    for i, j in present:
        if i != j and (i, j) not in highlights:
            edge(i, j, "#e3e3e8", "-", 0.9, 1)
    for (i, j), (color, ls, lw) in highlights.items():
        edge(i, j, color, ls, lw, 3)
    for k in range(n):
        x, y = pos[k]
        ax.add_patch(plt.Circle((x, y), 0.17, fc="white", ec=INK, lw=0.9,
                                zorder=4))
        ax.text(x, y, f"X{k+1}", ha="center", va="center", fontsize=7.5,
                zorder=5)
    if note:
        ax.text(0, -1.52, note, ha="center", fontsize=7.5, color=MUTED)


def fig_formation():
    qwen = rows(OUT / "qwen_qwen3-235b-a22b-thinking-2507_edge_add_300_ck55.jsonl")
    goss = rows(OUT / "gpt-oss_edge_add_300_ck55.jsonl")
    by_pair = {r["pair"]: {"truth": r["truth"]} for r in qwen}
    for r in qwen:
        by_pair[r["pair"]]["qwen"] = r["p"]
    for r in goss:
        by_pair.setdefault(r["pair"], {"truth": r["truth"]})["goss"] = r["p"]
    pairs = sorted(by_pair.items(), key=lambda kv: (-kv[1]["truth"], kv[0]))

    fig, ax = plt.subplots(figsize=(5.2, 3.7), dpi=200)
    models = (("qwen", BLUE, "Qwen3-235B thinking", -0.13),
              ("goss", ORANGE, "GPT-OSS 120B", +0.13))
    for model, col, label, off in models:
        means = []
        for gx, truth in ((0, 1), (1, 0)):
            vals = [d[model] for _, d in pairs
                    if d["truth"] == truth and d.get(model) is not None]
            m = float(np.mean(vals))
            se = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
            means.append((gx + off, m))
            ax.errorbar(gx + off, m, yerr=se,
                        fmt="o" if model == "qwen" else "s", color=col,
                        markersize=9, markeredgecolor="white",
                        markeredgewidth=1.2, elinewidth=1.6, capsize=0,
                        zorder=5)
        (x0, m0), (x1, m1) = means
        ax.plot([x0, x1], [m0, m1], color=col, lw=1.6, alpha=0.8, zorder=2,
                label=label)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Real", "Absent"], fontsize=11)
    ax.set_ylabel("stated P(influence is present)")
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = OUT / "formation_discrimination.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig_tracking():
    from knowable_worlds.dyn_battery import CHECKPOINTS

    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5), dpi=200,
                             sharey=True)
    axes_t = list(axes)
    for ax, ct in zip(axes_t, ("edge_add", "edge_remove")):
        # pool the two worlds of this operation, aligned on checkpoints
        series = {"changed": {}, "ctrl_true": {}, "ctrl_false": {}}
        for seed in (301, 302):
            for r in rows(OUT / f"gpt-oss_track_{ct}_{seed}.jsonl"):
                series[r["role"]].setdefault(r["checkpoint"], []).append(
                    r["p"])
        for role, style in (
                ("ctrl_true", dict(color=GRAY, lw=1.3, ls="-", marker="o",
                                   ms=3, zorder=2)),
                ("ctrl_false", dict(color=GRAY, lw=1.3, ls="--", marker="o",
                                    ms=3, zorder=2)),
                ("changed", dict(color=BLUE, lw=2.2, ls="-", marker="o",
                                 ms=4.5, zorder=3))):
            cks = [c for c in CHECKPOINTS if c in series[role]]
            m = [float(np.mean(series[role][c])) for c in cks]
            se = [float(np.std(series[role][c], ddof=1)
                        / np.sqrt(len(series[role][c]))) for c in cks]
            ax.errorbar(cks, m, yerr=se, capsize=0, elinewidth=1, **style)
        ax.axvline(60, color=INK, ls="--", lw=1)
        ax.set_title("edge added" if ct == "edge_add" else "edge removed",
                     fontsize=11)
        ax.set_ylim(0, 1)
        ax.set_xlabel("checkpoint")
        ax.spines[["top", "right"]].set_visible(False)
    axes_t[0].text(60.8, 0.05, "t* = 60", fontsize=8.5, color=INK)
    axes_t[0].set_ylabel("stated P(present)")
    handles = [plt.Line2D([], [], color=BLUE, lw=2.2, marker="o", ms=4.5,
                          label="changed edge"),
               plt.Line2D([], [], color=GRAY, lw=1.3, marker="o", ms=3,
                          label="control edges (exist in both regimes)"),
               plt.Line2D([], [], color=GRAY, lw=1.3, ls="--", marker="o",
                          ms=3, label="control edge (exists in neither)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=8.5,
               frameon=False)
    fig.subplots_adjust(top=0.92, bottom=0.26, left=0.08, right=0.98,
                        wspace=0.08)
    p = OUT / "tracking_trajectories.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig_qwen_tracking():
    """Both models on the same scenario (edge removed, world 302): the
    changed edge's stated P(present) across checkpoints."""
    files = {
        "Qwen3-235B thinking":
            "qwen_qwen3-235b-a22b-thinking-2507_track_edge_remove_302.jsonl",
        "GPT-OSS 120B": "gpt-oss_track_edge_remove_302.jsonl",
    }
    fig, ax = plt.subplots(figsize=(5.6, 3.5), dpi=200)
    for (label, fname), col, mk in zip(files.items(), (BLUE, ORANGE),
                                       ("o", "s")):
        rs = [r for r in rows(OUT / fname) if r["role"] == "changed"]
        rs.sort(key=lambda r: r["checkpoint"])
        ax.plot([r["checkpoint"] for r in rs], [r["p"] for r in rs],
                color=col, lw=2, marker=mk, ms=5, label=label)
    ax.axvline(60, color=INK, ls="--", lw=1)
    ax.text(60.8, 0.06, "edge removed\nat t* = 60", fontsize=8.5, color=INK)
    ax.set_xlabel("checkpoint")
    ax.set_ylabel("stated P(present), removed edge")
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = OUT / "qwen_perseverance.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print("wrote", fig_formation())
    print("wrote", fig_tracking())
    print("wrote", fig_qwen_tracking())
