from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Initialize database with the Flask app context."""
    db.init_app(app)
    with app.app_context():
        # Import models so tables are registered
        from models import user, dataset, evaluation  # noqa: F401
        db.create_all()
