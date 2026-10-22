from database.db import db


class DatasetVersion(db.Model):
    __tablename__ = "dataset_versions"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(
        db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True
    )
    version_number = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    row_count = db.Column(db.Integer, nullable=False)
    column_count = db.Column(db.Integer, nullable=False)
    metadata_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )

    dataset = db.relationship("Dataset", back_populates="versions")
    model_runs = db.relationship("MLModel", back_populates="dataset_version")
