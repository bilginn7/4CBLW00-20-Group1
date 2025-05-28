import joblib
import yaml
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error

from ingest import load_data
from preprocess import preprocess_data

def load_config(path: str = 'config.yaml') -> dict:
    """
    Load model and training parameters from a YAML config file.
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def encode_categoricals(*dfs: pd.DataFrame) -> None:
    """
    In-place label-encode all object-type (string) columns across provided DataFrames.
    Assumes training and test share the same categories.
    """
    # Identify categorical columns
    cat_cols = dfs[0].select_dtypes(include='object').columns.tolist()
    for col in cat_cols:
        # Create category from training set
        cats = dfs[0][col].astype('category').cat.categories
        # Map categories to codes, unseen categories as -1
        cat_dtype = pd.CategoricalDtype(categories=cats)
        for df in dfs:
            df[col] = df[col].astype(cat_dtype).cat.codes


def train_and_evaluate():
    """
    Train an XGBRegressor on processed data and evaluate performance.
    Saves the trained model to disk.
    """
    # Load configuration
    config = load_config()
    params = config.get('model_params', {})
    model_path = config['artifacts']['model_path']

    # Load and preprocess data
    X_train, X_test, y_train, y_test = load_data()
    X_train_proc, X_test_proc = preprocess_data(X_train, X_test)

    # Encode categorical (string) columns to numeric codes
    encode_categoricals(X_train_proc, X_test_proc)

    # Flatten target arrays
    y_train = y_train.values.ravel()
    y_test = y_test.values.ravel()

    # Initialize and train the model
    model = xgb.XGBRegressor(**params)
    model.fit(X_train_proc, y_train)

    # Generate predictions
    preds_train = model.predict(X_train_proc)
    preds_test = model.predict(X_test_proc)

    # Compute evaluation metrics
    rmse_train = mean_squared_error(y_train, preds_train) ** 0.5
    rmse_test = mean_squared_error(y_test, preds_test) ** 0.5
    mae_train = mean_absolute_error(y_train, preds_train)
    mae_test = mean_absolute_error(y_test, preds_test)

    print(f"Train RMSE: {rmse_train:.3f}, MAE: {mae_train:.3f}")
    print(f"Test  RMSE: {rmse_test:.3f}, MAE: {mae_test:.3f}")

    # Save the trained model
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

if __name__ == '__main__':
    train_and_evaluate()