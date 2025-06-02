from __future__ import annotations
from typing import Union
import polars as pl
import numpy as np
from .io import to_dataframe, to_lazyframe

DFLike = Union[str, pl.DataFrame, pl.LazyFrame]
WEIGHTS_CACHE: dict[int, list[int]] = {}

def normalize_time(df, date_col: str = "Month") -> pl.LazyFrame:
    """Adds normalized time columns.

    Args:
        df: Dataframe.
        date_col: Column name for date.

    Returns:
        pl.LazyFrame: LazyFrame with normalized time columns.
    """
    lf = to_lazyframe(df)

    # Parse Month column once
    lf = lf.with_columns(pl.col(date_col).str.strptime(pl.Date, "%Y-%m").alias("Month_dt"))

    # Compute min/max eager (small)
    _tmp = lf.select(pl.col("Month_dt").dt.year().min().alias("ymin"),
                     pl.col("Month_dt").dt.year().max().alias("ymax")).collect()
    ymin, ymax = _tmp.row(0)

    # Normalised index parameters
    idx_expr = (
        (pl.col("Month_dt").dt.year() - ymin) * 12 + (pl.col("Month_dt").dt.month() - 1)
    )
    _range = (ymax - ymin) * 12 or 1  # avoid zero-div

    return (
        lf.with_columns([
            pl.col("Month_dt").dt.year().alias("year"),
            pl.col("Month_dt").dt.month().alias("month"),
            # cyclic encodings
            np.sin((pl.col("Month_dt").dt.month() - 1) * (np.pi / 6)).alias("month_sin"),
            np.cos((pl.col("Month_dt").dt.month() - 1) * (np.pi / 6)).alias("month_cos"),
            # scaled index 0-1
            ((idx_expr - idx_expr.min()) / _range).alias("time_index_norm"),
        ])
        .drop("Month_dt")
    )

def _weights(n: int) -> list[int]:
    if n < 1:
        raise ValueError("period must be ≥ 1")
    return WEIGHTS_CACHE.setdefault(n, list(range(1, n + 1)))

def _nan_fill(s: pl.Expr | pl.Series) -> pl.Expr | pl.Series:
    return s.fill_null(float("nan"))

def _mask_nan_to_null(out: pl.Expr | pl.Series) -> pl.Expr | pl.Series:
    # restore the “proper” nulls for anything that became NaN
    return pl.when(out.is_nan()).then(None).otherwise(out)

def wma_pl(s: pl.Expr | pl.Series, period: int) -> pl.Expr | pl.Series:
    """Weighted Moving Average."""
    x = _nan_fill(s)
    wma = x.rolling_mean(
        window_size=period,
        weights=_weights(period),
        min_periods=period,
    )
    out = _mask_nan_to_null(wma)
    return out.clip(lower_bound=0)

def hma_pl(s: pl.Expr | pl.Series, period: int) -> pl.Expr | pl.Series:
    """Hull Moving Average."""
    half = period // 2
    root = int(np.sqrt(period))
    return wma_pl((wma_pl(s, half) * 2) - wma_pl(s, period), root)

def tema_pl(s: pl.Expr | pl.Series, period: int, *, adjust: bool = False) -> pl.Expr | pl.Series:
    """Triple Exponential Moving Average."""
    ema1 = s.ewm_mean(span=period, adjust=adjust)
    ema2 = ema1.ewm_mean(span=period, adjust=adjust)
    ema3 = ema2.ewm_mean(span=period, adjust=adjust)
    out = (ema1 * 3) - (ema2 * 3) + ema3
    return out.clip(lower_bound=0)

def safe_div(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    """num / den  → null when den is 0 or null"""
    return pl.when((den == 0) | den.is_null()).then(None).otherwise(num / den)

def add_temporal_features(df: DFLike, *, location_col: str = "LSOA code", target_col: str = "burglary_count") -> pl.LazyFrame:
    """Engineer lagged, rolling, seasonal and derived features.

    Feature columns will simply contain `null` for the early periods.
    """
    main = to_dataframe(df).sort([location_col, "year", "month"])

    # Lag features
    lags = (
        pl.col(target_col).shift(1).over(location_col).alias(f"{target_col}_lag_1"),
        pl.col(target_col).shift(3).over(location_col).alias(f"{target_col}_lag_3"),
        pl.col(target_col).shift(6).over(location_col).alias(f"{target_col}_lag_6"),
        pl.col(target_col).shift(12).over(location_col).alias(f"{target_col}_lag_12"),
    )

    # Exponential Weighted Moving averages
    ewms = (
        pl.col(target_col).ewm_mean(span=6, adjust=False).shift(1).over(location_col).alias(f"{target_col}_ewm_6"),
        pl.col(target_col).ewm_mean(span=12, adjust=False).shift(1).over(location_col).alias(f"{target_col}_ewm_12"),
        tema_pl(pl.col(target_col), 6).shift(1).over(location_col).alias(f"{target_col}_tema_6")
    )

    # Hull Moving average
    hmas = (
        hma_pl(pl.col(target_col), 4).shift(1).over(location_col).alias(f"{target_col}_hma_4"),
        hma_pl(pl.col(target_col), 5).shift(1).over(location_col).alias(f"{target_col}_hma_5"),
    )

    # Misc temporals
    extras = (
        pl.col(target_col).rolling_sum(12).shift(1).over(location_col).alias(f"{target_col}_sum_12"),

        pl.when(pl.col(target_col).rolling_sum(3) > 0).then(1).otherwise(0).shift(1).over(location_col)
        .alias(f"{target_col}_active_3"),

        # % change (t-3 vs t-6)
        safe_div(
            pl.col(target_col).shift(3) - pl.col(target_col).shift(6),
            pl.col(target_col).shift(6)
        ).over(location_col).alias(f"{target_col}_pct_change"),

        # σ / μ volatility over last 6 months
        safe_div(
            pl.col(target_col).shift(3).rolling_std(6),
            pl.col(target_col).shift(3).rolling_mean(6)
        ).over(location_col).alias(f"{target_col}_volatility_6m"),

        # short / long trend ratio
        safe_div(
            pl.col(target_col).shift(3).rolling_mean(3),
            pl.col(target_col).shift(9).rolling_mean(3)
        ).over(location_col).alias(f"{target_col}_trend_ratio"),
    )

    return (
        main.with_columns([
            *lags, *ewms, *hmas, *extras,
        ]).lazy()
    )