import pandas as pd
import numpy as np
import re
import warnings
import os
import sys

import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import RandomizedSearchCV, KFold
from sklearn.metrics import accuracy_score

warnings.filterwarnings("ignore")

# --- Utility functions ---

def load_data(x_train_path, x_test_path, y_train_path, y_test_path):
    """
    Load parquet datasets from given paths. Exits if any file is missing.
    """
    for path in [x_train_path, x_test_path, y_train_path, y_test_path]:
        if not os.path.exists(path):
            print(f"ERROR: File not found: {path}")
            sys.exit(1)
    x_train = pd.read_parquet(x_train_path)
    x_test  = pd.read_parquet(x_test_path)
    y_train = pd.read_parquet(y_train_path)
    y_test  = pd.read_parquet(y_test_path)
    return x_train, x_test, y_train, y_test

def clean_cols(df):
    """
    Replace any non‐alphanumeric characters in column names with underscores.
    """
    df.columns = [re.sub(r'[^\w]', '_', c) for c in df.columns]
    return df

# --- 1. Load & preprocess data (with path‐existence checks) ---

# Use forward slashes or raw strings to avoid accidental backslash‐escaping
x_train_path = r"data/X_train.parquet"
x_test_path  = r"data/X_test.parquet"
y_train_path = r"data/y_train.parquet"
y_test_path  = r"data/y_test.parquet"

x_train, x_test, y_train, y_test = load_data(
    x_train_path, x_test_path, y_train_path, y_test_path
)

print("x_train shape:", x_train.shape)
print("x_test shape: ", x_test.shape)
print("y_train shape:", y_train.shape)
print("y_test shape: ", y_test.shape)
print()

# Make sure y_train / y_test each have exactly one column
if y_train.shape[1] != 1 or y_test.shape[1] != 1:
    print("ERROR: y_train or y_test has more than one column.")
    sys.exit(1)

# If there are duplicate indices (unlikely), warn:
if x_train.index.duplicated().any() or x_test.index.duplicated().any():
    print("WARNING: Duplicate indices found in X data.")

# --- 1a. Clean column names and mark "LSOA code" as categorical first ---

x_train["LSOA code"] = x_train["LSOA code"].astype("category")
x_test ["LSOA code"] = x_test["LSOA code"].astype("category")

# Now clean every column name (replace non‐word chars with '_')
x_train = clean_cols(x_train)
x_test  = clean_cols(x_test)

# Check if any columns still have bad characters:
bad_pattern = re.compile(r'[^\w]')
bad_cols = [c for c in x_train.columns if bad_pattern.search(c)]
if bad_cols:
    print("WARNING: Columns with problematic characters still exist:", bad_cols)

# --- 1b. Extract and encode the target column ---

target_col = y_train.columns[0]
y_train_ser = y_train[target_col]
y_test_ser  = y_test[target_col]

# Make sure there are no missing values in target
if y_train_ser.isna().any() or y_test_ser.isna().any():
    print("ERROR: Missing values found in target. Please impute or drop missing targets.")
    sys.exit(1)

# Label‐encode target to 0..(n_classes−1)
le_y      = LabelEncoder()
y_train_e = le_y.fit_transform(y_train_ser)
y_test_e  = le_y.transform(y_test_ser)

num_classes = len(le_y.classes_)
print(f"Number of unique classes in target: {num_classes}")
print("Classes (original‐labels):", le_y.classes_)
print()

# Print training class‐distribution
class_counts = np.bincount(y_train_e)
print("Class distribution in training data:")
for idx, cnt in enumerate(class_counts):
    original_label = le_y.inverse_transform([idx])[0]
    print(f"  Class index {idx} (original={original_label}): {cnt} samples")
print()

if np.any(class_counts < 3):
    print("WARNING: Some classes have fewer than 3 samples. Using plain KFold (instead of stratified) may result in folds missing those classes entirely.")
    print()

# --- 1c. Encode the "LSOA_code" feature (LabelEncoder) ---

le_lsoa = LabelEncoder()
x_train["LSOA_code"] = le_lsoa.fit_transform(x_train["LSOA_code"].astype(str))
x_test ["LSOA_code"] = le_lsoa.transform(x_test["LSOA_code"].astype(str))

# Check for missing values in X_train (XGBoost can handle NaNs, but at least warn)
missing_per_col = x_train.isna().sum()
if missing_per_col.any():
    print("Warning: Missing values in features (train):")
    print(missing_per_col[missing_per_col > 0])
    print()

# --- 2. Determine n_estimators via xgb.cv (with fixed num_class) ---

dtrain = xgb.DMatrix(x_train, label=y_train_e)

xgb_params = {
    "objective":   "multi:softprob",
    "num_class":    num_classes,
    "eval_metric": "mlogloss",
}

print("Starting xgb.cv to find optimal number of boosting rounds (n_estimators)...")
cv_results = xgb.cv(
    params                = xgb_params,
    dtrain                = dtrain,
    num_boost_round       = 1000,
    nfold                 = 3,
    stratified            = False,           # because some classes are rare
    early_stopping_rounds = 50,
    seed                  = 42,
    verbose_eval          = False
)

best_nrounds = cv_results.shape[0]
print(f"Best number of boosting rounds (n_estimators): {best_nrounds}")
print()

# --- 3. Define hyper‐parameter grid/distributions for RandomizedSearchCV ---

param_dist = {
    "max_depth":        [3, 5, 7, 9, 12],
    "learning_rate":    [0.01, 0.03, 0.05, 0.1, 0.2],
    "subsample":        [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
    "gamma":            [0, 1, 5, 10],
    "reg_alpha":        [0, 0.1, 1, 5],
    "reg_lambda":       [1, 5, 10, 50],
}

# --- 4. RandomizedSearchCV using KFold to avoid missing‐class folds ---

kf = KFold(n_splits=3, shuffle=True, random_state=42)

search_clf = RandomizedSearchCV(
    estimator=xgb.XGBClassifier(
        objective         = "multi:softprob",
        num_class         = num_classes,
        use_label_encoder = False,
        eval_metric       = "mlogloss",
        n_estimators      = best_nrounds,
        verbosity         = 0
    ),
    param_distributions = param_dist,
    n_iter       = 25,
    scoring      = "accuracy",
    cv           = kf,
    verbose      = 2,
    random_state = 42,
    n_jobs       = -1,
    error_score  = "raise"  # Immediately show any fitting errors
)

print("Starting hyperparameter search (RandomizedSearchCV)...")
try:
    search_clf.fit(x_train, y_train_e)
except Exception as e:
    print("ERROR: RandomizedSearchCV.fit() failed with the following exception:")
    print(e)
    sys.exit(1)

print()
print("Best hyper-parameters found by RandomizedSearchCV:")
print(search_clf.best_params_)
print("Best CV accuracy:", search_clf.best_score_)
print()

# --- 5. Evaluate the tuned model on the held‐out test set ---

best_model = search_clf.best_estimator_
y_pred_e   = best_model.predict(x_test)
test_acc   = accuracy_score(y_test_e, y_pred_e)
print(f"Tuned test accuracy: {test_acc:.4f}")

# (Optional) Save results to disk
output_dir = "xgBoost/outputs"
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, "tuned_accuracies.txt"), "w") as f:
    f.write(f"Tuned test accuracy: {test_acc:.4f}\n")
