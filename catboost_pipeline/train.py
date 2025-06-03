import joblib
import yaml
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_squared_error, mean_absolute_error

from ingest import load_data
from preprocess import preprocess_data


def load_config(path: str = 'config.yaml') -> dict:
    """
    Load model and training parameters from a YAML config file.
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def train_and_evaluate():
    """
    Train a CatBoostRegressor on processed data and evaluate performance.
    Saves the trained model to disk.
    """
    # Load configuration
    config = load_config()
    params = config.get('model_params', {})
    model_path = config['artifacts']['model_path']

    # Load and preprocess data
    X_train, X_test, y_train, y_test = load_data()
    X_train_proc, X_test_proc = preprocess_data(X_train, X_test)

    # Identify categorical features (CatBoost handles categoricals natively)
    cat_features = X_train_proc.select_dtypes(include='object').columns.tolist()

    # CatBoost expects categorical features as column indices
    cat_features_idx = [X_train_proc.columns.get_loc(col) for col in cat_features]

    # Convert targets to 1D arrays
    y_train = y_train.values.ravel()
    y_test = y_test.values.ravel()

    # Create Pool objects for train and test sets (with categorical feature info)
    train_pool = Pool(data=X_train_proc, label=y_train, cat_features=cat_features_idx)
    test_pool = Pool(data=X_test_proc, label=y_test, cat_features=cat_features_idx)

    # Initialize CatBoostRegressor with params from config
    model = CatBoostRegressor(**params)

    # Train model with early stopping on test set
    model.fit(
        train_pool,
        eval_set=test_pool,
        early_stopping_rounds=config.get('early_stopping_rounds', 50),
        verbose=100
    )

    # Predict and evaluate
    preds_train = model.predict(X_train_proc)
    preds_test = model.predict(X_test_proc)

    rmse_train = mean_squared_error(y_train, preds_train, squared=False)
    rmse_test = mean_squared_error(y_test, preds_test, squared=False)
    mae_train = mean_absolute_error(y_train, preds_train)
    mae_test = mean_absolute_error(y_test, preds_test)

    print(f"Train RMSE: {rmse_train:.3f}, MAE: {mae_train:.3f}")
    print(f"Test  RMSE: {rmse_test:.3f}, MAE: {mae_test:.3f}")

    # Save model
    model.save_model(model_path)
    print(f"Model saved to {model_path}")


if __name__ == '__main__':
    train_and_evaluate()

