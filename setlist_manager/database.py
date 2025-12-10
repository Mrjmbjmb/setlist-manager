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
    )

    altered = False
    for column_name, statement in new_columns:
        if column_name not in columns:
            db.session.execute(statement)
            altered = True

    if altered:
        db.session.commit()
