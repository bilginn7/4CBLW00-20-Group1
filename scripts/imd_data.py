from excel_converter import data_processing
import polars as pl


def update_lsoa_codes(file_path, lookup):
    df = pl.read_parquet(file_path).unique(subset=["LSOA code (2011)"])
    lookup_clean = lookup.with_columns([
        pl.col("LSOA11CD").cast(pl.String),
        pl.col("LSOA21CD").cast(pl.String)
    ])

    # Join to get all mappings
    joined = df.with_columns(pl.col("LSOA code (2011)").cast(pl.String)).join(
        lookup_clean,
        left_on="LSOA code (2011)",
        right_on="LSOA11CD",
        how="right"
    ).drop("LSOA11CD")

    # Handle boundary changes by grouping by 2021 code
    numeric_cols = [col for col in df.columns if df[col].dtype.is_numeric()]

    # Group by 2021 code and aggregate
    agg_exprs = []
    for col in numeric_cols:
        if col in joined.columns:
            agg_exprs.append(pl.col(col).mean().alias(col))

    updated = joined.group_by("LSOA21CD").agg(agg_exprs).rename({"LSOA21CD": "LSOA code"})

    # Reorder columns
    final_cols = ["LSOA code"] + [col for col in numeric_cols if col in updated.columns]
    updated = updated.select(final_cols)

    updated.write_parquet(file_path)
    return updated

def main():
    """
    Writes IMD data to parquet files.
    """
    data_processing(data='ID 2010 for London.xls', sheet='IMD 2010', cols=[0, 7, 9, 11, 13, 15, 17, 19, 21], header=0, output='imd_2010')
    data_processing(data='ID 2015 for London.xls', sheet='IMD 2015', cols=[0, 4, 7, 10, 13, 16, 19, 22, 25], header=0, output='imd_2015')
    data_processing(data='ID 2019 for London.xlsx', sheet='IMD 2019', cols=[0, 4, 7, 10, 13, 16, 19, 22, 25], header=0, output='imd_2019')

    # Read files
    imd_2019 = pl.read_parquet("../data/imd_2019.parquet")
    imd_2015 = pl.read_parquet("../data/imd_2015.parquet")
    imd_2010 = pl.read_parquet("../data/imd_2010.parquet")

    # Fix 2019 IMD column name
    imd_2019_fixed = imd_2019.rename({"Index of Multiple Deprivation (IMD) Score": "IMD Score"})

    # Direct mapping
    mapping = {
        "LSOA": "LSOA code (2011)",
        "IMD SCORE": "IMD Score",
        "INCOME SCORE": "Income Score (rate)",
        "EMPLOYMENT SCORE": "Employment Score (rate)",
        "EDUCATION SKILLS AND TRAINING SCORE": "Education, Skills and Training Score",
        "HEALTH DEPRIVATION AND DISABILITY SCORE": "Health Deprivation and Disability Score",
        "CRIME AND DISORDER SCORE": "Crime Score",
        "BARRIERS TO HOUSING AND SERVICES SCORE": "Barriers to Housing and Services Score",
        "LIVING ENVIRONMENT SCORE": "Living Environment Score"
    }

    imd_2010_fixed = imd_2010.rename(mapping).select(imd_2015.columns)

    # Save fixed files
    imd_2019_fixed.write_parquet("../data/imd_2019.parquet")
    imd_2010_fixed.write_parquet("../data/imd_2010.parquet")

    lookup = pl.read_parquet("../data/london_areas_lookup.parquet")
    # Update all files
    for file in ["../data/imd_2010.parquet", "../data/imd_2015.parquet", "../data/imd_2019.parquet"]:
        update_lsoa_codes(file, lookup)

if __name__ == "__main__":
    main()