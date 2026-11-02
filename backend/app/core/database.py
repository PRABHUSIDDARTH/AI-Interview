import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

# For SQLite, we need to allow multiple threads to communicate with it
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def wait_for_db(max_retries: int = 15, delay: float = 2.0) -> bool:
    """
    Wait for the database connection to become available during startup.
    Useful for containerized deployments (Docker Compose / Kubernetes).
    """
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established successfully.")
            return True
        except Exception as exc:
            if attempt == max_retries:
                logger.error(f"Could not connect to database after {max_retries} attempts: {exc}")
                raise exc
            logger.warning(f"Database connection attempt {attempt}/{max_retries} failed: {exc}. Retrying in {delay}s...")
            time.sleep(delay)
    return False

