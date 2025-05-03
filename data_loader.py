# data_loader.py

import pandas as pd
import db_config
import sys
from sqlalchemy.exc import SQLAlchemyError

# --- Function to Load a Full Table ---
def load_table(table_name, db_user=None, db_password=None):
    """
    Loads a specific table from the database into a Pandas DataFrame.
    Prompts for credentials if not provided.

    Args:
        table_name (str): The exact name of the database table to load.
                          NOTE: Be cautious if table_name comes from untrusted input.
        db_user (str, optional): Database username. If None, prompts the user.
        db_password (str, optional): Database password. If None, prompts the user.

    Returns:
        pandas.DataFrame or None: The loaded DataFrame if successful, None otherwise.
    """
    engine = None
    df = None
    try:
        if db_user is None or db_password is None:
            user, password = db_config.get_db_credentials()
        else:
            user, password = db_user, db_password
        engine = db_config.create_db_engine(user, password)
        if engine is None:
            print(f"Failed to get database engine. Cannot load table '{table_name}'.", file=sys.stderr)
            return None
        # Basic SELECT * query
        sql_query = f"SELECT * FROM {table_name}" # Consider quoting table name for safety
        print(f"Loading data from table: '{table_name}'...")
        df = pd.read_sql_query(sql_query, engine)
        print(f"Successfully loaded {len(df)} rows from '{table_name}'.")
    except pd.io.sql.DatabaseError as e:
        print(f"Pandas SQL Error loading table '{table_name}': {e}", file=sys.stderr)
        df = None
    except SQLAlchemyError as e:
         print(f"SQLAlchemy Error during data loading for '{table_name}': {e}", file=sys.stderr)
         df = None
    except Exception as e:
        print(f"An unexpected error occurred loading table '{table_name}': {e}", file=sys.stderr)
        df = None
    finally:
        if engine: engine.dispose()
    return df

# --- NEW Function to Execute a Custom Query ---
def load_query_results(sql_query, params=None, db_user=None, db_password=None):
    """
    Executes a custom SQL query and returns results as a Pandas DataFrame.
    Prompts for credentials if not provided.

    Args:
        sql_query (str): The SQL query string to execute.
        params (dict or tuple, optional): Parameters to pass to the query
            for safe substitution (prevents SQL injection). Use placeholders
            in your query string (e.g., :param_name for named params in dict,
            or %s/%? for positional params in tuple - check SQLAlchemy docs
            for specific driver). Defaults to None.
        db_user (str, optional): Database username. If None, prompts the user.
        db_password (str, optional): Database password. If None, prompts the user.

    Returns:
        pandas.DataFrame or None: The DataFrame with query results if successful,
                                  None otherwise.
    """
    engine = None
    df = None
    try:
        if db_user is None or db_password is None:
            user, password = db_config.get_db_credentials()
        else:
            user, password = db_user, db_password
        engine = db_config.create_db_engine(user, password)
        if engine is None:
            print("Failed to get database engine. Cannot execute query.", file=sys.stderr)
            return None

        print(f"Executing custom query...")
        # Use pandas read_sql_query, passing the params argument
        df = pd.read_sql_query(sql_query, engine, params=params)
        print(f"Successfully executed query, loaded {len(df)} rows.")

    except pd.io.sql.DatabaseError as e:
        # Errors during query execution (syntax errors, invalid objects, etc.)
        print(f"Pandas SQL Error executing query: {e}", file=sys.stderr)
        print(f"Query attempted:\n{sql_query}", file=sys.stderr)
        if params: print(f"With params: {params}", file=sys.stderr)
        df = None
    except SQLAlchemyError as e:
         print(f"SQLAlchemy Error during query execution: {e}", file=sys.stderr)
         df = None
    except Exception as e:
        print(f"An unexpected error occurred executing query: {e}", file=sys.stderr)
        df = None
    finally:
        if engine: engine.dispose()
    return df

# --- Function to Load Multiple Tables (optional, unchanged) ---
def load_multiple_tables(table_names, db_user=None, db_password=None):
    # ... (implementation from previous example remains the same) ...
    # It internally calls create_db_engine and read_sql_query
    # but constructs simple SELECT * queries.
    engine = None
    loaded_data = {}
    try:
        if db_user is None or db_password is None: user, password = db_config.get_db_credentials()
        else: user, password = db_user, db_password
        engine = db_config.create_db_engine(user, password)
        if engine is None:
            print("Failed to get database engine. Cannot load tables.", file=sys.stderr)
            return {name: None for name in table_names}
        for table_name in table_names:
            df = None
            try:
                sql_query = f"SELECT * FROM {table_name}"
                print(f"Loading data from table: '{table_name}'...")
                df = pd.read_sql_query(sql_query, engine)
                print(f"Successfully loaded {len(df)} rows from '{table_name}'.")
                loaded_data[table_name] = df
            except Exception as e: # Catch errors per table
                 print(f"Error loading table '{table_name}': {e}", file=sys.stderr)
                 loaded_data[table_name] = None
    finally:
        if engine: engine.dispose()
    return loaded_data