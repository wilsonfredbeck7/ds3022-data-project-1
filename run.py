import logging
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(PROJECT_DIR, "run.log")), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

STEPS = ("load.py", "clean.py", "transform.py", "analysis.py")


def run_pipeline():
    """Run load -> clean -> transform -> analysis in order, stopping at the first failure.
    Each step runs from the project folder so relative paths like data/ resolve."""
    try:
        for step in STEPS:
            logger.info(f"Starting {step}")
            subprocess.run([sys.executable, step], cwd=PROJECT_DIR, check=True)
            logger.info(f"Finished {step}")
        logger.info("Pipeline complete")

    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline stopped: {e.cmd[-1]} exited with code {e.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
