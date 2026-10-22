
from database.db import db


class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)
    row_count = db.Column(db.Integer, nullable=True)
    column_count = db.Column(db.Integer, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    preprocessing_json = db.Column(db.JSON, nullable=True)
    target_column = db.Column(db.String(255), nullable=True)
    task_type = db.Column(db.String(20), nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    user = db.relationship("User", back_populates="datasets")

    models = db.relationship(
        "MLModel",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )

    versions = db.relationship(
        "DatasetVersion", back_populates="dataset", cascade="all, delete-orphan",
        order_by="DatasetVersion.version_number",
    )
