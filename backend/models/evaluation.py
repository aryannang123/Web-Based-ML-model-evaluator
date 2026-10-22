
from database.db import db


class EvaluationResult(db.Model):
    __tablename__ = "evaluation_results"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    model_id = db.Column(
        db.Integer,
        db.ForeignKey("models.id"),
        nullable=False
    )

    metrics_json = db.Column(db.JSON, nullable=False)
    confusion_matrix_json = db.Column(db.JSON, nullable=True)
    report_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    user = db.relationship("User", back_populates="evaluations")
    model = db.relationship("MLModel", back_populates="evaluations")
