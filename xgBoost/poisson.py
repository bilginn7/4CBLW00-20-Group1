import xgboost as xgb
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error
import re
import warnings
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# --- load data
x_train = pd.read_parquet("data\X_train.parquet")
x_test  = pd.read_parquet("data\X_test.parquet")
y_train = pd.read_parquet("data\y_train.parquet")
y_test  = pd.read_parquet("data\y_test.parquet")

# --- cleanup
def clean_column_names(df):
    df.columns = [re.sub(r'[^0-9a-zA-Z_]+', '_', c) for c in df.columns]
    return df

x_train = clean_column_names(x_train)
x_test  = clean_column_names(x_test)

bad_pattern = re.compile(r'[^0-9a-zA-Z_]')
print("Problematic columns:", [c for c in x_train.columns if bad_pattern.search(c)])

# --- prepare features & target
target_col = y_train.columns[0]
y_train_ser = y_train[target_col]
y_test_ser  = y_test[target_col]

le = LabelEncoder()
x_train['LSOA_code'] = le.fit_transform(x_train['LSOA_code'].astype(str))
x_test['LSOA_code']  = le.transform(x_test['LSOA_code'].astype(str))

# --- train XGBRegressor with Poisson objective
reg = xgb.XGBRegressor(objective='count:poisson', eval_metric='rmse')
reg.fit(x_train, y_train_ser)

# --- predictions & errors
y_pred = reg.predict(x_test)
rmse = mean_squared_error(y_test_ser, y_pred, squared=False)
mae  = mean_absolute_error(y_test_ser, y_pred)

print(f"Poisson RMSE: {rmse:.4f}")
print(f"Poisson MAE:  {mae:.4f}")

# save accuracy metrics
with open("outputs/accuracies.txt", "a") as f:
    f.write(f"Poisson RMSE: {rmse:.4f}\n")
    f.write(f"Poisson MAE:  {mae:.4f}\n")

# --- time-series plot
df_test = x_test.copy()
df_test['actual']    = y_test_ser.values
df_test['predicted'] = y_pred
df_test['year']      = pd.to_datetime(df_test['date_column']).dt.year
df_test['month']     = pd.to_datetime(df_test['date_column']).dt.month

grouped = df_test.groupby(['year','month']).agg(
    avg_actual   = ("actual",    "mean"),
    avg_predicted=("predicted", "mean")
).reset_index()
grouped["year_month"] = pd.to_datetime(grouped.year.astype(str) + "-" +
                                       grouped.month.astype(str).str.zfill(2))

plt.figure(figsize=(12, 6))
plt.plot(grouped.year_month, grouped.avg_actual,    label="Actual",    marker='o')
plt.plot(grouped.year_month, grouped.avg_predicted, label="Predicted", marker='x')
plt.xlabel("Time")
plt.ylabel("Average Count per LSOA")
plt.title("Poisson: Avg Predicted vs Actual Counts")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("outputs/poisson-timeseries.png")
plt.show()
