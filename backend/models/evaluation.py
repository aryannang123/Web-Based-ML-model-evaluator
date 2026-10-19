from datetime import datetime
from database.db import db
import json

class EvaluationResult(db.Model):
    __tablename__ = "evaluation_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True)
    model_name = db.Column(db.String(128), nullable=False)
    task_type = db.Column(db.String(64), nullable=False)  # 'classification' or 'regression'
    split_ratio = db.Column(db.Float, default=0.2)
    metrics_json = db.Column(db.Text, nullable=False, default="{}")
    model_file_path = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_metrics(self):
        try:
            return json.loads(self.metrics_json)
        except Exception:
            return {}

    def set_metrics(self, data):
        self.metrics_json = json.dumps(data)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "dataset_id": self.dataset_id,
            "model_name": self.model_name,
            "task_type": self.task_type,
            "split_ratio": self.split_ratio,
            "metrics": self.get_metrics(),
            "model_file_path": self.model_file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
