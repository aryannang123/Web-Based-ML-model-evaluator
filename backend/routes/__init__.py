from .auth_routes import auth_bp
from .dataset_routes import dataset_bp
from .ml_routes import ml_bp
from .admin_routes import admin_bp
from .instructor_routes import instructor_bp

__all__ = ["auth_bp", "dataset_bp", "ml_bp", "admin_bp", "instructor_bp"]
