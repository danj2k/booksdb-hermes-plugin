# Architecture

Booksdb is a Hermes Agent plugin that exposes the scraped book metadata
database (SQLite) as a set of LLM-queryable tools.

## Components

```
plugin.yaml        Manifest — name, version, description, env, tool list
__init__.py        Registration — maps tool names to handlers via _TOOL_MAP
schemas.py         JSON Schema definitions for every tool's parameters
tools.py           Handler functions that query the SQLite database
docs/              Architecture, design decisions, implementation notes
README.md          Quick-start and usage guide
```

## Data Flow

```
LLM tool call  →  Hermes runtime  →  tools.py handler
                                          ↓
                                    SQLite query (book_metadata.db)
                                          ↓
                                    Formatted text result  →  LLM
```

## Database

The source database lives at `book-metadata-scraper/book_metadata.db`.
Key tables:

| Table              | Purpose                                    |
|--------------------|--------------------------------------------|
| `books`            | Core book metadata (title, publisher, …)  |
| `authors`          | Normalised author names                    |
| `book_authors`     | Many-to-many with role (author/editor/…)  |
| `genres`           | Genre vocabulary                           |
| `book_genres`      | Book ↔ genre links                         |
| `book_identifiers` | ISBNs, ASINs, Goodreads IDs, etc.          |
| `sources`          | Data source registry (Aethon, Podium, …)   |
| `book_enrichment_log` | Tracks which source enriched each book  |
| `books_fts`        | FTS5 virtual table (title, subtitle, desc) |

## Connection Model

A single module-level `sqlite3.Connection` is created lazily on first
tool call and reused for the lifetime of the process.  WAL journal mode
and foreign keys are enabled.  This mirrors the Goodreads plugin's
pattern of one persistent connection.

## Tool Categories

**Search & lookup** — `booksdb_search` (FTS5), `booksdb_get_book_details`,
`booksdb_lookup_book_by_identifier`.

**Filtered listing** — `booksdb_get_books_by_author`, `booksdb_get_books_by_series`,
`booksdb_get_books_by_genre`, `booksdb_get_books_by_publisher`.

**Statistics** — `booksdb_get_database_stats`, `booksdb_get_genre_stats`,
`booksdb_get_publisher_stats`, `booksdb_get_author_stats`, `booksdb_list_sources`.
