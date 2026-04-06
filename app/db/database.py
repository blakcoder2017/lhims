from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Callable
from contextlib import contextmanager
from sqlalchemy.exc import InternalError
from fastapi import HTTPException
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=3600,   # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=True  # Expire objects after commit to prevent stale data
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Database session dependency with proper transaction management."""
    db = SessionLocal()
    try:
        yield db
    except HTTPException:
        # Don't log HTTP exceptions (like 401 authentication errors) as database errors
        raise
    except Exception as e:
        # Rollback the transaction on any exception
        db.rollback()
        logger.error(f"Database transaction error: {e}")
        raise e
    finally:
        db.close()


def get_fresh_db() -> Session:
    """Get a fresh database session with a new connection.
    Use this after catching an InFailedSqlTransaction error.
    """
    return SessionLocal()


def is_in_failed_transaction_error(e: Exception) -> bool:
    """Check if the error is an InFailedSqlTransaction error."""
    if isinstance(e, InternalError):
        return "InFailedSqlTransaction" in str(e)
    return False


@contextmanager
def safe_db_transaction(db: Session):
    """Context manager for database operations that handles transaction failures.
    
    Usage:
        with safe_db_transaction(db):
            db.query(SomeModel).filter(...).first()
    """
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction error, rolled back: {e}")
        # Check if we need a fresh session
        if is_in_failed_transaction_error(e):
            logger.warning("InFailedSqlTransaction detected, consider using get_fresh_db() for subsequent operations")
        raise e