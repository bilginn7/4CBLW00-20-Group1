import xgboost as xgb
import pandas as pd
import numpy as np
import re
import warnings
import matplotlib.pyplot as plt
import os
import sys

from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV

warnings.filterwarnings("ignore")

# ------------------------------------------------------------------------
# (1) LOAD DATA
# ------------------------------------------------------------------------
x_train = pd.read_parquet(r"data\X_train.parquet")
x_test  = pd.read_parquet(r"data\X_test.parquet")
y_train = pd.read_parquet(r"data\y_train.parquet")
y_test  = pd.read_parquet(r"data\y_test.parquet")

# ------------------------------------------------------------------------
# (2) CLEAN COLUMN NAMES
# ------------------------------------------------------------------------
def clean_column_names(df):
    df.columns = [re.sub(r"[^\w]", "_", col) for col in df.columns]
    return df

x_train["LSOA code"] = x_train["LSOA code"].astype("category")
x_test["LSOA code"]  = x_test["LSOA code"].astype("category")
x_train = clean_column_names(x_train)
x_test  = clean_column_names(x_test)

# ------------------------------------------------------------------------
# (3) EXTRACT RAW TARGET SERIES (don’t encode!)
# ------------------------------------------------------------------------
target_col   = y_train.columns[0]
y_train_ser  = y_train[target_col].astype(int)   # numeric burglary counts
y_test_ser   = y_test[target_col].astype(int)

# ------------------------------------------------------------------------
# (4) LABEL‐ENCODE “LSOA code” → “LSOA_enc”
# ------------------------------------------------------------------------
le_lsoa = LabelEncoder()
x_train["LSOA_enc"] = le_lsoa.fit_transform(x_train["LSOA_code"].astype(str))
x_test["LSOA_enc"]  = le_lsoa.transform(x_test["LSOA_code"].astype(str))

# ------------------------------------------------------------------------
# (5) FREQUENCY‐ENCODE “LSOA_enc” → “LSOA_freq”
# ------------------------------------------------------------------------
freq_series         = x_train["LSOA_enc"].value_counts(normalize=True)
x_train["LSOA_freq"] = x_train["LSOA_enc"].map(freq_series)
x_test["LSOA_freq"]  = x_test["LSOA_enc"].map(freq_series).fillna(freq_series.mean())

# ------------------------------------------------------------------------
# (6) BUILD LAG FEATURES (“lag1_count” & “lag12_count”) FOR TRAIN & TEST
# ------------------------------------------------------------------------
df_train_full = x_train.copy()
df_train_full["count"] = y_train_ser.values
df_train_full["year_month"] = pd.to_datetime(
    df_train_full["year"].astype(str) + "-" +
    df_train_full["month"].astype(str).str.zfill(2)
)
df_train_full = df_train_full.sort_values(["LSOA_enc", "year_month"]).reset_index(drop=True)

df_train_full["lag1_count"]  = (
    df_train_full.groupby("LSOA_enc")["count"]
    .shift(1).fillna(0).astype(int)
)
df_train_full["lag12_count"] = (
    df_train_full.groupby("LSOA_enc")["count"]
    .shift(12).fillna(0).astype(int)
)

x_train["lag1_count"]  = df_train_full["lag1_count"].values
x_train["lag12_count"] = df_train_full["lag12_count"].values

df_test_full = x_test.copy()
df_test_full["count"] = y_test_ser.values
df_test_full["year_month"] = pd.to_datetime(
    df_test_full["year"].astype(str) + "-" +
    df_test_full["month"].astype(str).str.zfill(2)
)

temp_for_test = pd.concat(
    [
        df_train_full[["LSOA_enc", "year_month", "count"]],
        df_test_full[["LSOA_enc", "year_month", "count"]]
    ],
    axis=0
).sort_values(["LSOA_enc", "year_month"]).reset_index(drop=True)

temp_for_test["lag1_temp"]  = (
    temp_for_test.groupby("LSOA_enc")["count"]
    .shift(1).fillna(0).astype(int)
)
temp_for_test["lag12_temp"] = (
    temp_for_test.groupby("LSOA_enc")["count"]
    .shift(12).fillna(0).astype(int)
)

n_train_rows = len(df_train_full)
n_test_rows  = len(df_test_full)
lagged_test = temp_for_test.iloc[n_train_rows : n_train_rows + n_test_rows].reset_index(drop=True)

x_test["lag1_count"]  = lagged_test["lag1_temp"].values
x_test["lag12_count"] = lagged_test["lag12_temp"].values

del df_train_full, df_test_full, temp_for_test, lagged_test

# ------------------------------------------------------------------------
# (7) VERIFY NEW COLUMNS
# ------------------------------------------------------------------------
required_cols = ["LSOA_enc", "LSOA_freq", "lag1_count", "lag12_count"]
print("\n=== CHECKING FEATURE COLUMNS ===")
print("ARE ALL LSOA‐FEATURES PRESENT IN x_train? ",
      all(col in x_train.columns for col in required_cols))
print("ARE ALL LSOA‐FEATURES PRESENT IN x_test?  ",
      all(col in x_test.columns  for col in required_cols))
print("SAMPLE x_train[required_cols]:")
print(x_train[required_cols].head(6))
print("SAMPLE x_test[required_cols]:")
print(x_test[required_cols].head(6))
print("=================================\n")

# ------------------------------------------------------------------------
# (8) SPLIT INTO TRAIN/VALIDATION BY TIME (last 6 months of training as validation)
# ------------------------------------------------------------------------
df_all_train = x_train.copy()
df_all_train["Target"] = y_train_ser.values
df_all_train["year_month"] = pd.to_datetime(
    df_all_train["year"].astype(str) + "-" +
    df_all_train["month"].astype(str).str.zfill(2)
)
df_all_train = df_all_train.sort_values("year_month").reset_index(drop=True)

cutoff = pd.to_datetime("2024-09")
df_val = df_all_train[df_all_train["year_month"] >= cutoff].copy()
df_tr  = df_all_train[df_all_train["year_month"]  < cutoff].copy()

df_val = df_val.drop(columns=["year_month"])
df_tr  = df_tr.drop(columns=["year_month"])

y_tr   = df_tr["Target"]
X_tr   = df_tr.drop(columns=["Target"])
y_val  = df_val["Target"]
X_val  = df_val.drop(columns=["Target"])

features = [
    "year", "month",
    "LSOA_enc", "LSOA_freq",
    "lag1_count", "lag12_count"
]

# ------------------------------------------------------------------------
# (9) SORT TRAIN BY TIME FOR TimeSeriesSplit
# ------------------------------------------------------------------------
temp = X_tr.copy()
temp["Target"] = y_tr.values
temp["year_month"] = pd.to_datetime(
    temp["year"].astype(str) + "-" +
    temp["month"].astype(str).str.zfill(2)
)
temp = temp.sort_values("year_month").reset_index(drop=True)

y_tr_sorted = temp["Target"].copy()
X_tr_sorted = temp[features].copy()

X_val_sub = X_val[features].copy()
y_val_sub = y_val.copy()

# ------------------------------------------------------------------------
# (10) TimeSeriesSplit FOR HYPERPARAMETER SEARCH
# ------------------------------------------------------------------------
tscv = TimeSeriesSplit(n_splits=3)

# ------------------------------------------------------------------------
# (11) DEFINE GRID OF HYPERPARAMETERS
# ------------------------------------------------------------------------
param_grid = {
    "max_depth":        [4, 6, 8],
    "learning_rate":    [0.01, 0.05, 0.1],
    "subsample":        [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
}

# ------------------------------------------------------------------------
# (12) WRAP XGBRegressor + GRIDSEARCHCV (neg-RMSE) → TIME-SERIES CV
# ------------------------------------------------------------------------
base_model = xgb.XGBRegressor(
    objective      = "reg:squarederror",
    n_estimators   = 1000,
    random_state   = 42
)

grid = GridSearchCV(
    estimator   = base_model,
    param_grid  = param_grid,
    scoring     = "neg_root_mean_squared_error",
    cv          = tscv,
    verbose     = 2,
    n_jobs      = -1
)

# ------------------------------------------------------------------------
# (13) FIT GRIDSEARCHCV ON X_tr_sorted / y_tr_sorted
# ------------------------------------------------------------------------
print("\n=== BEGINNING TIME‐SERIES HYPERPARAMETER SEARCH ===")
grid.fit(X_tr_sorted, y_tr_sorted)
print("=== HYPERPARAMETER SEARCH COMPLETE ===")
print("Best parameters (CV):", grid.best_params_)
print("Best CV ‐ RMSE      :", -grid.best_score_, "\n")

# ------------------------------------------------------------------------
# (14) RETRAIN FINAL MODEL WITH EARLY STOPPING ON Validation Period
# ------------------------------------------------------------------------
best = grid.best_params_
final_model = xgb.XGBRegressor(
    objective        = "reg:squarederror",
    n_estimators     = 1000,
    max_depth        = best["max_depth"],
    learning_rate    = best["learning_rate"],
    subsample        = best["subsample"],
    colsample_bytree = best["colsample_bytree"],
    random_state     = 42
)

print("\n=== BEGINNING FINAL TRAIN WITH EARLY STOPPING ===")
final_model.fit(
    X_tr_sorted, y_tr_sorted,
    eval_set              = [(X_tr_sorted, y_tr_sorted), (X_val_sub, y_val_sub)],
    eval_metric           = "rmse",
    early_stopping_rounds = 50,
    verbose               = 50
)
print("=== FINAL TRAIN COMPLETE ===\n")

# ------------------------------------------------------------------------
# (15) EVALUATE ON x_test → COMPUTE RMSE/MAE & EXACT‐COUNT ACCURACY
# ------------------------------------------------------------------------
X_test_feats   = x_test[features].copy()
y_test_pred_cont = final_model.predict(X_test_feats)
y_test_pred_int  = np.round(y_test_pred_cont).astype(int)

rmse_test = np.sqrt(mean_squared_error(y_test_ser, y_test_pred_cont))
mae_test  = mean_absolute_error(y_test_ser, y_test_pred_cont)

exact_matches = (y_test_pred_int == y_test_ser).sum()
accuracy_int_count = exact_matches / len(y_test_ser)

print("=== TEST SET PERFORMANCE (Mar 2025→…) ===")
print(f"RMSE: {rmse_test:.4f},   MAE: {mae_test:.4f}")
print(f"Exact‐count match accuracy: {accuracy_int_count:.4f}\n")

# Save performance metrics
output_dir = "xgBoost/outputs"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "regular_final_metrics.txt"), "w") as f:
    f.write(f"RMSE: {rmse_test:.4f}, MAE: {mae_test:.4f}, Exact‐count accuracy: {accuracy_int_count:.4f}\n")

# ------------------------------------------------------------------------
# (16) PLOT AVERAGE Predicted vs Actual BURGLARY COUNTS PER MONTH
# ------------------------------------------------------------------------
results_df = x_test.copy()
results_df["Actual"]    = y_test_ser.values
results_df["Predicted"] = y_test_pred_cont

grouped = results_df.groupby(["year", "month", "LSOA_enc"]).agg(
    avg_actual    = ("Actual",    "mean"),
    avg_predicted = ("Predicted", "mean")
).reset_index()

grouped["year_month"] = pd.to_datetime(
    grouped["year"].astype(str) + "-" +
    grouped["month"].astype(str).str.zfill(2)
)

time_avg = grouped.groupby("year_month").agg(
    avg_actual    = ("avg_actual",    "mean"),
    avg_predicted = ("avg_predicted", "mean")
).reset_index()

plt.figure(figsize=(12, 6))
plt.plot(time_avg["year_month"], time_avg["avg_actual"],    label="Actual",    marker="o")
plt.plot(time_avg["year_month"], time_avg["avg_predicted"], label="Predicted", marker="x")
plt.xlabel("Time")
plt.ylabel("Average Burglary Count per LSOA")
plt.title("Average Predicted vs. Actual Burglary Counts (Final XGBRegressor)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(r"xgBoost\outputs\regular‐timeseries_final.png")
plt.show()

# ------------------------------------------------------------------------
# (17) OUTPUT LSOA RISK RATES TO A CSV
#
# Here, we define “risk rate” per LSOA as the average predicted burglary count
# over all test‐rows belonging to that LSOA.
# ------------------------------------------------------------------------
df_risk = x_test[["LSOA_code"]].copy()  # original LSOA string codes
df_risk["predicted_count"] = y_test_pred_cont

# Aggregate by LSOA_code to compute the average predicted count → risk_rate
df_lsoa_risk = (
    df_risk
    .groupby("LSOA_code", as_index=False)
    .agg(risk_rate = pd.NamedAgg(column="predicted_count", aggfunc="mean"))
)

risk_output = os.path.join(output_dir, "lsoa_risk_rates.csv")
df_lsoa_risk.rename(columns={"LSOA_code": "lsoa_id"}).to_csv(risk_output, index=False)
print(f"Wrote LSOA risk‐rates to: {risk_output}")
