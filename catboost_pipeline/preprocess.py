import pandas as pd
from typing import Tuple

# Paths to raw data
X_TRAIN_PATH = 'data/raw/x_train.parquet'
X_TEST_PATH  = 'data/raw/x_test.parquet'
Y_TRAIN_PATH = 'data/raw/y_train.parquet'
Y_TEST_PATH  = 'data/raw/y_test.parquet'


def clean_data(X: pd.DataFrame) -> pd.DataFrame:
    """
    Perform basic data cleaning:
    - Drop duplicate rows
    - Impute missing values:
      * Numeric: median
      * Categorical: mode
    """
    X = X.drop_duplicates()

    # Fill missing values
    numeric_cols = X.select_dtypes(include='number').columns
    X[numeric_cols] = X[numeric_cols].fillna(X[numeric_cols].median())

    categorical_cols = X.select_dtypes(include='object').columns
    for col in categorical_cols:
        if X[col].isnull().any():
            X[col] = X[col].fillna(X[col].mode()[0])

    return X


def add_date_features(X: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
    """
    Ensure 'year' and 'month' columns are present and correctly typed.
    """
    X = X.copy()

    if 'year' in X.columns:
        X['year'] = X['year'].astype(int)
    if 'month' in X.columns:
        X['month'] = X['month'].astype(int)

    return X


def preprocess_data(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    date_col: str = 'date'
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Complete preprocessing pipeline: clean and align date-related features.
    """
    X_train_clean = clean_data(X_train)
    X_test_clean  = clean_data(X_test)

    X_train_feat = add_date_features(X_train_clean, date_col)
    X_test_feat  = add_date_features(X_test_clean, date_col)

    return X_train_feat, X_test_feat


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load train and test data from local parquet files.
    """
    X_train = pd.read_parquet(X_TRAIN_PATH)
    X_test  = pd.read_parquet(X_TEST_PATH)
    y_train = pd.read_parquet(Y_TRAIN_PATH)
    y_test  = pd.read_parquet(Y_TEST_PATH)
    return X_train, X_test, y_train, y_test


if __name__ == '__main__':
    X_train, X_test, y_train, y_test = load_data()
    X_train_proc, X_test_proc = preprocess_data(X_train, X_test)
    print(f'Processed X_train: {X_train_proc.shape}')
    print(f'Processed X_test:  {X_test_proc.shape}')

