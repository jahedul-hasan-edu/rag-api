"""
Async SQLAlchemy engine and session factory.

The engine is created once at startup and disposed on shutdown.
Sessions are short-lived and injected per request via get_db().
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings) -> AsyncEngine:
    """Create the async SQLAlchemy engine from settings."""
    return create_async_engine(
        settings.database_url.get_secret_value(),
        echo=not settings.is_production,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def init_db(settings: Settings) -> None:
    """Initialize global engine and session factory (call at app startup)."""
    global _engine, _session_factory
    _engine = create_engine(settings)
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def dispose_db() -> None:
    """Dispose the engine connection pool (call at app shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    """Return the initialized engine or raise if not ready."""
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the initialized session factory or raise if not ready."""
    if _session_factory is None:
        raise RuntimeError("Session factory is not initialized. Call init_db() first.")
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession for a single request.

    Commits on success, rolls back on exception, always closes.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
