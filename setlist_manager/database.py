from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Create all database tables if they do not yet exist."""
    with app.app_context():
        db.create_all()
