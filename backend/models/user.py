from database.db import db

# TODO: US-02 - Design database schema
# Assigned to: @aryannang123
# Description: Define user table schema, fields (username, email, password_hash), and relationships.

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # TODO: Add relationships to Dataset and EvaluationResult
