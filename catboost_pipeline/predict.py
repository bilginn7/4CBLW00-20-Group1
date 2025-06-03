import joblib
import yaml
import pandas as pd
from catboost import CatBoostRegressor
from ingest import load_data
from preprocess import preprocess_data
from pathlib import Path

# Set root and config paths
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "catboost_config.yaml"
RAW_DATA_DIR = "data/raw"
MODEL_PATH = "catboost_regressor.cbm"
OUTPUT_DIR = "outputs"

def load_config(path: Path = CONFIG_PATH) -> dict:
    """
    Load prediction settings (e.g., model path) from YAML config.
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def predict():
    """
    Load trained CatBoost model, preprocess data, and output predictions.
    """
    # Load configuration
    config = load_config()
    global MODEL_PATH
    MODEL_PATH = ROOT_DIR / "data" / config['artifacts']['model_path']
    output_path = ROOT_DIR / config['artifacts'].get('predictions_path', 'outputs/catboost_predictions.csv')

    # Load raw train/test data
    X_train, X_test, y_train, y_test = load_data()

    # Preprocess (clean + date features)
    X_train_proc, X_test_proc = preprocess_data(X_train, X_test)

    # Identify categorical columns (if needed)
    cat_cols = X_train_proc.select_dtypes(include='object').columns.tolist()

    # Load model
    model = CatBoostRegressor()
    model.load_model(str(MODEL_PATH))

    # Predict
    preds = model.predict(X_test_proc)

    # Prepare output DataFrame
    df_out = X_test.copy()
    df_out['prediction'] = preds
    if y_test is not None:
        df_out['actual'] = y_test.values.ravel()

    # Save predictions
    df_out.to_csv(output_path, index=False)
    print(f"Predictions saved to {output_path}")


def main():
    predict()


if __name__ == '__main__':
    main()

