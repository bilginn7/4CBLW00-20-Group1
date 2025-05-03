import data_loader
import pandas as pd

user, password = data_loader.db_config.get_db_credentials()

# Custom query using the MySQL/MariaDB compatible parameter style (%s)
custom_query = """
SELECT 
    month_year, 
    reported_by, 
    crime_type, 
    last_outcome_category,
    COUNT(*) as incident_count
FROM met_force
WHERE 
    month_year >= %s 
    AND crime_type = %s
GROUP BY 
    month_year, 
    reported_by, 
    crime_type, 
    last_outcome_category
ORDER BY 
    month_year DESC, 
    incident_count DESC
LIMIT 25;
"""

# Parameters as a tuple (positional) instead of a dictionary (named)
query_params = ('2023-01', 'Burglary')  # First param is start_date, second is crime_category

# Execute the custom query with parameters
results_df = data_loader.load_query_results(
    custom_query,
    params=query_params,  # Pass as a tuple for positional parameters
    db_user=user,
    db_password=password
)

if results_df is not None and not results_df.empty:
    print("\nSuccessfully executed custom query:")
    print(results_df)

    # Basic analysis on the results
    print("\nQuery Results Info:")
    results_df.info()

    # Count by reporting force
    if 'reported_by' in results_df.columns:
        print("\nIncidents by Reporting Force:")
        print(results_df['reported_by'].value_counts())

    # Count by outcome category if not too many nulls
    if 'last_outcome_category' in results_df.columns and results_df['last_outcome_category'].notna().sum() > 5:
        print("\nIncidents by Outcome Category:")
        print(results_df['last_outcome_category'].value_counts())

    # Calculate percentage of incidents with no outcome yet
    null_outcomes = results_df['last_outcome_category'].isna().sum()
    total_records = len(results_df)
    if total_records > 0:
        print(f"\nPercentage of incidents with no outcome recorded: {(null_outcomes / total_records) * 100:.2f}%")
else:
    print("\nFailed to execute custom query on 'met_force'.")