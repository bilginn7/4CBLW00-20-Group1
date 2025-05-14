from __future__ import annotations
import polars as pl
from pathlib import Path
from functools import reduce
from typing import Sequence, Iterable, Dict, Mapping, Any


def scan_lookup_csv(path: str | Path, columns: Iterable[str],
                    categorical: Iterable[str] | None = None, **scan_kwargs) -> pl.LazyFrame:
    """Scan path and keep wanted columns.
    Makes use of LazyFrame.

    Args:
        path: File path.
        columns: Columns to scan.
        categorical: Categorical columns to scan.
        **scan_kwargs: Passed to LazyFrame.

    Returns:
        pl.LazyFrame: LazyFrame of CSV file.
    """
    columns = list(columns)
    if categorical is None:
        categorical = [c for c in columns if c.endswith(("CD", "IND"))]

    overrides: Dict[str, pl.PolarsDataType] = {
        c: pl.Categorical for c in categorical
    }

    return (
        pl.scan_csv(Path(path), schema_overrides=overrides, **scan_kwargs)
        .select(columns)
    )

def build_lookup_parquet(out_file: str | Path, key: str, file_specs: Sequence[dict],
                         parquet_kwargs: Mapping[str, Any] | None = None, filter_func=None) -> None:
    """Build a parquet file.

    Args:
        out_file: Output file.
        key: Column key.
        file_specs: File specifications.
        parquet_kwargs: Passed to LazyFrame.
        filter_func: Optional function to filter rows before saving.
    """
    parquet_kwargs = dict(parquet_kwargs or {})
    lazy_frames = [scan_lookup_csv(**spec) for spec in file_specs]

    with pl.StringCache():
        lookup = reduce(lambda l, r: l.join(r, on=key, how="left"), lazy_frames)
        lookup = lookup.select([c for c in ORDER if c in lookup.collect_schema().names()])

        # Apply filter if provided
        if filter_func is not None:
            lookup = lookup.filter(filter_func)

        lookup.sink_parquet(
            out_file,
            compression="zstd",
            statistics=True,
            **parquet_kwargs,
        )

if __name__ == "__main__":
    SPECS = [
        {  # 1: OA → LSOA → MSOA (188k rows)
            "path": "../data/lookup/Output_Area_to_Lower_layer_Super_Output_Area_to_Middle_layer_Super_Output_Area_to_Local_Authority_District_(December_2021)_Lookup_in_England_and_Wales_v3.csv",
            "columns": ["OA21CD",
                        "LSOA21CD", "LSOA21NM",
                        "MSOA21CD", "MSOA21NM"],
        },
        {  # 2: LSOA11 → LSOA21 → LAD (35k rows)
            "path": "../data/lookup/LSOA_(2011)_to_LSOA_(2021)_to_Local_Authority_District_(2022)_Exact_Fit_Lookup_for_EW_(V3).csv",
            "columns": ["LSOA21CD", "LSOA11CD", "CHGIND",
                        "LAD22CD",  "LAD22NM"],
        },
        {  # 3: LSOA21 → Ward24 (35k rows)
            "path": "../data/lookup/LSOA_(2021)_to_Electoral_Ward_(2024)_to_LAD_(2024)_Best_Fit_Lookup_in_EW.csv",
            "columns": ["LSOA21CD", "WD24CD", "WD24NM"],
        },
    ]

    ORDER = [
        "OA21CD",
        "LSOA21CD", "LSOA21NM",
        "LSOA11CD", "CHGIND",
        "MSOA21CD", "MSOA21NM",
        "WD24CD", "WD24NM",
        "LAD22CD", "LAD22NM",
    ]

    build_lookup_parquet(
        out_file="../data/uk_areas_lookup.parquet",
        key="LSOA21CD",
        file_specs=SPECS,
    )

    build_lookup_parquet(
        out_file="../data/london_areas_lookup.parquet",
        key="LSOA21CD",
        file_specs=SPECS,
        filter_func=pl.col("LAD22CD").cast(pl.Utf8).str.starts_with("E09")
    )