"""Shared Flask extension singletons.

These are initialized in :func:`app.create_app` to keep the application
factory pattern clean and test-friendly.
"""

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
