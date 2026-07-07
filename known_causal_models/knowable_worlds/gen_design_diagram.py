"""Study-design figure for the Knowable Worlds study (KNOWABLE_WORLDS_DESIGN.md).

v3 — paper-figure layout with lettered sub-panels:
  (a) environment (SCM + noise dial)      (b) event battery with p*-strata strip
  (c) MODEL PATH band (ladder -> LLM -> p; declared-SCM alt mode)
  (d) TRUTH PATH band (exact moments -> p*)
  (e) per-event comparison, incl. an illustrative calibration mini-plot
plus a caption block. Outputs knowable_worlds_design.{png,pdf}.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

INK, MUTED, EDGE = "#1b1b1f", "#5c5c66", "#c9c9c9"
BLUE, GREEN, PURP, ORAN = "#3a6ea5", "#2f7d4f", "#7d4f8d", "#b5652f"
GTINT, BTINT, RQBG = "#f0f6f1", "#edf3f9", "#fff3c4"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig = plt.figure(figsize=(14, 8.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 14); ax.set_ylim(0, 8.4); ax.axis("off")


def box(x, y, w, h, text="", fc="white", ec=EDGE, tc=INK, fs=9, weight="normal",
        lw=1.4, rounding=0.08, zorder=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0.02,rounding_size={rounding}",
                 linewidth=lw, edgecolor=ec, facecolor=fc, zorder=zorder))
    if text:
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=fs,
                color=tc, weight=weight, zorder=zorder+1)


def arrow(x1, y1, x2, y2, color=MUTED, lw=2.0, z=4):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=15, linewidth=lw, color=color, zorder=z,
                 shrinkA=4, shrinkB=4))


def rq(x, y, label, z=6):
    box(x, y, 0.52, 0.3, label, fc=RQBG, ec=INK, fs=7.2, weight="bold", lw=1.0,
        zorder=z)


def panel_letter(x, y, letter):
    ax.text(x, y, letter, fontsize=12, weight="bold", color=INK)


# ============================ title ============================
ax.text(0.35, 8.05, "Measuring LLM calibration against knowable probabilities",
        fontsize=14.5, weight="bold")

# ============================ (a) environment ============================
axp, ayp, awp, ahp = 0.35, 4.7, 3.1, 2.95
panel_letter(axp, ayp+ahp+0.08, "a")
box(axp, ayp, awp, ahp, fc="white", ec=INK, lw=1.5)
ax.text(axp+awp/2, ayp+ahp-0.28, "Simulated environment", ha="center",
        fontsize=9.5, weight="bold")
ax.text(axp+awp/2, ayp+ahp-0.58, "structural causal model, equations known",
        ha="center", fontsize=7.6, color=MUTED)
ndz = {"X1": (axp+0.75, ayp+1.85), "X2": (axp+2.35, ayp+1.85),
       "X3": (axp+1.55, ayp+1.3)}
for a, b in [("X1", "X3"), ("X2", "X3")]:
    arrow(*ndz[a], *ndz[b], color=BLUE, lw=1.4, z=3)
for nid, (nx, ny) in ndz.items():
    ax.add_patch(Circle((nx, ny), 0.19, facecolor="white", edgecolor=BLUE,
                        lw=1.5, zorder=4))
    ax.text(nx, ny, nid, ha="center", va="center", fontsize=7.4, zorder=5)
ax.text(axp+awp/2, ayp+0.82, "X3 = 0.91·X1 − 1.10·X2 + Normal(0, σ)",
        ha="center", fontsize=7.8, family="monospace")
ax.add_patch(Circle((axp+0.62, ayp+0.35), 0.2, facecolor="white", edgecolor=ORAN,
                    lw=1.8, zorder=4))
ax.text(axp+0.62, ayp+0.35, "σ", ha="center", va="center", fontsize=10,
        color=ORAN, weight="bold", zorder=5)
ax.text(axp+0.92, ayp+0.35, "noise scale is an experimental dial",
        fontsize=7.2, color=ORAN, va="center")
rq(axp+awp-0.62, ayp+0.2, "RQ4")

# ============================ (b) events ============================
bxp, byp, bwp, bhp = 0.35, 1.35, 3.1, 2.8
panel_letter(bxp, byp+bhp+0.08, "b")
box(bxp, byp, bwp, bhp, fc="white", ec=INK, lw=1.5)
ax.text(bxp+bwp/2, byp+bhp-0.28, "Forecast events", ha="center", fontsize=9.5,
        weight="bold")
ax.text(bxp+bwp/2, byp+bhp-0.78,
        "P( Xk > τ )\nP( Xk > τ | do(Xi = v) )", ha="center", fontsize=8.6,
        family="monospace")
# strata strip
sx0, sy0, sw0 = bxp+0.35, byp+0.85, bwp-0.7
strata = [.05, .1, .2, .35, .5, .65, .8, .9, .95]
cmap = plt.get_cmap("RdYlGn")
for i, p in enumerate(strata):
    ax.add_patch(plt.Rectangle((sx0 + i*sw0/9, sy0), sw0/9-0.015, 0.3,
                 facecolor=cmap(p), edgecolor="none", zorder=3))
ax.text(sx0, sy0+0.44, "τ set analytically so true p* lands exactly on:",
        fontsize=7.0, color=MUTED)
for i, p in enumerate([.05, .35, .65, .95]):
    ax.text(sx0 + strata.index(p)*sw0/9 + sw0/18, sy0-0.16, f"{p}",
            ha="center", fontsize=6.4, color=MUTED)
ax.text(bxp+bwp/2, byp+0.32,
        "full calibration-curve coverage\nby construction", ha="center",
        fontsize=7.2, color=MUTED, style="italic")

# connect a->b
arrow(axp+awp/2, ayp, axp+awp/2, byp+bhp, color=INK, lw=1.6)

# ============================ (c) model path band ============================
cxp, cyp, cwp, chp = 3.95, 4.35, 6.6, 3.3
panel_letter(cxp, cyp+chp+0.08, "c")
box(cxp, cyp, cwp, chp, fc=GTINT, ec=GREEN, lw=1.6)
ax.text(cxp+0.25, cyp+chp-0.32, "MODEL PATH", fontsize=10, weight="bold",
        color=GREEN, va="center")
ax.text(cxp+1.85, cyp+chp-0.32, "— the LLM sees the event plus one rung of context, "
        "and produces a probability", fontsize=8, color=MUTED, va="center")

# ladder rungs with descriptions
rung_x, rung_y, rung_w, rung_h = cxp+0.25, cyp+1.55, 0.98, 1.15
rungs = [("L0", "50 joint\nsamples", "#ffffff"),
         ("L1", "+ DAG\nstructure", "#f2f6f3"),
         ("L2", "+ edge\nsigns", "#e4ede7"),
         ("L3", "+ exact\nequations", "#d3e4d8")]
for i, (tag, desc, shade) in enumerate(rungs):
    xx = rung_x + i*(rung_w+0.12)
    box(xx, rung_y, rung_w, rung_h, fc=shade,
        ec=GREEN if i == 3 else EDGE, lw=2.0 if i == 3 else 1.0)
    ax.text(xx+rung_w/2, rung_y+rung_h-0.28, tag, ha="center", fontsize=9,
            weight="bold")
    ax.text(xx+rung_w/2, rung_y+0.4, desc, ha="center", fontsize=7.2)
    if i < 3:
        arrow(xx+rung_w, rung_y+rung_h/2, xx+rung_w+0.13, rung_y+rung_h/2,
              color=MUTED, lw=1.2)
ax.text(rung_x, rung_y-0.25, "information ladder (between-item manipulation)",
        fontsize=7.2, color=MUTED)
rq(rung_x+4.35, rung_y+0.75, "RQ3")
rq(rung_x+3*(rung_w+0.12)+0.18, rung_y+rung_h+0.1, "RQ2")
ax.text(rung_x, cyp+0.62,
        "at L3 the true answer is computable from the prompt alone —\n"
        "any remaining error is a pure reasoning failure (RQ2)",
        fontsize=7.2, color=MUTED, va="center")

# response modes
mx0 = cxp+5.0
box(mx0, cyp+1.9, 1.4, 0.85, "LLM states\np", fc="white", ec=GREEN, fs=9,
    weight="bold", lw=1.9)
box(mx0, cyp+0.55, 1.4, 0.95, "LLM declares\nequations →\nengine runs them",
    fc="white", ec=PURP, fs=7.4, lw=1.7)
rq(mx0-0.6, cyp+0.62, "RQ5")
arrow(rung_x+4*(rung_w+0.12)+0.5, rung_y+rung_h/2, mx0, cyp+2.32, color=GREEN, lw=1.8)
arrow(rung_x+4*(rung_w+0.12)+0.5, rung_y+rung_h/2, mx0, cyp+1.15, color=PURP, lw=1.5)

# ============================ (d) truth path band ============================
dxp, dyp, dwp, dhp = 3.95, 1.35, 6.6, 2.5
panel_letter(dxp, dyp+dhp+0.08, "d")
box(dxp, dyp, dwp, dhp, fc=BTINT, ec=BLUE, lw=1.6)
ax.text(dxp+0.25, dyp+dhp-0.32, "TRUTH PATH", fontsize=10, weight="bold",
        color=BLUE, va="center")
ax.text(dxp+1.95, dyp+dhp-0.32, "— computed from the generating process; "
        "no language model involved", fontsize=8, color=MUTED, va="center")
box(dxp+0.25, dyp+0.45, 3.4, 1.25,
    "exact Gaussian moments\nμ = (I−Wᵀ)⁻¹c,   Σ = (I−Wᵀ)⁻¹D(I−Wᵀ)⁻ᵀ\n"
    "(linear SCMs; 10,000 re-simulations otherwise)",
    fc="white", ec=BLUE, fs=7.6, lw=1.5)
box(dxp+5.0, dyp+0.65, 1.4, 0.85, "true\nprobability\np*", fc="white", ec=BLUE,
    fs=8.6, weight="bold", lw=1.9)
arrow(dxp+3.65, dyp+1.07, dxp+5.0, dyp+1.07, color=BLUE, lw=2.0)

# events feed both bands
arrow(bxp+bwp, byp+bhp/2+0.9, cxp, cyp+1.4, color=GREEN, lw=2.0)
arrow(bxp+bwp, byp+bhp/2+0.4, dxp, dyp+1.2, color=BLUE, lw=2.0)

# ============================ (e) comparison ============================
expn, eyp, ewp, ehp = 10.95, 1.35, 2.7, 6.3
panel_letter(expn, eyp+ehp+0.08, "e")
box(expn, eyp, ewp, ehp, fc="white", ec=INK, lw=1.6)
ax.text(expn+ewp/2, eyp+ehp-0.3, "Per-event comparison", ha="center",
        fontsize=9.5, weight="bold")
ax.text(expn+ewp/2, eyp+ehp-0.6, "exact — no bins, no proxies", ha="center",
        fontsize=7.4, color=MUTED, style="italic")

# mini calibration plot (illustrative)
ins = fig.add_axes([ (expn+0.45)/14, (eyp+3.35)/8.4, 1.9/14, 2.1/8.4 ])
xx = np.linspace(0.02, 0.98, 50)
ins.plot(xx, xx, "--", color=MUTED, lw=1.2, label="perfect (slope 1)")
ins.plot(xx, 0.42 + 0.25*(xx-0.5), color=GREEN, lw=2.0, label="anchored LLM\n(registered pred.)")
ins.set_xlim(0, 1); ins.set_ylim(0, 1)
ins.set_xticks([0, .5, 1]); ins.set_yticks([0, .5, 1])
ins.tick_params(labelsize=6, length=2)
ins.set_xlabel("true p*", fontsize=7); ins.set_ylabel("stated p", fontsize=7)
ins.legend(fontsize=5.4, frameon=False, loc="upper left")
for s in ins.spines.values():
    s.set_color(MUTED)

metrics = [("calibration error", "|p − p*|"),
           ("discrimination", "slope of p on p*"),
           ("excess Brier", "(p − p*)²  vs optimal"),
           ("aleatoric sensitivity", "does p track σ? (RQ4)")]
yy = eyp+2.7
for name, formula in metrics:
    ax.text(expn+0.25, yy, f"• {name}", fontsize=8, weight="bold")
    ax.text(expn+0.4, yy-0.26, formula, fontsize=7.4, color=MUTED,
            family="monospace")
    yy -= 0.62
rq(expn+ewp-0.72, eyp+0.18, "RQ1")

arrow(mx0+1.4, cyp+2.32, expn, eyp+5.2, color=GREEN, lw=2.0)
arrow(mx0+1.4, cyp+1.05, expn, eyp+4.6, color=PURP, lw=1.5)
arrow(dxp+6.4, dyp+1.07, expn, eyp+1.1, color=BLUE, lw=2.0)

# ============================ caption ============================
box(0.35, 0.12, 13.3, 0.95, fc="#fbfbf9", ec=EDGE, lw=1.0)
ax.text(0.55, 0.86, "Study design.", fontsize=8.2, weight="bold", va="center")
ax.text(0.55, 0.55,
   "Each forecast event is posed about a simulated system whose generating equations are known, with thresholds placed so the true probability p* spans the full unit interval. "
   "The same event travels two paths: the model path (the LLM answers, given one rung of the information ladder — or declares its own equations, which the engine executes),",
   fontsize=7.3, color=INK, va="center")
ax.text(0.55, 0.28,
   "and the truth path (p* computed exactly from the mechanism). Comparing p to p* per event yields calibration, discrimination, and distance-from-optimal without bins or "
   "proxies — and dialing the noise σ tests whether stated uncertainty tracks true randomness. RQ1-RQ5 mark where each research question is answered.",
   fontsize=7.3, color=INK, va="center")

out = os.path.dirname(os.path.abspath(__file__))
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(out, f"knowable_worlds_design.{ext}"), dpi=185,
                bbox_inches="tight")
print("wrote", os.path.join(out, "knowable_worlds_design.{png,pdf}"))
