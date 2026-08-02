"""
Reusable pgvector SQLAlchemy type.

Wraps pgvector's Vector so models can declare embedding columns with a
consistent dimension without scattering vendor imports.
"""

from pgvector.sqlalchemy import Vector

# Default OpenAI text-embedding-3-small dimension; override per-column if needed.
DEFAULT_EMBEDDING_DIMENSION = 1536


def vector_type(dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> Vector:
    """Return a SQLAlchemy Vector type for the given dimension."""
    return Vector(dimension)
