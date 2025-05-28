import pandas as pd
from typing import Tuple
from ingest import load_data


def clean_data(X: pd.DataFrame) -> pd.DataFrame:
    """
    Basic cleaning: drop duplicates, handle missing values.
    """
    X = X.drop_duplicates()

    # Impute numeric features with median
    numeric_cols = X.select_dtypes(include='number').columns
    X[numeric_cols] = X[numeric_cols].fillna(X[numeric_cols].median())

    # Impute categorical features with mode
    categorical_cols = X.select_dtypes(include='object').columns
    for col in categorical_cols:
        X[col] = X[col].fillna(X[col].mode()[0])

    return X


def add_date_features(X: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
    """
    Ensures year and month columns are present and properly typed.

    Args:
        X: DataFrame containing at least the 'year' and 'month' columns.
        date_col: unused, kept for interface compatibility.

    Returns:
        DataFrame with 'year' and 'month' as integers.
    """
    X = X.copy()

    # Ensure year and month are integer types
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
    Full preprocessing pipeline: cleaning and date feature alignment.

    Args:
        X_train: Raw training DataFrame.
        X_test: Raw test DataFrame.
        date_col: placeholder for compatibility.

    Returns:
        Tuple of processed train and test DataFrames.
    """
    # Clean datasets
    X_train_clean = clean_data(X_train)
    X_test_clean  = clean_data(X_test)

    # Align date-related columns
    X_train_feat = add_date_features(X_train_clean, date_col)
    X_test_feat  = add_date_features(X_test_clean, date_col)

    return X_train_feat, X_test_feat


if __name__ == '__main__':
    X_train, X_test, y_train, y_test = load_data()
    X_train_proc, X_test_proc = preprocess_data(X_train, X_test)
    print(f'Processed X_train: {X_train_proc.shape}')
    print(f'Processed X_test:  {X_test_proc.shape}')
