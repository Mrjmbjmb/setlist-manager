from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()


def init_db(app):
    """Create all database tables if they do not yet exist."""
    with app.app_context():
        db.create_all()
        _ensure_song_columns()
        _ensure_setlist_song_columns()


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
