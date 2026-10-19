from database.db import db

# TODO: US-02 - Design database schema
# Assigned to: @aryannang123
# Description: Define dataset table schema, foreign keys, and metadata columns.

class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)

    # TODO: US-10: Store dataset metadata (row_count, column_count, columns_json)
    # Assigned to: @aryannang123
