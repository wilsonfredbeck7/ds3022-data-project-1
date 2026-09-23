import duckdb
import logging

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='clean.log'
)
logger = logging.getLogger(__name__)

def clean_trips():

    con = None

    try:
        con = duckdb.connect(database='emissions.duckdb', read_only=False)
        logger.info("Connected to DuckDB instance")

        for table in ("yellow_trips", "green_trips"):

            con.execute(f"""
                CREATE TABLE {table}_clean AS
                SELECT DISTINCT * FROM {table};
            """)
            con.execute(f"DROP TABLE {table};")
            con.execute(f"ALTER TABLE {table}_clean RENAME TO {table};")
            logger.info(f"{table}: removed duplicate trips")

            before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE passenger_count = 0").fetchone()[0]
            con.execute(f"DELETE FROM {table} WHERE passenger_count = 0;")
            after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE passenger_count = 0").fetchone()[0]
            logger.info(f"{table}: 0-passenger trips before={before}, after={after}")

            before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance = 0").fetchone()[0]
            con.execute(f"DELETE FROM {table} WHERE trip_distance = 0;")
            after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance = 0").fetchone()[0]
            logger.info(f"{table}: 0-mile trips before={before}, after={after}")

            before = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance > 100").fetchone()[0]
            con.execute(f"DELETE FROM {table} WHERE trip_distance > 100;")
            after = con.execute(f"SELECT COUNT(*) FROM {table} WHERE trip_distance > 100").fetchone()[0]
            logger.info(f"{table}: over-100-mile trips before={before}, after={after}")

            before = con.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE date_diff('second', pickup_time, dropoff_time) > 86400
            """).fetchone()[0]
            con.execute(f"""
                DELETE FROM {table}
                WHERE date_diff('second', pickup_time, dropoff_time) > 86400;
            """)
            after = con.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE date_diff('second', pickup_time, dropoff_time) > 86400
            """).fetchone()[0]
            logger.info(f"{table}: over-1-day trips before={before}, after={after}")

            final_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"{table}: final row count after cleaning = {final_count}")
            print(f"{table}: final row count after cleaning = {final_count}")

    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")

    finally:
        if con:
            con.close()

if __name__ == "__main__":
    clean_trips()