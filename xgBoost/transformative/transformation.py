#!/usr/bin/env python3
"""
transformative.py

This version still allocates “daily” officers exactly as before, but then
applies an hourly filter (based on your burglary‐by‐hour graph) to split
that daily headcount into 24 hour‐blocks.

Usage:  python transformative.py

After running, you will get two CSVs:
  1) OUTPUT_CSV_DAILY    ← exactly one row per (borough, ward, lsoa) with a daily officer count.
  2) OUTPUT_CSV_HOURLY   ← one row per (borough, ward, lsoa, hour‐block) with an hourly officer count.
"""

import json
import csv
import sys
from pathlib import Path


# ─── USER‐EDITABLE SETTINGS ────────────────────────────────────────────────────
# Path to your JSON file of future predictions (Borough → Ward → LSOA → predictions)
INPUT_JSON = "xgBoost/outputs/london_future_predictions.json"

# Target month in YYYY-MM format (e.g. "2025-04")
TARGET_MONTH = "2025-07"

# Where to write the output CSVs
OUTPUT_CSV_DAILY   = "xgBoost/outputs/officer_assignment_daily_2025-07.csv"
OUTPUT_CSV_HOURLY  = "xgBoost/outputs/officer_assignment_hourly_2025-07.csv"
# ──────────────────────────────────────────────────────────────────────────────


# ─── (1) Load the nested predictions JSON ─────────────────────────────────────
def load_predictions(json_path: Path) -> dict:
    """
    Load and return the nested prediction dictionary from the JSON file.
    """
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading JSON from '{json_path}': {e}", file=sys.stderr)
        sys.exit(1)


# ─── (2) Allocate “daily” officers per LSOA (exactly as you had before) ────────
def allocate_officers_for_month(pred_data: dict, target_month: str) -> list:
    """
    Given the loaded JSON data and a target_month (e.g. "2025-04"), compute how many officers
    should be assigned to each LSOA on a single day, subject to:
      - Each ward has 100 officers, each can spend 2 hours/day on burglary (total = 200 officer‐hours/day).
      - Distribute those 200 hours across the LSOAs in proportion to each LSOA’s prediction score for target_month.
      - Convert hours → officers via floor(hours / 2). If an LSOA has score > 0 but floor(hours/2) == 0, we still give it 1 officer.
    Returns a flat list of dicts:
      [ {borough_code, borough_name, ward_code, ward_name, lsoa_code, lsoa_name,
         prediction_score, officers_assigned}, ... ]
    """
    assignments = []

    for borough_code, borough_entry in pred_data.items():
        borough_name = borough_entry.get("name", borough_code)
        wards_dict = borough_entry.get("wards", {})

        for ward_code, ward_entry in wards_dict.items():
            ward_name = ward_entry.get("name", ward_code)
            lsoas_dict = ward_entry.get("lsoas", {})

            # 2.a) Gather (lsoa_code, lsoa_name, score) for this ward in target_month
            lsoa_scores = []
            for lsoa_code, lsoa_entry in lsoas_dict.items():
                lsoa_name = lsoa_entry.get("name", lsoa_code)
                preds = lsoa_entry.get("predictions", {})
                score = float(preds.get(target_month, 0.0))
                lsoa_scores.append((lsoa_code, lsoa_name, score))

            # 2.b) Compute the ward‐level total score and total available hours
            ward_total_score = sum(score for (_, _, score) in lsoa_scores)
            total_officer_hours = 200.0  # 100 officers × 2 hours/day

            if ward_total_score > 0.0:
                for (lsoa_code, lsoa_name, score) in lsoa_scores:
                    # Fraction of ward‐risk
                    proportion = score / ward_total_score
                    hours_allocated = proportion * total_officer_hours

                    # Convert “hours → officers” (2 h each)
                    raw_officers = int(hours_allocated // 2)
                    # Guarantee at least 1 officer if this LSOA has any predicted risk
                    if score > 0 and raw_officers < 1:
                        officers_assigned = 1
                    else:
                        officers_assigned = raw_officers

                    assignments.append({
                        "borough_code":       borough_code,
                        "borough_name":       borough_name,
                        "ward_code":          ward_code,
                        "ward_name":          ward_name,
                        "lsoa_code":          lsoa_code,
                        "lsoa_name":          lsoa_name,
                        "prediction_score":   score,
                        "officers_assigned":  officers_assigned
                    })
            else:
                # No predicted risk in this ward → 0 officers to every LSOA
                for (lsoa_code, lsoa_name, score) in lsoa_scores:
                    assignments.append({
                        "borough_code":       borough_code,
                        "borough_name":       borough_name,
                        "ward_code":          ward_code,
                        "ward_name":          ward_name,
                        "lsoa_code":          lsoa_code,
                        "lsoa_name":          lsoa_name,
                        "prediction_score":   score,
                        "officers_assigned":  0
                    })

    return assignments


# ─── (3) Define your burglary‐by‐hour counts and normalize to fractions ───────
# Fill in these 24 integers with the exact counts you read off your plot. In the order:
#   [00:00–00:59, 01:00–01:59, …, 23:00–23:59].
# (These numbers below are placeholders—please replace with your actual counts.)
HOURLY_BURGLARY_COUNTS = [
    100,  80,  50,  40,  150,  600, 1550, 2050,
   1780, 1320,  980,  680,  520,  450,  480,  550,
    620,  780,  850,  830,  740,  705,  690,  500
]

def compute_hourly_fractions(hourly_counts: list) -> list:
    """
    Given 24 raw burglary counts (one per hour‐bucket), normalize so that they sum to 1.0.
    Returns a list of 24 floats, e.g. [0.015, 0.012, … ] with sum == 1.0.
    """
    total = float(sum(hourly_counts))
    if total <= 0:
        # If the data is invalid or empty, default to a uniform 1/24 distribution
        return [1.0 / 24.0] * 24
    return [cnt / total for cnt in hourly_counts]


# ─── (4) Take “daily” assignments and expand them into 24 hourly lines ──────────
def expand_to_hourly(daily_assignments: list, hourly_fractions: list) -> list:
    """
    Given a list of daily assignments (one dict per (borough,ward,lsoa) with 'officers_assigned'),
    produce a new list that contains 24 × N rows, each tagged with an 'hour_block' (0..23).
    For each LSOA with daily_officers = D, we compute:
        officers_in_hour_h = floor(D * hourly_fractions[h])
    BUT we also guarantee that if daily_officers >= 1, then the single hour with the
    largest fraction gets at least 1 officer, to avoid “all zero” when D is small.

    Returns a new list of dicts, each with these fields:
      borough_code, borough_name, ward_code, ward_name,
      lsoa_code, lsoa_name, prediction_score, hour_block, officers_assigned_hour.
    """
    hourly_list = []

    # Pre‐compute “which hour index has the maximum fraction?”
    # so that any LSOA with daily_officers ≥ 1 can be bumped to at least 1 officer
    # in its busiest hour.
    max_frac = max(hourly_fractions)
    busiest_hours = [i for i, f in enumerate(hourly_fractions) if f == max_frac]
    # In case of a tie, we’ll just pick the first busy hour:
    busiest_hour_index = busiest_hours[0]

    for row in daily_assignments:
        D = row["officers_assigned"]
        # If D == 0, we’ll just output zeros for every hour
        # If D > 0, we want to allocate floor(D * fraction) to each hour,
        # then bump at least one hour’s allocation to 1 if they all turned out 0.
        allocations = []
        for h in range(24):
            alloc = int(D * hourly_fractions[h])  # floor(...)
            allocations.append(alloc)

        if D > 0 and sum(allocations) == 0:
            # If D was small but nonzero, and everything floored to 0,
            # force the “busiest_hour_index” to get 1 officer:
            allocations[busiest_hour_index] = 1

        # Now emit 24 rows for this LSOA
        for h in range(24):
            hourly_list.append({
                "borough_code":        row["borough_code"],
                "borough_name":        row["borough_name"],
                "ward_code":           row["ward_code"],
                "ward_name":           row["ward_name"],
                "lsoa_code":           row["lsoa_code"],
                "lsoa_name":           row["lsoa_name"],
                "prediction_score":    row["prediction_score"],
                "hour_block":          f"{h:02d}:00–{h:02d}:59",
                "officers_assigned":   allocations[h]
            })

    return hourly_list


# ─── (5) Write CSV utilities (daily + hourly) ─────────────────────────────────
def write_csv_daily(assignments: list, output_path: Path):
    """
    Write the list of DAILY assignment dicts to a CSV with columns:
      borough_code, borough_name, ward_code, ward_name,
      lsoa_code, lsoa_name, prediction_score, officers_assigned
    """
    fieldnames = [
        "borough_code",
        "borough_name",
        "ward_code",
        "ward_name",
        "lsoa_code",
        "lsoa_name",
        "prediction_score",
        "officers_assigned",
    ]
    try:
        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in assignments:
                writer.writerow(row)
    except Exception as e:
        print(f"Error writing daily CSV to '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)


def write_csv_hourly(hourly_assignments: list, output_path: Path):
    """
    Write the list of HOURLY assignment dicts to a CSV with columns:
      borough_code, borough_name, ward_code, ward_name,
      lsoa_code, lsoa_name, prediction_score, hour_block, officers_assigned
    """
    fieldnames = [
        "borough_code",
        "borough_name",
        "ward_code",
        "ward_name",
        "lsoa_code",
        "lsoa_name",
        "prediction_score",
        "hour_block",
        "officers_assigned",
    ]
    try:
        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in hourly_assignments:
                writer.writerow(row)
    except Exception as e:
        print(f"Error writing hourly CSV to '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)


# ─── (6) main() ties it all together ───────────────────────────────────────────
def main():
    # 6.a) Load the JSON
    json_path = Path(INPUT_JSON)
    predictions = load_predictions(json_path)

    # 6.b) Allocate a DAILY officer count to each LSOA
    daily_assignments = allocate_officers_for_month(predictions, TARGET_MONTH)

    # 6.c) Write out the “daily” CSV exactly as before
    out_path_daily = Path(OUTPUT_CSV_DAILY)
    write_csv_daily(daily_assignments, out_path_daily)
    print(f"Daily officer assignments written to → '{out_path_daily}'")

    # 6.d) Now compute hourly fractions from your burglary‐by‐hour graph
    hourly_fractions = compute_hourly_fractions(HOURLY_BURGLARY_COUNTS)

    # 6.e) Expand the daily assignments into 24 hourly lines per LSOA
    hourly_assignments = expand_to_hourly(daily_assignments, hourly_fractions)

    # 6.f) Write out the new “hourly” CSV
    out_path_hourly = Path(OUTPUT_CSV_HOURLY)
    write_csv_hourly(hourly_assignments, out_path_hourly)
    print(f"Hourly‐split officer assignments written to → '{out_path_hourly}'")


if __name__ == "__main__":
    main()
