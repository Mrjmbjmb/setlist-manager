from flask import Flask

from .database import db, init_db
from .routes import bp


def create_app():
    """Application factory that wires up the Flask app and database."""
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key",
        SQLALCHEMY_DATABASE_URI="sqlite:///setlists.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    init_db(app)

    app.register_blueprint(bp)
    return app
