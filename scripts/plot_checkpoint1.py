# makes the checkpoint 1 plots from results/final_checkpoint1.csv
import csv
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.transforms import blended_transform_factory

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GROUP_COLOR = {"AI": BLUE, "control": ORANGE}
GROUP_NAME = {"AI": "Llama2 (AI)", "control": "Non-AI control"}
OUT = "results/plots"

plt.rcParams.update({"font.size": 12, "text.color": INK, "axes.labelcolor": INK2, "figure.facecolor": SURFACE})


def short(trace):
    for suffix in (".champsimtrace.xz", ".champsimtrace.gz", ".trace.gz"):
        trace = trace.replace(suffix, "")
    return trace.replace("llama2.c-", "").replace("llama2_7b", "llama2-7B")


rows = list(csv.DictReader(open("results/final_checkpoint1.csv")))
groups = ["AI", "control"]
rows.sort(key=lambda r: (groups.index(r["group"]), -float(r["speedup"])))

# y positions, gap between the two groups
ys, y = [], 0.0
for i, r in enumerate(rows):
    if i and r["group"] != rows[i - 1]["group"]:
        y += 0.9
    ys.append(y)
    y += 1.0
labels = [short(r["trace"]) for r in rows]


def new_axes(title, subtitle):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_yticks(ys, labels)
    ax.tick_params(axis="y", colors=INK, labelsize=12)
    ax.invert_yaxis()
    fig.suptitle(title, x=0.02, y=0.985, ha="left", fontsize=16, fontweight="bold")
    fig.text(0.02, 0.915, subtitle, ha="left", fontsize=11, color=INK2)
    # group labels
    trans = blended_transform_factory(ax.transAxes, ax.transData)
    for g in groups:
        first = next(ys[i] for i, r in enumerate(rows) if r["group"] == g)
        ax.text(-0.005, first - 0.62, GROUP_NAME[g], transform=trans, ha="right", fontsize=11, color=INK2, fontweight="bold")
    return fig, ax


def save(fig, name):
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=200, facecolor=SURFACE)
    plt.close(fig)


def geomean(values):
    return math.exp(sum(map(math.log, values)) / len(values))


os.makedirs(OUT, exist_ok=True)

# 1. speedup
speedup = [float(r["speedup"]) for r in rows]
fig, ax = new_axes("Speedup from prefetching", "IPC with Berti (L1D) + Pythia (L2) vs. no prefetching; SRRIP at the LLC; 50M warmup + 200M instructions")
ax.barh(ys, speedup, height=0.62, color=[GROUP_COLOR[r["group"]] for r in rows], edgecolor=SURFACE, linewidth=2)
ax.axvline(1.0, color=INK2, linewidth=1, linestyle="--")
ax.text(1.02, ys[0] - 0.62, "1.0× = no change", ha="left", va="center", fontsize=10, color=INK2)
for yv, v in zip(ys, speedup):
    ax.text(v + 0.03, yv, f"{v:.2f}×", va="center", fontsize=11, color=INK)
ax.set_xlim(0, max(speedup) * 1.15)
ax.set_xlabel("Speedup (IPC ratio)")
ax.legend(handles=[Patch(color=GROUP_COLOR[g], label=f"{GROUP_NAME[g]}: geomean {geomean([s for s, r in zip(speedup, rows) if r['group'] == g]):.2f}×")
                   for g in groups], loc="lower right", frameon=False, fontsize=11)
save(fig, "1_speedup")

# 2. prefetch fate
used_upper = [100 * float(r["frac_used_upper_only"]) for r in rows]
used_llc = [100 * float(r["frac_used_llc"]) for r in rows]
unused = [100 * float(r["frac_unused"]) for r in rows]
fig, ax = new_axes("Where prefetched lines in the LLC get used",
                   f"Fate of each prefetch fill in the LLC, at eviction. Used from the LLC copy: ≤{max(used_llc):.1f}% on every trace")
kw = dict(height=0.62, edgecolor=SURFACE, linewidth=2)
ax.barh(ys, used_upper, color=BLUE, label="Used in L1D/L2 only", **kw)
ax.barh(ys, used_llc, left=used_upper, color=AQUA, label="Used from the LLC", **kw)
ax.barh(ys, unused, left=[a + b for a, b in zip(used_upper, used_llc)], color=ORANGE, label="Never used (pollution)", **kw)
for yv, v in zip(ys, unused):
    ax.text(101.5, yv, f"{v:.0f}% unused" if v >= 1 else f"{v:.1f}% unused", va="center", fontsize=11, color=INK)
ax.set_xlim(0, 100)
ax.set_xlabel("Share of LLC prefetch fills (%)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False, fontsize=11)
save(fig, "2_prefetch_fate")

# 3. harmful evictions
harmful = [float(r["harmful_pki"]) for r in rows]
fig, ax = new_axes("Harmful evictions caused by prefetching",
                   "Lines evicted by a prefetch fill and demanded again before 12 more evictions in that set, per 1000 instructions")
ax.barh(ys, harmful, height=0.62, color=[GROUP_COLOR[r["group"]] for r in rows], edgecolor=SURFACE, linewidth=2)
for yv, v in zip(ys, harmful):
    ax.text(v + max(harmful) * 0.01, yv, f"{v:.3g}", va="center", fontsize=11, color=INK)
ax.set_xlim(0, max(harmful) * 1.12)
ax.set_xlabel("Harmful evictions per 1000 instructions")
ax.legend(handles=[Patch(color=GROUP_COLOR[g], label=GROUP_NAME[g]) for g in groups], loc="upper right", frameon=False, fontsize=11)
save(fig, "3_harmful_evictions")

print(f"wrote 3 plots (PNG + PDF) to {OUT}/")
