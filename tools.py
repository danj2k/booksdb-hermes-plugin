"""
Booksdb tool handlers.

Every public function in this module:
  • Accepts (args: dict, **kwargs)
  • Returns a JSON string (never raises)
  • Uses a module-level SQLite connection (shared across calls)

The database path is read from the BOOKSDB_DB_PATH environment variable,
which is required by plugin.yaml.
"""

import json
import logging
import os
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response helpers (match goodreads plugin convention)
# ---------------------------------------------------------------------------

def _ok(data) -> str:
    """Return a JSON-encoded success payload."""
    return json.dumps(data, default=str)


def _err(msg: str) -> str:
    """Return a JSON-encoded error payload."""
    return json.dumps({"error": msg})


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

_db_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    """Return a module-level SQLite connection (created lazily).

    The connection is module-scoped so every handler shares a single
    persistent connection — identical to how the Goodreads plugin avoids
    per-call connect overhead.
    """
    global _db_conn
    if _db_conn is None:
        path = os.environ.get("BOOKSDB_DB_PATH")
        if not path:
            raise RuntimeError(
                "BOOKSDB_DB_PATH is not set.  Configure the plugin via "
                "hermes config set plugins.booksdb.env.BOOKSDB_DB_PATH /path/to/book_metadata.db"
            )
        _db_conn = sqlite3.connect(path, check_same_thread=False)
        _db_conn.row_factory = sqlite3.Row
        _db_conn.execute("PRAGMA journal_mode=WAL")
        _db_conn.execute("PRAGMA foreign_keys=ON")
    return _db_conn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: Any, default: int, lo: int, hi: int) -> int:
    """Coerce *value* to an int in [lo, hi], falling back to *default*."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _row_get(row: sqlite3.Row, key: str):
    """Safe attribute access for sqlite3.Row (which lacks .get())."""
    keys = row.keys()
    if key in keys:
        return row[key]
    return None


def _book_summary(row: sqlite3.Row) -> str:
    """One-line summary for a book row that has at least b.* columns."""
    parts = [f"[{row['id']}] {row['title']}"]
    author = _row_get(row, "author_name")
    if author:
        parts.append(f"by {author}")
    series = _row_get(row, "series")
    if series:
        pos = _row_get(row, "series_position")
        pos_str = f" #{int(pos)}" if pos else ""
        parts.append(f"({series}{pos_str})")
    publisher = _row_get(row, "publisher")
    if publisher:
        parts.append(f"- {publisher}")
    pub_date = _row_get(row, "published_date")
    if pub_date:
        parts.append(f"({pub_date[:4]})")
    return " ".join(parts)


def _join_authors(book_id: int) -> str:
    """Comma-separated author names for a book."""
    rows = _db().execute(
        "SELECT a.name, ba.role FROM book_authors ba "
        "JOIN authors a ON a.id = ba.author_id WHERE ba.book_id = ?",
        (book_id,),
    ).fetchall()
    if not rows:
        return "Unknown author"
    return ", ".join(
        f"{r['name']}" + (f" ({r['role']})" if r["role"] != "author" else "")
        for r in rows
    )


def _join_genres(book_id: int) -> str:
    """Comma-separated genre names for a book."""
    rows = _db().execute(
        "SELECT g.name FROM book_genres bg "
        "JOIN genres g ON g.id = bg.genre_id WHERE bg.book_id = ?",
        (book_id,),
    ).fetchall()
    return ", ".join(r["name"] for r in rows) if rows else ""


def _join_identifiers(book_id: int) -> str:
    """Semicolon-separated identifier:type pairs for a book."""
    rows = _db().execute(
        "SELECT identifier_type, identifier_value FROM book_identifiers WHERE book_id = ?",
        (book_id,),
    ).fetchall()
    return "; ".join(f"{r['identifier_type']}:{r['identifier_value']}" for r in rows)


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def booksdb_search(args: dict, **kwargs) -> str:
    """Full-text search via FTS5."""
    query = args.get("query", "").strip()
    if not query:
        return _ok({"text": "Error: query is required."})
    limit = _clamp(args.get("limit"), 20, 1, 50)
    offset = _clamp(args.get("offset"), 0, 0, 10000)

    db = _db()
    try:
        rows = db.execute(
            "SELECT b.id, b.title, b.series, b.series_position, "
            "       b.publisher, b.published_date, b.page_count, "
            "       (SELECT a.name FROM book_authors ba "
            "        JOIN authors a ON a.id = ba.author_id "
            "        WHERE ba.book_id = b.id "
            "        ORDER BY ba.rowid LIMIT 1) AS author_name "
            "FROM books_fts fts "
            "JOIN books b ON b.id = fts.rowid "
            "WHERE books_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ? OFFSET ?",
            (query, limit, offset),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        return _ok({"text": f"FTS error: {exc}"})

    if not rows:
        return _ok({"text": f"No books found matching '{query}'."})

    lines = [f"Found {len(rows)} result(s) for \'{query}\':\n"]
    for row in rows:
        lines.append(_book_summary(row))
    return _ok({"text": "\n".join(lines)})


def booksdb_get_book_details(args: dict, **kwargs) -> str:
    """Full details for a single book."""
    book_id = args.get("book_id")
    title = args.get("title", "").strip()

    db = _db()
    if book_id:
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    elif title:
        row = db.execute(
            "SELECT * FROM books WHERE title = ? COLLATE NOCASE", (title,)
        ).fetchone()
        if not row:
            # Try partial match
            row = db.execute(
                "SELECT * FROM books WHERE title LIKE ? COLLATE NOCASE LIMIT 1",
                (f"%{title}%",),
            ).fetchone()
    else:
        return _ok({"text": "Error: provide book_id or title."})

    if not row:
        return _ok({"text": "Book not found."})

    bid = row["id"]
    parts = [
        f"[{bid}] {row['title']}",
    ]
    if row["subtitle"]:
        parts.append(f"Subtitle: {row['subtitle']}")
    parts.append(f"Author(s): {_join_authors(bid)}")
    if row["series"]:
        pos = row["series_position"]
        parts.append(f"Series: {row['series']}" + (f" #{int(pos)}" if pos else ""))
    if row["publisher"]:
        parts.append(f"Publisher: {row['publisher']}")
    if row["published_date"]:
        parts.append(f"Published: {row['published_date']}")
    if row["page_count"]:
        parts.append(f"Pages: {row['page_count']}")
    if row["language"]:
        parts.append(f"Language: {row['language']}")
    genres = _join_genres(bid)
    if genres:
        parts.append(f"Genres: {genres}")
    ids = _join_identifiers(bid)
    if ids:
        parts.append(f"Identifiers: {ids}")
    if row["cover_image_url"]:
        parts.append(f"Cover: {row['cover_image_url']}")
    if row["source_url"]:
        parts.append(f"Source URL: {row['source_url']}")
    if row["description"]:
        desc = row["description"]
        if len(desc) > 1000:
            desc = desc[:1000] + "..."
        parts.append(f"\nDescription: {desc}")
    return _ok({"text": "\n".join(parts)})


def booksdb_get_books_by_author(args: dict, **kwargs) -> str:
    """List books by a given author (partial, case-insensitive name match)."""
    db = _db()
    limit = _clamp(args.get("limit"), 20, 1, 50)
    offset = _clamp(args.get("offset"), 0, 0, 10000)
    count_only = bool(args.get("count_only", False))
    author = args.get("author", "").strip()
    first_only = bool(args.get("first_only", False))

    if not author:
        return _ok({"text": "Error: author is required."})

    where = "a.name LIKE ? COLLATE NOCASE"
    params: list = [f"%{author}%"]

    if first_only:
        where += " AND b.series_position = 1"

    # Count-only mode
    if count_only:
        count_sql = f"""
            SELECT COUNT(DISTINCT b.id)
            FROM books b
            JOIN book_authors ba ON ba.book_id = b.id
            JOIN authors a ON a.id = ba.author_id
            WHERE {where}
        """
        count = db.execute(count_sql, params).fetchone()[0]
        return _ok({"author": author, "count": count})

    sql = f"""
        SELECT b.id, b.title, b.series, b.series_position,
               b.publisher, b.published_date, b.page_count,
               a.name AS author_name
        FROM books b
        JOIN book_authors ba ON ba.book_id = b.id
        JOIN authors a ON a.id = ba.author_id
        WHERE {where}
        ORDER BY b.published_date DESC NULLS LAST, b.title
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    rows = db.execute(sql, params).fetchall()

    if not rows:
        return _ok({"text": f"No books found for author '{author}'."})

    books = []
    for row in rows:
        books.append({
            "id": row["id"], "title": row["title"],
            "author": row["author_name"],
            "series": row["series"], "series_position": row["series_position"],
            "publisher": row["publisher"],
            "publication_date": row["published_date"],
            "page_count": row["page_count"],
        })
    return _ok({"author": author, "books": books, "count": len(books), "offset": offset})


def booksdb_get_books_by_series(args: dict, **kwargs) -> str:
    """List all books in a named series, ordered by series position."""
    db = _db()
    limit = _clamp(args.get("limit"), 20, 1, 50)
    offset = _clamp(args.get("offset"), 0, 0, 10000)
    count_only = bool(args.get("count_only", False))
    series = args.get("series", "").strip()
    first_only = bool(args.get("first_only", False))

    if not series:
        return _ok({"text": "Error: series is required."})

    where = "b.series LIKE ? COLLATE NOCASE"
    params: list = [f"%{series}%"]

    if first_only:
        where += " AND b.series_position = 1"

    # Count-only mode
    if count_only:
        count_sql = f"SELECT COUNT(DISTINCT b.id) FROM books b WHERE {where}"
        count = db.execute(count_sql, params).fetchone()[0]
        return _ok({"series": series, "count": count})

    sql = f"""
        SELECT b.id, b.title, b.series, b.series_position,
               b.publisher, b.published_date, b.page_count,
               (SELECT a.name FROM book_authors ba
                JOIN authors a ON a.id = ba.author_id
                WHERE ba.book_id = b.id
                ORDER BY ba.rowid LIMIT 1) AS author_name
        FROM books b
        WHERE {where}
        ORDER BY b.series_position ASC NULLS LAST, b.title
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    rows = db.execute(sql, params).fetchall()

    if not rows:
        return _ok({"text": f"No books found in series '{series}'."})

    series_name = rows[0]["series"]
    books = []
    for row in rows:
        books.append({
            "id": row["id"], "title": row["title"],
            "author": row["author_name"],
            "series": row["series"], "series_position": row["series_position"],
            "publisher": row["publisher"],
            "publication_date": row["published_date"],
            "page_count": row["page_count"],
        })
    return _ok({"series": series_name, "books": books, "count": len(books), "offset": offset})


def booksdb_get_books_by_genre(args: dict, **kwargs) -> str:
    """List books matching one or more genres (OR logic, case-insensitive partial match)."""
    db = _db()
    limit = _clamp(args.get("limit"), 20, 1, 50)
    offset = _clamp(args.get("offset"), 0, 0, 10000)
    count_only = bool(args.get("count_only", False))
    first_only = bool(args.get("first_only", False))

    # Support both single "genre" and multi-genre "genres" array (OR logic)
    genres_raw = args.get("genres") or ([args["genre"]] if args.get("genre") else [])
    if not genres_raw:
        return _ok({"text": "Error: genre is required (e.g. 'fantasy', 'litrpg')."})

    placeholders = " OR ".join(["g.name LIKE ? COLLATE NOCASE"] * len(genres_raw))
    params: list = [f"%{g}%" for g in genres_raw]

    if first_only:
        placeholders += " AND b.series_position = 1"

    # Count-only mode
    if count_only:
        count_sql = f"""
            SELECT COUNT(DISTINCT b.id)
            FROM books b
            JOIN book_genres bg ON bg.book_id = b.id
            JOIN genres g ON g.id = bg.genre_id
            WHERE {placeholders}
        """
        count = db.execute(count_sql, params).fetchone()[0]
        return _ok({"genre": genres_raw, "count": count})

    sql = f"""
        SELECT b.id, b.title, b.series, b.series_position,
               b.publisher, b.published_date, b.page_count,
               (SELECT a.name FROM book_authors ba
                JOIN authors a ON a.id = ba.author_id
                WHERE ba.book_id = b.id
                ORDER BY ba.rowid LIMIT 1) AS author_name
        FROM books b
        JOIN book_genres bg ON bg.book_id = b.id
        JOIN genres g ON g.id = bg.genre_id
        WHERE ({placeholders})
        ORDER BY b.published_date DESC NULLS LAST, b.title
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    rows = db.execute(sql, params).fetchall()

    if not rows:
        return _ok({"text": f"No books found in genre(s): {genres_raw}."})

    books = []
    for row in rows:
        books.append({
            "id": row["id"], "title": row["title"],
            "author": row["author_name"],
            "series": row["series"], "series_position": row["series_position"],
            "publisher": row["publisher"],
            "publication_date": row["published_date"],
            "page_count": row["page_count"],
        })
    return _ok({"genre": genres_raw, "books": books, "count": len(books), "offset": offset})


def booksdb_get_books_by_publisher(args: dict, **kwargs) -> str:
    """List books from a given publisher."""
    db = _db()
    limit = _clamp(args.get("limit"), 20, 1, 50)
    offset = _clamp(args.get("offset"), 0, 0, 10000)
    count_only = bool(args.get("count_only", False))
    publisher = args.get("publisher", "").strip()
    first_only = bool(args.get("first_only", False))

    if not publisher:
        return _ok({"text": "Error: publisher is required."})

    where = "b.publisher LIKE ? COLLATE NOCASE"
    params: list = [f"%{publisher}%"]

    if first_only:
        where += " AND b.series_position = 1"

    # Count-only mode
    if count_only:
        count_sql = f"SELECT COUNT(DISTINCT b.id) FROM books b WHERE {where}"
        count = db.execute(count_sql, params).fetchone()[0]
        return _ok({"publisher": publisher, "count": count})

    sql = f"""
        SELECT b.id, b.title, b.series, b.series_position,
               b.publisher, b.published_date, b.page_count,
               (SELECT a.name FROM book_authors ba
                JOIN authors a ON a.id = ba.author_id
                WHERE ba.book_id = b.id
                ORDER BY ba.rowid LIMIT 1) AS author_name
        FROM books b
        WHERE {where}
        ORDER BY b.published_date DESC NULLS LAST, b.title
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    rows = db.execute(sql, params).fetchall()

    if not rows:
        return _ok({"text": f"No books found from publisher '{publisher}'."})

    books = []
    for row in rows:
        books.append({
            "id": row["id"], "title": row["title"],
            "author": row["author_name"],
            "series": row["series"], "series_position": row["series_position"],
            "publisher": row["publisher"],
            "publication_date": row["published_date"],
            "page_count": row["page_count"],
        })
    return _ok({"publisher": publisher, "books": books, "count": len(books), "offset": offset})


def booksdb_lookup_book_by_identifier(args: dict, **kwargs) -> str:
    """Look up a book by identifier type and value."""
    id_type = args.get("identifier_type", "").strip()
    id_value = args.get("identifier_value", "").strip()
    if not id_type or not id_value:
        return _ok({"text": "Error: both identifier_type and identifier_value are required."})

    db = _db()
    row = db.execute(
        "SELECT bi.book_id FROM book_identifiers bi "
        "WHERE bi.identifier_type = ? AND bi.identifier_value = ?",
        (id_type, id_value),
    ).fetchone()

    if not row:
        return _ok({"text": f"No book found with {id_type}={id_value}."})

    # Reuse book details handler
    return booksdb_get_book_details({"book_id": row["book_id"]})


def booksdb_get_database_stats(args: dict, **kwargs) -> str:
    """High-level database statistics."""
    db = _db()

    stats = {}
    for label, sql in [
        ("books", "SELECT COUNT(*) FROM books"),
        ("authors", "SELECT COUNT(*) FROM authors"),
        ("genres", "SELECT COUNT(*) FROM genres"),
        ("series", "SELECT COUNT(DISTINCT series) FROM books WHERE series IS NOT NULL"),
        ("sources", "SELECT COUNT(*) FROM sources"),
        ("identifiers", "SELECT COUNT(*) FROM book_identifiers"),
        ("total_identifiers", "SELECT COUNT(DISTINCT book_id) FROM book_identifiers"),
    ]:
        stats[label] = db.execute(sql).fetchone()[0]

    # Source breakdown
    source_rows = db.execute(
        "SELECT s.name, COUNT(DISTINCT bel.book_id) AS cnt "
        "FROM sources s LEFT JOIN book_enrichment_log bel ON bel.source_name = s.name "
        "GROUP BY s.id ORDER BY cnt DESC"
    ).fetchall()

    lines = [
        "=== Books Database Statistics ===",
        f"Books: {stats['books']}",
        f"Authors: {stats['authors']}",
        f"Genres: {stats['genres']}",
        f"Series: {stats['series']}",
        f"Data sources: {stats['sources']}",
        f"Identifiers: {stats['identifiers']} across {stats['total_identifiers']} books",
        "",
        "Source enrichment counts:",
    ]
    for s in source_rows:
        lines.append(f"  {s['name']}: {s['cnt']} books enriched")
    return _ok({"text": "\n".join(lines)})


def booksdb_get_genre_stats(args: dict, **kwargs) -> str:
    """Genre breakdown with counts."""
    limit = _clamp(args.get("limit"), 20, 1, 50)

    db = _db()
    rows = db.execute(
        "SELECT g.name, COUNT(bg.book_id) AS cnt, "
        "       MAX(b.published_date) AS latest "
        "FROM genres g "
        "JOIN book_genres bg ON bg.genre_id = g.id "
        "JOIN books b ON b.id = bg.book_id "
        "GROUP BY g.id "
        "ORDER BY cnt DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()

    if not rows:
        return _ok({"text": "No genre data found."})

    lines = [f"=== Genre Statistics (top {limit}) ==="]
    for r in rows:
        latest = r["latest"][:4] if r["latest"] else "unknown"
        lines.append(f"  {r['name']}: {r['cnt']} books (latest: {latest})")
    return _ok({"text": "\n".join(lines)})


def booksdb_get_publisher_stats(args: dict, **kwargs) -> str:
    """Publisher breakdown with counts."""
    limit = _clamp(args.get("limit"), 20, 1, 50)

    db = _db()
    rows = db.execute(
        "SELECT publisher, COUNT(*) AS cnt, MAX(published_date) AS latest "
        "FROM books "
        "WHERE publisher IS NOT NULL "
        "GROUP BY publisher "
        "ORDER BY cnt DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()

    if not rows:
        return _ok({"text": "No publisher data found."})

    lines = [f"=== Publisher Statistics (top {limit}) ==="]
    for r in rows:
        latest = r["latest"][:4] if r["latest"] else "unknown"
        lines.append(f"  {r['publisher']}: {r['cnt']} books (latest: {latest})")
    return _ok({"text": "\n".join(lines)})


def booksdb_get_author_stats(args: dict, **kwargs) -> str:
    """Author statistics by book count."""
    limit = _clamp(args.get("limit"), 20, 1, 50)

    db = _db()
    rows = db.execute(
        "SELECT a.name, COUNT(ba.book_id) AS cnt, "
        "       GROUP_CONCAT(DISTINCT g.name) AS genres, "
        "       MAX(b.published_date) AS latest "
        "FROM authors a "
        "JOIN book_authors ba ON ba.author_id = a.id "
        "JOIN books b ON b.id = ba.book_id "
        "LEFT JOIN book_genres bg ON bg.book_id = b.id "
        "LEFT JOIN genres g ON g.id = bg.genre_id "
        "GROUP BY a.id "
        "ORDER BY cnt DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()

    if not rows:
        return _ok({"text": "No author data found."})

    lines = [f"=== Author Statistics (top {limit}) ==="]
    for r in rows:
        latest = r["latest"][:4] if r["latest"] else "unknown"
        genres = (r["genres"] or "")[:60]
        if len(r["genres"] or "") > 60:
            genres += "..."
        lines.append(f"  {r['name']}: {r['cnt']} books (genres: {genres}, latest: {latest})")
    return _ok({"text": "\n".join(lines)})


def booksdb_list_sources(args: dict, **kwargs) -> str:
    """List data sources."""
    db = _db()
    rows = db.execute(
        "SELECT s.name, s.source_type, COUNT(bel.book_id) AS cnt "
        "FROM sources s "
        "LEFT JOIN book_enrichment_log bel ON bel.source_name = s.name "
        "GROUP BY s.id "
        "ORDER BY s.name"
    ).fetchall()

    if not rows:
        return _ok({"text": "No sources found."})

    lines = ["=== Data Sources ==="]
    for r in rows:
        lines.append(f"  {r['name']} ({r['source_type']}): {r['cnt']} books enriched")
    return _ok({"text": "\n".join(lines)})
