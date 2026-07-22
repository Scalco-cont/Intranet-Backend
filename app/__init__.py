from flask import Flask, request, jsonify
from flasgger import Swagger
import requests
from app.config.config import Config
from app.extensions import db, migrate, jwt, cors
from app.routes.auth_routes import auth_bp
from app.routes.sistemas_routes import sistemas_bp
from app.routes.links_routes import links_bp
from app.routes.comunicados_routes import comunicados_bp
from app.routes.arquivos_routes import arquivos_bp
from app.services.drive_service import validar_credencial_google


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

    if not app.config.get('ARQUIVOS_ORIGIN_PERMITIDA'):
        raise RuntimeError(
            "ARQUIVOS_ORIGIN_PERMITIDA não definida. Obrigatória para o CORS do blueprint "
            "'Arquivos do curso' — sem ela a feature não sobe com um fallback inseguro."
        )
    if not app.config.get('ARQUIVOS_PASTA_RAIZ'):
        raise RuntimeError("ARQUIVOS_PASTA_RAIZ não definida.")
    validar_credencial_google(app.config.get('GOOGLE_SERVICE_ACCOUNT_JSON'))

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"^/(?!api/arquivos-do-curso).*$": {"origins": "*"}}, supports_credentials=True)
    Swagger(app, config=SWAGGER_CONFIG, merge=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(sistemas_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(comunicados_bp)
    app.register_blueprint(arquivos_bp)

    @app.after_request
    def add_cors_headers(response):
        if not request.path.startswith('/api/arquivos-do-curso'):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            response = jsonify({})
            response.status_code = 200
            return response

    with app.app_context():
        from app.models import Administrador, Sistema, LinkUtil, Log  # noqa
        from app.models import Usuario, Comunicado, Comentario, Reacao  # noqa

    return app