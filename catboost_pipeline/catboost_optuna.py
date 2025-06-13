from __future__ import annotations

from typing import Tuple, Dict, Any, Callable

import numpy as np
import pandas as pd
import polars as pl
import optuna
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Data utilities
def read_parquet_file(file_path: str) -> pl.DataFrame:
    """Load a parquet file into a Polars DataFrame."""
    return pl.read_parquet(file_path)


def load_dataset_splits(x_train_p: str, y_train_p: str, x_test_p: str, y_test_p: str
                        ) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Read feature/target parquet splits and convert to pandas / numpy.

    The column ``LSOA code`` is cast to categorical exactly like the XGBoost script.
    """
    X_train = (
        read_parquet_file(x_train_p)
        .with_columns(pl.col("LSOA code").cast(pl.Categorical))
        .to_pandas()
    )
    y_train = read_parquet_file(y_train_p).to_numpy().ravel()

    X_test = (
        read_parquet_file(x_test_p)
        .with_columns(pl.col("LSOA code").cast(pl.Categorical))
        .to_pandas()
    )
    y_test = read_parquet_file(y_test_p).to_numpy().ravel()

    return X_train, X_test, y_train, y_test


def _cat_feature_indices(df: pd.DataFrame) -> list[int]:
    """Return column indices with dtype 'object' or 'category' for CatBoost."""
    return [
        idx
        for idx, dtype in enumerate(df.dtypes)
        if dtype == "object" or str(dtype).startswith("category")
    ]

# Single-objective train/eval
def train_and_evaluate_single_objective(params_template: Dict[str, Any], loss_name: str, X_tr: pd.DataFrame,
                                        y_tr: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray, cat_idx: list[int]) -> float:
    """Train CatBoost with *loss_name* and return validation RMSE."""
    params = params_template.copy()
    params["loss_function"] = loss_name

    train_pool = Pool(X_tr, y_tr, cat_features=cat_idx)
    val_pool = Pool(X_val, y_val, cat_features=cat_idx)

    model = CatBoostRegressor(**params)
    model.fit(train_pool, eval_set=val_pool, verbose=False)

    preds = model.predict(val_pool)
    rmse = np.sqrt(mean_squared_error(y_val, preds))
    return rmse

# Optuna objective
def define_objective(X_tr: pd.DataFrame, y_tr: np.ndarray, X_val: pd.DataFrame,
                     y_val: np.ndarray) -> Callable[[optuna.trial.Trial], float]:
    """Return Optuna objective that samples **GPU-valid** CatBoost parameters."""
    cat_idx = _cat_feature_indices(X_tr)

    def objective(trial: optuna.trial.Trial) -> float:
        params: Dict[str, Any] = {
            "task_type": "GPU",
            "devices": "0",
            "logging_level": "Silent",
            "random_state": 42,
            "early_stopping_rounds": 20,
            "iterations": trial.suggest_int("iterations", 200, 1500),
            "learning_rate": trial.suggest_float("learning_rate", 1e-4, 0.3, log=True),
            "depth": trial.suggest_int("depth", 4, 12),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1, 10, log=True),
            "border_count": trial.suggest_int("border_count", 32, 255),
        }

        # only Bayesian/Bernoulli bootstrap types
        bootstrap_type = trial.suggest_categorical("bootstrap_type", ["Bayesian", "Bernoulli"])
        params["bootstrap_type"] = bootstrap_type

        if bootstrap_type == "Bayesian":
            # Bayesian uses bagging_temperature, *no* subsample
            params["bagging_temperature"] = trial.suggest_float("bagging_temperature", 0.0, 10.0)
        else:  # Bernoulli
            params["subsample"] = trial.suggest_float("subsample", 0.4, 1.0)

        # Evaluate two loss functions and return the best RMSE
        losses = ["RMSE", "Poisson"]
        rmse_per_loss: dict[str, float] = {}

        for loss in losses:
            rmse = train_and_evaluate_single_objective(
                params, loss, X_tr, y_tr, X_val, y_val, cat_idx
            )
            rmse_per_loss[loss] = rmse

        best_loss = min(rmse_per_loss, key=rmse_per_loss.get)
        trial.set_user_attr("best_loss_function", best_loss)
        return rmse_per_loss[best_loss]

    return objective

# Hyper-parameter search
def run_hyperparameter_optimization(objective_callable: Callable[[optuna.trial.Trial], float],
                                    n_trials: int = 30) -> Dict[str, Any]:
    """Run Optuna and return best param dict (incl. winning loss_function)."""
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize")
    study.optimize(objective_callable, n_trials=n_trials, show_progress_bar=True)

    best_params = study.best_params.copy()
    best_params["loss_function"] = study.best_trial.user_attrs["best_loss_function"]
    print("Best hyper-parameters:", best_params)
    return best_params

# Final model train
def train_final_model(params: Dict[str, Any], X_tr: pd.DataFrame, y_tr: np.ndarray,
                      X_val: pd.DataFrame | None = None, y_val: np.ndarray | None = None) -> CatBoostRegressor:
    """Train CatBoost with *params*.  Uses validation data if supplied."""
    cat_idx = _cat_feature_indices(X_tr)
    train_pool = Pool(X_tr, y_tr, cat_features=cat_idx)
    eval_set = Pool(X_val, y_val, cat_features=cat_idx) if X_val is not None else None

    model = CatBoostRegressor(**params, logging_level="Silent", random_state=42)
    model.fit(train_pool, eval_set=eval_set, verbose=False)
    return model

# Evaluation
def evaluate_final_model(model: CatBoostRegressor, X_te: pd.DataFrame, y_te: np.ndarray) -> Tuple[float, float, float]:
    """Return (MAE, RMSE, R²) for the test set, printing nice output."""
    test_pool = Pool(X_te, cat_features=_cat_feature_indices(X_te))
    preds = model.predict(test_pool)

    rmse = np.sqrt(mean_squared_error(y_te, preds))
    mae = mean_absolute_error(y_te, preds)
    r2 = r2_score(y_te, preds)

    print(f"{'Best Tuned Model MAE on Test Set:':<40}{mae:10.4f}")
    print(f"{'Best Tuned Model RMSE on Test Set:':<40}{rmse:10.4f}")
    print(f"{'Best Tuned Model R2 on Test Set:':<40}{r2:10.4f}")

    return mae, rmse, r2

# Persistence
def model_output(model: CatBoostRegressor, file_path: str) -> None:
    """Save CatBoost model to *file_path* (.cbm)."""
    model.save_model(file_path)
    print(f"Model saved to {file_path}")

if __name__ == "__main__":
    # ------ Paths ---------------------------------------------------------- #
    X_TRAIN_PATH = "../data/X_train.parquet"
    Y_TRAIN_PATH = "../data/y_train.parquet"
    X_TEST_PATH = "../data/X_test.parquet"
    Y_TEST_PATH = "../data/y_test.parquet"
    MODEL_OUTPUT_PATH = "final_catboost_model.cbm"

    # ------ Load data ------------------------------------------------------ #
    X_train, X_test, y_train, y_test = load_dataset_splits(
        X_TRAIN_PATH, Y_TRAIN_PATH, X_TEST_PATH, Y_TEST_PATH
    )

    # ------ Optuna search -------------------------------------------------- #
    objective_fn = define_objective(X_train, y_train, X_test, y_test)
    best_params = run_hyperparameter_optimization(objective_fn, n_trials=50)

    # ------ Train final model & evaluate ----------------------------------- #
    final_model = train_final_model(
        best_params, X_train, y_train, X_val=X_test, y_val=y_test
    )
    evaluate_final_model(final_model, X_test, y_test)

    # ------ Save model ----------------------------------------------------- #
    model_output(final_model, MODEL_OUTPUT_PATH)
