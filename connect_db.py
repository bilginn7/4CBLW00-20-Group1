from dotenv import load_dotenv
from google.cloud import bigquery
from typing import List, Dict, Any
import logging, coloredlogs, os
import pandas as pd

logging.basicConfig(
    filename="bigquery.log",
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
coloredlogs.install(
    level=logging.DEBUG,
    logger=logger,
    fmt='%(levelname)s: %(message)s',
    level_styles={
        'debug': {'color': 'cyan'},
        'info': {'color': 'green'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'},
        'critical': {'color': 'red', 'bold': True}
    }
)


class BigQueryConnector:
    """A class to handle BigQuery connections and queries."""

    def __init__(self, project_id: str = None, credentials_path: str = None, dataset_id: str = None) -> None:
        """Initialize the BigQuery connector.

        Args:
            project_id: The GCP project ID. If None, reads from environment.
            credentials_path: Path to credentials file. If None, reads from environment.
            dataset_id: Default dataset to use for queries. If set, allows using just table names.
        """
        load_dotenv()
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID") or 'cbl-group1'
        self.dataset_id = dataset_id or os.getenv("GCP_DATASET_ID") or 'london_crimes'
        self._validate_credentials()
        self.client = None
        self._connect()

    def _validate_credentials(self) -> None:
        """Validate that credentials exist and are accessible."""
        if not self.credentials_path:
            raise ValueError("Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at path: {self.credentials_path}")

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path

    def _connect(self) -> None:
        """Establish connection to BigQuery."""
        try:
            self.client = bigquery.Client(project=self.project_id)
            logger.debug(f"Connected to BigQuery: {self.client.project}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to BigQuery: {str(e)}")

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a BigQuery SQL query and return results as a list of dictionaries.

        Args:
            query: SQL query to execute

        Returns:
            List of dictionaries, each representing a row of results
        """
        try:
            logger.info("Executing query...")
            logger.debug(f"Query: {query}")

            # Configure job with default dataset
            job_config = bigquery.QueryJobConfig()
            job_config.default_dataset = f"{self.project_id}.{self.dataset_id}"

            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()

            # Convert to list of dictionaries
            rows = []
            for row in results:
                row_dict = dict(row.items())
                rows.append(row_dict)

            logger.info(f"Query executed successfully, returned {len(rows)} rows")
            return rows
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            raise

    def execute_query_to_dataframe(self, query: str) -> pd.DataFrame:
        """Execute a BigQuery SQL query and return results as a pandas DataFrame."""
        try:
            # Configure job with default dataset
            job_config = bigquery.QueryJobConfig()
            job_config.default_dataset = f"{self.project_id}.{self.dataset_id}"

            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()

            # Convert to pandas DataFrame directly
            df = results.to_dataframe()

            return df
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        # Create connector
        bq = BigQueryConnector()

        query = """
        SELECT 
            EXTRACT(YEAR FROM month) as year,
            COUNT(*) as burglary_count
        FROM 
            crimes c
        JOIN
            crime_types ct 
            ON c.crime_type_id = ct.crime_type_id
        WHERE
            ct.crime_type = 'Burglary'
        GROUP BY 
            year
        ORDER BY 
            year
        """

        results = bq.execute_query(query)

        for result in results:
            print(result)
        df = bq.execute_query_to_dataframe(query)
        print(df)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")