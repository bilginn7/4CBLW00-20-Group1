import xgboost as xgb
import optuna
import polars as pl
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, explained_variance_score
import numpy as np
from typing import Tuple, Callable, Dict, Any


def read_parquet_file(file_path: str) -> pl.DataFrame:
    """Loads a parquet file into a Polars DataFrame.

    :param file_path: Location of the parquet file.
    :return: pl.DataFrame
    """
    return pl.read_parquet(file_path)

def load_dataset_splits(x_train_p: str, y_train_p: str, x_test_p: str, y_test_p: str) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """Loads training and test splits into numpy arrays.

    The 'LSOA code' column is dropped from the feature sets (X_train, X_test).
    Target arrays (y_train, y_test) are raveled to ensure they are 1-dimensional.

    :param x_train_p: Path to X_train data.
    :param y_train_p: Path to y_train data.
    :param x_test_p: Path to X_test data.
    :param y_test_p: Path to y_test data.
    :return: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    """
    X_train = read_parquet_file(x_train_p).with_columns(pl.col("LSOA code").cast(pl.Categorical)).to_pandas()
    y_train_df = read_parquet_file(y_train_p).to_numpy().ravel()
    X_test = read_parquet_file(x_test_p).with_columns(pl.col("LSOA code").cast(pl.Categorical)).to_pandas()
    y_test_df = read_parquet_file(y_test_p).to_numpy().ravel()

    return X_train, X_test, y_train_df, y_test_df

def train_and_evaluate_single_objective(params_template: Dict[str, Any], current_objective: str, X_tr: pd.DataFrame, y_tr: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray) -> float:
    """Trains an XGBoost model with a specific objective and evaluates it.

    :param params_template: Dictionary of XGBoost parameters (excluding 'objective').
    :param current_objective: The XGBoost objective function string (e.g., 'reg:squarederror').
    :param X_tr: Training features.
    :param y_tr: Training target.
    :param X_val: Validation features.
    :param y_val: Validation target.
    :return: The Root Mean Squared Error (RMSE) on the validation set.
    """
    params = params_template.copy()
    params['objective'] = current_objective
    model = xgb.XGBRegressor(**params)
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    predictions = model.predict(X_val)
    mse = mean_squared_error(y_val, predictions)
    rmse = np.sqrt(mse)
    return rmse

def define_objective(X_tr: pd.DataFrame, y_tr: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray) -> Callable[[optuna.trial.Trial], float]:
    """Defines the objective function for Optuna hyperparameter optimization.

    :param X_tr: Training features.
    :param y_tr: Training target.
    :param X_val: Validation features for early stopping and evaluation within the trial.
    :param y_val: Validation target for early stopping and evaluation within the trial.
    :return: An objective function that Optuna can call for each trial.
    """
    def objective_func(trial: optuna.trial.Trial) -> float:
        """Optuna objective function for a single trial.

        :param trial: An Optuna Trial object.
        :return: The best RMSE achieved in this trial across the evaluated objectives.
        """
        params = {
            'eval_metric': 'rmse',
            'verbosity': 0,
            'enable_categorical': True,
            'device': "cuda",
            'n_estimators': trial.suggest_int('n_estimators', 50, 500, step=1),
            'learning_rate': trial.suggest_float('learning_rate', 1e-4, 2),
            'max_depth': trial.suggest_int('max_depth', 2, 15),
            'subsample': trial.suggest_float('subsample', 0, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0.0, 3.0),
            'lambda': trial.suggest_float('lambda', 1e-4, 3.0, log=True),
            'alpha': trial.suggest_float('alpha', 1e-4, 3.0, log=True),
            'random_state': 42,
            'early_stopping_rounds': 10,
        }

        objectives_to_evaluate = ['reg:squarederror', 'count:poisson']
        results = {}

        for obj_type in objectives_to_evaluate:
            rmse = train_and_evaluate_single_objective(params, obj_type, X_tr, y_tr, X_val, y_val)
            results[obj_type] = rmse

        best_obj_for_trial = min(results, key=results.get)
        min_rmse_for_trial = results[best_obj_for_trial]

        trial.set_user_attr("best_objective_for_this_trial", best_obj_for_trial)
        return min_rmse_for_trial

    return objective_func

def run_hyperparameter_optimization(objective_callable, n_trials: int = 30):
    """Runs Optuna hyperparameter optimization.

    :param objective_callable: The objective function for Optuna to optimize.
    :param n_trials: The number of trials for the optimization, defaults to 30.
    :return: A dictionary of the best hyperparameters found by Optuna.
    """
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction='minimize')
    study.optimize(objective_callable, n_trials=n_trials, show_progress_bar=True)

    best_params = study.best_params.copy()
    best_objective_from_user_attr = study.best_trial.user_attrs.get("best_objective_for_this_trial")
    best_params['objective'] = best_objective_from_user_attr
    return best_params

def train_final_model(params: Dict[str, Any], X_tr: pd.DataFrame, y_tr: np.ndarray, X_val: pd.DataFrame, y_val: np.ndarray) -> xgb.XGBRegressor:
    """Trains the final XGBoost model using the provided hyperparameters.

    :param params: Dictionary of hyperparameters for the XGBoost model.
    :param X_tr: Training features.
    :param y_tr: Training target.
    :return: The trained XGBoost Regressor model.
    """
    final_model_params = params.copy()
    final_model_params['enable_categorical'] = True
    final_model = xgb.XGBRegressor(**final_model_params)

    if final_model_params.get('early_stopping_rounds', 0) > 0:
        final_model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    else:
        final_model.fit(X_tr, y_tr, verbose=False)
    return final_model

def evaluate_final_model(model: xgb.XGBRegressor, X_te: pd.DataFrame, y_te: np.ndarray) -> Tuple[float, float, float]:
    """Evaluates the final trained model on the test set.

    :param model: The trained XGBoost model.
    :param X_te: Test features.
    :param y_te: Test target.
    :return: The score of the final model. (MAE, RMSE, R2)
    """
    predictions = model.predict(X_te)
    mse = mean_squared_error(y_te, predictions)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_te, predictions)
    mae = mean_absolute_error(y_te, predictions)

    print(f"{'Best Tuned Model MAE on Test Set:':<40} {mae:.4f}")
    print(f"{'Best Tuned Model RMSE on Test Set:':<40} {rmse:.4f}")
    print(f"{'Best Tuned Model R2 on Test Set:':<40} {r2:.4f}")
    return mae, rmse, r2

def model_output(model: xgb.XGBRegressor, file_path: str) -> None:
    """Saves the trained XGBoost model to a file.

    :param model: The trained XGBoost model to save.
    :param file_path: The path (including filename) where the model will be saved.
    """
    model.save_model(file_path)
    print(f"Model saved to {file_path}")

if __name__ == '__main__':
    X_TRAIN_PATH = '../data/X_train.parquet'
    Y_TRAIN_PATH = '../data/y_train.parquet'
    X_TEST_PATH = '../data/X_test.parquet'
    Y_TEST_PATH = '../data/y_test.parquet'
    MODEL_OUTPUT_PATH = 'final_xgboost_model.json'

    X_train_data, X_test_data, y_train_data, y_test_data = load_dataset_splits(X_TRAIN_PATH, Y_TRAIN_PATH, X_TEST_PATH, Y_TEST_PATH)

    objective_to_optimize = define_objective(X_train_data, y_train_data, X_test_data, y_test_data)

    best_model_params = run_hyperparameter_optimization(objective_to_optimize, n_trials=50)
    print(f"Best hyperparameters found: {best_model_params}")

    trained_model = train_final_model(best_model_params, X_train_data, y_train_data, X_test_data, y_test_data)
    evaluate_final_model(trained_model, X_test_data, y_test_data)
    model_output(trained_model, MODEL_OUTPUT_PATH)