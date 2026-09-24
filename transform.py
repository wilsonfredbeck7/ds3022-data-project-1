import logging
import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("transform.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
TABLES = ("yellow_trips", "green_trips")
VEHICLE_TYPE = {"yellow_trips": "yellow_taxi", "green_trips": "green_taxi"}

NEW_COLUMNS = {
    "trip_co2_kgs":  "DOUBLE",
    "avg_mph":       "DOUBLE",
    "hour_of_day":   "INTEGER",
    "day_of_week":   "INTEGER",
    "week_of_year":  "INTEGER",
    "month_of_year": "INTEGER",
}


def add_columns(con, table):
    """Add all six new columns if they don't already exist."""
    for column, dtype in NEW_COLUMNS.items():
        con.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {dtype}")
    logger.info(f"{table}: ensured columns {list(NEW_COLUMNS)} exist")


def set_trip_co2(con, table):
    """Set trip_co2_kgs = distance x co2_grams_per_mile / 1000, looking the rate up
    in vehicle_emissions at run time instead of hard-coding it."""
    vehicle_type = VEHICLE_TYPE[table]
    con.execute(f"""
        UPDATE {table} SET trip_co2_kgs = (
            SELECT ({table}.trip_distance * ve.co2_grams_per_mile) / 1000.0
            FROM vehicle_emissions ve
            WHERE ve.vehicle_type = '{vehicle_type}'
        )
    """)
    logger.info(f"{table}: set trip_co2_kgs from vehicle_emissions lookup ({vehicle_type})")


def set_avg_mph(con, table):
    """Set avg_mph = distance / duration in hours. NULLIF avoids dividing by zero
    on trips with a 0-second duration."""
    con.execute(f"""
        UPDATE {table}
        SET avg_mph = trip_distance /
            NULLIF(date_diff('second', pickup_time, dropoff_time) / 3600.0, 0)
    """)
    logger.info(f"{table}: set avg_mph")


def set_date_parts(con, table):
    """Extract hour, day of week (0=Sunday), week and month from pickup_time."""
    con.execute(f"""
        UPDATE {table} SET
            hour_of_day   = date_part('hour', pickup_time),
            day_of_week   = date_part('dow', pickup_time),
            week_of_year  = date_part('week', pickup_time),
            month_of_year = date_part('month', pickup_time)
    """)
    logger.info(f"{table}: set hour_of_day, day_of_week, week_of_year, month_of_year")


def transform_trips():
    """Add and populate the six calculated columns on each trip table."""
    con = None
    try:
        con = duckdb.connect(database=DB_PATH, read_only=False)
        logger.info("Connected to DuckDB instance")

        for table in TABLES:
            add_columns(con, table)
            set_trip_co2(con, table)
            set_avg_mph(con, table)
            set_date_parts(con, table)

            sample = con.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()
            logger.info(f"{table}: sample row after transform = {sample}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    transform_trips()