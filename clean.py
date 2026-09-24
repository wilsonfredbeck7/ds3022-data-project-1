import logging
import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("clean.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
TABLES = ("yellow_trips", "green_trips")


def remove_duplicates(con, table):
    """Rebuild the table from SELECT DISTINCT so exact duplicate trips are removed."""
    con.execute(f"""
        CREATE OR REPLACE TABLE {table}_clean AS
        SELECT DISTINCT * FROM {table};
        DROP TABLE {table};
        ALTER TABLE {table}_clean RENAME TO {table};
    """)
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table} — after remove duplicates: {n}")
    logger.info(f"{table}: removed duplicates, row count now {n}")


def remove_where(con, table, label, condition):
    """Delete rows matching condition, then verify the condition no longer exists."""
    before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}").fetchone()[0]
    print(f"Before delete: {before}")

    con.execute(f"DELETE FROM {table} WHERE {condition}")

    after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}").fetchone()[0]
    print(f"After delete (verify): {after}")

    logger.info(f"{table} — {label}: before={before}, after={after}")


def clean_trips():
    """Apply all five cleaning rules to each trip table and log the final row counts."""
    con = None
    try:
        con = duckdb.connect(database=DB_PATH, read_only=False)
        logger.info("Connected to DuckDB instance")

        for table in TABLES:
            raw_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"{table}: raw row count {raw_count}")

            remove_duplicates(con, table)
            remove_where(con, table, "0-passenger trips", "passenger_count = 0")
            remove_where(con, table, "0-mile trips", "trip_distance = 0")
            remove_where(con, table, "trips > 100 miles", "trip_distance > 100")
            remove_where(con, table, "trips > 1 day",
                         "date_diff('second', pickup_time, dropoff_time) > 86400")

            final_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"{table}: final row count after cleaning = {final_count}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    clean_trips()