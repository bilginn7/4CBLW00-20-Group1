import polars as pl
from . import settings as _S

def add_neighbor_features(main_df: pl.DataFrame,
                          neighbors_path=_S.NEIGH_PATH,
                          location_col="LSOA code",
                          target="burglary_count") -> pl.DataFrame:

    neighbors = pl.read_parquet(neighbors_path)

    expanded = main_df.join(
        neighbors,
        left_on=location_col,
        right_on="lsoa_code",
        how="left"
    ).join(
        main_df.select([location_col,"year","month",target]),
        left_on=["neighbor_code","year","month"],
        right_on=[location_col,"year","month"],
        how="left",
        suffix="_neighbor"
    )

    neighbor_weighted = expanded.with_columns([
        (1/(pl.col("distance")+100)).alias("w"),
        (pl.col("burglary_count_neighbor")/ (pl.col("distance")+100)).alias("w_val")
    ])

    spatial_features = neighbor_weighted.group_by([location_col,"year","month"]).agg([
        pl.col("burglary_count_neighbor").mean().alias("neighbor_burglary_avg"),
        pl.col("burglary_count_neighbor").max().alias("neighbor_burglary_max"),
        pl.col("burglary_count_neighbor").std().alias("neighbor_burglary_std"),
        (pl.col("w_val").sum() / pl.col("w").sum()).alias("neighbor_burglary_weighted_avg"),
        pl.col("burglary_count_neighbor").filter(pl.col("neighbor_rank")==1).first().alias("closest_neighbor_burglary")
    ])

    return main_df.join(spatial_features, on=[location_col,"year","month"], how="left")


def filter_residential_lsoas(df: pl.DataFrame,
                           lsoa_col: str = "LSOA code",
                           residential_classification_path: str = _S.RES_CLASS_PATH) -> pl.DataFrame:
    """Filter dataframe to only include residential-dominant LSOAs"""

    residential_df = pl.read_csv(residential_classification_path)

    residential_lsoas = residential_df.filter(
        pl.col("is_residential_dominant") == True
    ).select("LSOA21CD").to_series().to_list()

    # Filter the main dataframe
    return df.filter(pl.col(lsoa_col).is_in(residential_lsoas))