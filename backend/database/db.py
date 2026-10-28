
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize database with the Flask app context."""
    db.init_app(app)

    with app.app_context():
        # Import all models so tables are registered
        from models import user, dataset, model, evaluation, user_session, activity_log  # noqa: F401

        db.create_all()

        # Lightweight schema migration for SQLite: ensure role and is_active columns exist on users
        try:
            inspector = db.inspect(db.engine)
            if "users" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("users")]
                with db.engine.connect() as conn:
                    if "role" not in columns:
                        conn.execute(db.text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'student'"))
                    if "is_active" not in columns:
                        conn.execute(db.text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
                    conn.commit()
        except Exception:
            pass
