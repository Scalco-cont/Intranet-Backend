import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config.config import Config
from app.extensions import db as _db


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-jwt-secret'
    SECRET_KEY = 'test-secret'
    RATELIMIT_ENABLED = False


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def admin_token(app, db):
    from app.models import Administrador

    admin = Administrador(nome='Admin Teste', email='admin@teste.com')
    admin.set_senha('Senha@123')
    db.session.add(admin)
    db.session.commit()
    with app.app_context():
        token = create_access_token(identity=f'admin-{admin.id}')
    return token, admin.id


@pytest.fixture()
def editor_token(app, db):
    from app.models import Usuario

    editor = Usuario(nome='Editor Teste', email='editor@teste.com', perfil='EDITOR')
    editor.set_senha('Senha@123')
    db.session.add(editor)
    db.session.commit()
    with app.app_context():
        token = create_access_token(identity=f'editor-{editor.id}')
    return token, editor.id
