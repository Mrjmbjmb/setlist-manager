from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()


def init_db(app):
    """Create all database tables if they do not yet exist."""
    with app.app_context():
        db.create_all()
        _ensure_song_columns()
        _ensure_setlist_song_columns()
        _ensure_settings_table()
        _ensure_setlist_columns()
        _ensure_database_indexes()


def _ensure_song_columns() -> None:
    inspector = inspect(db.engine)
    try:
        columns = {column["name"] for column in inspector.get_columns("songs")}
    except Exception:  # pragma: no cover - fallback if table missing
        return

    required_columns = (
        ("is_multitrack", text("ALTER TABLE songs ADD COLUMN is_multitrack BOOLEAN NOT NULL DEFAULT 0")),
        ("is_cover", text("ALTER TABLE songs ADD COLUMN is_cover BOOLEAN NOT NULL DEFAULT 0")),
        ("is_vocals_only", text("ALTER TABLE songs ADD COLUMN is_vocals_only BOOLEAN NOT NULL DEFAULT 0")),
        ("alias", text("ALTER TABLE songs ADD COLUMN alias VARCHAR(120)")),
    )

    altered = False
    for column_name, statement in required_columns:
        if column_name not in columns:
            db.session.execute(statement)
            altered = True

    if altered:
        db.session.commit()


def _ensure_setlist_song_columns() -> None:
    inspector = inspect(db.engine)
    try:
        columns = {column["name"] for column in inspector.get_columns("setlist_songs")}
    except Exception:  # pragma: no cover - fallback if table missing
        return

    required_columns = (
        ("starts_encore", text("ALTER TABLE setlist_songs ADD COLUMN starts_encore BOOLEAN NOT NULL DEFAULT 0")),
    )

    altered = False
    for column_name, statement in required_columns:
        if column_name not in columns:
            db.session.execute(statement)
            altered = True

    if altered:
        db.session.commit()


def _ensure_settings_table() -> None:
    """Create the settings table if it doesn't exist."""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "settings" not in tables:
        # Create the settings table
        db.session.execute(text("""
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(80) UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description VARCHAR(255),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create index on key for faster lookups
        db.session.execute(text("CREATE INDEX ix_settings_key ON settings (key)"))

        db.session.commit()


def _ensure_setlist_columns() -> None:
    """Add new columns to setlists table if they don't exist."""
    inspector = inspect(db.engine)
    try:
        columns = {column["name"] for column in inspector.get_columns("setlists")}
    except Exception:
        return

    new_columns = (
        ("show_start_time", text("ALTER TABLE setlists ADD COLUMN show_start_time TIME")),
        ("show_end_time", text("ALTER TABLE setlists ADD COLUMN show_end_time TIME")),
        ("cached_song_count", text("ALTER TABLE setlists ADD COLUMN cached_song_count INTEGER NOT NULL DEFAULT 0")),
        ("cached_total_duration_seconds", text("ALTER TABLE setlists ADD COLUMN cached_total_duration_seconds INTEGER NOT NULL DEFAULT 0")),
    )

    altered = False
    for column_name, statement in new_columns:
        if column_name not in columns:
            db.session.execute(statement)
            altered = True

    if altered:
        db.session.commit()


def _ensure_database_indexes() -> None:
    """Create database indexes for better performance."""
    inspector = inspect(db.engine)

    # Get existing indexes
    try:
        setlists_indexes = {index["name"] for index in inspector.get_indexes("setlists")}
        setlist_songs_indexes = {index["name"] for index in inspector.get_indexes("setlist_songs")}
    except Exception:
        return

    # Indexes for setlists table
    setlists_indexes_to_create = [
        ("ix_setlists_show_date", "CREATE INDEX IF NOT EXISTS ix_setlists_show_date ON setlists(show_date)"),
        ("ix_setlists_created_at", "CREATE INDEX IF NOT EXISTS ix_setlists_created_at ON setlists(created_at)"),
    ]

    for index_name, statement in setlists_indexes_to_create:
        if index_name not in setlists_indexes:
            try:
                db.session.execute(text(statement))
                db.session.commit()
            except Exception:
                pass  # Index might already exist or other error

    # Indexes for setlist_songs table
    setlist_songs_indexes_to_create = [
        ("ix_setlist_songs_setlist_id", "CREATE INDEX IF NOT EXISTS ix_setlist_songs_setlist_id ON setlist_songs(setlist_id)"),
        ("ix_setlist_songs_position", "CREATE INDEX IF NOT EXISTS ix_setlist_songs_position ON setlist_songs(position)"),
    ]

    for index_name, statement in setlist_songs_indexes_to_create:
        if index_name not in setlist_songs_indexes:
            try:
                db.session.execute(text(statement))
                db.session.commit()
            except Exception:
                pass  # Index might already exist or other error
