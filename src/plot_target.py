"""Draw the README chart: official vs policy-adjusted core-core inflation, 1995 onward.

Run from the project folder:
    python src/plot_target.py
Output:
    results/figures/core_core_inflation_light.png
"""

import matplotlib

matplotlib.use("Agg")  # save to file without opening a window
import matplotlib.pyplot as plt
import pandas as pd

from build_target import ROOT, build_target, read_official

OUT = ROOT / "results" / "figures" / "core_core_inflation_light.png"


def main():
    # The two series: official from 1995, our adjusted target from 2006
    official = read_official().loc["1995-01":]
    target = build_target()["target"]
    official.index = official.index.to_timestamp()  # monthly periods -> dates, for plotting
    target.index = target.index.to_timestamp()
    last = target.index[-1]

    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    ax.plot(official, color="gray", label="Official core-core CPI (unadjusted)")
    ax.plot(target, color="tab:blue", linewidth=2,
            label="Adjusted for tax rises and other government measures (this project)")
    ax.axhline(2, color="black", linestyle="--", linewidth=1, label="2% (Bank of Japan target)")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvspan(pd.Timestamp("2022-01-01"), last, color="gray", alpha=0.12, label="Since 2022")  # shaded period

    # Short labels for the main shocks: (month on the grey line, label, where the label goes)
    events = [
        ("1997-04", "1997: consumption tax rise (3% to 5%)", "2000-01", 3.6),
        ("2008-10", "2008: oil and food price spike,\nthen global financial crisis", "2004-06", 2.6),
        ("2014-04", "2014: consumption tax rise (5% to 8%)", "2010-06", 3.6),
        ("2019-10", "2019: consumption tax rise (8% to 10%)", "2018-06", 1.7),
        ("2021-04", "2021: mobile-phone fee cut", "2016-06", -1.3),
    ]
    for month, label, text_month, text_y in events:
        x = pd.Timestamp(month)
        ax.annotate(label, xy=(x, official[x]), xytext=(pd.Timestamp(text_month), text_y),
                    fontsize=8, ha="center", va="center",
                    arrowprops=dict(arrowstyle="-", color="gray", linewidth=0.8))

    ax.set_title(f"Japan's core-core inflation, 1995-{last.year} (% change on a year earlier)")
    ax.set_ylabel("%")
    ax.margins(x=0.01)  # no empty space at the left and right ends
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False, fontsize=9)  # below the chart
    fig.text(0.01, 0.01, f"Source: Statistics Bureau of Japan; Bank of Japan. Adjusted series: author's calculations. "
             f"Latest: {last:%b %Y}.", fontsize=7.5, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

