import polars as pl
from pathlib import Path
from typing import Dict, Set, Union
from collections import defaultdict
import json
import logging

# Type hints
LADDict = Dict[str, Union[str, Dict]]
LADDefaultDict = defaultdict

logger = logging.getLogger(__name__)


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


def load_burglary_data(parquet_path: str | Path, allowed_lsoas: Set[str]) -> Dict[str, Dict[str, list]]:
    """Load and process burglary data, grouped by LSOA code and then by month."""
    logger.info("Reading burglary parquet: %s", parquet_path)

    df = (
        pl.read_parquet(str(parquet_path))
        .select(["Month", "Longitude", "Latitude", "LSOA code"])
        .filter(
            (pl.col("LSOA code").is_in(allowed_lsoas)) &
            (pl.col("Longitude").is_not_null()) &
            (pl.col("Latitude").is_not_null()) &
            (pl.col("Month").is_not_null())
        )
        .rename({"LSOA code": "lsoa_code"})
    )

    # Group burglaries by LSOA code, then by month
    burglary_by_lsoa = {}

    for row in df.iter_rows(named=True):
        lsoa_code = row["lsoa_code"]
        month = row["Month"]

        if lsoa_code not in burglary_by_lsoa:
            burglary_by_lsoa[lsoa_code] = {}

        if month not in burglary_by_lsoa[lsoa_code]:
            burglary_by_lsoa[lsoa_code][month] = []

        burglary_by_lsoa[lsoa_code][month].append({
            "longitude": row["Longitude"],
            "latitude": row["Latitude"]
        })

    return burglary_by_lsoa


def integrate_burglary_data(areas_dict: Dict[str, LADDict], burglary_data: Dict[str, Dict[str, list]]) -> Dict[
    str, LADDict]:
    """Add burglary data to the areas dictionary structure."""
    logger.info("Integrating burglary data into areas structure")

    # Create a deep copy to avoid modifying the original
    integrated_dict = {}

    for lad_code, lad_data in areas_dict.items():
        integrated_dict[lad_code] = {
            "name": lad_data["name"],
            "wards": {}
        }

        for ward_code, ward_data in lad_data["wards"].items():
            integrated_dict[lad_code]["wards"][ward_code] = {
                "name": ward_data["name"],
                "lsoas": {}
            }

            for lsoa_code, lsoa_data in ward_data["lsoas"].items():
                # Add burglary data if available for this LSOA
                burglary_months = burglary_data.get(lsoa_code, {})

                # Calculate total burglaries across all months
                total_burglaries = sum(len(incidents) for incidents in burglary_months.values())

                # Sort months chronologically
                sorted_months = dict(sorted(burglary_months.items()))

                integrated_dict[lad_code]["wards"][ward_code]["lsoas"][lsoa_code] = {
                    "name": lsoa_data["name"],
                    "burglaries_by_month": sorted_months,
                    "total_burglary_count": total_burglaries,
                    "months_with_data": sorted(burglary_months.keys())
                }

    return integrated_dict


def get_residential_lsoas(csv_path: str | Path) -> Set[str]:
    """Extract LSOA codes that are residential dominant."""
    logger.info("Reading residential classification CSV: %s", csv_path)

    df = (
        pl.read_csv(str(csv_path))
        .filter(pl.col("is_residential_dominant") == True)
        .select("LSOA21CD")
    )

    residential_lsoas = set(df.to_series().to_list())
    logger.info(f"Found {len(residential_lsoas)} residential dominant LSOA codes")
    return residential_lsoas


def get_filtered_lsoas(burglary_path: str | Path, residential_path: str | Path) -> Set[str]:
    """Get LSOA codes that are both in burglary data AND residential dominant."""
    logger.info("Finding intersection of burglary LSOAs and residential LSOAs")

    # Get LSOAs from burglary data
    burglary_df = pl.read_parquet(str(burglary_path))
    burglary_lsoas = set(burglary_df.select("LSOA code").drop_nulls().to_series().to_list())

    # Get residential LSOAs
    residential_lsoas = get_residential_lsoas(residential_path)

    # Find intersection
    filtered_lsoas = burglary_lsoas.intersection(residential_lsoas)

    logger.info(f"Burglary LSOAs: {len(burglary_lsoas)}")
    logger.info(f"Residential LSOAs: {len(residential_lsoas)}")
    logger.info(f"Filtered LSOAs (intersection): {len(filtered_lsoas)}")

    return filtered_lsoas


def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # File paths
    lookup_path = "../data/london_areas_lookup.parquet"
    burglary_path = "../data/london_burglaries.parquet"
    residential_path = "../data/geo/lsoa_residential_classification_2018.csv"
    output_path = "../data/london_areas_with_burglaries.json"

    try:
        # Get LSOA codes that are both in burglary data AND residential dominant
        allowed_lsoas = get_filtered_lsoas(burglary_path, residential_path)

        # Create the base areas structure
        areas_dict = create_london_areas_dict(lookup_path, allowed_lsoas)
        logger.info(f"Created areas structure with {len(areas_dict)} LADs")

        # Load burglary data
        burglary_data = load_burglary_data(burglary_path, allowed_lsoas)
        logger.info(f"Loaded burglary data for {len(burglary_data)} LSOAs")

        # Integrate burglary data into areas structure
        integrated_data = integrate_burglary_data(areas_dict, burglary_data)

        # Calculate some statistics
        total_burglaries = sum(
            len(incidents)
            for lsoa_data in burglary_data.values()
            for incidents in lsoa_data.values()
        )
        logger.info(f"Total burglaries integrated: {total_burglaries}")

        # Get month range
        all_months = set()
        for lsoa_data in burglary_data.values():
            all_months.update(lsoa_data.keys())

        if all_months:
            month_range = f"{min(all_months)} to {max(all_months)}"
            logger.info(f"Data spans from {month_range}")

        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(integrated_data, f, indent=2)

        logger.info(f"Saved integrated data to {output_path}")

        # Print some summary statistics
        print(f"\nSummary:")
        print(f"- LADs (Local Authority Districts): {len(integrated_data)}")
        print(f"- Total burglaries in residential areas: {total_burglaries}")
        print(f"- Residential LSOAs with burglary data: {len(burglary_data)}")
        print(f"- Unique months in data: {len(all_months)}")
        if all_months:
            print(f"- Date range: {month_range}")
        print(f"- Output saved to: {output_path}")
        print(f"- Note: Only residential dominant LSOAs included")

    except Exception as e:
        logger.error(f"Error processing data: {e}")
        raise


if __name__ == "__main__":
    main()