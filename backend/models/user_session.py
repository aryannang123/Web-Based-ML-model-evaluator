from database.db import db


class UserSession(db.Model):
    """Server-side session state used to expire and revoke signed cookies."""

    __tablename__ = "user_sessions"

    session_id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp(),
    )
    last_seen_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="sessions")
