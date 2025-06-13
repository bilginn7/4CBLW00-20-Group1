from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, Callable, Tuple

import joblib
import numpy as np
import optuna
import pandas as pd
import polars as pl
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    explained_variance_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# Logging
LOG_FILE = "rf_model_runs.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger(__name__)

# File paths & constants
DATA_DIR = Path("../data")
X_TRAIN_PATH = DATA_DIR / "X_train.parquet"
X_TEST_PATH = DATA_DIR / "X_test.parquet"
Y_TRAIN_PATH = DATA_DIR / "y_train.parquet"
Y_TEST_PATH = DATA_DIR / "y_test.parquet"

ID_COL = "LSOA code"
TARGET = "burglary_count"
MODEL_OUTPUT_PATH = "final_random_forest.pkl"

# Helpers – I/O
def read_parquet(file_path: str | Path) -> pl.DataFrame:
    """Load a parquet file into Polars DataFrame."""
    return pl.read_parquet(file_path)


def load_dataset_splits(x_train_p: str | Path, y_train_p: str | Path, x_test_p: str | Path,
                        y_test_p: str | Path) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Parquet → Polars → Pandas, dropping the identifier column and raveling the
    target arrays.  All remaining columns are assumed numeric.
    """
    X_train = read_parquet(x_train_p).drop(ID_COL).to_pandas()
    X_test = read_parquet(x_test_p).drop(ID_COL).to_pandas()

    y_train = read_parquet(y_train_p)[TARGET].to_numpy().ravel()
    y_test = read_parquet(y_test_p)[TARGET].to_numpy().ravel()

    return X_train, X_test, y_train, y_test


# Optuna objective
def build_objective(X_full: pd.DataFrame, y_full: np.ndarray) -> Callable[[optuna.trial.Trial], float]:
    """
    • Split training data 80/20.
    • Build Pipeline(Imputer → RF) with trial-sampled hyper-parameters.
    • Return validation RMSE.
    """
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_full, y_full, test_size=0.3, random_state=42, shuffle=True
    )

    def objective(trial: optuna.trial.Trial) -> float:
        rf_params: Dict[str, Any] = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 800),
            "max_depth": trial.suggest_categorical(
                "max_depth", [None] + list(range(3, 41))
            ),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 20),
            "max_features": trial.suggest_categorical(
                "max_features", ["sqrt", "log2", 0.5, 0.7, 1.0]
            ),
            "bootstrap": trial.suggest_categorical("bootstrap", [True, False]),
            "criterion": trial.suggest_categorical(
                "criterion", ["squared_error", "friedman_mse", "absolute_error"]
            ),
            "n_jobs": -1,
            "random_state": 42,
        }

        pipe = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("rf", RandomForestRegressor(**rf_params)),
            ]
        )
        pipe.fit(X_tr, y_tr)
        preds = pipe.predict(X_val)
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        return rmse

    return objective


def run_hyperparameter_optimization(objective: Callable[[optuna.trial.Trial], float],
                                    n_trials: int = 50) -> Dict[str, Any]:
    """
    Execute Optuna study, minimise RMSE, return best hyper-parameter dictionary.
    """
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize")
    logger.info("Running Optuna search (%d trials)…", n_trials)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    logger.info("Optuna finished.")

    logger.info("Best trial RMSE: %.4f", study.best_value)
    logger.info("Best parameters: %s", study.best_params)
    return study.best_params


# Training / evaluation helpers
def train_final_model(params: Dict[str, Any], X_train: pd.DataFrame, y_train: np.ndarray) -> RandomForestRegressor:
    """Fit RF on the full training data with the chosen params."""
    rf_best = RandomForestRegressor(**best_params, n_jobs=-1, random_state=42)
    pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("rf", rf_best),
        ]
    )
    pipe.fit(X_train, y_train)
    return pipe


def evaluate_final_model(model: RandomForestRegressor, X_test: pd.DataFrame,
                         y_test: np.ndarray) -> Tuple[float, float, float, float]:
    """Compute MAE, RMSE, R², EVS on the held-out test set."""
    preds = np.clip(model.predict(X_test), 0, None)  # keep predictions ≥ 0

    mse = mean_squared_error(y_test, preds)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    evs = explained_variance_score(y_test, preds)

    logger.info("--- Model Performance Report ---")
    logger.info("%-5s: %10.4f", "MSE", mse)
    logger.info("%-5s: %10.4f", "RMSE", rmse)
    logger.info("%-5s: %10.4f", "MAE", mae)
    logger.info("%-5s: %10.4f", "R²", r2)
    logger.info("%-5s: %10.4f", "EV", evs)
    logger.info("--- End of Report ---")

    return mae, rmse, r2, evs


def model_output(model: RandomForestRegressor, file_path: str | Path) -> None:
    """Serialise model to disk using joblib."""
    joblib.dump(model, file_path)
    logger.info("Model saved to %s", file_path)


if __name__ == "__main__":
    # -------------------- Data loading ------------------------------------ #
    logger.info("Loading data …")
    X_train_df, X_test_df, y_train_arr, y_test_arr = load_dataset_splits(
        X_TRAIN_PATH, Y_TRAIN_PATH, X_TEST_PATH, Y_TEST_PATH
    )
    logger.info("X_train: %s | X_test: %s", X_train_df.shape, X_test_df.shape)
    logger.info("y_train: %s | y_test: %s", y_train_arr.shape, y_test_arr.shape)
    logger.info("Feature count: %d", X_train_df.shape[1])

    # -------------------- Hyper-parameter tuning -------------------------- #
    objective_fn = build_objective(X_train_df, y_train_arr)
    best_params = run_hyperparameter_optimization(objective_fn, n_trials=50)

    # -------------------- Train final model ------------------------------- #
    logger.info("Training final Random-Forest model …")
    final_rf = train_final_model(best_params, X_train_df, y_train_arr)

    # -------------------- Evaluate ---------------------------------------- #
    evaluate_final_model(final_rf, X_test_df, y_test_arr)

    # -------------------- Feature importances ----------------------------- #
    logger.info("--- Top 15 Feature Importances ---")
    importances = final_rf.feature_importances_
    top_idx = np.argsort(importances)[::-1][:15]
    for idx in top_idx:
        logger.info("%-45s %6.4f", X_train_df.columns[idx], importances[idx])
    logger.info("--- End of Feature Importances ---")

    # -------------------- Save model -------------------------------------- #
    model_output(final_rf, MODEL_OUTPUT_PATH)
