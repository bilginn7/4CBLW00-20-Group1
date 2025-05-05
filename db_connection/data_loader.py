import pandas as pd
import mariadb
from typing import Optional, Any, List, Tuple, Union
from db_connection.db_config import get_connection
import logging

logger = logging.getLogger(__name__)

class CrimeDataLoader:
    """
    Handles sql_inserts connection and query execution for the crime data.
    Manages transactions explicitly.
    """

    def __init__(self) -> None:
        """Initialize sql_inserts connection and cursor."""
        self.conn: Optional[mariadb.Connection] = None
        self.cur: Optional[mariadb.Cursor] = None
        try:
            self.conn = get_connection()
            if self.conn: # Check if connection was successful
                self.cur = self.conn.cursor()
            else:
                 raise mariadb.Error("Failed to establish sql_inserts connection.")
        except mariadb.Error as e:
            logger.critical(f"Database connection failed on init: {e}", exc_info=True)
            raise


    def execute_query(self,
                      query: str,
                      params: Optional[Union[Tuple[Any, ...], List[Any]]] = None,
                      return_affected_rows: bool = False) -> Union[Optional[pd.DataFrame], Optional[int]]:
        """
        Execute an SQL query. Returns a DataFrame for SELECT, affected rows for DML
        if requested, or None otherwise/on error.

        Args:
            query: SQL query string.
            params: Optional tuple/list of parameters for a parameterized query.
            return_affected_rows: If True and query is DML (INSERT/UPDATE/DELETE),
                                 return the count of affected rows instead of None.

        Returns:
            - pandas.DataFrame: If the query returns results (e.g., SELECT).
            - int: If return_affected_rows is True and a query is DML.
            - None: If a query is DML and return_affected_rows is False, or on error,
                    or if the connection is not valid.
        """
        if not self.cur or not self.conn:
             logger.error("Cannot execute query, sql_inserts connection not available.")
             return None

        try:
            if params:
                self.cur.execute(query, params)
            else:
                self.cur.execute(query)

            # Check if the query returns rows
            if self.cur.description:
                columns = [desc[0] for desc in self.cur.description]
                results = self.cur.fetchall()
                return pd.DataFrame(results, columns=columns)
            else:
                affected_rows = self.cur.rowcount
                if return_affected_rows:
                    return affected_rows
                else:
                    return None

        except mariadb.Error as e:
            logger.error(f"MariaDB query execution error: {e}")
            logger.error(f"Failed Query: {query[:500]}{'...' if len(query)>500 else ''}") # Log query on error
            if params:
                param_repr = repr(params)
                logger.error(f"Params: {param_repr[:500]}{'...' if len(param_repr)>500 else ''}")
            return None
        except Exception as e:
            logger.error(f"General error during query execution: {e}", exc_info=True)
            logger.error(f"Failed Query: {query[:500]}{'...' if len(query)>500 else ''}")
            return None

    def commit(self) -> None:
        """Commit the current transaction."""
        if self.conn:
            try:
                self.conn.commit()
            except mariadb.Error as e:
                logger.error(f"Failed to commit transaction: {e}")
        else:
             logger.warning("Attempted to commit with no active connection.")


    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self.conn:
            try:
                logger.warning("Rolling back transaction.")
                self.conn.rollback()
            except mariadb.Error as e:
                logger.error(f"Failed to rollback transaction: {e}")
        else:
             logger.warning("Attempted to rollback with no active connection.")


    def close(self) -> None:
        """Close the sql_inserts cursor and connection."""
        if self.cur:
            try:
                self.cur.close()
                self.cur = None
            except mariadb.Error as e:
                logger.warning(f"Error closing cursor: {e}")
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.info("Database connection closed.")
            except mariadb.Error as e:
                 logger.warning(f"Error closing connection: {e}")

    def __del__(self) -> None:
        """Ensure the connection is closed when an object is destroyed."""
        self.close()