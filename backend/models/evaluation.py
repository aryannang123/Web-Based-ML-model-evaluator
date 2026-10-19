from database.db import db

# TODO: US-02 - Design database schema
# Assigned to: @aryannang123
# Description: Define evaluation results table schema and relationships.

class EvaluationResult(db.Model):
    __tablename__ = "evaluation_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False)
    model_name = db.Column(db.String(128), nullable=False)

    # TODO: US-19: Store evaluation metrics JSON and model file path
    # Assigned to: @abhishekdeene-eng
