from flask import Flask, request, jsonify
from flasgger import Swagger
import requests
from app.config.config import Config
from app.extensions import db, migrate, jwt, cors
from app.routes.auth_routes import auth_bp
from app.routes.sistemas_routes import sistemas_bp
from app.routes.links_routes import links_bp
from app.routes.comunicados_routes import comunicados_bp


SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
    "title": "Intranet Corporativa API",
    "description": "API REST para gerenciamento da Intranet Corporativa.",
    "version": "1.0.0",
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Informe: Bearer <token>"
        }
    }
}


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    Swagger(app, config=SWAGGER_CONFIG, merge=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(sistemas_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(comunicados_bp)



    with app.app_context():
        from app.models import Administrador, Sistema, LinkUtil, Log  # noqa
        from app.models import Usuario, Comunicado, Comentario, Reacao  # noqa

    return app