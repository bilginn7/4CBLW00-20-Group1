import pandas as pd


def main():
    # Read the land cover data
    df = pd.read_csv("../data/auxilliary/lsoa_land_cover.csv")

    # Read London areas lookup data
    codes_2021 = pd.read_parquet("../data/london_areas_lookup.parquet", engine="fastparquet")
    lookup_mapping = codes_2021.drop_duplicates(["LSOA11CD"]).set_index("LSOA11CD")["LSOA21CD"].to_dict()

    # Map LSOA codes (add London mapping early)
    df["LSOA21CD"] = df["LSOA11CD"].map(lookup_mapping)

    # Define residential columns for 2018
    res_cols_2018 = [
        "Continuous urban fabric [111] (2018)",
        "Discontinuous urban fabric [112] (2018)"
    ]

    # Identify all columns containing '2018'
    cols_2018 = [col for col in df.columns if "(2018)" in col]
    non_res_cols = [col for col in cols_2018 if col not in res_cols_2018]

    # Calculate residential percentage for 2018
    df["residential_pct_2018"] = df[res_cols_2018].sum(axis=1)

    # Calculate additional metrics for dominance analysis
    df["max_non_residential_pct"] = df[non_res_cols].max(axis=1)
    df["is_residential_dominant"] = df["residential_pct_2018"] > df["max_non_residential_pct"]
    df["residential_advantage"] = df["residential_pct_2018"] - df["max_non_residential_pct"]

    # Create first output: basic residential percentage data
    output_df = df[["LSOA11CD", "LSOA11NM", "residential_pct_2018"]]
    output_df.to_csv("../data/geo/lsoa_residential_percent_2018.csv", index=False)

    # Create London-specific dataframe
    london_df = df[df["LSOA21CD"].notna()]

    # Create second output: London classification data with dominance metrics
    output_df2 = london_df[["LSOA11CD", "LSOA21CD", "LSOA11NM", "residential_pct_2018",
                            "is_residential_dominant", "residential_advantage"]]
    output_df2.to_csv("../data/geo/lsoa_residential_classification_2018.csv", index=False)

    print("Data processing complete!")
    print(f"Total LSOAs processed: {len(df)}")
    print(f"London LSOAs: {len(london_df)}")
    print(f"Residential dominant areas in London: {london_df['is_residential_dominant'].sum()}")


if __name__ == "__main__":
    main()