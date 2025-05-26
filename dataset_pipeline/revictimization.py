import polars as pl
from .io import to_dataframe

def _timing_factor(lag_expr: pl.Expr) -> pl.Expr:
    val = 0.106 * lag_expr.pow(-0.383) - 0.018
    return pl.when(lag_expr <= 0).then(0.0).otherwise(pl.max_horizontal(val, pl.lit(0.0)))

def add_revictimization_risk(df, max_lag=24, prob=0.134) -> pl.DataFrame:
    df = to_dataframe(df).clone()
    df = df.with_columns(pl.datetime(pl.col("year"), pl.col("month"), 1).alias("month_dt"))
    df = df.sort(["LSOA code","month_dt"])

    lag_cols = [(
        pl.col("burglary_count").shift(l).over("LSOA code").fill_null(0) * _timing_factor(pl.lit(float(l)))
    ).alias(f"lag_{l}_w") for l in range(1, max_lag+1)]

    df = df.with_columns(lag_cols)
    df = df.with_columns(
        (prob * pl.sum_horizontal([f"lag_{l}_w" for l in range(1, max_lag+1)]))
        .alias("revictimization_risk")
    ).drop([f"lag_{l}_w" for l in range(1, max_lag+1)] + ["month_dt"])

    return df
