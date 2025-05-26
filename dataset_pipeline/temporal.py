from __future__ import annotations
from typing import Union
import polars as pl
import numpy as np
from .io import to_dataframe, to_lazyframe

DFLike = Union[str, pl.DataFrame, pl.LazyFrame]

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


def add_temporal_features(df: DFLike, *, location_col: str = "LSOA code", target_col: str = "burglary_count") -> pl.LazyFrame:
    """Engineer lagged, rolling, seasonal and derived features.

    Feature columns will simply contain `null` for the early periods.
    """
    main = to_dataframe(df).sort([location_col, "year", "month"])

    return (
        main.with_columns([
            # 1 ── lags ───────────────────────────────────────────────
            pl.col(target_col).shift(3).over(location_col).alias(f"{target_col}_lag_3"),
            pl.col(target_col).shift(6).over(location_col).alias(f"{target_col}_lag_6"),
            pl.col(target_col).shift(12).over(location_col).alias(f"{target_col}_lag_12"),

            # 2 ── rolling stats on shifted data ─────────────────────
            pl.col(target_col).shift(3).rolling_mean(3).over(location_col).alias(f"{target_col}_avg_3m_lag3"),
            pl.col(target_col).shift(3).rolling_mean(6).over(location_col).alias(f"{target_col}_avg_6m_lag3"),
            pl.col(target_col).shift(3).rolling_std(6).over(location_col).alias(f"{target_col}_std_6m_lag3"),
            pl.col(target_col).shift(3).rolling_max(6).over(location_col).alias(f"{target_col}_max_6m_lag3"),
            pl.col(target_col).shift(3).rolling_min(6).over(location_col).alias(f"{target_col}_min_6m_lag3"),

            # 3 ── seasonal anchors ──────────────────────────────────
            pl.col(target_col).shift(12).over(location_col).alias(f"{target_col}_same_month_last_year"),
            pl.col(target_col).shift(24).over(location_col).alias(f"{target_col}_same_month_2_years_ago"),

            # 4 ── safe differences ──────────────────────────────────
            (pl.col(target_col).shift(3) - pl.col(target_col).shift(6)).over(location_col).alias(f"{target_col}_diff_3m_6m"),
            (pl.col(target_col).shift(3) - pl.col(target_col).shift(12)).over(location_col).alias(f"{target_col}_diff_3m_12m"),

            # 5 ── percentage changes ────────────────────────────────
            ((pl.col(target_col).shift(3) - pl.col(target_col).shift(6)) / (pl.col(target_col).shift(6) + 0.1)).over(location_col).alias(f"{target_col}_pct_change_3m_6m"),
            ((pl.col(target_col).shift(3) - pl.col(target_col).shift(15)) / (pl.col(target_col).shift(15) + 0.1)).over(location_col).alias(f"{target_col}_pct_change_3m_15m"),

            # 6 ── volatility ────────────────────────────────────────
            (pl.col(target_col).shift(3).rolling_std(6) / (pl.col(target_col).shift(3).rolling_mean(6) + 0.1)).over(location_col).alias(f"{target_col}_volatility_6m"),

            # 7 ── trend indicator ───────────────────────────────────
            (pl.col(target_col).shift(3).rolling_mean(3) / (pl.col(target_col).shift(9).rolling_mean(3) + 0.1)).over(location_col).alias(f"{target_col}_trend_ratio"),

            # 8 ── **EWM-weighted lag (NEW)** ─────────────────────────
            pl.col(target_col).ewm_mean(span=12, adjust=False).shift(1).over(location_col).alias(f"{target_col}_ewm_12"),
        ]).with_columns([
            (pl.col(f"{target_col}_lag_3") / (pl.col(f"{target_col}_same_month_last_year") + 0.1)).alias(f"{target_col}_vs_seasonal"),
            (pl.col(f"{target_col}_std_6m_lag3") / (pl.col(f"{target_col}_avg_6m_lag3") + 0.1)).alias(f"{target_col}_cv_6m"),
            ((pl.col(f"{target_col}_max_6m_lag3") - pl.col(f"{target_col}_min_6m_lag3")) / (pl.col(f"{target_col}_avg_6m_lag3") + 0.1)).alias(f"{target_col}_range_normalized"),
        ])
    ).lazy()