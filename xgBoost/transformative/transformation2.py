#!/usr/bin/env python3
"""
transformative_enhanced.py

This version calculates officer assignments and integrates them directly into the JSON structure,
adding both daily and hourly officer assignments alongside the existing predictions.

The enhanced JSON structure will look like:
{
  "E09000021": {
    "name": "Kingston upon Thames",
    "wards": {
      "E05013944": {
        "name": "Surbiton Hill",
        "lsoas": {
          "E01002995": {
            "name": "Kingston upon Thames 013D",
            "predictions": { "2025-03": 0.218, ... },
            "officer_assignments": {
              "daily": { "2025-03": 5, "2025-04": 3, ... },
              "hourly": {
                "2025-03": [0,0,0,0,0,1,2,2,1,1,0,0,0,0,0,1,1,1,1,1,0,0,0,0],
                "2025-04": [0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0],
                ...
              }
            }
          }
        }
      }
    }
  }
}

Usage:  python transformative_enhanced.py
"""

import json
import csv
import sys
from pathlib import Path

# ─── USER‐EDITABLE SETTINGS ────────────────────────────────────────────────────
# Path to your JSON file of future predictions
INPUT_JSON = "xgBoost/outputs/london_future_predictions.json"

# Output paths - will be created if they don't exist
OUTPUT_JSON = "outputs/london_predictions_with_officers.json"  # Write to outputs folder
OUTPUT_CSV_DAILY = "outputs/officer_assignment_daily_all_months.csv"
OUTPUT_CSV_HOURLY = "outputs/officer_assignment_hourly_all_months.csv"

# Months to calculate assignments for (you can add/remove as needed)
TARGET_MONTHS = ["2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11",
                 "2025-12"]
# ──────────────────────────────────────────────────────────────────────────────


# ─── Hourly burglary distribution (replace with your actual data) ─────────────
HOURLY_BURGLARY_COUNTS = [
    100, 80, 50, 40, 150, 600, 1550, 2050,
    1780, 1320, 980, 680, 520, 450, 480, 550,
    620, 780, 850, 830, 740, 705, 690, 500
]


def load_predictions(json_path: Path) -> dict:
    """Load and return the nested prediction dictionary from the JSON file."""

    # Try multiple possible paths - adjusted for running from transformative folder
    possible_paths = [
        json_path,
        Path("london_future_predictions.json"),  # Current directory
        Path("outputs/london_future_predictions.json"),  # outputs subfolder
        Path("../outputs/london_future_predictions.json"),  # up to xgBoost then outputs
        Path("../../xgBoost/outputs/london_future_predictions.json"),  # up to root then full path
    ]

    for path_to_try in possible_paths:
        try:
            if path_to_try.exists():
                print(f"Found JSON file at: {path_to_try}")
                with path_to_try.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
        except Exception as e:
            continue

    # If none of the paths worked, show detailed error
    print(f"Could not find JSON file. Tried these paths:", file=sys.stderr)
    for path_to_try in possible_paths:
        print(f"  - {path_to_try.absolute()} (exists: {path_to_try.exists()})", file=sys.stderr)
    print(f"Current working directory: {Path.cwd()}", file=sys.stderr)
    sys.exit(1)


def compute_hourly_fractions(hourly_counts: list) -> list:
    """Convert raw hourly counts to fractions that sum to 1.0."""
    total = float(sum(hourly_counts))
    if total <= 0:
        return [1.0 / 24.0] * 24
    return [cnt / total for cnt in hourly_counts]


def allocate_officers_for_month(pred_data: dict, target_month: str) -> dict:
    """
    Calculate officer assignments for a specific month and return a structured dict
    organized by borough -> ward -> lsoa with both daily and hourly assignments.
    """
    hourly_fractions = compute_hourly_fractions(HOURLY_BURGLARY_COUNTS)
    max_frac = max(hourly_fractions)
    busiest_hour_index = [i for i, f in enumerate(hourly_fractions) if f == max_frac][0]

    assignments = {}

    for borough_code, borough_entry in pred_data.items():
        assignments[borough_code] = {}
        wards_dict = borough_entry.get("wards", {})

        for ward_code, ward_entry in wards_dict.items():
            assignments[borough_code][ward_code] = {}
            lsoas_dict = ward_entry.get("lsoas", {})

            # Gather LSOA scores for this ward
            lsoa_scores = []
            for lsoa_code, lsoa_entry in lsoas_dict.items():
                preds = lsoa_entry.get("predictions", {})
                score = float(preds.get(target_month, 0.0))
                lsoa_scores.append((lsoa_code, score))

            # Calculate ward totals
            ward_total_score = sum(score for (_, score) in lsoa_scores)
            total_officer_hours = 200.0  # 100 officers × 2 hours/day

            # Allocate officers to each LSOA in this ward
            for lsoa_code, score in lsoa_scores:
                if ward_total_score > 0.0:
                    proportion = score / ward_total_score
                    hours_allocated = proportion * total_officer_hours
                    raw_officers = int(hours_allocated // 2)

                    # Guarantee at least 1 officer if LSOA has any predicted risk
                    if score > 0 and raw_officers < 1:
                        daily_officers = 1
                    else:
                        daily_officers = raw_officers
                else:
                    daily_officers = 0

                # Calculate hourly distribution
                hourly_officers = []
                if daily_officers > 0:
                    # First pass: distribute using proportions
                    for h in range(24):
                        hourly_alloc = int(daily_officers * hourly_fractions[h])
                        hourly_officers.append(hourly_alloc)

                    # Calculate how many officers we're missing due to rounding
                    allocated_total = sum(hourly_officers)
                    missing_officers = daily_officers - allocated_total

                    # Distribute the missing officers to the hours with highest fractions
                    if missing_officers > 0:
                        # Get hour indices sorted by their fractions (highest first)
                        hour_indices_by_fraction = sorted(range(24),
                                                          key=lambda h: hourly_fractions[h],
                                                          reverse=True)

                        # Add one officer to the top hours until we've allocated all
                        for i in range(min(missing_officers, 24)):
                            hour_idx = hour_indices_by_fraction[i]
                            hourly_officers[hour_idx] += 1
                else:
                    # No daily officers = no hourly officers
                    hourly_officers = [0] * 24

                assignments[borough_code][ward_code][lsoa_code] = {
                    "daily": daily_officers,
                    "hourly": hourly_officers,
                    "prediction_score": score
                }

    return assignments


def integrate_assignments_into_json(pred_data: dict, target_months: list) -> dict:
    """
    Calculate officer assignments for all months and integrate them into the JSON structure.
    Returns a deep copy of the original data with officer assignments added.
    """
    # Create a deep copy to avoid modifying the original
    enhanced_data = json.loads(json.dumps(pred_data))

    # Calculate assignments for each month
    for month in target_months:
        print(f"Calculating officer assignments for {month}...")
        monthly_assignments = allocate_officers_for_month(pred_data, month)

        # Integrate assignments into the enhanced JSON structure
        for borough_code, wards in monthly_assignments.items():
            for ward_code, lsoas in wards.items():
                for lsoa_code, assignment_data in lsoas.items():
                    # Initialize officer_assignments if it doesn't exist
                    lsoa_path = enhanced_data[borough_code]["wards"][ward_code]["lsoas"][lsoa_code]
                    if "officer_assignments" not in lsoa_path:
                        lsoa_path["officer_assignments"] = {"daily": {}, "hourly": {}}

                    # Add the assignments for this month
                    lsoa_path["officer_assignments"]["daily"][month] = assignment_data["daily"]
                    lsoa_path["officer_assignments"]["hourly"][month] = assignment_data["hourly"]

    return enhanced_data


def extract_csv_data_from_enhanced_json(enhanced_data: dict, target_months: list) -> tuple:
    """
    Extract CSV-compatible data from the enhanced JSON structure.
    Returns (daily_rows, hourly_rows) for CSV output.
    """
    daily_rows = []
    hourly_rows = []

    for borough_code, borough_entry in enhanced_data.items():
        borough_name = borough_entry.get("name", borough_code)
        wards_dict = borough_entry.get("wards", {})

        for ward_code, ward_entry in wards_dict.items():
            ward_name = ward_entry.get("name", ward_code)
            lsoas_dict = ward_entry.get("lsoas", {})

            for lsoa_code, lsoa_entry in lsoas_dict.items():
                lsoa_name = lsoa_entry.get("name", lsoa_code)
                officer_assignments = lsoa_entry.get("officer_assignments", {})
                predictions = lsoa_entry.get("predictions", {})

                for month in target_months:
                    daily_officers = officer_assignments.get("daily", {}).get(month, 0)
                    hourly_officers = officer_assignments.get("hourly", {}).get(month, [0] * 24)
                    prediction_score = predictions.get(month, 0.0)

                    # Daily row
                    daily_rows.append({
                        "borough_code": borough_code,
                        "borough_name": borough_name,
                        "ward_code": ward_code,
                        "ward_name": ward_name,
                        "lsoa_code": lsoa_code,
                        "lsoa_name": lsoa_name,
                        "month": month,
                        "prediction_score": prediction_score,
                        "officers_assigned": daily_officers
                    })

                    # Hourly rows (24 per LSOA per month)
                    for h in range(24):
                        hourly_rows.append({
                            "borough_code": borough_code,
                            "borough_name": borough_name,
                            "ward_code": ward_code,
                            "ward_name": ward_name,
                            "lsoa_code": lsoa_code,
                            "lsoa_name": lsoa_name,
                            "month": month,
                            "prediction_score": prediction_score,
                            "hour_block": f"{h:02d}:00–{h:02d}:59",
                            "officers_assigned": hourly_officers[h]
                        })

    return daily_rows, hourly_rows


def write_enhanced_json(enhanced_data: dict, output_path: Path):
    """Write the enhanced data structure to JSON file."""
    try:
        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing enhanced JSON to '{output_path}': {e}", file=sys.stderr)
        print(f"Attempted to write to: {output_path.absolute()}", file=sys.stderr)
        print(f"Parent directory: {output_path.parent.absolute()}", file=sys.stderr)
        print(f"Parent exists: {output_path.parent.exists()}", file=sys.stderr)
        sys.exit(1)


def write_csv(data: list, output_path: Path, fieldnames: list):
    """Generic CSV writer."""
    try:
        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
    except Exception as e:
        print(f"Error writing CSV to '{output_path}': {e}", file=sys.stderr)
        print(f"Attempted to write to: {output_path.absolute()}", file=sys.stderr)
        sys.exit(1)


def main():
    # Load the original JSON
    json_path = Path(INPUT_JSON)
    predictions = load_predictions(json_path)
    print(f"Loaded predictions from '{json_path}'")

    # Calculate and integrate officer assignments for all months
    enhanced_data = integrate_assignments_into_json(predictions, TARGET_MONTHS)

    # FORCE WRITING TO XGBOOST OUTPUTS FOLDER - NOT TRANSFORMATIVE!
    # Get current working directory and navigate to xgBoost/outputs
    current_dir = Path.cwd()
    if "transformative" in str(current_dir):
        # We're in transformative folder, go up to xgBoost
        xgboost_outputs = current_dir.parent / "outputs"
    else:
        # We're somewhere else, try to find xgBoost folder
        xgboost_outputs = Path("xgBoost/outputs")

    # Ensure the xgBoost/outputs directory exists
    xgboost_outputs.mkdir(parents=True, exist_ok=True)

    # Write files to xgBoost/outputs folder
    output_json_path = xgboost_outputs / "london_predictions_with_officers.json"
    daily_csv_path = xgboost_outputs / "officer_assignment_daily_all_months.csv"
    hourly_csv_path = xgboost_outputs / "officer_assignment_hourly_all_months.csv"

    print(f"WRITING TO XGBOOST OUTPUTS: {xgboost_outputs.absolute()}")

    # Write the enhanced JSON
    write_enhanced_json(enhanced_data, output_json_path)
    print(f"Enhanced JSON written to → '{output_json_path.absolute()}'")

    # Optional: Extract and write CSV files for backward compatibility
    daily_rows, hourly_rows = extract_csv_data_from_enhanced_json(enhanced_data, TARGET_MONTHS)

    # Write daily CSV
    daily_fieldnames = [
        "borough_code", "borough_name", "ward_code", "ward_name",
        "lsoa_code", "lsoa_name", "month", "prediction_score", "officers_assigned"
    ]
    write_csv(daily_rows, daily_csv_path, daily_fieldnames)
    print(f"Daily CSV written to → '{daily_csv_path.absolute()}'")

    # Write hourly CSV
    hourly_fieldnames = [
        "borough_code", "borough_name", "ward_code", "ward_name",
        "lsoa_code", "lsoa_name", "month", "prediction_score", "hour_block", "officers_assigned"
    ]
    write_csv(hourly_rows, hourly_csv_path, hourly_fieldnames)
    print(f"Hourly CSV written to → '{hourly_csv_path.absolute()}'")

    print(f"\nProcessed {len(TARGET_MONTHS)} months: {', '.join(TARGET_MONTHS)}")
    print(f"Total LSOAs processed: {len(daily_rows) // len(TARGET_MONTHS)}")
    print(f"ALL FILES WRITTEN TO XGBOOST/OUTPUTS FOLDER: {xgboost_outputs.absolute()}")


if __name__ == "__main__":
    main()