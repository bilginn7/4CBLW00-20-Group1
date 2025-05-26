from dataset_pipeline import (
    normalize_time,
    create_full_grid,
    is_holiday_month,
    add_population_data,
    add_imd_data,
    add_housing_data,
    add_neighbor_features,
    add_temporal_features,
    add_revictimization_risk,
)
from dataset_pipeline import settings as S

DATA_DIR = S.DATA_DIR

# ------------------------------------------------------------------#
# A. Build the full modelling table
# ------------------------------------------------------------------#
df = normalize_time(S.DATA_PATH)
df = create_full_grid(df)
df = df.with_columns(is_holiday_month(df["month"]).alias("holiday_month"))
df = add_population_data(df)
df = add_imd_data(df)
df = add_housing_data(df)
df = add_neighbor_features(df)
df = add_temporal_features(df)
df = add_revictimization_risk(df)

# save the COMPLETE table
full_path = DATA_DIR / "features.parquet"
df.write_parquet(full_path)

# ------------------------------------------------------------------#
# B. Train-test split (70 / 30, reproducible)
# ------------------------------------------------------------------#
target_col = "burglary_count"
df = df.sort(["LSOA code", "year", "month"])

cut = int(df.height * 0.7)
train_df = df.slice(0, cut)
test_df  = df.slice(cut)

X_train = train_df.drop(target_col)
y_train = train_df.select(target_col)

X_test  = test_df.drop(target_col)
y_test  = test_df.select(target_col)

# ------------------------------------------------------------------#
# C. Persist everything
# ------------------------------------------------------------------#
X_train.write_parquet(DATA_DIR / "X_train.parquet")
X_test.write_parquet (DATA_DIR / "X_test.parquet")
y_train.write_parquet(DATA_DIR / "y_train.parquet")
y_test.write_parquet (DATA_DIR / "y_test.parquet")

print(
    "✓ files saved:\n"
    f"  • {full_path.name}   : {df.shape[0]:,} rows × {df.shape[1]} cols\n"
    f"  • X_train.parquet     : {X_train.shape[0]:,} rows × {X_train.shape[1]} cols\n"
    f"  • X_test.parquet      : {X_test.shape[0]:,} rows × {X_test.shape[1]} cols\n"
    f"  • y_train.parquet     : {y_train.shape[0]:,} rows\n"
    f"  • y_test.parquet      : {y_test.shape[0]:,} rows"
)