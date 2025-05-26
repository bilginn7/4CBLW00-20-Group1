from pathlib import Path

# Base directory for data files
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

DATA_PATH      = DATA_DIR / "london_burglaries.parquet"
POP_PATH       = DATA_DIR / "pop_density_2011_2022.parquet"
IMD_2010_PATH  = DATA_DIR / "imd_2010.parquet"
IMD_2015_PATH  = DATA_DIR / "imd_2015.parquet"
IMD_2019_PATH  = DATA_DIR / "imd_2019.parquet"
HOUSING_PATH   = DATA_DIR / "housing.parquet"
NEIGH_PATH     = DATA_DIR / "spatial_neighbors.parquet"
RES_CLASS_PATH = DATA_DIR / "geo" / "lsoa_residential_classification_2018.csv"