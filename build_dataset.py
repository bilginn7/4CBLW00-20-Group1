from dataset_pipeline import *
from dataset_pipeline import settings as S
import polars as pl

DATA_DIR = S.DATA_DIR

# ------------------------------------------------------------------#
# A. Build the full modelling table
# ------------------------------------------------------------------#
df = normalize_time(S.DATA_PATH)
df = create_full_grid(df)
df = df.with_columns(is_holiday_month(pl.col("month")).alias("holiday_month"))
df = add_population_data(df)
df = add_imd_data(df)
df = add_housing_data(df)
df = add_temporal_features(df)
df = add_revictimization_risk(df)
df = df.collect()
df = add_neighbor_features(df)
df = filter_residential_lsoas(df)

# save the COMPLETE table
full_path = DATA_DIR / "features.parquet"
df.write_parquet(full_path)

# ------------------------------------------------------------------#
# B. Train-test split (70 / 30, reproducible)
# ------------------------------------------------------------------#
target_col = "burglary_count"

# Find the 70% cutoff point in time_index_norm
max_time_index = df.select(pl.col("time_index_norm").max()).item()
split_time_index = max_time_index * 0.7

# Split based on time_index_norm
train_df = df.filter(pl.col("time_index_norm") <= split_time_index)
test_df = df.filter(pl.col("time_index_norm") > split_time_index)

X_train = train_df.drop(target_col)
y_train = train_df.select(target_col)

X_test = test_df.drop(target_col)
y_test = test_df.select(target_col)

# ------------------------------------------------------------------#
# C. Persist everything
# ------------------------------------------------------------------#
X_train.write_parquet(DATA_DIR / "X_train.parquet")
X_test.write_parquet (DATA_DIR / "X_test.parquet")
y_train.write_parquet(DATA_DIR / "y_train.parquet")
y_test.write_parquet (DATA_DIR / "y_test.parquet")

print(
    "✓ files saved:\n"
    f"  • {full_path.name}    : {df.shape[0]:,} rows × {df.shape[1]} cols\n"
    f"  • X_train.parquet     : {X_train.shape[0]:,} rows × {X_train.shape[1]} cols\n"
    f"  • X_test.parquet      : {X_test.shape[0]:,} rows × {X_test.shape[1]} cols\n"
    f"  • y_train.parquet     : {y_train.shape[0]:,} rows\n"
    f"  • y_test.parquet      : {y_test.shape[0]:,} rows"
)