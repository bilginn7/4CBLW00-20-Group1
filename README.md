# 4CBLW00-20-Group1

**Addressing real-world crime and security problems with data science**

A machine learning project for predicting burglary counts in London using multiple ML algorithms, 
geospatial analysis, and temporal features.

## Project Overview
This project analyzes London burglary data to predict crime counts at the Lower Layer Super Output Area (LSOA) level. 
We combine demographic, temporal, spatial, and housing data to build predictive models that can help inform crime prevention strategies.

### Features
- **Multiple ML Models**: LightGBM, XGBoost, CatBoost, and Random Forest implementations
- **Geospatial Analysis**: LSOA-level geographic data processing and neighborhood features
- **Temporal Features**: Holiday effects, seasonal patterns, and time-based aggregations
- **Demographic Integration**: Population density, Index of Multiple Deprivation (IMD), housing data
- **Model Interpretability**: SHAP values for feature importance analysis
- **Interactive Dashboard**: Visualization and exploration tools
- **Hyperparameter Optimization**: Optuna-based model tuning with progress tracking

## Tech Stack

- **Data Processing**: Polars, Pandas, NumPy
- **Machine Learning**: LightGBM, XGBoost, CatBoost, Scikit-learn
- **Model Interpretation**: SHAP
- **Geospatial**: GeoPandas, Contextily, Shapely
- **Visualization**: Matplotlib, Seaborn
- **Statistical Analysis**: StatsModels, SciPy
- **Optimization**: Optuna with progress tracking
- **Data I/O**: PyArrow for efficient Parquet handling

## 📁 Project Structure

```
├── catboost_pipeline/         # CatBoost implementation with GPU support
├── dataset_pipeline/          # Data processing and feature engineering
│   ├── temporal.py            # Time-based feature creation
│   ├── aggregations.py        # Data aggregation utilities
│   ├── demographics.py        # Population and IMD data integration
│   ├── spatial.py             # Geospatial features and neighbor analysis
│   └── revictimization.py     # Revictimization risk features
├── data/                      # All datasets required for this project
├── dashboard/                 # Interactive dashboard components
├── lightgbm/                  # LightGBM model implementation
├── randomforest/              # Random Forest model implementation
├── xgBoost/                   # XGBoost model implementation
├── notebooks/                 # Jupyter notebooks for analysis and visualization
├── scripts/                   # Utility scripts for data processing
├── build_dataset.py           # Main dataset construction pipeline
└── requirements.txt           # Project dependencies
```

---

## Getting Started

### Prerequisites
- Python 3.12+ (recommended for compatibility with all dependencies)
- Git Large File Storage (Git LFS) for managing large dataset files
  - Install Git LFS: [https://git-lfs.com/](https://git-lfs.com/)
  - After installing, run the following command to initialize LFS:
    ```bash
    git lfs install
    ```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/bilginn7/4CBLW00-20-Group1.git
   cd 4CBLW00-20-Group1
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up data directory structure**
   ```bash
   mkdir data
   mkdir data/geo
   mkdir data/lookup
   mkdir data/auxilliary
   mkdir data/all_crime_data_zips
   ```
### Data Setup

The processed data is already available in this project, 
but if you want to recreate the project then follow the steps below.

#### Required Crime Data from Police.uk

**Step 1: Building the lookup table**
- Download the following **3 CSV files**:
  - File 1: [LSOA (2011) to LSOA (2021) to Local Authority District (2022)](https://www.data.gov.uk/dataset/03a52a27-36e7-4f33-a632-83282faea36f/lsoa-2011-to-lsoa-2021-to-local-authority-district-2022-exact-fit-lookup-for-ew-v3)
  - File 2: [LSOA (2021) to Electoral Ward (2024) to LAD (2024)](https://geoportal.statistics.gov.uk/datasets/lsoa-2021-to-electoral-ward-2024-to-lad-2024-best-fit-lookup-in-ew/about)
  - File 3: [Output Area (2021) to LSOA to MSOA to LAD (December 2021)](https://geoportal.statistics.gov.uk/datasets/ons::output-area-2021-to-lsoa-to-msoa-to-lad-december-2021-exact-fit-lookup-in-ew-v3/about)
- Put all 3 CSV files in: `data/lookup`

**Step 2: Download Crime Data**
1. Visit [https://data.police.uk/data/archive/](https://data.police.uk/data/archive/)
2. Download the historical crime data archives (ZIP files) for your analysis period
3. Extract all downloaded ZIP files
4. Place the extracted crime data files in: `data/all_crime_data_zips/`
5. Run `burglary_collector.py` in `scripts` folder

**Step 3: Additional Required Data Files**

Place the following auxiliary data files in the `data/auxilliary` directory:
- `sapelsoapopulationdensity20112022.xlsx` - Population estimates for LSOAs between 2011 and 2022
  - Can be downloaded via: [ONS - LSOA population estimates 2011-2022](https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/lowersuperoutputareapopulationdensity)
- `dwelling-property-type-2015-lsoa-msoa.csv` - Dwellings by property type and number of bedrooms.
  - Download CSV file: [dwelling-property-type-2015-lsoa-msoa](https://data.london.gov.uk/dataset/property-build-period-lsoa/?resource=0198b6ca-9297-418a-97d2-)
- `ID 2010 for London.xls`, `ID 2015 for London.xls`, `ID 2019 for London.xlsx` - Deprivation indices
  - Download from: [Indices of Deprivation](https://data.london.gov.uk/dataset/indices-of-deprivation/)
  - File 1: `indices-of-deprivation-2010.zip`
    - Extract `id-2010-for-london.xls` from the zip and rename it to `ID 2010 for London.xls`
  - File 2: `ID 2015 for London.xls`
  - File 3: `ID 2019 for London.xlsx`
- `lsoa_land_cover.csv` - Land cover over the years of 2000, 2006, 2012, and 2018
  - Download: [lsoa_clustered.csv](https://github.com/GDSL-UL/APPG-LBA/tree/main/data)
- `LLSOA_Dec_2021_PWC_for_England_and_Wales_2022_1028145039677403461.csv` - LSOA population weighted centroids
  - Download: [LSOA weighted centroids](https://www.data.gov.uk/dataset/1b61943c-f5e1-4398-babe-5c487257864e/lower-layer-super-output-areas-december-2021-ew-population-weighted-centroids)

**Step 3.1: Geographical datasets**

The following 3 datasets are required for the dashboard, these will be placed in `data/geo`:
- File 1 (LAD/Borough level): [Local Authority Districts (May 2022) Boundaries UK BGC (V3)](https://geoportal.statistics.gov.uk/datasets/ons::local-authority-districts-may-2022-boundaries-uk-bgc-v3/about)
- File 2 (Wards level): [Wards (December 2024) Boundaries UK BGC](https://geoportal.statistics.gov.uk/datasets/ons::wards-december-2024-boundaries-uk-bgc-2/about)
- File 3 (LSOA level): [Lower layer Super Output Areas (December 2021) Boundaries EW BGC (V5)](https://geoportal.statistics.gov.uk/datasets/ons::lower-layer-super-output-areas-december-2021-boundaries-ew-bgc-v5-2/about)

**Step 4: Scripts to run**

Run the following scripts in `script` to create the required datasets:
- `excel_converter.py` - Creates a parquet dataset from the population excel file
  - `pop_density_2011_2022.parquet`
- `area_mapping.py` - Creates lookup table 
  - `uk_areas_lookup.parquet` 
  - `london_areas_lookup.parquet`
- `houses.py` - Creates the housing dataset
  - `housing.parquet`
- `imd_data.py` - Creates the 3 IMD datasets
  - `imd_2010.parquet`
  - `imd_2015.parquet`
  - `imd_2019.parquet`
- `residential.py` - Creates CSV file of residential dominant areas
  - `lsoa_residential_percent_2018.csv` in `data/geo`
  - `lsoa_residential_classification_2018.csv` in `data/geo`
- `geojson_converter.py` - Create geoparquet files
  - `LAD_shape.geoparquet` in `data/geo`
  - `WARD_shape.geoparquet` in `data/geo`
  - `LSOA_shape.geoparquet` in `data/geo`
- `spatial.py` - Creates spatial neighboring dataset
  - `spatial_neighbors.parquet`
- `burglary_geo_locations.py` - Creates JSON file with residential burglaries per LSOA (needed for dashboard)
  - `london_areas_with_burglaries.json` in `dashboard/data`

**Step 5: Build X and Y dataset for Machine Learning**

   ```bash
      python build_dataset.py
   ```

#### Complete Data Directory Structure
```
data/
├── all_crime_data_zips/                                # Raw police.uk crime data (extracted ZIP files)
├── auxilliary/                                         # Auxiliary data used for processing
├── lookup/                                             # Lookup tables tables for processing
├── geo/                                                # Geographic boundary files
│   ├── LAD_shape.geoparquet
│   ├── WARD_shape.geoparquet
│   ├── LSOA_shape.geoparquet
│   ├── lsoa_residential_percent_2018.csv
│   └── lsoa_residential_classification_2018.csv
├── features.parquet                                    # ML dataset with the features preserved
├── london_burglaries.parquet                           # Processed burglary dataset
├── london_areas_lookup.parquet                         # Lookup table for London
├── uk_areas_lookup.parquet
├── pop_density_2011_2022.parquet
├── imd_2010.parquet
├── imd_2015.parquet
├── imd_2019.parquet
├── housing.parquet
├── spatial_neighbors.parquet
├── X_test.parquet
├── X_train.parquet
├── y_test.parquet
└── y_train.parquet
```

---

## Machine Learning

This section is about running the 4 different ML models:

### 1. Catboost
Run `catboost_pipeline/catboost_optuna.py`

### 2. LightGBM
Run `lightgbm/lightgbm_optimized.py`

### 3. Random Forest
Run `randomforest/rf_optimized.py`

### 4. XGBoost
Run `xgBoost/xgboost_optimized.py`

### Outputs:
This should give the following outputs:

| Model             |  MAE   |  RMSE  |   R2   |
|:------------------|:------:|:------:|:------:|
| XGBoost           | 0.7813 | 1.0731 | 0.3113 |
| LightGBM          | 0.7882 | 1.0827 | 0.2989 |
| Random Forest     | 0.7897 | 1.0846 | 0.2964 |
| CatBoost          | 0.7938 | 1.0749 | 0.3090 |

---

## Dashboard
1. Run `script/lsoa_predictor.py`, this should create a file called: 
   - `data/london_future_predictions.json`
2. Run `xgBoost/transformative/transformation2.py`, this creates a file called:
   - `xgBoost/outputs/london_predictions_with_officers.json`
   - Copy this file into `dashboard/data`

To have the dashboard working correctly, the `data` folder in `dashboard` should look like:
```
data/
├── geo/                                                # Geographic boundary files
│   ├── LAD_shape.geoparquet
│   ├── WARD_shape.geoparquet
│   ├── LSOA_shape.geoparquet
├── features.parquet
├── london_areas_with_burglaries.json.parquet
└── london_predictions_with_officers.json.parquet
```

---

## Ethics

For the ethical evaluation, SHAP is used.
- The feature importance of the model run `xgBoost/ethics.py`
- To see how XGBoost decides for 1 instance run `xgBoost/eval_case.py`