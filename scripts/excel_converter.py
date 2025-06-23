import polars as pl
import os
from pathlib import Path
from itertools import batched
from concurrent.futures import ThreadPoolExecutor, as_completed

def data_processing(data: str, sheet: str, cols: list, header: int, output: str) -> None:
    """Creates a parquet file from an Excel file.
    Finds the file in directories, only mentioning the title is enough.

    Args:
        data (str): Path to data file
        sheet (str): Sheet name
        cols (list): Columns to include
        header (int): Column header
        output (str): File output name
    """
    # Get the project root directory (parent of scripts folder)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent

    # Remove file extension if present
    data_base = data.split('.')[0] if '.' in data else data

    # Search for the file within the project root directory
    file_path = None
    for root, dirs, files in os.walk(project_root):
        possible_filenames = [
            data,
            f"{data_base}.xlsx",
            f"{data_base}.xls"
        ]

        for filename in possible_filenames:
            if filename in files:
                file_path = os.path.join(root, filename)
                print(f"Found file: {file_path}")
                break

        if file_path:
            break

    if not file_path:
        raise FileNotFoundError(f"Could not find '{data}' in project folders. Searched from {project_root}")

    # Read an Excel file into polars
    df = pl.read_excel(source=file_path,
                       sheet_name=sheet,
                       columns=cols,
                       engine='calamine',
                       has_header=True,
                       read_options={'header_row': header})

    script_dir = Path(__file__).parent.absolute()
    data_dir = script_dir.parent / "data"
    os.makedirs(data_dir, exist_ok=True)

    # Write dataframe to a parquet file
    df.write_parquet(file=data_dir / f"{output}.parquet", compression='zstd')

def main():
    """Convert Excel file into parquet file."""
    parallel = [
        {
            'data' : 'sapelsoapopulationdensity20112022.xlsx',
            'sheet' : 'Mid-2011 to mid-2022 LSOA 2021',
            'cols' : list(range(2, 29)),
            'header' : 3,
            'output' : 'pop_density_2011_2022'
        }
    ]

    batch_size = 3
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        for batch in batched(parallel, batch_size):
            futures = [executor.submit(data_processing, **job) for job in batch]

            # Get results
            for future in as_completed(futures):
                try:
                    print(future.result())
                except Exception as e:
                    print(f"Error processing job: {str(e)}")

if __name__ == '__main__':
    main()