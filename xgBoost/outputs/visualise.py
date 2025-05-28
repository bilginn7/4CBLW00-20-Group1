#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx


def main():
    # Setup paths
    ROOT = Path(__file__).resolve().parents[1]
    PRED_PATH = ROOT / 'outputs' / 'predictions.csv'
    GPKG_PATH = ROOT / 'data' / 'raw' / 'london_lsoa.gpkg'
    OUTPUT_IMG = ROOT / 'outputs' / 'heatmap.png'

    # Load predictions
    preds = pd.read_csv(PRED_PATH)
    # Standardize code column name
    if 'LSOA code' in preds.columns:
        preds = preds.rename(columns={'LSOA code': 'lsoa_code'})
    elif 'lsoa_code' not in preds.columns:
        raise KeyError("No LSOA code column in predictions.csv")

    # Load LSOA geometries
    lsoa_gdf = gpd.read_file(GPKG_PATH)

    # Rename code column to match predictions
    if 'LSOA21CD' in lsoa_gdf.columns:
        lsoa_gdf = lsoa_gdf.rename(columns={'LSOA21CD': 'lsoa_code'})
    elif 'lsoa_code' not in lsoa_gdf.columns:
        raise KeyError('No LSOA code column found in GeoDataFrame')

    # Merge geometries with predictions
    merged = lsoa_gdf.merge(preds, on='lsoa_code', how='left')

    # Project to Web Mercator for basemap
    merged = merged.to_crs(epsg=3857)

    # Plot choropleth
    fig, ax = plt.subplots(figsize=(12, 12))
    merged.plot(
        column='prediction',
        cmap='YlOrRd',
        vmin=0,
        vmax=15,
        legend=True,
        legend_kwds={'label': 'Predicted Crime Count', 'shrink': 0.5, 'ticks': list(range(0, 16, 3))},
        linewidth=0.2,
        edgecolor='grey',
        ax=ax
    )


    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

    ax.set_axis_off()
    ax.set_title('Predicted Crime Risk by LSOA', fontsize=16)

    plt.tight_layout()
    OUTPUT_IMG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(OUTPUT_IMG), dpi=300)
    print(f'Heatmap saved to {OUTPUT_IMG}')


if __name__ == '__main__':
    main()
