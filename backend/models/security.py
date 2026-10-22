from database.db import db


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    token_hash = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.Integer, nullable=False)
    last_activity = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)

    user = db.relationship("User", back_populates="sessions")


class LoginThrottle(db.Model):
    __tablename__ = "login_throttles"

    key_hash = db.Column(db.String(64), primary_key=True)
    window_started = db.Column(db.Integer, nullable=False)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
    blocked_until = db.Column(db.Integer, nullable=False, default=0)


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )
    event_type = db.Column(db.String(80), nullable=False, index=True)
    target_type = db.Column(db.String(80), nullable=True)
    target_id = db.Column(db.String(80), nullable=True)
    details_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.current_timestamp()
    )

    actor = db.relationship("User", foreign_keys=[actor_user_id])
