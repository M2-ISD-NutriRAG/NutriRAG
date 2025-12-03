"""Embeddings table creation package.

This package provides functionality to create Snowflake tables with recipe embeddings.
Supports both Snowflake Cortex and local SentenceTransformer models, with in-memory
and batch processing modes.

Main entry point:
    python -m data.embeddings.create_table

Note: This package is internal and should not be imported directly from outside. Consider using `shared` instead.
"""

# Prevent external imports by not exposing anything
__all__ = []
