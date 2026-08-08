import asyncio
import os
import sys

import asyncpg
from dotenv import load_dotenv

load_dotenv()


def _normalize_for_asyncpg(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return dsn


async def main() -> None:
    dsn = os.getenv("DATABASE_URL")

    if not dsn:
        print("DATABASE_URL not set in environment or .env")
        sys.exit(2)

    normalized = _normalize_for_asyncpg(dsn)

    print("Using DSN:", normalized)

    try:
        conn = await asyncpg.connect(
            dsn=normalized,
            ssl=False,
            timeout=10,
        )

        try:
            val = await conn.fetchval("SELECT 1")
            print("Connected successfully!")
            print("Test query result:", val)
        finally:
            await conn.close()

    except Exception as exc:
        print("Connection failed:", type(exc).__name__, str(exc))
        raise


if __name__ == "__main__":
    asyncio.run(main())