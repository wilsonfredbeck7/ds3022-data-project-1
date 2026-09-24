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
    """Load the vehicle_emissions lookup table from the local CSV and log its row count."""
    con.execute("""
        DROP TABLE IF EXISTS vehicle_emissions;
        CREATE TABLE vehicle_emissions AS
        SELECT * FROM read_csv_auto('data/vehicle_emissions.csv');
    """)
    n = con.execute("SELECT COUNT(*) FROM vehicle_emissions").fetchone()[0]
    print(f"vehicle_emissions — raw row count: {n}")
    logger.info(f"vehicle_emissions: {n} rows loaded")


def create_trip_table(con, color):
    """Create an empty trip table with only the four columns this project needs."""
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
    """Insert all 12 monthly 2024 Parquet files for one taxi color, renaming the
    tpep_/lpep_ time columns to a shared pickup_time/dropoff_time."""
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
    print(f"{table} — raw row count: {n}")
    logger.info(f"{table}: {n} rows loaded (raw)")


def describe_trips(con, table):
    """Print and log descriptive statistics for a raw trip table, before cleaning."""
    stats = con.execute(f"""
        SELECT
            MIN(pickup_time),
            MAX(pickup_time),
            AVG(trip_distance),
            MAX(trip_distance),
            AVG(passenger_count),
            MAX(passenger_count)
        FROM {table}
    """).fetchone()
    print(f"{table} — earliest pickup: {stats[0]}, latest pickup: {stats[1]}")
    print(f"{table} — avg trip_distance: {stats[2]:.2f} mi, max trip_distance: {stats[3]:.2f} mi")
    print(f"{table} — avg passenger_count: {stats[4]:.2f}, max passenger_count: {stats[5]}")
    logger.info(f"{table}: pickup range {stats[0]} to {stats[1]}")
    logger.info(f"{table}: avg trip_distance={stats[2]:.2f}, max trip_distance={stats[3]:.2f}")
    logger.info(f"{table}: avg passenger_count={stats[4]:.2f}, max passenger_count={stats[5]}")


def load_parquet_files():
    """Connect to DuckDB and load vehicle_emissions, yellow_trips and green_trips."""
    con = None
    try:
        con = duckdb.connect(database=DB_PATH, read_only=False)
        logger.info("Connected to DuckDB instance")

        load_vehicle_emissions(con)

        for color in COLORS:
            create_trip_table(con, color)
            load_trips(con, color)
            describe_trips(con, f"{color}_trips")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    load_parquet_files()