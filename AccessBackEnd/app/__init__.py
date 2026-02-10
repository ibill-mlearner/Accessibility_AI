
from flask import Flask

import config
from extensions import db, migrate, jwt, cors
from api.v1.routes import api_v1_bp
from blueprints.auth.routes import auth_bp


def create_app(config_name=None):
    app = Flask(__name__)

    cfg = config.get_config() if config_name is None else config.CONFIG_BY_NAME.get(config_name)
    app.config.from_object(cfg)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    app.register_blueprint(api_v1_bp)
    app.register_blueprint(auth_bp)

    return app