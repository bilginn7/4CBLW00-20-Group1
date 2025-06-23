#!/usr/bin/env python3
"""
Enhanced transformation2.py with Historical Data Integration (JSON only)

Adds historical burglary data alongside predictions and officer assignments.
"""

import json
import sys
import pandas as pd
from pathlib import Path

# ─── USER‐EDITABLE SETTINGS ────────────────────────────────────────────────────
INPUT_JSON = "xgBoost/outputs/london_future_predictions.json"
HISTORICAL_FEATURES = "../data/features.parquet"
OUTPUT_JSON = "outputs/london_predictions_with_officers.json"

TARGET_MONTHS = ["2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11",
                 "2025-12"]

HOURLY_BURGLARY_COUNTS = [
    100, 80, 50, 40, 150, 600, 1550, 2050,
    1780, 1320, 980, 680, 520, 450, 480, 550,
    620, 780, 850, 830, 740, 705, 690, 500
]


def load_historical_data(features_path: Path) -> dict:
    """Load historical burglary data and return as LSOA -> {month: count} dict."""
    print(f"Loading historical data from {features_path}...")

    possible_paths = [
        features_path,
        Path("../data/features.parquet"),
        Path("../../data/features.parquet"),
        Path("data/features.parquet")
    ]

    df = None
    for path_to_try in possible_paths:
        try:
            if path_to_try.exists():
                print(f"Found historical data at: {path_to_try}")
                df = pd.read_parquet(path_to_try)
                break
        except Exception as e:
            continue

    if df is None:
        print("Warning: Could not load historical data. Continuing without historical data.")
        return {}

    # Convert to the format we need: LSOA -> {YYYY-MM: count}
    historical_dict = {}

    # Handle different possible column names
    lsoa_col = None
    for col in ['LSOA_code', 'LSOA code', 'lsoa_code', 'LSOA21CD']:
        if col in df.columns:
            lsoa_col = col
            break

    if lsoa_col is None:
        print("Warning: No LSOA column found in historical data")
        return {}

    count_col = 'burglary_count'
    if count_col not in df.columns:
        print("Warning: No burglary_count column found in historical data")
        return {}

    print(f"Processing {len(df)} historical records...")

    for _, row in df.iterrows():
        lsoa_code = row[lsoa_col]
        year = int(row['year'])
        month = int(row['month'])
        count = int(row[count_col])

        month_key = f"{year}-{month:02d}"

        if lsoa_code not in historical_dict:
            historical_dict[lsoa_code] = {}

        historical_dict[lsoa_code][month_key] = count

    print(f"Loaded historical data for {len(historical_dict)} LSOAs")
    return historical_dict


def load_predictions(json_path: Path) -> dict:
    """Load and return the nested prediction dictionary from the JSON file."""
    possible_paths = [
        json_path,
        Path("../../data/london_future_predictions.json"),
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

    print(f"Could not find JSON file. Tried these paths:", file=sys.stderr)
    for path_to_try in possible_paths:
        print(f"  - {path_to_try.absolute()} (exists: {path_to_try.exists()})", file=sys.stderr)
    sys.exit(1)


def compute_hourly_fractions(hourly_counts: list) -> list:
    """Convert raw hourly counts to fractions that sum to 1.0."""
    total = float(sum(hourly_counts))
    if total <= 0:
        return [1.0 / 24.0] * 24
    return [cnt / total for cnt in hourly_counts]


def allocate_officers_for_month(pred_data: dict, target_month: str) -> dict:
    """Calculate officer assignments for a specific month."""
    hourly_fractions = compute_hourly_fractions(HOURLY_BURGLARY_COUNTS)
    assignments = {}

    for borough_code, borough_entry in pred_data.items():
        assignments[borough_code] = {}
        wards_dict = borough_entry.get("wards", {})

        for ward_code, ward_entry in wards_dict.items():
            assignments[borough_code][ward_code] = {}
            lsoas_dict = ward_entry.get("lsoas", {})

            lsoa_scores = []
            for lsoa_code, lsoa_entry in lsoas_dict.items():
                preds = lsoa_entry.get("predictions", {})
                score = float(preds.get(target_month, 0.0))
                lsoa_scores.append((lsoa_code, score))

            ward_total_score = sum(score for (_, score) in lsoa_scores)
            total_officer_hours = 200.0

            for lsoa_code, score in lsoa_scores:
                if ward_total_score > 0.0:
                    proportion = score / ward_total_score
                    hours_allocated = proportion * total_officer_hours
                    raw_officers = int(hours_allocated // 2)

                    if score > 0 and raw_officers < 1:
                        daily_officers = 1
                    else:
                        daily_officers = raw_officers
                else:
                    daily_officers = 0

                hourly_officers = []
                if daily_officers > 0:
                    for h in range(24):
                        hourly_alloc = int(daily_officers * hourly_fractions[h])
                        hourly_officers.append(hourly_alloc)

                    allocated_total = sum(hourly_officers)
                    missing_officers = daily_officers - allocated_total

                    if missing_officers > 0:
                        hour_indices_by_fraction = sorted(range(24),
                                                          key=lambda h: hourly_fractions[h],
                                                          reverse=True)
                        for i in range(min(missing_officers, 24)):
                            hour_idx = hour_indices_by_fraction[i]
                            hourly_officers[hour_idx] += 1
                else:
                    hourly_officers = [0] * 24

                assignments[borough_code][ward_code][lsoa_code] = {
                    "daily": daily_officers,
                    "hourly": hourly_officers,
                    "prediction_score": score
                }

    return assignments


def integrate_all_data(pred_data: dict, historical_data: dict, target_months: list) -> dict:
    """Integrate predictions, historical data, and officer assignments."""
    enhanced_data = json.loads(json.dumps(pred_data))

    # Add historical data first
    print("Adding historical data...")
    for borough_code, borough_entry in enhanced_data.items():
        for ward_code, ward_entry in borough_entry["wards"].items():
            for lsoa_code, lsoa_entry in ward_entry["lsoas"].items():
                if lsoa_code in historical_data:
                    lsoa_entry["historical"] = historical_data[lsoa_code]
                else:
                    lsoa_entry["historical"] = {}

    # Add officer assignments
    for month in target_months:
        print(f"Calculating officer assignments for {month}...")
        monthly_assignments = allocate_officers_for_month(pred_data, month)

        for borough_code, wards in monthly_assignments.items():
            for ward_code, lsoas in wards.items():
                for lsoa_code, assignment_data in lsoas.items():
                    lsoa_path = enhanced_data[borough_code]["wards"][ward_code]["lsoas"][lsoa_code]
                    if "officer_assignments" not in lsoa_path:
                        lsoa_path["officer_assignments"] = {"daily": {}, "hourly": {}}

                    lsoa_path["officer_assignments"]["daily"][month] = assignment_data["daily"]
                    lsoa_path["officer_assignments"]["hourly"][month] = assignment_data["hourly"]

    return enhanced_data


def write_enhanced_json(enhanced_data: dict, output_path: Path):
    """Write the enhanced data structure to JSON file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing enhanced JSON to '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)


def main():
    # Load data
    json_path = Path(INPUT_JSON)
    predictions = load_predictions(json_path)
    print(f"Loaded predictions from '{json_path}'")

    historical_path = Path(HISTORICAL_FEATURES)
    historical_data = load_historical_data(historical_path)

    # Integrate everything
    enhanced_data = integrate_all_data(predictions, historical_data, TARGET_MONTHS)

    # Set output path
    current_dir = Path.cwd()
    if "transformative" in str(current_dir):
        xgboost_outputs = current_dir.parent / "outputs"
    else:
        xgboost_outputs = Path("xgBoost/outputs")

    xgboost_outputs.mkdir(parents=True, exist_ok=True)
    output_json_path = xgboost_outputs / "london_predictions_with_officers.json"

    # Write enhanced JSON
    write_enhanced_json(enhanced_data, output_json_path)
    print(f"Enhanced JSON with historical data written to → '{output_json_path.absolute()}'")

    print(f"Processed {len(TARGET_MONTHS)} months: {', '.join(TARGET_MONTHS)}")

    # Show sample structure
    sample_lsoa = next(iter(enhanced_data.values()))["wards"]
    sample_lsoa = next(iter(sample_lsoa.values()))["lsoas"]
    sample_lsoa = next(iter(sample_lsoa.values()))

    print(f"Enhanced LSOA structure includes:")
    print(f"- Predictions: {'predictions' in sample_lsoa}")
    print(f"- Historical: {'historical' in sample_lsoa}")
    print(f"- Officer assignments: {'officer_assignments' in sample_lsoa}")

    if 'historical' in sample_lsoa:
        hist_count = len(sample_lsoa['historical'])
        print(f"- Historical data points: {hist_count}")


if __name__ == "__main__":
    main()