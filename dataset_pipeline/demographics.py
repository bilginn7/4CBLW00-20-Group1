import polars as pl
from .io import to_dataframe
from . import settings as _S
from typing import List

def _load_pop(path=_S.POP_PATH, loc="LSOA code") -> pl.DataFrame:
    pop = pl.read_parquet(path)
    if "LSOA 2021 Code" in pop.columns:
        pop = pop.rename({"LSOA 2021 Code": loc})
    return pop


def load_population_long(path=_S.POP_PATH, loc="LSOA code") -> pl.DataFrame:
    pop = _load_pop(path, loc)
    pop_cols = [c for c in pop.columns if "Mid-" in c and "Population" in c]
    dens_cols = [c for c in pop.columns if "Mid-" in c and "Sq Km" in c]

    pop_long = (
        pop.select([loc]+pop_cols)
            .melt(id_vars=[loc], variable_name="year_col", value_name="population")
            .with_columns(pl.col("year_col").str.extract(r"(\d{4})").cast(pl.Int32).alias("year"))
            .drop("year_col")
    )

    dens_long = (
        pop.select([loc]+dens_cols)
            .melt(id_vars=[loc], variable_name="year_col", value_name="population_density")
            .with_columns(pl.col("year_col").str.extract(r"(\d{4})").cast(pl.Int32).alias("year"))
            .drop("year_col")
    )

    return pop_long.join(dens_long, on=[loc,"year"], how="inner")


def predict_missing_years(
    pop_data: pl.DataFrame,
    missing_years: List[int],
    loc: str = "LSOA code",
) -> pl.DataFrame:
    """Linear-trend extrapolation when burglars out-run the ONS :)"""
    trends = (
        pop_data.group_by(loc).agg([
            pl.col("population").first().alias("pop_start"),
            pl.col("population").last().alias("pop_end"),
            pl.col("population_density").first().alias("dens_start"),
            pl.col("population_density").last().alias("dens_end"),
            pl.col("year").min().alias("yr_start"),
            pl.col("year").max().alias("yr_end"),
        ])
        .with_columns([
            ((pl.col("pop_end")  - pl.col("pop_start"))  / (pl.col("yr_end") - pl.col("yr_start")))
            .alias("pop_trend"),
            ((pl.col("dens_end") - pl.col("dens_start")) / (pl.col("yr_end") - pl.col("yr_start")))
            .alias("dens_trend"),
        ])
    )

    rows = []
    for y in missing_years:
        rows.append(
            trends.with_columns([
                pl.lit(y).alias("year"),
                (pl.col("pop_end")  + pl.col("pop_trend")  * (y - pl.col("yr_end"))).round().cast(pl.Int64)
                    .alias("population"),
                (pl.col("dens_end") + pl.col("dens_trend") * (y - pl.col("yr_end")))
                    .alias("population_density"),
            ]).select([loc, "year", "population", "population_density"])
        )
    return pl.concat(rows)


def add_population_data(
    df,
    pop_path: str = _S.POP_PATH,
    loc: str = "LSOA code",
) -> pl.DataFrame:
    """Attach population & density columns to the burglary table (and predict future years)."""
    main = to_dataframe(df)
    pop  = load_population_long(pop_path, loc)

    main_years = main.get_column("year").unique().to_list()
    pop_years  = pop.get_column("year").unique().to_list()
    missing    = [y for y in main_years if y not in pop_years]

    if missing:
        preds = predict_missing_years(pop, missing, loc)
        schema = [loc, "year", "population", "population_density"]
        pop    = pop.select(schema)
        preds  = preds.select(schema)

        pop = pl.concat([pop, preds], rechunk=True)

    return main.join(pop, on=[loc, "year"], how="left")

def add_imd_data(
    df,
    imd10: str = _S.IMD_2010_PATH,
    imd15: str = _S.IMD_2015_PATH,
    imd19: str = _S.IMD_2019_PATH,
    loc: str = "LSOA code",
) -> pl.DataFrame:
    """Join the right IMD snapshot for the given year."""
    main     = to_dataframe(df)
    imd_2010 = pl.read_parquet(imd10)
    imd_2015 = pl.read_parquet(imd15)
    imd_2019 = pl.read_parquet(imd19)

    return pl.concat([
        main.filter(pl.col("year").is_between(2010, 2014)).join(imd_2010, on=loc, how="left"),
        main.filter(pl.col("year").is_between(2015, 2018)).join(imd_2015, on=loc, how="left"),
        main.filter(pl.col("year") >= 2019).join(imd_2019, on=loc, how="left"),
    ]).sort([loc, "year", "month"])


def add_housing_data(
    df,
    housing_path: str = _S.HOUSING_PATH,
    loc: str = "LSOA code",
) -> pl.DataFrame:
    """Join property-type fractions; drop AREA_NAME and fill nulls with 0."""
    main = to_dataframe(df)
    hdf  = pl.read_parquet(housing_path).drop("AREA_NAME")

    joined = main.join(hdf, on=loc, how="left")
    h_cols = [c for c in hdf.columns if c != loc]
    return joined.with_columns(pl.col(h_cols).fill_null(0))