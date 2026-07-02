# booksdb

Hermes Agent plugin for searching and querying the scraped book metadata
database.

## What it does

Exposes 12 tools that let the LLM search, filter, and analyse book
metadata stored in a SQLite database:

- **Search** — full-text search across titles, subtitles, and descriptions
  (FTS5)
- **Look up** — by book ID, title, or identifier (ISBN, ASIN, etc.)
- **Filter** — by author, series, genre, or publisher
- **Stats** — database overview, genre/publisher/author breakdowns

## Setup

```bash
# Point the plugin at your database
hermes config set plugins.booksdb.env.BOOKSDB_DB_PATH /path/to/book_metadata.db
```

## Tools

| Tool | Description |
|------|-------------|
| `booksdb_search` | Full-text search (FTS5 syntax) |
| `booksdb_get_book_details` | Full metadata for one book |
| `booksdb_get_books_by_author` | Books by author (partial match) |
| `booksdb_get_books_by_series` | Books in a series (ordered) |
| `booksdb_get_books_by_genre` | Books by genre |
| `booksdb_get_books_by_publisher` | Books by publisher |
| `booksdb_lookup_book_by_identifier` | Find by ISBN/ASIN/Goodreads ID |
| `booksdb_get_database_stats` | High-level DB statistics |
| `booksdb_get_genre_stats` | Genre breakdown |
| `booksdb_get_publisher_stats` | Publisher breakdown |
| `booksdb_get_author_stats` | Author stats by book count |
| `booksdb_list_sources` | List data sources and enrichment counts |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for component layout
and data flow.

## Design rationale

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) for why
decisions were made the way they were.

## Implementation notes

See [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md) for
technical details on query patterns, connection management, and testing.
