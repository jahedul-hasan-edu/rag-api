"""
Reusable pgvector SQLAlchemy type.

Wraps pgvector's Vector so models can declare embedding columns with a
consistent dimension without scattering vendor imports.
"""

from pgvector.sqlalchemy import Vector

# BAAI/bge-small-en-v1.5 produces 384-dimensional embeddings.
DEFAULT_EMBEDDING_DIMENSION = 384


def vector_type(dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> Vector:
    """Return a SQLAlchemy Vector type for the given dimension."""
    return Vector(dimension)
