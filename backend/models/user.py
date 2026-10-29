
from database.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(
        db.String(20),
        nullable=False,
        default="student",
        server_default="student"
    )
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.text("1")
    )

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
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
