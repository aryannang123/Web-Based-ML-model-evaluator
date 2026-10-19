from datetime import datetime
from database.db import db
import json

class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    row_count = db.Column(db.Integer, default=0)
    column_count = db.Column(db.Integer, default=0)
    columns_json = db.Column(db.Text, default="[]")  # List of column names and detected types
    target_column = db.Column(db.String(128), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    evaluations = db.relationship("EvaluationResult", backref="dataset", lazy=True, cascade="all, delete-orphan")

    def get_columns(self):
        try:
            return json.loads(self.columns_json)
        except Exception:
            return []

    def set_columns(self, cols):
        self.columns_json = json.dumps(cols)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.get_columns(),
            "target_column": self.target_column,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }
