
from database.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    # Relationships
    datasets = db.relationship(
        "Dataset",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    models = db.relationship(
        "MLModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    evaluations = db.relationship(
        "EvaluationResult",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    sessions = db.relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
