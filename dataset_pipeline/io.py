import polars as pl
from typing import Union, overload
from pathlib import Path
from . import settings as _S

PathLike = Union[str, Path]
DFLike   = Union[PathLike, pl.DataFrame, pl.LazyFrame]

@overload
def to_lazyframe(df: str) -> pl.LazyFrame: ...
@overload
def to_lazyframe(df: pl.DataFrame) -> pl.LazyFrame: ...
@overload
def to_lazyframe(df: pl.LazyFrame) -> pl.LazyFrame: ...


def to_lazyframe(df: DFLike) -> pl.LazyFrame:
    if isinstance(df, (str, Path)):
        return pl.scan_parquet(df)
    if isinstance(df, pl.DataFrame):
        return df.lazy()
    if isinstance(df, pl.LazyFrame):
        return df
    raise TypeError("df must be path, DataFrame or LazyFrame")


def to_dataframe(df: DFLike) -> pl.DataFrame:
    if isinstance(df, (str, Path)):
        return pl.read_parquet(df)
    if isinstance(df, pl.DataFrame):
        return df
    if isinstance(df, pl.LazyFrame):
        return df.collect()
    raise TypeError("df must be path, DataFrame or LazyFrame")
