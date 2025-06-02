import polars as pl
import numpy as np
import logging
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, explained_variance_score
from sklearn.experimental import enable_halving_search_cv # noqa
from sklearn.model_selection import HalvingRandomSearchCV
from scipy.stats import randint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("rf_model_runs.log")
    ]
)
logger = logging.getLogger(__name__)

PATH = Path("../data")
ID_COL = "LSOA code"
TARGET = "burglary_count"

# Data loading
logger.info("Loading training and testing data...")
X_train_pl = pl.read_parquet(PATH / "X_train.parquet").drop(ID_COL)
X_test_pl  = pl.read_parquet(PATH / "X_test.parquet").drop(ID_COL)

y_train = pl.read_parquet(PATH / "y_train.parquet")[TARGET].to_numpy()
y_test  = pl.read_parquet(PATH / "y_test.parquet")[TARGET].to_numpy()
logger.info(f"X_train shape: {X_train_pl.shape}, X_test shape: {X_test_pl.shape}")
logger.info(f"y_train shape: {y_train.shape}, y_test shape: {y_test.shape}")

X_train = X_train_pl.to_numpy()
X_test  = X_test_pl.to_numpy()
feat_names = X_train_pl.columns
logger.info(f"Number of features: {len(feat_names)}")

# Pipeline
base_rf = RandomForestRegressor(
    n_jobs=-1,
    random_state=42,
    verbose=0
)

imputer = SimpleImputer(strategy="median")

search_pipe = Pipeline([
    ("impute", imputer),
    ("rf", base_rf)
])

param_distributions = {
    'rf__n_estimators': randint(50, 300),
    'rf__max_depth': [None] + list(randint(5, 30).rvs(5)),
    'rf__min_samples_split': randint(2, 20),
    'rf__min_samples_leaf': randint(1, 20),
    'rf__max_features': ['sqrt', 'log2', 0.5, 0.7, 1.0]
}

n_initial_candidates = 20
halving_search = HalvingRandomSearchCV(
    estimator=search_pipe,
    param_distributions=param_distributions,
    n_candidates=n_initial_candidates,
    factor=3,
    resource='n_samples',
    min_resources='smallest',
    cv=5,
    scoring='neg_mean_absolute_error',
    verbose=2,
    random_state=42,
    n_jobs=-1
)

logger.info("Starting hyperparameter tuning with HalvingRandomSearchCV...")
halving_search.fit(X_train, y_train)
logger.info("Hyperparameter tuning complete.")

best_model = halving_search.best_estimator_
logger.info(f"Best parameters found: {halving_search.best_params_}")
logger.info(f"Best cross-validation score (neg MAE): {halving_search.best_score_:.4f}")

logger.info("Generating predictions on the test set using the best model...")
preds  = np.clip(best_model.predict(X_test), 0, None)
logger.info("Predictions generated and clipped to be non-negative.")

# Model report
mse = mean_squared_error(y_test, preds)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)
evs = explained_variance_score(y_test, preds)

logger.info("--- Model Performance Report ---")
logger.info(f"{'MSE':<5}: {mse:>10.4f}")
logger.info(f"{'RMSE':<5}: {rmse:>10.4f}")
logger.info(f"{'MAE':<5}: {mae:>10.4f}")
logger.info(f"{'R²':<5}: {r2:>10.4f}")
logger.info(f"{'EV':<5}: {evs:>10.4f}")
logger.info("--- End of Report ---")

# Top importances (from the best model)
if hasattr(best_model.named_steps["rf"], 'feature_importances_'):
    imp = best_model.named_steps["rf"].feature_importances_
    top = sorted(zip(feat_names, imp), key=lambda x: -x[1])[:15]

    logger.info("--- Top 15 Feature Importances (Best Tuned Model) ---")
    for name, val in top:
        logger.info(f"{name:<45} {val:6.4f}")
    logger.info("--- End of Feature Importances ---")
else:
    logger.warning("Could not retrieve feature importances from the best model.")