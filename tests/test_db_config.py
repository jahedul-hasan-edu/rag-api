from app.db.database import _normalize_database_url


def test_normalize_database_url_uses_asyncpg_driver() -> None:
    assert _normalize_database_url("postgresql://user:pass@localhost:5432/db") == (
        "postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    assert _normalize_database_url("postgresql+asyncpg://user:pass@localhost:5432/db") == (
        "postgresql+asyncpg://user:pass@localhost:5432/db"
    )
