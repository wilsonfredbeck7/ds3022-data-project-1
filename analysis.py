import logging
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("analysis.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DB_PATH = "emissions.duckdb"
TABLES = ("yellow_trips", "green_trips")
PLOT_PATH = "co2_by_month.png"

DAY_NAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December")

# (column, label) pairs for the heaviest/lightest questions
TIME_PERIODS = (
    ("hour_of_day",   "hour of day"),
    ("day_of_week",   "day of week"),
    ("week_of_year",  "week of year"),
    ("month_of_year", "month of year"),
)


def period_name(column, value):
    """Turn a date-part number into a readable label (e.g. 0 -> Sunday, 3 -> March)."""
    if column == "day_of_week":
        return DAY_NAMES[value]
    if column == "month_of_year":
        return MONTH_NAMES[value - 1]
    if column == "hour_of_day":
        return f"{value:02d}:00"
    return f"week {value}"


def largest_trip(con, table):
    """Print and log the single trip with the highest trip_co2_kgs in the table."""
    trip = con.execute(f"""
        SELECT pickup_time, trip_distance, trip_co2_kgs
        FROM {table}
        ORDER BY trip_co2_kgs DESC
        LIMIT 1
    """).fetchone()
    print(f"{table} — largest CO2 trip: {trip[2]:.3f} kg "
          f"({trip[1]:.2f} mi, picked up {trip[0]})")
    logger.info(f"{table}: largest CO2 trip = {trip[2]:.3f} kg, "
                f"distance={trip[1]:.2f} mi, pickup_time={trip[0]}")


def heaviest_and_lightest(con, table, column, label):
    """Average trip_co2_kgs by one time period, then print and log the
    heaviest (highest average) and lightest (lowest average) period."""
    rows = con.execute(f"""
        SELECT {column}, AVG(trip_co2_kgs) AS avg_co2
        FROM {table}
        GROUP BY {column}
        ORDER BY avg_co2 DESC
    """).fetchall()
    heaviest = rows[0]
    lightest = rows[-1]
    print(f"{table} — heaviest {label}: {period_name(column, heaviest[0])} "
          f"(avg {heaviest[1]:.3f} kg per trip)")
    print(f"{table} — lightest {label}: {period_name(column, lightest[0])} "
          f"(avg {lightest[1]:.3f} kg per trip)")
    logger.info(f"{table}: heaviest {label} = {period_name(column, heaviest[0])}, "
                f"avg={heaviest[1]:.3f} kg")
    logger.info(f"{table}: lightest {label} = {period_name(column, lightest[0])}, "
                f"avg={lightest[1]:.3f} kg")


def monthly_co2(con, table):
    """Return total trip_co2_kgs for each month 1-12 as a list of 12 values."""
    rows = con.execute(f"""
        SELECT month_of_year, SUM(trip_co2_kgs)
        FROM {table}
        GROUP BY month_of_year
        ORDER BY month_of_year
    """).fetchall()
    totals = dict(rows)
    return [totals.get(month, 0) for month in range(1, 13)]


def plot_co2_by_month(con):
    """Plot total monthly CO2 for yellow and green taxis as two series and save it as a PNG."""
    months = range(1, 13)
    plt.figure(figsize=(10, 6))
    for table, color in (("yellow_trips", "gold"), ("green_trips", "green")):
        totals = monthly_co2(con, table)
        plt.plot(months, totals, marker="o", color=color, label=table.replace("_trips", " taxi"))
    plt.title("Total CO2 Output by Month, NYC Taxis 2024")
    plt.xlabel("Month")
    plt.ylabel("Total CO2 (kg, log scale)")
    plt.xticks(months, [name[:3] for name in MONTH_NAMES])
    plt.yscale("log")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_PATH)
    plt.close()
    print(f"Saved CO2-by-month plot to {PLOT_PATH}")
    logger.info(f"Saved CO2-by-month plot to {PLOT_PATH}")


def analyze_trips():
    """Answer the five analysis questions for each cab type and render the CO2 plot."""
    con = None
    try:
        con = duckdb.connect(database=DB_PATH, read_only=True)
        logger.info("Connected to DuckDB instance")

        for table in TABLES:
            largest_trip(con, table)
            for column, label in TIME_PERIODS:
                heaviest_and_lightest(con, table, column, label)

        plot_co2_by_month(con)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    analyze_trips()
