import mariadb
import sys


def get_connection() -> mariadb.Connection:
    """
    Create and return a connection to the MariaDB sql_inserts.
    First tries connecting to 192.168.178.189, then to 192.168.178.190 if the first attempt fails.

    Returns:
        mariadb.Connection: An active connection to the sql_inserts

    Raises:
        SystemExit: If connection fails on both IP addresses
    """
    # First try with .189
    try:
        conn = mariadb.connect(
            host="192.168.178.189",
            port=3306,
            user="bilgin",
            password="1735403",
            database="crime_reports"
        )
        print("Connected successfully to 192.168.178.189")
        return conn
    except mariadb.Error as e:
        print(f"Failed to connect to 192.168.178.189: {e}")

        # Second try with .190
        try:
            conn = mariadb.connect(
                host="192.168.178.190",
                port=3306,
                user="bilgin",
                password="1735403",
                database="crime_reports"
            )
            print("Connected successfully to 192.168.178.190")
            return conn
        except mariadb.Error as e:
            print(f"Failed to connect to 192.168.178.190: {e}")
            print("Error connecting to either sql_inserts server")
            sys.exit(1)