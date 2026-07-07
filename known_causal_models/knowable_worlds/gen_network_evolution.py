"""How the model's stated network evolves across checkpoints (pilot data).

Top: one mini graph per checkpoint — the edges the model asserted at that
moment, green if present in the CURRENT regime's true graph with the right
sign, orange if not. The changed slot is drawn underneath as a gray dashed
reference on every panel.

Bottom: edge persistence — every edge the model ever asserted in this
scenario (rows) against checkpoints (columns); a filled cell means the edge
was asserted in that answer. Row-sparse stripes = churn: the model redraws
its graph almost from scratch each time (pilot mean consecutive-answer
Jaccard overlap: printed in the title).

Usage:
    python -m knowable_worlds.gen_network_evolution \
        --run-dir knowable_worlds/outputs/dynamic_gptoss --scenario sign_flip_300
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KCM = Path(__file__).parent.parent
sys.path.insert(0, str(KCM))

from knowable_worlds.dyn_engine import DynSCM          # noqa: E402
from knowable_worlds.dyn_battery import CHECKPOINTS    # noqa: E402

GREEN, ORANGE, MUTED, INK = "#2f7d4f", "#b5652f", "#9a9aa2", "#1b1b1f"


def node_pos(n, r=1.0):
    return {k: (r * math.cos(2 * math.pi * k / n - math.pi / 2),
                r * math.sin(2 * math.pi * k / n - math.pi / 2))
            for k in range(n)}


def parse(e):
    a, rest = e.split("->")
    b, s = rest.split(":")
    return int(a[1:]) - 1, int(b[1:]) - 1, s


def draw_graph(ax, edges, truth_now, changed_key, n=8):
    pos = node_pos(n)
    # changed slot as reference
    ci, cj = [int(x) - 1 for x in changed_key.replace("X", "").split("->")]
    ax.annotate("", xy=pos[cj], xytext=pos[ci],
                arrowprops=dict(arrowstyle="-|>", color=MUTED, ls="--",
                                lw=1.0, alpha=0.5, shrinkA=9, shrinkB=9))
    for e in sorted(edges):
        i, j, s = parse(e)
        ok = e in truth_now
        ax.annotate("", xy=pos[j], xytext=pos[i],
                    arrowprops=dict(arrowstyle="-|>",
                                    color=GREEN if ok else ORANGE,
                                    lw=1.6 if ok else 1.1,
                                    ls="-" if s == "+" else (0, (4, 2)),
                                    shrinkA=9, shrinkB=9, alpha=0.9))
    for k, (x, y) in pos.items():
        ax.add_patch(plt.Circle((x, y), 0.14, fc="white", ec=INK, lw=0.8, zorder=3))
        ax.text(x, y, f"{k+1}", ha="center", va="center", fontsize=6, zorder=4)
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3)
    ax.set_aspect("equal"); ax.axis("off")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--scenario", default="sign_flip_300")
    args = ap.parse_args()
    run_dir = KCM / args.run_dir if not Path(args.run_dir).is_absolute() \
        else Path(args.run_dir)

    rows = [json.loads(l) for l in
            (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    st = {}
    for r in rows:
        if r.get("edges") is not None and r["scenario"] == args.scenario:
            st[r["checkpoint"]] = (set(r["edges"]), r)
    assert st, f"no structure rows for {args.scenario}"
    any_r = next(iter(st.values()))[1]
    d = DynSCM(n_nodes=any_r.get("n_nodes", 8), edge_prob=any_r.get("edge_prob", 0.2),
               seed=any_r["seed"], change_type=any_r["change_type"],
               n_changes=any_r.get("n_changes", 1))
    ce = d.changed_edge
    changed_key = f"X{ce['i']+1}->X{ce['j']+1}"

    # churn stat across ALL scenarios in the run
    st_all = {}
    for r in rows:
        if r.get("edges") is not None:
            st_all[(r["scenario"], r["checkpoint"])] = set(r["edges"])
    jacs = []
    for sc in {k[0] for k in st_all}:
        for a, b in zip(CHECKPOINTS, CHECKPOINTS[1:]):
            A, B = st_all.get((sc, a)), st_all.get((sc, b))
            if A is not None and B is not None:
                jacs.append(len(A & B) / max(len(A | B), 1))
    jac = float(np.mean(jacs))

    fig = plt.figure(figsize=(13, 6.4))
    gs = fig.add_gridspec(2, 8, height_ratios=[1.15, 1.0], hspace=0.34)

    for q, ck in enumerate(CHECKPOINTS):
        ax = fig.add_subplot(gs[0, q])
        if ck not in st:
            ax.axis("off"); continue
        edges, _ = st[ck]
        truth_now = d.signed_edges(2 if ck >= d.t_change else 1)
        draw_graph(ax, edges, truth_now, changed_key)
        okn = len(edges & truth_now)
        ax.set_title(f"t={ck} ({'pre' if ck < d.t_change else 'post'})\n"
                     f"{okn} correct / {len(edges)-okn} false",
                     fontsize=7.5,
                     color=INK if ck < d.t_change else "#7d4f8d")

    # persistence panel
    union = sorted(set().union(*[e for e, _ in st.values()]))
    ax = fig.add_subplot(gs[1, :])
    for yi, e in enumerate(union):
        for xi, ck in enumerate(CHECKPOINTS):
            if ck in st and e in st[ck][0]:
                truth_now = d.signed_edges(2 if ck >= d.t_change else 1)
                ax.add_patch(plt.Rectangle((xi, yi), 0.92, 0.85,
                             fc=GREEN if e in truth_now else ORANGE, alpha=0.85))
    ax.axvline(3.0, color=INK, ls=":", lw=1.2)   # between ck 55 and 62
    ax.text(3.05, len(union) + 0.2, "t* = 60: the causal model changes", fontsize=8)
    ax.set_xticks([i + 0.46 for i in range(len(CHECKPOINTS))])
    ax.set_xticklabels([f"t={c}" for c in CHECKPOINTS], fontsize=8)
    ax.set_yticks([i + 0.42 for i in range(len(union))])
    ax.set_yticklabels(union, fontsize=6, family="monospace")
    ax.set_xlim(0, len(CHECKPOINTS)); ax.set_ylim(0, len(union) + 0.1)
    ax.invert_yaxis()
    ax.set_ylabel("every edge the model ever asserted", fontsize=8)
    for sp in ax.spines.values():
        sp.set_visible(False)

    fig.suptitle(
        f"The model's stated network over time — {args.scenario} "
        f"(green = correct for the current regime, orange = false; "
        f"gray dashed = the changed slot)\n"
        f"Run-wide overlap between consecutive answers: Jaccard = {jac:.2f} — "
        f"the graph is redrawn nearly from scratch at every checkpoint",
        fontsize=10)
    out = run_dir / f"network_evolution_{args.scenario}.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    print(f"wrote {out}  (consecutive-answer Jaccard, all scenarios: {jac:.3f})")


if __name__ == "__main__":
    main()
