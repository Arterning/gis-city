"""Database connection and session management."""
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "gis_city")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

# URL encode the credentials to handle special characters
encoded_user = quote_plus(DB_USER)
encoded_password = quote_plus(DB_PASSWORD)
encoded_host = quote_plus(DB_HOST)
encoded_db = quote_plus(DB_NAME)

# Create database URL with encoded parameters
DATABASE_URL = f"postgresql://{encoded_user}:{encoded_password}@{encoded_host}:{DB_PORT}/{encoded_db}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"options": f"-csearch_path={DB_SCHEMA}"}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print(f"Database tables created in schema: {DB_SCHEMA}")
