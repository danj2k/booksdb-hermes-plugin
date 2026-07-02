"""
Booksdb plugin — registration entry point.

Hermes calls register(ctx) exactly once at startup.
Every tool is paired with its schema (what the LLM sees) and
its handler (the code that runs).
"""

import logging

from . import schemas, tools

logger = logging.getLogger(__name__)

_TOOLSET = "booksdb"

_TOOL_MAP = [
    ("booksdb_search",                      schemas.SEARCH,                      tools.booksdb_search),
    ("booksdb_get_book_details",            schemas.GET_BOOK_DETAILS,           tools.booksdb_get_book_details),
    ("booksdb_get_books_by_author",         schemas.GET_BOOKS_BY_AUTHOR,        tools.booksdb_get_books_by_author),
    ("booksdb_get_books_by_series",         schemas.GET_BOOKS_BY_SERIES,        tools.booksdb_get_books_by_series),
    ("booksdb_get_books_by_genre",          schemas.GET_BOOKS_BY_GENRE,         tools.booksdb_get_books_by_genre),
    ("booksdb_get_books_by_publisher",      schemas.GET_BOOKS_BY_PUBLISHER,     tools.booksdb_get_books_by_publisher),
    ("booksdb_lookup_book_by_identifier",   schemas.LOOKUP_BOOK_BY_IDENTIFIER,  tools.booksdb_lookup_book_by_identifier),
    ("booksdb_get_database_stats",          schemas.GET_DATABASE_STATS,         tools.booksdb_get_database_stats),
    ("booksdb_get_genre_stats",             schemas.GET_GENRE_STATS,            tools.booksdb_get_genre_stats),
    ("booksdb_get_publisher_stats",         schemas.GET_PUBLISHER_STATS,        tools.booksdb_get_publisher_stats),
    ("booksdb_get_author_stats",            schemas.GET_AUTHOR_STATS,           tools.booksdb_get_author_stats),
    ("booksdb_list_sources",                schemas.LIST_SOURCES,               tools.booksdb_list_sources),
]


def register(ctx):
    """Register all booksdb tools with Hermes."""
    for name, schema, handler in _TOOL_MAP:
        ctx.register_tool(
            name=name,
            toolset=_TOOLSET,
            schema=schema,
            handler=handler,
        )
    logger.info(
        "booksdb plugin: registered %d tools (toolset=%r)",
        len(_TOOL_MAP),
        _TOOLSET,
    )
