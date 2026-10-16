"""Plot median net worth of college-degree vs. high-school-or-less families,
and the ratio between them, from data/networth_by_education.csv.

Writes figures/networth_gap.png.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

DATA = Path("data/networth_by_education.csv")
OUT = Path("figures/networth_gap.png")

INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SERIES = {
    "college": ("College degree", "#2a78d6"),
    "hs_or_less": ("High school or less", "#eb6834"),
}


def style(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK_2)
    ax.tick_params(colors=INK_2, length=0, labelsize=9)


def main():
    df = pd.read_csv(DATA)
    wide = df.pivot(index="year", columns="group", values="median_networth") / 1e3
    ratio = wide["college"] / wide["hs_or_less"]
    years = wide.index.to_numpy()

    fig, (top, bot) = plt.subplots(
        2, 1, figsize=(8, 6.5), sharex=True, gridspec_kw={"height_ratios": [2, 1], "hspace": 0.35}
    )

    for group, (label, color) in SERIES.items():
        y = wide[group]
        top.plot(years, y, color=color, linewidth=2, marker="o", markersize=5, label=label)
        top.annotate(f"{label}\n${y.iloc[-1]:,.0f}k", (years[-1], y.iloc[-1]), xytext=(8, 0),
                     textcoords="offset points", va="center", fontsize=9, color=INK)
    top.set_ylim(0, None)
    top.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}k" if v else "$0"))
    top.set_title("Median family net worth, thousands of 2025 dollars",
                  loc="left", fontsize=10, color=INK_2)
    top.legend(loc="upper left", frameon=False, fontsize=9)
    style(top)

    bot.plot(years, ratio, color=INK, linewidth=2, marker="o", markersize=5)
    for i in (0, -1):
        bot.annotate(f"{ratio.iloc[i]:.1f}×", (years[i], ratio.iloc[i]), xytext=(0, 8),
                     textcoords="offset points", ha="center", fontsize=9, color=INK)
    bot.set_ylim(0, ratio.max() * 1.25)
    bot.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}×"))
    bot.set_title("Ratio: college degree ÷ high school or less", loc="left", fontsize=10, color=INK_2)
    bot.set_xticks(years)
    bot.set_xticklabels(years, rotation=0)
    bot.set_xlim(years[0] - 1, years[-1] + 6)
    style(bot)

    fig.suptitle("The wealth gap by education has widened since 1989",
                 x=0.125, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.125, 0.01,
             "Education of the family's reference person. 'High school or less' includes no diploma; "
             "'some college' excluded.\nSource: Federal Reserve Board, Survey of Consumer Finances "
             "summary extracts, 1989–2025.",
             fontsize=7.5, color=INK_2, va="bottom")

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
