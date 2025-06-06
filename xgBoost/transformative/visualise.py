import pandas as pd
import matplotlib.pyplot as plt
import os

# ─── USER‐EDITABLE SETTINGS ────────────────────────────────────────────────────
# 1) This must point to the daily‐output CSV from our last script (i.e. the file named
#    officer_assignment_daily_<YYYY-MM>.csv). In our example, TARGET_MONTH = "2025-04",
#    so the daily file is:
INPUT_CSV_DAILY = r"xgBoost/outputs/officer_assignment_daily_2025-07.csv"

# 2) Make sure the folder below matches where that CSV actually lives.
OUTPUT_DIR = "xgBoost/outputs"

# 3) Change these if you decide to use a different target‐month in transformative.py:
TARGET_MONTH = "2025-07"
# ──────────────────────────────────────────────────────────────────────────────

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─── (1) Load the “daily” CSV ──────────────────────────────────────────────────
try:
    df = pd.read_csv(INPUT_CSV_DAILY)
except FileNotFoundError:
    print(f"Error: Cannot find '{INPUT_CSV_DAILY}'.\n"
          f"Please make sure you ran transformative.py with TARGET_MONTH = '{TARGET_MONTH}',\n"
          f"and that the file is named exactly 'officer_assignment_daily_{TARGET_MONTH}.csv' in {OUTPUT_DIR}.")
    raise


# ─── (2) Aggregate by borough ──────────────────────────────────────────────────
# Sum up all officers_assigned per borough, and compute the mean prediction_score.
grouped = (
    df.groupby("borough_name")
      .agg(
          total_officers=("officers_assigned", "sum"),
          avg_prediction_score=("prediction_score", "mean")
      )
      .reset_index()
)

# Sort by total_officers descending so that our bar charts share the same borough order.
grouped = grouped.sort_values(by="total_officers", ascending=False).reset_index(drop=True)


# ─── (3) BAR CHART: Total Officers per Borough ────────────────────────────────
fig1, ax1 = plt.subplots(figsize=(12, 7))
bars1 = ax1.bar(
    grouped["borough_name"],
    grouped["total_officers"],
    color="tab:orange",
    edgecolor="black",
    alpha=0.8
)

# Add annotations on top of each bar
for bar in bars1:
    height = bar.get_height()
    ax1.annotate(
        f"{int(height)}",
        xy=(bar.get_x() + bar.get_width() / 2, height),
        xytext=(0, 4),               # 4 points vertical offset
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9
    )

ax1.set_ylabel("Total Officers Assigned (per day)", fontsize=12)
ax1.set_xlabel("Borough", fontsize=12)
ax1.set_title(f"Total Officers Assigned per Borough ({TARGET_MONTH})", fontsize=14)

# Rotate X‐labels for readability
ax1.set_xticklabels(grouped["borough_name"], rotation=90, fontsize=9)
ax1.grid(axis="y", linestyle="--", alpha=0.5)

plt.tight_layout()
file1 = os.path.join(OUTPUT_DIR, f"total_officers_per_borough_{TARGET_MONTH}.png")
fig1.savefig(file1, dpi=300)
plt.close(fig1)


# ─── (4) BAR CHART: Average Prediction Score per Borough ─────────────────────
fig2, ax2 = plt.subplots(figsize=(12, 7))
bars2 = ax2.bar(
    grouped["borough_name"],
    grouped["avg_prediction_score"],
    color="tab:blue",
    edgecolor="black",
    alpha=0.8
)

# Annotate each bar with its exact average score (rounded to, say, two decimals)
for bar in bars2:
    height = bar.get_height()
    ax2.annotate(
        f"{height:.2f}",
        xy=(bar.get_x() + bar.get_width() / 2, height),
        xytext=(0, 4),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9
    )

ax2.set_ylabel("Average Prediction Score", fontsize=12)
ax2.set_xlabel("Borough", fontsize=12)
ax2.set_title(f"Average Prediction Score per Borough ({TARGET_MONTH})", fontsize=14)

ax2.set_xticklabels(grouped["borough_name"], rotation=90, fontsize=9)
ax2.grid(axis="y", linestyle="--", alpha=0.5)

plt.tight_layout()
file2 = os.path.join(OUTPUT_DIR, f"avg_prediction_score_per_borough_{TARGET_MONTH}.png")
fig2.savefig(file2, dpi=300)
plt.close(fig2)


# ─── (5) SCATTER PLOT: Total Officers vs. Avg. Prediction Score ─────────────
fig3, ax3 = plt.subplots(figsize=(10, 6))
scatter = ax3.scatter(
    grouped["avg_prediction_score"],
    grouped["total_officers"],
    s=80,
    color="tab:green",
    edgecolor="black",
    alpha=0.7
)

# Label each point with its borough name
for i, row in grouped.iterrows():
    ax3.annotate(
        row["borough_name"],
        (row["avg_prediction_score"], row["total_officers"]),
        textcoords="offset points",
        xytext=(5, 5),
        ha="left",
        fontsize=8
    )

ax3.set_xlabel("Average Prediction Score", fontsize=12)
ax3.set_ylabel("Total Officers Assigned (per day)", fontsize=12)
ax3.set_title(f"Total Officers vs. Average Prediction Score by Borough ({TARGET_MONTH})", fontsize=14)
ax3.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
file3 = os.path.join(OUTPUT_DIR, f"officers_vs_score_scatter_{TARGET_MONTH}.png")
fig3.savefig(file3, dpi=300)
plt.close(fig3)


# ─── (6) Print out where the files are ─────────────────────────────────────────
print("Visualizations saved to:")
print(f"  1) {file1}")
print(f"  2) {file2}")
print(f"  3) {file3}")
