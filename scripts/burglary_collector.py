from pathlib import Path
import csv, logging, os, polars as pl
from tqdm.contrib.concurrent import process_map

# Logging module
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)


def _filter_file(args):
    path, valid_codes, lsoa_mapping, crime = args
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lsoa_code = row["LSOA code"].strip()
            if lsoa_code in lsoa_mapping:
                lsoa_code = lsoa_mapping[lsoa_code]
                row["LSOA code"] = lsoa_code
            if (row["Crime ID"].strip() and
                row["LSOA code"] in valid_codes and
                row["Crime type"] == crime):
                rows.append(row)
    return rows

def create_file(file_path: str, output_name: str, lsoa_path: str, crime: str = 'Burglary') -> None:
    """Create the crime dataset for London burglaries.

    Args:
        file_path: Path to the CSV files.
        output_name: Name of the output CSV file.
        lsoa_path: File path for the london areas.
        crime: Crime to filter on.

    Returns:
        Generates a parquet file of merged data.
    """

    base_dir = Path(__file__).resolve().parent
    csv_files = list((base_dir / file_path).rglob("*-street.csv"))
    lsoa_df = pl.read_parquet(lsoa_path)
    valid_codes = set(pl.read_parquet(lsoa_path)["LSOA21CD"])

    # Mapping for changed LSOA codes (S, M, X)
    lsoa_mapping = {}
    changes = lsoa_df.filter(pl.col("CHGIND").is_in(["S", "M", "X"]))
    for row in changes.select(["LSOA11CD", "LSOA21CD"]).iter_rows(named=True):
        lsoa_mapping[row["LSOA11CD"]] = row["LSOA21CD"]

    logging.info(f'Found {len(csv_files)} files.')
    logging.info(f'Found {len(valid_codes)} London LSOA codes')

    chunks = process_map(
        _filter_file,
        [(p, valid_codes, lsoa_mapping, crime) for p in csv_files],
        max_workers=os.cpu_count(),
        chunksize=1,
        desc="Processing files",
        unit="files"
    )

    # Write everything the workers give us into one temporary CSV
    tmp_csv = base_dir / "temp.csv"
    with open(tmp_csv, "w", newline="") as out_f:
        writer = None
        for rows in chunks:
            if not rows:
                continue
            if writer is None:
                writer = csv.DictWriter(out_f, fieldnames=rows[0].keys())
                writer.writeheader()
            writer.writerows(rows)


    # Convert to parquet & deduplicate
    parquet_path = base_dir.parent / "data" / f"{output_name}.parquet"
    (
        pl.read_csv(tmp_csv)
          .unique(subset=["Crime ID"])
          .write_parquet(parquet_path, compression="zstd", compression_level=3)
    )
    os.remove(tmp_csv)
    logging.info(f"Wrote {parquet_path}")



if __name__ == '__main__':
    create_file(file_path='../data/all_crime_data_zips',
                   output_name='london_burglaries',
                   lsoa_path='../data/london_areas_lookup.parquet')