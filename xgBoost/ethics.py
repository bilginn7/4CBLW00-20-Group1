import os, shap
import numpy as np, pandas as pd, xgboost as xgb, matplotlib.pyplot as plt


# ──────────────── USER SETTINGS ──────────────── #
MODEL_PATH   = "final_xgboost_model.json"   # booster file
XTEST_PATH   = "../data/X_test.parquet"     # test set
CAT_COLUMN   = "LSOA code"                  # categorical feature name
OUT_DIR      = "shap_outputs"               # output folder
SAMPLE_ROWS  = None                         # e.g. 5000, or None for all rows
# ─────────────────────────────────────────────── #

def main() -> None:
    # 1. Load the trained model
    booster = xgb.Booster()
    booster.load_model(MODEL_PATH)
    print(f"[✓] Loaded model: {MODEL_PATH}")

    # 2. Read the test data
    X_test = pd.read_parquet(XTEST_PATH)
    print(f"[✓] Loaded X_test with shape {X_test.shape}")

    # Optional down-sample for large datasets
    if SAMPLE_ROWS is not None and SAMPLE_ROWS < len(X_test):
        X_test = X_test.sample(SAMPLE_ROWS, random_state=42).reset_index(drop=True)
        print(f"[i] Using a random sample of {len(X_test)} rows")

    # 3. Ensure the categorical column is really categorical
    if CAT_COLUMN not in X_test.columns:
        raise KeyError(f"Column '{CAT_COLUMN}' not found in X_test")
    if X_test[CAT_COLUMN].dtype != "category":
        X_test[CAT_COLUMN] = X_test[CAT_COLUMN].astype("category")
        print(f"[✓] Converted '{CAT_COLUMN}' to pandas.Categorical")

    # 4. Build a DMatrix with enable_categorical=True
    dmatrix = xgb.DMatrix(
        X_test,
        enable_categorical=True,
        feature_names=list(X_test.columns)
    )

    # 5. Ask XGBoost itself for SHAP contributions
    print("[i] Computing SHAP values via booster.predict(..., pred_contribs=True)")
    contrib = booster.predict(dmatrix, pred_contribs=True)

    # Split into per-feature shap_values and the bias term
    shap_values = contrib[:, :-1]          # all but last column
    base_value  = contrib[0,  -1]          # bias (same for every row)

    # 6. Save everything to disk
    os.makedirs(OUT_DIR, exist_ok=True)
    np.save(os.path.join(OUT_DIR, "shap_values.npy"), shap_values)
    with open(os.path.join(OUT_DIR, "base_value.txt"), "w") as f:
        f.write(str(base_value))

    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X_test, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "shap_summary.png"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[✓] All SHAP outputs written to: {os.path.abspath(OUT_DIR)}")


if __name__ == "__main__":
    main()
