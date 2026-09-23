import duckdb
import os
import logging

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename='load.log'
)
logger = logging.getLogger(__name__)

def load_parquet_files():

    con = None

    try:
        # Connect to local DuckDB instance
        con = duckdb.connect(database='emissions.duckdb', read_only=False)
        logger.info("Connected to DuckDB instance")

        con.execute("INSTALL httpfs; LOAD httpfs;")
        logger.info("Loaded httpfs extension")

        con.execute("DROP TABLE IF EXISTS yellow_trips;")
        con.execute("""
            CREATE TABLE yellow_trips (
                pickup_time TIMESTAMP,
                dropoff_time TIMESTAMP,
                passenger_count BIGINT,
                trip_distance DOUBLE
            );
        """)

        con.execute("DROP TABLE IF EXISTS green_trips;")
        con.execute("""
            CREATE TABLE green_trips (
                pickup_time TIMESTAMP,
                dropoff_time TIMESTAMP,
                passenger_count BIGINT,
                trip_distance DOUBLE
            );
        """)
        logger.info("Created yellow_trips and green_trips tables")

        base_url = "https://d37ci6vzurychx.cloudfront.net/trip-data"

        for month in range(1, 13):
            url = f"{base_url}/yellow_tripdata_2024-{month:02d}.parquet"
            con.execute(f"""
                INSERT INTO yellow_trips
                SELECT
                    tpep_pickup_datetime AS pickup_time,
                    tpep_dropoff_datetime AS dropoff_time,
                    passenger_count,
                    trip_distance
                FROM read_parquet('{url}');
            """)
            logger.info(f"Loaded yellow trips for 2024-{month:02d}")

        for month in range(1, 13):
            url = f"{base_url}/green_tripdata_2024-{month:02d}.parquet"
            con.execute(f"""
                INSERT INTO green_trips
                SELECT
                    lpep_pickup_datetime AS pickup_time,
                    lpep_dropoff_datetime AS dropoff_time,
                    passenger_count,
                    trip_distance
                FROM read_parquet('{url}');
            """)
            logger.info(f"Loaded green trips for 2024-{month:02d}")

        con.execute("DROP TABLE IF EXISTS vehicle_emissions;")
        con.execute("""
            CREATE TABLE vehicle_emissions AS
            SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
        """)
        logger.info("Loaded vehicle_emissions table")

        for table in ("yellow_trips", "green_trips", "vehicle_emissions"):
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info(f"{table} row count: {count}")
            print(f"{table} row count: {count}")

    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    load_parquet_files()