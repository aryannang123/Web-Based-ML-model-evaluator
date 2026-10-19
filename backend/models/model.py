
from database.db import db


class MLModel(db.Model):
    __tablename__ = "models"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    dataset_id = db.Column(
        db.Integer,
        db.ForeignKey("datasets.id"),
        nullable=False
    )

    model_name = db.Column(db.String(128), nullable=False)
    algorithm = db.Column(db.String(128), nullable=False)
    model_path = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="pending")
    config_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    user = db.relationship("User", back_populates="models")
    dataset = db.relationship("Dataset", back_populates="models")

    evaluations = db.relationship(
        "EvaluationResult",
        back_populates="model",
        cascade="all, delete-orphan"
    )
