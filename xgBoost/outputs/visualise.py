#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import joblib

# Simplified visualisation script: heatmap + timeseries

def main():
    ROOT = Path(__file__).resolve().parents[1]

    # Paths
    PRED_CSV   = ROOT / 'outputs' / 'predictions.csv'
    X_TRAIN_CSV = ROOT / 'data' / 'raw' / 'x_train.csv'
    Y_TRAIN_CSV = ROOT / 'data' / 'raw' / 'y_train.csv'
    X_TEST_CSV  = ROOT / 'data' / 'raw' / 'x_test.csv'
    Y_TEST_CSV  = ROOT / 'data' / 'raw' / 'y_test.csv'
    MODEL_PATH  = ROOT / 'data' / 'xgb_regressor.pkl'
    GPKG_PATH   = ROOT / 'data' / 'raw' / 'london_lsoa.gpkg'
    OUTPUT_HEATMAP  = ROOT / 'outputs' / 'heatmap.png'
    OUTPUT_TIMESERIES = ROOT / 'outputs' / 'timeseries.png'

    # Load heatmap data
    preds = pd.read_csv(PRED_CSV)
    if 'LSOA code' in preds.columns:
        preds = preds.rename(columns={'LSOA code': 'lsoa_code'})
    lsoa_gdf = gpd.read_file(GPKG_PATH)
    if 'LSOA21CD' in lsoa_gdf.columns:
        lsoa_gdf = lsoa_gdf.rename(columns={'LSOA21CD': 'lsoa_code'})
    merged = lsoa_gdf.merge(preds, on='lsoa_code', how='left').to_crs(epsg=3857)

    # Plot heatmap
    fig, ax = plt.subplots(figsize=(12, 12))
    merged.plot(
        column='prediction', cmap='YlOrRd', vmin=0, vmax=15,
        legend=True,
        legend_kwds={'label': 'Predicted Crime Count', 'shrink': 0.5, 'ticks': list(range(0, 16, 3))},
        linewidth=0.2, edgecolor='grey', ax=ax
    )
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_axis_off()
    ax.set_title('Predicted Crime Risk by LSOA', fontsize=16)
    plt.tight_layout()
    OUTPUT_HEATMAP.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_HEATMAP, dpi=300)
    print(f'Heatmap saved to {OUTPUT_HEATMAP}')

    # ----------------------------------------------------------------
    # Time-series plot: average actual vs predicted by month/year
    # ----------------------------------------------------------------
    # Load CSV data
    x_train = pd.read_csv(X_TRAIN_CSV)
    y_train = pd.read_csv(Y_TRAIN_CSV)
    x_test  = pd.read_csv(X_TEST_CSV)
    y_test  = pd.read_csv(Y_TEST_CSV)
    model   = joblib.load(MODEL_PATH)

    # Ensure holiday_month is numeric if present
    for df in (x_train, x_test):
        if 'holiday_month' in df.columns:
            df['holiday_month'] = df['holiday_month'].astype(int)

    # Select numeric features (drop non-numeric like codes)
    num_cols_train = x_train.select_dtypes(include=['number']).columns.tolist()
    num_cols_test  = x_test.select_dtypes(include=['number']).columns.tolist()

    # Predict
    preds_train = model.predict(x_train[num_cols_train])
    preds_test  = model.predict(x_test[num_cols_test])

    # Build DataFrames
    df_train = pd.DataFrame({
        'year': x_train.year,
        'month': x_train.month,
        'actual': y_train.values.ravel(),
        'predicted': preds_train
    })
    df_test = pd.DataFrame({
        'year': x_test.year,
        'month': x_test.month,
        'actual': y_test.values.ravel(),
        'predicted': preds_test
    })

    # Aggregate by month/year
    agg_train = df_train.groupby(['year', 'month']).mean().reset_index()
    agg_test  = df_test.groupby(['year', 'month']).mean().reset_index()

    # Create date for plotting
    agg_train['date'] = pd.to_datetime(dict(year=agg_train.year, month=agg_train.month, day=1))
    agg_test['date']  = pd.to_datetime(dict(year=agg_test.year,  month=agg_test.month,  day=1))

    # Split date = last training date
    split_date = agg_train['date'].max()

    # Plot time series
    fig2, ax2 = plt.subplots(figsize=(14, 6))
    ax2.plot(agg_train['date'], agg_train['actual'], label='Training Actual (Avg)', color='blue')
    ax2.plot(agg_train['date'], agg_train['predicted'], linestyle='--', label='Training Predicted (Avg)', color='blue')
    ax2.plot(agg_test['date'],  agg_test['actual'], marker='s', label='Test Actual (Avg)', color='green')
    ax2.plot(agg_test['date'],  agg_test['predicted'], marker='s', label='Test Predicted (Avg)', color='red')
    ax2.axvline(split_date, linestyle=':', color='black', label='Train/Test Split')

    ax2.set_title(
        'Average Burglary Count Across All LSOAs\n'
        f'(Training: {len(agg_train)} months, Testing: {len(agg_test)} months)',
        fontsize=14
    )
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Average Burglary Count per LSOA')
    ax2.legend()
    plt.tight_layout()
    OUTPUT_TIMESERIES.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_TIMESERIES, dpi=300)
    print(f'Time-series plot saved to {OUTPUT_TIMESERIES}')

if __name__ == '__main__':
    main()