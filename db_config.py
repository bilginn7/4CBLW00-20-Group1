import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# --- Configuration Constants ---
DB_HOST = '192.168.178.190'
DB_NAME = 'crime_reports'
DB_PORT = 3306

# --- Engine Creation Function ---
def create_db_engine(db_user, db_password):
    """
    Creates and returns a SQLAlchemy engine using provided credentials.

    Args:
        db_user (str): The database username.
        db_password (str): The database password.

    Returns:
        sqlalchemy.engine.Engine or None: The engine object if successful, None otherwise.
    """
    engine = None
    try:
        db_uri = (
            f"mysql+pymysql://{db_user}:{db_password}@"
            f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        engine = create_engine(db_uri, echo=False)
        with engine.connect() as connection:
            print(f"Successfully tested connection to {DB_NAME} as user '{db_user}'.")
        return engine
    except SQLAlchemyError as e:
        print(f"Error creating/connecting DB engine for user '{db_user}': {e}", file=sys.stderr)
        if engine: engine.dispose()
        return None
    except Exception as e:
        print(f"An unexpected error occurred during engine creation: {e}", file=sys.stderr)
        if engine: engine.dispose()
        return None

# --- Helper to Get Credentials ---
def get_db_credentials():
    """Prompts the user for database username and password."""
    print("--- Database Credentials Required ---")
    db_user = input("Enter database username: ")
    db_password = input("Enter database password: ")
    print("------------------------------------")
    return db_user, db_password