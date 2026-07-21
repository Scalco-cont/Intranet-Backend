import os
import sys

from app.models import Administrador, Usuario


def test_seed_usa_senha_do_env_quando_definida(app, db, monkeypatch, request):
    # Ensure seed module is cleaned up from sys.modules after test to prevent pollution
    def cleanup_seed_module():
        sys.modules.pop('seed', None)
    request.addfinalizer(cleanup_seed_module)

    monkeypatch.setenv('ADMIN_SEED_PASSWORD', 'MinhaSenhaForte@1')
    monkeypatch.setenv('EDITOR_SEED_PASSWORD', 'OutraSenhaForte@1')

    # Remove seed from sys.modules if already loaded to ensure clean reload
    if 'seed' in sys.modules:
        del sys.modules['seed']

    import importlib
    # Monkeypatch app.create_app BEFORE importing seed
    monkeypatch.setattr('app.create_app', lambda config_class=None: app)

    import seed
    # Reload to ensure it uses the monkeypatched create_app
    importlib.reload(seed)

    with app.app_context():
        admin = Administrador.query.filter_by(email='admin@empresa.com').first()
        editor = Usuario.query.filter_by(email='editor@empresa.com').first()
        assert admin.verificar_senha('MinhaSenhaForte@1')
        assert editor.verificar_senha('OutraSenhaForte@1')
