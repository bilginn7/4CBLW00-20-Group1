import joblib
import yaml
import pandas as pd
import xgboost as xgb
from ingest import load_data
from preprocess import preprocess_data
from pathlib import Path

# Adjust these to point at your folders
ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.yaml"
RAW_DATA_DIR   = "data/raw"
MODEL_PATH     = "xgb_regressor.pkl"
CONFIG_PATH    = "config.yaml"
OUTPUT_DIR =  "outputs"

def load_config(path: Path = CONFIG_PATH) -> dict:
    """
    Load prediction settings (e.g., model path) from YAML config.
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def encode_categoricals(*dfs: pd.DataFrame) -> None:
    """
    Label-encode object-type columns across all DataFrames.
    """
    cat_cols = dfs[0].select_dtypes(include='object').columns
    for col in cat_cols:
        cats = dfs[0][col].astype('category').cat.categories
        dtype = pd.CategoricalDtype(categories=cats)
        for df in dfs:
            df[col] = df[col].astype(dtype).cat.codes


def predict():
    """
    Load trained XGBoost model, preprocess data, and output predictions.
    """
    # Load configuration
    config = load_config()
    global MODEL_PATH
    MODEL_PATH = ROOT_DIR / "data" / config['artifacts']['model_path']
    output_path = ROOT_DIR / config['artifacts'].get('predictions_path', 'outputs/predictions.csv')

    # Ensure output directory exists

    # Load raw train/test data
    X_train, X_test, y_train, y_test = load_data()

    # Preprocess (clean + date features)
    X_train_proc, X_test_proc = preprocess_data(X_train, X_test)

    # Encode categorical features
    encode_categoricals(X_train_proc, X_test_proc)

    # Load model
    model = joblib.load(MODEL_PATH)

    # Predict on test set
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
