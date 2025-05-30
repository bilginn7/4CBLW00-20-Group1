import lightgbm as lgb
import pandas as pd
from sklearn.metrics import accuracy_score
import re
import warnings
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error
import numpy as np

warnings.filterwarnings("ignore")

x_test = pd.read_parquet("../data/X_test.parquet")
x_train = pd.read_parquet("../data/X_train.parquet")
y_test = pd.read_parquet("../data/y_test.parquet")
y_train = pd.read_parquet("../data/y_train.parquet")

print(x_test.info())

def clean_column_names(df):
    df.columns = [re.sub(r'[^\w]', '_', col) for col in df.columns]
    return df

x_train["LSOA code"] = x_train["LSOA code"].astype("category")
x_test["LSOA code"] = x_test["LSOA code"].astype("category")

x_train = clean_column_names(x_train)
x_test = clean_column_names(x_test)

# regex to catch any character other than letters, numbers, or underscore
bad_pattern = re.compile(r'[^\w]')

bad_cols = [col for col in x_train.columns if bad_pattern.search(col)]
print("Columns with problematic characters:", bad_cols)

target_col = y_train.columns[0]
y_train_ser = y_train[target_col]
y_test_ser  = y_test[target_col]

clf = lgb.LGBMClassifier(categorical_feature=["LSOA_code"])
clf.fit(x_train, y_train.values.ravel())

y_pred=clf.predict(x_test)

accuracy=accuracy_score(y_pred, y_test)
print('LightGBM Model accuracy score: {0:0.4f}'.format(accuracy_score(y_test, y_pred)))

y_pred_train = clf.predict(x_train)
print('Training-set accuracy score: {0:0.4f}'. format(accuracy_score(y_train, y_pred_train)))

print('Training set score: {:.4f}'.format(clf.score(x_train, y_train)))

print('Test set score: {:.4f}'.format(clf.score(x_test, y_test)))

from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y_test, y_pred)
print('Confusion matrix\n\n', cm)
print('\nTrue Positives(TP) = ', cm[0,0])
print('\nTrue Negatives(TN) = ', cm[1,1])
print('\nFalse Positives(FP) = ', cm[0,1])
print('\nFalse Negatives(FN) = ', cm[1,0])

from sklearn.metrics import classification_report
print(classification_report(y_test, y_pred))

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
