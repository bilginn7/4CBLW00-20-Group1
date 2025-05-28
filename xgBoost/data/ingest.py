import pandas as pd

# Paths to raw data
X_TRAIN_PATH = 'raw/x_train.parquet'
X_TEST_PATH  = 'raw/x_test.parquet'
Y_TRAIN_PATH = 'raw/y_train.parquet'
Y_TEST_PATH  = 'raw/y_test.parquet'


def load_data():
    """
    Load train and test datasets from parquet files.

    Returns:
        X_train (DataFrame)
        X_test  (DataFrame)
        y_train (DataFrame or Series)
        y_test  (DataFrame or Series)
    """
    X_train = pd.read_parquet(X_TRAIN_PATH)
    X_test  = pd.read_parquet(X_TEST_PATH)
    y_train = pd.read_parquet(Y_TRAIN_PATH)
    y_test  = pd.read_parquet(Y_TEST_PATH)
    return X_train, X_test, y_train, y_test


if __name__ == '__main__':
    X_train, X_test, y_train, y_test = load_data()
    print(f'Loaded X_train: {X_train.shape}, y_train: {y_train.shape}')
    print(f'Loaded X_test:  {X_test.shape},  y_test:  {y_test.shape}')
