from database.db import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    user = db.relationship("User", backref=db.backref("activity_logs", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }
