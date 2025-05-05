import logging
from db_connection.data_loader import CrimeDataLoader

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("crime_data_example")


def show_recent_crimes():
    """
    Example function demonstrating how to query recent crimes
    from a specific police force in a given area.
    """
    # Create data loader instance
    loader = CrimeDataLoader()

    try:
        query = """
        SELECT 
            c.crime_id, 
            c.month, 
            ct.crime_type_name,
            l.location_description,
            oc.outcome_description
        FROM 
            crimes c
            JOIN crime_types ct ON c.crime_type_id = ct.crime_type_id
            JOIN locations l ON c.location_id = l.location_id
            JOIN outcome_categories oc ON c.outcome_id = oc.outcome_id
        WHERE 
            c.month >= ? 
            AND c.falls_within_id = (SELECT force_id FROM police_forces WHERE force_name = ?)
        ORDER BY 
            c.month DESC
        LIMIT 10
        """

        # Parameters for the query
        params = ("2023-01", "Metropolitan Police Service")

        # Execute the query and get results as a DataFrame
        results = loader.execute_query(query=query, params=params)

        # Check if we got results and display them
        if results is not None and not results.empty:
            print(results)
            print("\nSummary by crime type:")
            print(results.groupby('crime_type_name').size())
        else:
            logger.warning("No crime data found for the given parameters")

    except Exception as e:
        logger.error(f"Error querying crime data: {e}")
        # Roll back any changes if there was an error
        loader.rollback()

    finally:
        # Always close the connection when done
        loader.close()


if __name__ == "__main__":
    show_recent_crimes()