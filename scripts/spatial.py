import polars as pl
import numpy as np
from sklearn.neighbors import NearestNeighbors

# Load spatial data
spatial_df = pl.read_csv('../data/auxilliary/LLSOA_Dec_2021_PWC_for_England_and_Wales_2022_1028145039677403461.csv')

# Extract coordinates for sklearn
coords = spatial_df.select(['x', 'y']).to_numpy()
lsoa_codes = spatial_df['LSOA21CD'].to_list()

# Find 6 nearest neighbors (including self)
nbrs = NearestNeighbors(n_neighbors=6, algorithm='ball_tree').fit(coords)
distances, indices = nbrs.kneighbors(coords)

# Create neighbor mapping dataframe in Polars
neighbor_data = []
for i, lsoa in enumerate(lsoa_codes):
    # Get 5 nearest neighbors (excluding self)
    for j in range(1, 6):  # Skip index 0 (self)
        neighbor_data.append({
            'lsoa_code': lsoa,
            'neighbor_code': lsoa_codes[indices[i][j]],
            'distance': distances[i][j],
            'neighbor_rank': j
        })

neighbors_df = pl.DataFrame(neighbor_data)
neighbors_df.write_parquet('../data/spatial_neighbors.parquet')