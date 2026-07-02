# Design Decisions

## Why mirror the Goodreads plugin?

The Goodreads plugin is the established pattern in this workspace.
Following its structure (plugin.yaml → __init__.py → schemas.py → tools.py)
means consistent conventions, easier review, and no surprises for anyone
familiar with the codebase.

## FTS5 for search

SQLite's FTS5 extension provides ranked full-text search without any
external dependencies.  The `books_fts` virtual table is already
maintained by the scraper's import pipeline, so the plugin gets search
"for free".

## Partial LIKE for filtered listings

Genre, author, series, and publisher filters use `LIKE '%term%'` with
`COLLATE NOCASE`.  This is intentional — the database contains varied
name forms (e.g. "Aethon Books" vs "Aethon"), and partial matching
avoids the user needing to know exact strings.

## Module-level connection

A single `sqlite3.Connection` created lazily and reused avoids the
overhead of reconnecting on every tool call.  The connection is
process-scoped, which is safe because Hermes runs each tool call
in the same Python process.

## JSON string returns

Each handler accepts `(args: dict, **kwargs)` and returns a JSON-encoded
string via the `_ok()` / `_err()` helpers.  The `**kwargs` parameter is
required by the Hermes framework, which passes additional keyword arguments
(such as `task_id`, `session_id`, `user_task`) at call time.  Handlers
that omit `**kwargs` raise `TypeError` on invocation.

This matches the Goodreads plugin convention and lets the runtime
deserialize results uniformly.  For structured data (stats), the text
is line-oriented for easy reading.

## Identifier lookup delegates to book details

Rather than duplicating the book-formatting logic, the identifier
lookup handler calls `booksdb_get_book_details` with the resolved
book_id.  DRY principle.

## Environment variable for DB path

The database path is injected via `BOOKSDB_DB_PATH` in plugin.yaml's
env section, overridable via `hermes config set`.  This avoids
hardcoding paths and lets the plugin work across environments.
