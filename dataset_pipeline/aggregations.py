import polars as pl
from .io import to_dataframe

def create_full_grid(df, location_col="LSOA code", count_col="burglary_count") -> pl.DataFrame:
    data = to_dataframe(df)
    unique_locations = data.select(location_col).unique()
    unique_months = data.select(["year","month","month_sin","month_cos","time_index_norm"]).unique()
    full_grid = unique_locations.join(unique_months, how="cross")

    aggregated = (
        data.group_by([location_col,"year","month"])
            .agg(pl.len().alias(count_col))
    )

    return (
        full_grid.join(aggregated, on=[location_col,"year","month"], how="left")
                 .with_columns(pl.col(count_col).fill_null(0))
    )


def is_holiday_month(df, month_col="month") -> pl.Expr:
    """Boolean expression marking UK extended-holiday months."""
    return pl.col(month_col).is_in([4,7,8,10,12])
