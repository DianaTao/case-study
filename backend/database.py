"""Database client and utilities."""
from supabase import create_client, Client
from config import settings
import structlog

logger = structlog.get_logger()

# Global Supabase client
supabase: Client = None


def init_db():
    """Initialize database connection."""
    global supabase
    try:
        supabase = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


def get_db() -> Client:
    """Get database client."""
    if supabase is None:
        init_db()
    return supabase
