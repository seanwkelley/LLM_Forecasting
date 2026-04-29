"""Generate the intervention anatomy diagram."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import numpy as np

fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, height_ratios=[1.2, 1.8, 1.5], hspace=0.35, wspace=0.45,
                       left=0.05, right=0.95, top=0.94, bottom=0.04)

BLUE, ORANGE, GREEN, VERMILLION, GRAY = '#0072B2', '#E69F00', '#009E73', '#D55E00', '#666666'

# ── Top left: Intervention description ──
ax_intv = fig.add_subplot(gs[0, 0])
ax_intv.axis('off')
ax_intv.set_xlim(0, 10); ax_intv.set_ylim(0, 4)
box = FancyBboxPatch((0.2, 0.3), 9.6, 3.2, boxstyle='round,pad=0.15',
                       facecolor='#FFF3D4', edgecolor=ORANGE, linewidth=2)
ax_intv.add_patch(box)
ax_intv.text(0.6, 3.1, 'INTERVENTION (Step 1)', fontsize=13, fontweight='bold', color=ORANGE)
ax_intv.text(0.6, 2.4, 'Type: EVENT \u2014 Supply Disruption (magnitude=3.0)', fontsize=11, color='#333')
ax_intv.text(0.6, 1.8, 'Purpose: Test shock \u2192 production_cost \u2192 fundamental_price pathway', fontsize=10, color='#555')
ax_intv.text(0.6, 1.1, 'Mechanism: Clamp shock variable, run 3 periods,\ncompare vs. no-intervention baseline', fontsize=10, color='#777')

# ── Top right: Delta bar chart ──
ax_delta = fig.add_subplot(gs[0, 1])
ax_delta.margins(y=0.1)
var_names = ['Clearing Price', 'Volume', 'Fundamental Price', 'Best Ask', 'Total Cash', 'Total Inventory']
deltas = [5.93, -33.33, 77.40, 184.34, -165.58, 38.33]
colors = [GREEN if d > 0 else VERMILLION for d in deltas]
ax_delta.barh(range(len(var_names)), deltas, color=colors, alpha=0.7, height=0.6)
ax_delta.set_yticks(range(len(var_names)))
ax_delta.set_yticklabels(var_names, fontsize=10)
ax_delta.axvline(0, color='#ccc', linewidth=0.8)
ax_delta.set_xlabel('Delta (intervention \u2212 baseline)', fontsize=10)
ax_delta.set_title('Observed Effects', fontsize=13, fontweight='bold', color=GRAY)
ax_delta.spines['top'].set_visible(False)
ax_delta.spines['right'].set_visible(False)
ax_delta.tick_params(axis='y', pad=8)
fig.subplots_adjust()

# ── Middle: Before/After graphs ──
all_nodes = ['shock', 'production_cost', 'demand_value', 'demand_per_period',
             'storage_cost', 'agent_orders', 'clearing_price', 'volume',
             'fundamental_price', 'price_history', 'cash', 'inventory']
n = len(all_nodes)
angles = np.linspace(0, 2*np.pi, n, endpoint=False) - np.pi/2
node_pos = {name: (1.0*np.cos(a), 1.0*np.sin(a)) for name, a in zip(all_nodes, angles)}

before_edges = [
    ('agent_orders', 'clearing_price'),
    ('agent_orders', 'volume'),
    ('clearing_price', 'price_history'),
]
after_edges = [
    ('agent_orders', 'clearing_price'),
    ('agent_orders', 'volume'),
    ('clearing_price', 'price_history'),
    ('shock', 'production_cost'),
    ('production_cost', 'fundamental_price'),
    ('production_cost', 'agent_orders'),
    ('clearing_price', 'cash'),
    ('volume', 'cash'),
    ('volume', 'inventory'),
]
before_set = set(before_edges)

for ax_idx, (ax_pos, edges, title, is_after) in enumerate([
    (gs[1, 0], before_edges, 'Graph BEFORE Intervention (3 edges)', False),
    (gs[1, 1], after_edges, 'Graph AFTER Intervention (9 edges, +6 new)', True),
]):
    ax = fig.add_subplot(ax_pos)
    ax.set_title(title, fontsize=12, fontweight='bold', color=BLUE if not is_after else GREEN)
    ax.axis('off')
    ax.set_xlim(-1.8, 1.8); ax.set_ylim(-1.65, 1.65)

    active = set()
    for s, t in edges:
        active.add(s); active.add(t)

    active_before = set()
    for s, t in before_edges:
        active_before.add(s); active_before.add(t)

    # Draw edges
    for (src, tgt) in edges:
        x1, y1 = node_pos[src]
        x2, y2 = node_pos[tgt]
        # Shorten arrow to not overlap node
        dx, dy = x2 - x1, y2 - y1
        dist = np.sqrt(dx**2 + dy**2)
        shrink = 0.14 / dist if dist > 0 else 0
        x1s, y1s = x1 + dx * shrink, y1 + dy * shrink
        x2s, y2s = x2 - dx * shrink, y2 - dy * shrink

        is_new = is_after and (src, tgt) not in before_set
        color = BLUE if is_new else GREEN
        lw = 2.5 if is_new else 1.5
        ax.annotate('', xy=(x2s, y2s), xytext=(x1s, y1s),
                     arrowprops=dict(arrowstyle='->', color=color, lw=lw))

    # Draw nodes
    for name, (x, y) in node_pos.items():
        is_active = name in active
        is_newly_active = is_after and is_active and name not in active_before
        if is_newly_active:
            c, ec, lw = '#D4E8F7', BLUE, 2
        elif is_active:
            c, ec, lw = 'white', '#333', 1.5
        else:
            c, ec, lw = '#f5f5f5', '#ddd', 0.5

        circle = plt.Circle((x, y), 0.13, facecolor=c, edgecolor=ec, linewidth=lw, zorder=5)
        ax.add_patch(circle)

        fontcolor = BLUE if is_newly_active else ('#222' if is_active else '#bbb')
        fw = 'bold' if is_active else 'normal'
        label = name.replace('_', '\n')

        # Radial label placement so edges don't overlap labels
        angle = np.arctan2(y, x)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        lx = x + 0.28 * cos_a
        ly = y + 0.28 * sin_a
        if cos_a > 0.3:
            ha = 'left'
        elif cos_a < -0.3:
            ha = 'right'
        else:
            ha = 'center'
        if sin_a > 0.3:
            va = 'bottom'
        elif sin_a < -0.3:
            va = 'top'
        else:
            va = 'center'
        ax.text(lx, ly, label, ha=ha, va=va, fontsize=7,
                color=fontcolor, fontweight=fw, zorder=6,
                bbox=dict(facecolor='white', edgecolor='none', pad=0.8))

    if is_after:
        legend_elements = [
            Line2D([0], [0], color=GREEN, lw=2, label='Existing edge'),
            Line2D([0], [0], color=BLUE, lw=2.5, label='New edge (this step)'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=9, frameon=True,
                  facecolor='white', edgecolor='#ddd', bbox_to_anchor=(1.0, -0.08))

# ── Bottom: Model reasoning ──
ax_reason = fig.add_subplot(gs[2, :])
ax_reason.axis('off')
ax_reason.set_xlim(0, 20); ax_reason.set_ylim(-0.3, 4.3)
box = FancyBboxPatch((0.2, 0.1), 19.6, 3.7, boxstyle='round,pad=0.15',
                       facecolor='#F5F5F5', edgecolor=GRAY, linewidth=1.5)
box.set_clip_on(False)
ax_reason.add_patch(box)
ax_reason.text(10, 3.45, 'MODEL REASONING (Gemini 3.1 Pro)', fontsize=13, fontweight='bold',
               color=GRAY, ha='center')

import textwrap

reasoning = (
    "Supply shock caused massive increases in fundamental_price (+77) and best_ask (+184), "
    "while bid prices remained unchanged. This confirms the shock affects supply-side parameters "
    "(production_cost), driving up fundamental_price and ask prices. Volume drop (\u221233) and "
    "cash/inventory changes are downstream effects."
)
wrapped = textwrap.fill(reasoning, width=90)
ax_reason.text(10, 2.9, wrapped, fontsize=11, color='#333',
               verticalalignment='top', ha='center', fontfamily='sans-serif', linespacing=1.5)

ax_reason.text(10, 1.35, 'Key uncertainties:', fontsize=11, fontweight='bold', color='#555', ha='center')
ax_reason.text(10, 0.95,
    '\u2022 Does fundamental_price directly influence agent_orders?\n'
    '\u2022 Does price_history influence agent_orders (technical trading)?',
    fontsize=10, color='#666', ha='center', va='top', linespacing=1.5)

fig.suptitle('Anatomy of a Single Intervention Step', fontsize=14, fontweight='bold', y=0.97)

out_dir = 'known_causal_models'
fig.savefig(f'{out_dir}/intervention_example.png', dpi=200, bbox_inches='tight', facecolor='white')
fig.savefig(f'{out_dir}/intervention_example.pdf', dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print('Saved')
