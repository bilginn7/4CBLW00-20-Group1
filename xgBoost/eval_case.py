import os, shap
import numpy as np, pandas as pd, matplotlib.pyplot as plt


# ──────────────── USER SETTINGS ──────────────── #
XTEST_PATH   = "../data/X_test.parquet"     # Same file used earlier
SHAP_DIR     = "shap_outputs"               # Where the .npy & .txt live
OUT_PNG      = "shap_single_case.png"       # Name of the plot file
CASE_INDEX   = 0                            # 0-based row index you want to inspect
TOP_N        = 8                            # How many strongest ± features to list
# ─────────────────────────────────────────────── #

def main() -> None:
    # 1. Load SHAP matrix and base value
    shap_values = np.load(os.path.join(SHAP_DIR, "shap_values.npy"))
    with open(os.path.join(SHAP_DIR, "base_value.txt")) as f:
        base_value = float(f.read().strip())
    print(f"[✓] Loaded SHAP matrix: {shap_values.shape}, base value: {base_value:.4f}")

    # 2. Load the test set and fetch the requested row
    X_test = pd.read_parquet(XTEST_PATH)
    if CASE_INDEX < 0 or CASE_INDEX >= len(X_test):
        raise IndexError(f"CASE_INDEX {CASE_INDEX} is out of bounds (0…{len(X_test)-1})")
    x_row     = X_test.iloc[CASE_INDEX]
    shap_row  = shap_values[CASE_INDEX]

    # 3. Compute the model prediction for this row
    prediction = base_value + shap_row.sum()
    print(f"\nCase #{CASE_INDEX} prediction: {prediction:.4f}")
    print(f"    base value: {base_value:.4f}")
    print(f"    sum(SHAP): {shap_row.sum():.4f}")

    # 4. Display strongest positive / negative contributors
    contribs = pd.Series(shap_row, index=X_test.columns)
    pos = contribs.sort_values(ascending=False).head(TOP_N)
    neg = contribs.sort_values(ascending=True).head(TOP_N)
    print(f"\nTop {TOP_N} positive contributions:")
    for feat, val in pos.items():
        print(f"  + {feat:<30} {val:+.4f}")
    print(f"\nTop {TOP_N} negative contributions:")
    for feat, val in neg.items():
        print(f"  - {feat:<30} {val:+.4f}")

    # 5. Build the SHAP Explanation object for plotting
    exp = shap.Explanation(
        values        = shap_row,
        base_values   = base_value,
        data          = x_row,
        feature_names = X_test.columns
    )

    # 6. Create the waterfall plot (no automatic display)
    plt.figure(figsize=(10, 6))
    shap.plots.waterfall(exp, max_display=14, show=False)
    ax = plt.gca()

    for txt in ax.texts:
        if txt.get_text().lstrip().startswith("="):
            txt.set_visible(False)

    ax.set_title(
        f"Case #{CASE_INDEX}  |  Prediction = {prediction:.3f}   (Base = {base_value:.3f})",
        fontweight="bold",
        pad=20,
        fontsize=13
    )

    plt.subplots_adjust(top=0.88)

    # 7. Save & close
    out_path = os.path.join(SHAP_DIR, OUT_PNG)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\n[✓] Waterfall plot saved to: {out_path}")


if __name__ == "__main__":
    main()