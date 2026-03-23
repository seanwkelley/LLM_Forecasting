# Figure Style Guide

All figures in this project should follow these conventions for visual consistency.

## Global matplotlib rcParams

```python
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "mathtext.default": "regular",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "boxplot.medianprops.color": "black",
    "boxplot.medianprops.linewidth": 1.5,
})
```

## Color Palettes

### Model colors (Wong 2011 / IBM Design, colorblind-safe)

| Model             | Hex       | Name            |
|-------------------|-----------|-----------------|
| Llama-3.1-8B      | `#E69F00` | Orange          |
| Llama-3.3-70B     | `#0072B2` | Blue            |
| DeepSeek-V3       | `#D55E00` | Vermillion      |
| Qwen3-235B        | `#009E73` | Green           |
| Gemini-Flash-Lite | `#CC79A7` | Reddish purple  |

### Probe category colors

| Category   | Hex       | Name         |
|------------|-----------|--------------|
| Node       | `#0072B2` | Blue         |
| Edge       | `#D55E00` | Vermillion   |
| Structural | `#009E73` | Bluish green |
| Control    | `#999999` | Gray         |

### Single-model figures

When a figure shows results for a single model, use `#0072B2` (blue) as the primary color.

## Layout

- **Multi-panel figures**: Use `_label_axes()` to add (a), (b), (c) labels at `fontsize=14`, `fontweight="bold"`, positioned at `(-0.02, 1.02)` in axes coordinates.
- **Figure size**: Typically `(8, 3.2)` for two-panel, `(10, 3.5)` for three-panel. Scale height as needed.
- **Panel spacing**: Use `gridspec_kw={'wspace': 0.35}` for side-by-side panels.
- **No suptitle**: Prefer panel titles over `fig.suptitle()` for consistency with the paper figures.

## Typography

| Element         | Size |
|-----------------|------|
| Base font       | 11   |
| Axis labels     | 12   |
| Axis titles     | 13   |
| Legend           | 10   |
| Tick labels      | 9    |
| Panel labels     | 14   |
| Annotations      | 9    |
| Significance stars | 9--13, bold |

## Axes

- **Spines**: Top and right spines hidden (via rcParams).
- **Model tick labels**: Use `_short_model_name()` which maps to two-line format (e.g., "Llama\n8B"), `fontsize=9`.
- **Percent axes**: Use `matplotlib.ticker.PercentFormatter(1.0)`.

## Confidence Intervals

- Bootstrap CIs (10,000 resamples by default, 2,000 acceptable for supplementary figures).
- Show as `fill_between` with `alpha=0.2` matching the line color.
- Error bars: use caps where appropriate.

## Statistical Annotations

- Significance stars: `***` for p < 0.001, `**` for p < 0.01, `*` for p < 0.05, `n.s.` otherwise.
- Place above bars/points with bracket lines where comparing groups.

## Output

- Save both PDF and PNG: `fig.savefig(path, bbox_inches='tight', dpi=300)`.
- Main figures go in `paper/figures/`.
- Supplementary figures go in `paper/figures/supplementary/`.

## Legends

- `frameon=False` for all legends.
- Position: `loc="upper right"` or `loc="lower right"` depending on data, or external via `bbox_to_anchor`.
