from __future__ import annotations
from pathlib import Path
from typing import Tuple, Dict, Any, Callable, List

import optuna, lightgbm as lgb
import numpy as np, pandas as pd, polars as pl
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

EARLY_STOP_ROUNDS = 10

# ----------  Feature-name sanitiser (unchanged) ---------------------------
def sanitize_feature_names(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    safe_cols = [f"f{i}" for i in range(df.shape[1])]
    df_safe = df.copy()
    df_safe.columns = safe_cols
    return df_safe, list(df.columns)

# ----------  I/O  ---------------------------------------------------------
def read_parquet(p: str | Path) -> pl.DataFrame: return pl.read_parquet(p)

def load_splits(xtr, ytr, xte, yte) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, List[str]]:
    Xtr_raw = read_parquet(xtr).with_columns(pl.col("LSOA code").cast(pl.Categorical)).to_pandas()
    Xte_raw = read_parquet(xte).with_columns(pl.col("LSOA code").cast(pl.Categorical)).to_pandas()
    Xtr, orig = sanitize_feature_names(Xtr_raw)
    Xte, _    = sanitize_feature_names(Xte_raw)
    ytr_arr   = read_parquet(ytr).to_numpy().ravel()
    yte_arr   = read_parquet(yte).to_numpy().ravel()
    return Xtr, Xte, ytr_arr, yte_arr, orig

# ----------  One-objective train & RMSE -----------------------------------
def _fit_rmse(params: Dict[str, Any], objective: str,
              Xtr, ytr, Xval, yval) -> float:
    params = params.copy(); params["objective"] = objective
    model = lgb.LGBMRegressor(**params)
    model.fit(
        Xtr, ytr,
        eval_set=[(Xval, yval)], eval_metric="rmse",
        callbacks=[lgb.early_stopping(EARLY_STOP_ROUNDS, first_metric_only=True, verbose=False),
                   lgb.log_evaluation(0)]
    )
    preds = model.predict(Xval, num_iteration=model.best_iteration_ or model.n_estimators)
    return np.sqrt(mean_squared_error(yval, preds))

# ----------  Optuna objective ---------------------------------------------
def build_objective(Xtr, ytr, Xval, yval):
    def obj(trial: optuna.trial.Trial) -> float:
        params = {
            "metric": "rmse",
            "boosting_type": "gbdt",
            "device_type": "cpu",
            "verbosity": -1,
            "random_state": 42,
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 0.5, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 16, 512),
            "max_depth": trial.suggest_categorical("max_depth", [-1] + list(range(2, 16))),
            "subsample": trial.suggest_float("subsample", 0.4, 1.0), "subsample_freq": 1,
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "lambda_l1": trial.suggest_float("lambda_l1", 1e-4, 10, log=True),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-4, 10, log=True),
        }
        rmse = {obj: _fit_rmse(params, obj, Xtr, ytr, Xval, yval)
                for obj in ("regression", "poisson")}
        best_obj = min(rmse, key=rmse.get)
        trial.set_user_attr("best_objective_for_this_trial", best_obj)
        return rmse[best_obj]
    return obj

def run_hpo(obj, n=50):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    st = optuna.create_study(direction="minimize")
    st.optimize(obj, n_trials=n, show_progress_bar=True)
    bp = st.best_params.copy()
    bp["objective"] = st.best_trial.user_attrs["best_objective_for_this_trial"]
    return bp

# ----------  Final train / eval / save ------------------------------------
def train_final(params, Xtr, ytr, Xval, yval):
    model = lgb.LGBMRegressor(**params)
    model.fit(Xtr, ytr,
              eval_set=[(Xval, yval)], eval_metric="rmse",
              callbacks=[lgb.early_stopping(EARLY_STOP_ROUNDS, first_metric_only=True, verbose=False),
                         lgb.log_evaluation(0)])
    return model

def eval_model(m, Xte, yte):
    p = m.predict(Xte, num_iteration=m.best_iteration_ or m.n_estimators)
    rmse = np.sqrt(mean_squared_error(yte, p))
    mae  = mean_absolute_error(yte, p)
    r2   = r2_score(yte, p)
    print(f"{'MAE:':<6}{mae:.4f}\n{'RMSE:':<6}{rmse:.4f}\n{'R2:':<6}{r2:.4f}")

def save(m, path): m.booster_.save_model(str(path)); print("Model saved:", path)

# ----------  Main ----------------------------------------------------------
if __name__ == "__main__":
    Xtr_p, Ytr_p = "../data/X_train.parquet", "../data/y_train.parquet"
    Xte_p, Yte_p = "../data/X_test.parquet", "../data/y_test.parquet"
    model_path   = "final_lightgbm_model.txt"

    Xtrain, Xtest, ytrain, ytest, orig_names = load_splits(Xtr_p, Ytr_p, Xte_p, Yte_p)
    X_tr, X_val, y_tr, y_val = train_test_split(Xtrain, ytrain, test_size=0.2, random_state=42)

    best = run_hpo(build_objective(X_tr, y_tr, X_val, y_val), n=50)
    print("Best params:", best)

    final = train_final(best, Xtrain, ytrain, X_val, y_val)
    eval_model(final, Xtest, ytest)

    imp = final.booster_.feature_importance()
    top = np.argsort(imp)[::-1][:15]
    print("\nTop-15 Features")
    for idx in top:
        print(f"{orig_names[idx]:<45}{imp[idx]:>10.4f}")

    save(final, model_path)
