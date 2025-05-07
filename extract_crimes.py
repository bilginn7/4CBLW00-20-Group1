import pandas as pd
from pathlib import Path
from typing import List, Set, Optional
import logging, os
from concurrent.futures import ProcessPoolExecutor
from functools import partial

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)


class BurglaryDataCombiner:
    """Class to combine burglary crime data for London from all the UK police data.
    Files needed can be downloaded via:
        https://data.police.uk/data/archive/
    """

    def __init__(self, base_dir: str = 'data/all_crime_data_zips',
                 london_lsoa_file: str = 'data/london_lsoa_codes.csv',
                 output_file: str = 'data/london_burglary_crimes_combined.csv') -> None:
        """Initialize with Path objects and load LSOA codes.

        Args:
            base_dir (str): All the raw data files folder path.
            london_lsoa_file (str): File with London LSOA codes.
            output_file (str): Output file path.
        """
        self.base_dir: Path = Path(base_dir)
        self.london_lsoa_file: Path = Path(london_lsoa_file)
        self.output_file: Path = Path(output_file)
        self.london_lsoa_codes: Set[str] = set()
        self.all_dfs: List[pd.DataFrame] = []
        self._load_london_lsoa_codes()

    def _load_london_lsoa_codes(self) -> None:
        """Load London LSOA codes into DataFrame."""
        london_lsoa_df = pd.read_csv(self.london_lsoa_file)
        self.london_lsoa_codes = set(london_lsoa_df['lsoa_code'].str.strip().tolist())

    @staticmethod
    def _filter_for_crime(df: pd.DataFrame, crime: str) -> Optional[pd.DataFrame]:
        """Filter dataframe to only include burglary crimes.

        Args:
            df (pd.DataFrame): Dataframe to filter.
            crime (str): The type of crime to filter on.

        Returns:
            pd.DataFrame: Filtered dataframe.
            Or None
        """
        if "Crime type" not in df.columns:
            return None

        return df[df["Crime type"].str.contains(crime, case=False,na=False)]

    def _filter_by_lsoa(self, df: pd.DataFrame, filename: Path) -> Optional[pd.DataFrame]:
        """Filter dataframe to only include LSOA codes.

        Args:
            df (pd.DataFrame): Dataframe to filter.
            filename (Path): File with LSOA codes.

        Returns:
            pd.DataFrame: Filtered dataframe.
            Or None
        """
        filename_str = filename.name

        # MET and COL police force that don't need LSOA filtering
        if "metropolitan-street.csv" in filename_str or "city-of-london-street.csv" in filename_str:
            logging.info(f"Added all burglary data from {filename_str}")
            return df

        # Other police forces that need LSOA filtering
        if 'LSOA code' not in df.columns:
            logging.warning(f"'LSOA code' column not found in {filename_str}, skipping.")
            return None

        # Skip files where all LSOA values are empty/null
        if df['LSOA code'].isna().all() or (df['LSOA code'] == '').all():
            logging.warning(f"'LSOA code' column is empty in {filename_str}, skipping.")
            return None

        filtered_df = df[df['LSOA code'].str.strip().isin(self.london_lsoa_codes)]
        if len(filtered_df) != 0:
            logging.info(f"Added {len(filtered_df)} burglary rows from {filename_str} (filtered by LSOA).")
        return filtered_df

    def process_file(self, file_path: Path, crime: str) -> Optional[pd.DataFrame]:
        """Process a single file and return filtered dataframe if valid.

        Args:
            file_path (Path): File with crime data.
            crime (str): The type of crime to filter on.

        Returns:
            pd.DataFrame: Filtered dataframe.
            Or None
        """
        try:
            df = pd.read_csv(file_path)
            filtered_df = self._filter_for_crime(df, crime)
            if filtered_df is None:
                logging.warning(f"'Crime type' column not found in {file_path.name}, skipping.")
                return None

            return self._filter_by_lsoa(filtered_df, file_path)

        except Exception as e:
            logging.error(f"Processing {file_path.name}: {str(e)}")
            return None

    def find_street_files(self) -> List[Path]:
        """Find all street.csv files in the directory structure using Path.glob.

        Returns:
            List[Path]: List of all street.csv files.
        """
        return list(self.base_dir.rglob('*-street.csv'))

    def run(self, crime: str = 'Burglary') -> bool:
        """Execute the entire process.

        Returns:
            bool: True if all processed files are valid.
        """
        # Find all files
        street_files = self.find_street_files()
        logging.info(f"Found {len(street_files)} street.csv files.")
        logging.info(f"Filtering for crime type: {crime}")

        process_func = partial(self.process_file, crime=crime)

        # Parallel file processing
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            results = list(executor.map(process_func, street_files))

        # Collect valid results
        self.all_dfs = [df for df in results if df is not None]

        # Combine and save
        if not self.all_dfs:
            logging.warning(f"No {crime.lower()} data was processed. Check file paths and data structure.")
            return False

        # Update output file name to reflect the crime type
        if crime.lower() != 'burglary':
            crime_slug = crime.lower().replace(' ', '_')
            self.output_file = self.output_file.with_name(f"london_{crime_slug}_crimes_combined.csv")

        combined_df = pd.concat(self.all_dfs, ignore_index=True)

        # Ensure parent directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_csv(self.output_file, index=False)
        print(f"Successfully created {self.output_file} with {len(combined_df)} total {crime.lower()} cases")
        return True


if __name__ == "__main__":
    combiner = BurglaryDataCombiner()
    combiner.run()