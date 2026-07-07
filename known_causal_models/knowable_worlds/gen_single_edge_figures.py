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

    from knowable_worlds.dyn_engine import DynSCM
    dyn = DynSCM(n_nodes=8, edge_prob=0.2, seed=300, change_type="edge_add")

    fig = plt.figure(figsize=(11.4, 3.9), dpi=200)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 2.9], wspace=0.05)
    axg = fig.add_subplot(gs[0])
    hl = {}
    for name, d in pairs:
        i, j = (int(x[1:]) - 1 for x in name.split("->"))
        hl[(i, j)] = ((GREEN, "-", 1.8) if d["truth"]
                      else ("#b03030", ":", 1.4))
    draw_world(axg, dyn, hl)
    ax = fig.add_subplot(gs[1])
    rng = np.random.default_rng(3)          # tiny fixed jitter, n=5 per group
    models = (("qwen", BLUE, "Qwen3-235B thinking", -0.13),
              ("goss", ORANGE, "GPT-OSS 120B", +0.13))
    for model, col, label, off in models:
        means = []
        for gx, truth in ((0, 1), (1, 0)):
            vals = [d[model] for _, d in pairs
                    if d["truth"] == truth and d.get(model) is not None]
            x = gx + off + 0.055 + rng.uniform(-0.015, 0.015, len(vals))
            ax.scatter(x, vals, s=34, color=col, alpha=0.4, zorder=3,
                       marker="o" if model == "qwen" else "s")
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
        ax.text(0.5 + off * 2.6, (m0 + m1) / 2 + 0.03,
                f"gap {m0 - m1:+.2f}", fontsize=9.5, color=col,
                ha="center")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["influence is real", "influence is absent"],
                       fontsize=11)
    ax.set_ylabel("stated P(influence is present)")
    ax.set_xlim(-0.45, 1.45)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.1, top=0.95)
    p = OUT / "formation_discrimination.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


def fig_tracking():
    from knowable_worlds.dyn_engine import DynSCM
    from knowable_worlds.run_single_edge import (select_tracking_pairs,
                                                 pair_idx)

    scens = [("edge_add", 301), ("edge_add", 302),
             ("edge_remove", 301), ("edge_remove", 302)]
    fig = plt.figure(figsize=(12.8, 6.4), dpi=200)
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 2.15, 1, 2.15],
                          hspace=0.5, wspace=0.3)
    axes_t = []
    for k, (ct, seed) in enumerate(scens):
        r, c = divmod(k, 2)
        axg = fig.add_subplot(gs[r, 2 * c])
        ax = fig.add_subplot(gs[r, 2 * c + 1])
        axes_t.append(ax)
        dyn = DynSCM(n_nodes=8, edge_prob=0.2, seed=seed, change_type=ct)
        hl = {}
        for q in select_tracking_pairs(dyn):
            ij = pair_idx(q["pair"])
            if q["role"] == "changed":
                hl[ij] = (BLUE, "--" if ct == "edge_add" else "-", 2.4)
            elif q["role"] == "ctrl_true":
                hl[ij] = ("#8d8d96", "-", 1.6)
            else:
                hl[ij] = ("#8d8d96", ":", 1.4)
        draw_world(axg, dyn, hl)
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
                     f"{np.mean(post):.2f})", fontsize=9.5)
        ax.set_ylim(0, 1)
        ax.spines[["top", "right"]].set_visible(False)
    axes_t[0].text(60.8, 0.05, "t* = 60", fontsize=8.5, color=INK)
    for ax in axes_t[2:]:
        ax.set_xlabel("checkpoint (period)")
    for ax in (axes_t[0], axes_t[2]):
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
    fig.subplots_adjust(top=0.9, bottom=0.14, left=0.055, right=0.985)
    p = OUT / "tracking_trajectories.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print("wrote", fig_formation())
    print("wrote", fig_tracking())
