import logging
import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("load.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
COLORS = ("yellow", "green")


def load_vehicle_emissions(con):
    con.execute("""
        DROP TABLE IF EXISTS vehicle_emissions;
        CREATE TABLE vehicle_emissions AS
        SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
    """)
    n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
    logger.info(f"vehicle_emissions: {n} rows loaded")


def create_trip_table(con, color):
    con.execute(f"""
        DROP TABLE IF EXISTS {color}_trips;
        CREATE TABLE {color}_trips (
            pickup_time TIMESTAMP,
            dropoff_time TIMESTAMP,
            passenger_count BIGINT,
            trip_distance DOUBLE
        );
    """)


def load_trips(con, color):
    table = f"{color}_trips"
    pickup_col = "tpep_pickup_datetime" if color == "yellow" else "lpep_pickup_datetime"
    dropoff_col = "tpep_dropoff_datetime" if color == "yellow" else "lpep_dropoff_datetime"

    for month in range(1, 13):
        url = f"{BASE_URL}/{color}_tripdata_2024-{month:02d}.parquet"
        con.execute(f"""
            INSERT INTO {table}
            SELECT
                {pickup_col} AS pickup_time,
                {dropoff_col} AS dropoff_time,
                passenger_count,
                trip_distance
            FROM read_parquet('{url}')
        """)
        logger.info(f"{table}: loaded month {month:02d}/2024")

    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    logger.info(f"{table}: {n} rows loaded (raw)")


def load_parquet_files():
    con = None
    try:
        con = duckdb.connect(database=DB_PATH, read_only=False)
        logger.info("Connected to DuckDB instance")

        load_vehicle_emissions(con)

        for color in COLORS:
            create_trip_table(con, color)
            load_trips(con, color)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    load_parquet_files()