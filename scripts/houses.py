import polars as pl


def main():
    """
    Process housing data for London LSOAs and save to parquet.
    """
    # Read CSV with null value handling
    houses = pl.read_csv(
        "../data/auxilliary/dwelling-property-type-2015-lsoa-msoa.csv",
        null_values=["-"]
    ).fill_null(0)

    # Keep only these columns as strings, cast everything else to integers
    text_cols = ['GEOGRAPHY', 'ECODE', 'AREA_NAME', 'BAND']

    houses = houses.with_columns([
        # Handle both string and numeric columns - convert to string first, clean, then cast to int
        pl.exclude(text_cols).cast(pl.String).str.replace_all(r'[",]', '').cast(pl.Int64, strict=False)
    ])

    # Load the London lookup table
    lookup = pl.read_parquet("../data/london_areas_lookup.parquet")

    # Get unique London LSOA codes from the lookup and cast to string
    london_lsoas = lookup.select("LSOA21CD").unique().with_columns(
        pl.col("LSOA21CD").cast(pl.String)
    )

    # Filter for Band='All' AND Geography='LSOA', then join with London LSOAs
    houses_london = houses.filter(
        (pl.col("BAND") == 'All') & (pl.col("GEOGRAPHY") == 'LSOA')
    ).join(
        london_lsoas,
        left_on="ECODE",
        right_on="LSOA21CD",
        how="inner"
    ).fill_null(0)  # Fill any nulls that appeared after the join

    # Rename ECODE to match other datasets and drop unnecessary columns
    houses_london = houses_london.rename({"ECODE": "LSOA code"}).drop([
        "GEOGRAPHY",
        "BAND"
    ])

    # Save to parquet
    houses_london.write_parquet("../data/housing.parquet")

    print(f"London LSOA records: {houses_london.height}")
    print(f"Unique London LSOAs: {houses_london['LSOA code'].n_unique()}")
    print("Housing data saved to ../data/housing.parquet")


if __name__ == "__main__":
    main()