import lightgbm as lgb
import pandas as pd
import numpy as np
import re
import warnings
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error

warnings.filterwarnings("ignore")

x_train = pd.read_parquet("../data/X_train.parquet")
x_test  = pd.read_parquet("../data/X_test.parquet")
y_train = pd.read_parquet("../data/y_train.parquet")
y_test  = pd.read_parquet("../data/y_test.parquet")

def clean_column_names(df):
    df.columns = [re.sub(r'[^\w]', '_', col) for col in df.columns]
    return df

x_train = clean_column_names(x_train)
x_test  = clean_column_names(x_test)

x_train["LSOA_code"] = x_train["LSOA_code"].astype("category")
x_test["LSOA_code"]  = x_test["LSOA_code"].astype("category")

target_col = y_train.columns[0]
y_train_ser = y_train[target_col]
y_test_ser  = y_test[target_col]

reg = lgb.LGBMRegressor(
    objective='poisson',
    metric=['rmse', 'mae'],
    categorical_feature=['LSOA_code'],
    random_state=42
)

reg.fit(
    x_train, y_train_ser,
    eval_set=[(x_train, y_train_ser), (x_test, y_test_ser)],
    eval_names=['train','test'],
)

y_pred = reg.predict(x_test)

rmse = np.sqrt(mean_squared_error(y_test_ser, y_pred))
mae  = mean_absolute_error(y_test_ser, y_pred)
print(f"Test RMSE: {rmse:.4f}")
print(f"Test MAE:  {mae:.4f}")

results_df = x_test.copy()
results_df["Actual"] = y_test_ser.values
results_df["Predicted"] = y_pred

grouped = results_df.groupby(["year", "month", "LSOA_code"]).agg(
    avg_actual=("Actual", "mean"),
    avg_predicted=("Predicted", "mean")
).reset_index()

grouped["year_month"] = pd.to_datetime(grouped["year"].astype(str) + "-" + grouped["month"].astype(str).str.zfill(2))

time_avg = grouped.groupby("year_month").agg(
    avg_actual=("avg_actual", "mean"),
    avg_predicted=("avg_predicted", "mean")
).reset_index()

plt.figure(figsize=(12, 6))
plt.plot(time_avg["year_month"], time_avg["avg_actual"], label="Actual", marker='o')
plt.plot(time_avg["year_month"], time_avg["avg_predicted"], label="Predicted", marker='x')
plt.xlabel("Time")
plt.ylabel("Average Burglary Count per LSOA")
plt.title("Average Predicted vs Actual Burglary Counts across all LSOAs")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
