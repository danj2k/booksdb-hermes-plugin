"""JSON Schema definitions for every booksdb tool."""

_LIMIT_DESC = "Maximum results to return.  Clamped to 1-50.  Default 20 if omitted."
_OFFSET_DESC = "Offset into the full result set for pagination.  Zero-based.  Default 0 if omitted."

SEARCH = {
    "name": "booksdb_search",
    "description": "Full-text search across book titles, subtitles, and descriptions using FTS5.  Returns matching books with author, genre, and series information.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query.  Supports FTS5 syntax: plain words, quoted phrases, AND/OR/NOT operators, and prefix wildcards."},
            "limit": {"type": "integer", "description": _LIMIT_DESC},
            "offset": {"type": "integer", "description": _OFFSET_DESC},
        },
        "required": ["query"],
    },
}

GET_BOOK_DETAILS = {
    "name": "booksdb_get_book_details",
    "description": "Return full metadata for a single book: title, subtitle, description, publisher, publication date, page count, language, series info, cover image URL, source URL, authors (with roles), genres, and all known identifiers.",
    "parameters": {
        "type": "object",
        "properties": {
            "book_id": {"type": "integer", "description": "Numeric book ID from the database."},
            "title": {"type": "string", "description": "Book title to look up (case-insensitive exact match).  Ignored if book_id is provided."},
        },
    },
}

GET_BOOKS_BY_AUTHOR = {
    "name": "booksdb_get_books_by_author",
    "description": "List books by a given author (partial, case-insensitive name match).  Returns title, series, series position, publication date, page count, and genres.",
    "parameters": {
        "type": "object",
        "properties": {
            "author": {"type": "string", "description": "Author name to search for (partial match, case-insensitive)."},
            "limit": {"type": "integer", "description": _LIMIT_DESC},
            "offset": {"type": "integer", "description": _OFFSET_DESC},
        },
        "required": ["author"],
    },
}

GET_BOOKS_BY_SERIES = {
    "name": "booksdb_get_books_by_series",
    "description": "List all books in a named series, ordered by series position.  Returns title, author, publication date, page count, and genres.",
    "parameters": {
        "type": "object",
        "properties": {
            "series": {"type": "string", "description": "Series name to search for (partial, case-insensitive match)."},
            "limit": {"type": "integer", "description": _LIMIT_DESC},
            "offset": {"type": "integer", "description": _OFFSET_DESC},
        },
        "required": ["series"],
    },
}

GET_BOOKS_BY_GENRE = {
    "name": "booksdb_get_books_by_genre",
    "description": "List books tagged with a given genre (partial, case-insensitive match).  Returns title, author, series, publication date, page count, and other genres.",
    "parameters": {
        "type": "object",
        "properties": {
            "genre": {"type": "string", "description": "Genre name to search for (partial match, case-insensitive)."},
            "limit": {"type": "integer", "description": _LIMIT_DESC},
            "offset": {"type": "integer", "description": _OFFSET_DESC},
        },
        "required": ["genre"],
    },
}

GET_BOOKS_BY_PUBLISHER = {
    "name": "booksdb_get_books_by_publisher",
    "description": "List books from a given publisher (partial, case-insensitive match).  Returns title, author, series, publication date, page count, and genres.",
    "parameters": {
        "type": "object",
        "properties": {
            "publisher": {"type": "string", "description": "Publisher name to search for (partial match, case-insensitive)."},
            "limit": {"type": "integer", "description": _LIMIT_DESC},
            "offset": {"type": "integer", "description": _OFFSET_DESC},
        },
        "required": ["publisher"],
    },
}

LOOKUP_BOOK_BY_IDENTIFIER = {
    "name": "booksdb_lookup_book_by_identifier",
    "description": "Look up a book by a specific identifier: ISBN-10, ISBN-13, ASIN, Goodreads book ID, Google Books ID, or any other identifier type stored in the database.",
    "parameters": {
        "type": "object",
        "properties": {
            "identifier_type": {"type": "string", "description": "Type of identifier.  Common values: isbn10, isbn13, asin, asin_ebook, asin_audiobook, asin_paperback, goodreads, google_books."},
            "identifier_value": {"type": "string", "description": "The identifier value to look up."},
        },
        "required": ["identifier_type", "identifier_value"],
    },
}

GET_DATABASE_STATS = {
    "name": "booksdb_get_database_stats",
    "description": "Return high-level statistics about the book metadata database: total books, authors, genres, series, sources, and identifier counts.",
    "parameters": {"type": "object", "properties": {}},
}

GET_GENRE_STATS = {
    "name": "booksdb_get_genre_stats",
    "description": "Return a breakdown of books by genre: genre name, book count, and the most recent book in each genre.  Ordered by book count descending.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": _LIMIT_DESC},
        },
    },
}

GET_PUBLISHER_STATS = {
    "name": "booksdb_get_publisher_stats",
    "description": "Return a breakdown of books by publisher: publisher name, book count, and the most recent book from each publisher.  Ordered by book count descending.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": _LIMIT_DESC},
        },
    },
}

GET_AUTHOR_STATS = {
    "name": "booksdb_get_author_stats",
    "description": "Return author statistics: name, book count, genres written, and the most recent book.  Ordered by book count descending.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": _LIMIT_DESC},
        },
    },
}

LIST_SOURCES = {
    "name": "booksdb_list_sources",
    "description": "List all data sources in the database: name, source type, and the number of books contributed by each.",
    "parameters": {"type": "object", "properties": {}},
}
