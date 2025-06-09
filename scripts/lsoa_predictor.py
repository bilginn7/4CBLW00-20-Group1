from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, DefaultDict, Dict, Tuple, Set

import pandas as pd
import polars as pl
import xgboost as xgb
from xgBoost.predict_future import predict_month_range

# ─────────────────────────────── Logging ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lsoa_predictor")

# ──────────────────────────── Type aliases ──────────────────────────────
LSOADict = Dict[str, Dict[str, str]]      # LSOA code -> {"name": lsoa_name}
WardDict = Dict[str, Any]                 # {"name": ward_name, "lsoas": LSOADict}
LADDict  = Dict[str, Any]                 # {"name": lad_name,  "wards": Dict[str, WardDict]}
WardDefaultDict = DefaultDict[str, Dict[str, Any]]
LADDefaultDict  = DefaultDict[str, Dict[str, Any]]

# ─────────────────────────── Helper functions ───────────────────────────

def parse_year_month(value: str) -> Tuple[int, int]:
    """Convert *YYYY-MM* to ``(year, month)`` ints for CLI parsing."""
    try:
        y, m = value.split("-")
        year, month = int(y), int(m)
        if not 1 <= month <= 12:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date must be YYYY-MM with month 1–12") from exc
    return year, month


def create_london_areas_dict(parquet_path: str | Path, allowed_lsoas: Set[str]) -> Dict[str, LADDict]:
    """Return a nested {LAD → Ward → LSOA} dict **restricted** to *allowed_lsoas*."""
    logger.info("Reading lookup parquet: %s", parquet_path)
    df = (
        pl.read_parquet(str(parquet_path))
        .drop(["OA21CD", "CHGIND", "LSOA11CD"])
        .unique(subset=["LSOA21CD"], keep="first")
        .filter(pl.col("LSOA21CD").is_in(allowed_lsoas))
    )

    nested: LADDefaultDict = defaultdict(
        lambda: {"name": "", "wards": defaultdict(lambda: {"name": "", "lsoas": {}})}
    )

    for row in df.iter_rows(named=True):
        nested[row["LAD22CD"]]["name"] = row["LAD22NM"]
        nested[row["LAD22CD"]]["wards"][row["WD24CD"]]["name"] = row["WD24NM"]
        nested[row["LAD22CD"]]["wards"][row["WD24CD"]]["lsoas"][row["LSOA21CD"]] = {
            "name": row["LSOA21NM"],
        }

    # DefaultDict → dict for JSON serialisation
    return {
        lad_code: {
            "name": lad_data["name"],
            "wards": {
                ward_code: {
                    "name": ward_data["name"],
                    "lsoas": dict(ward_data["lsoas"]),
                }
                for ward_code, ward_data in lad_data["wards"].items()
            },
        }
        for lad_code, lad_data in nested.items()
    }


def attach_predictions(
    lookup_tree: Dict[str, LADDict],
    predictions: pd.DataFrame,
    date_fmt: str = "{year}-{month:02d}",
) -> Dict[str, LADDict]:
    """Attach a ``"predictions"`` mapping to each LSOA in *lookup_tree*."""
    logger.info("Merging predictions into lookup tree …")
    tree = deepcopy(lookup_tree)

    by_lsoa = predictions.groupby("LSOA_code", observed=True)
    for lsoa_code, frame in by_lsoa:
        month_map = {
            date_fmt.format(year=int(r.year), month=int(r.month)): float(r.prediction)
            for r in frame.itertuples(index=False)
        }

        for lad in tree.values():
            ward_found = next((w for w in lad["wards"].values() if lsoa_code in w["lsoas"]), None)
            if ward_found:
                ward_found["lsoas"][lsoa_code]["predictions"] = month_map
                break
    return tree

# ──────────────────────────────── CLI ───────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create JSON with predictions attached to LSOA lookup tree (predicted codes only)")
    p.add_argument("--model-path", required=True, type=Path, help="path to XGBoost .json model")
    p.add_argument("--features-path", required=True, type=Path, help="path to X_test parquet")
    p.add_argument("--lookup-path", required=True, type=Path, help="path to london_areas_lookup.parquet")
    p.add_argument("--start", required=True, type=parse_year_month, help="first forecast month YYYY-MM")
    p.add_argument("--end",   required=True, type=parse_year_month, help="last forecast month YYYY-MM (inclusive)")
    p.add_argument("--output", type=Path, default=Path("../data/london_future_predictions.json"), help="JSON output path")
    p.add_argument("--lsoa-col", default="LSOA code", help="LSOA column name in features file")
    return p


def main() -> None:  # pragma: no cover
    args = build_parser().parse_args()

    start_year, start_month = args.start
    end_year,   end_month   = args.end

    # 1) Load XGBoost model
    logger.info("Loading XGBoost model …")
    model = xgb.XGBRegressor()
    model.load_model(str(args.model_path))

    # 2) Load feature template (no residential filtering)
    logger.info("Loading feature template …")
    X_template = pd.read_parquet(args.features_path)
    X_template[args.lsoa_col] = X_template[args.lsoa_col].astype("category")

    # 3) Forecast
    preds = predict_month_range(
        model=model,
        X_template=X_template,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        lsoa_col=args.lsoa_col,
    )

    allowed_lsoas: Set[str] = set(preds["LSOA_code"].unique())
    logger.info("Number of LSOAs predicted: %s", len(allowed_lsoas))

    # 4) Build lookup tree restricted to predicted LSOAs
    lookup = create_london_areas_dict(args.lookup_path, allowed_lsoas)

    # 5) Merge predictions
    enriched = attach_predictions(lookup, preds)

    # 6) Save JSON
    logger.info("Writing output JSON => %s", args.output)
    args.output.write_text(json.dumps(enriched, ensure_ascii=False, indent=2))
    logger.info("Done ✔")


if __name__ == "__main__":
    """Run from IDE without CLI flags by injecting defaults."""
    import sys

    if len(sys.argv) == 1:
        logger.info("No command‑line arguments detected – falling back to hard‑coded defaults.")
        root = Path(__file__).resolve().parent.parent  # project root
        sys.argv += [
            "--model-path", str(root / "xgBoost" / "final_xgboost_model.json"),
            "--features-path", str(root / "data" / "X_test.parquet"),
            "--lookup-path", str(root / "data" / "london_areas_lookup.parquet"),
            "--start", "2025-03",
            "--end", "2025-12",
            # --output omitted -> default
        ]
        logger.info("Injected default arguments: %s", " ".join(sys.argv[1:]))

    main()