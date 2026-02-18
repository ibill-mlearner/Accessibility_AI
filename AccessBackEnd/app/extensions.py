"""

Shared Flask extension singletons.

.. dev note
These were made as single entry points for readability
Issues:
flask_jwt_extended was not fully implemented
flask_login is not the best use for session management, should just be using flask_jwt
no migration setup yet

.. codex note
These are initialized in :func:`app.create_app` to keep the application
factory pattern clean and test-friendly. (instantiate here, make available everywhere)

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
