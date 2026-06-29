from functools import wraps
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import Administrador, Usuario


def admin_required(fn):
    """Protege rotas exigindo um JWT válido de Administrador."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        identity = get_jwt_identity()
        # identity format: "admin-{id}" or "editor-{id}"
        if not identity.startswith('admin-'):
            return {'message': 'Acesso negado. Apenas administradores.'}, 403
        admin_id = int(identity.split('-')[1])
        admin = Administrador.query.get(admin_id)
        if not admin or not admin.ativo:
            return {'message': 'Administrador inativo ou inexistente.'}, 403
        return fn(*args, **kwargs)
    return wrapper


def editor_or_admin_required(fn):
    """Protege rotas que aceitam tanto Editores quanto Administradores."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        identity = get_jwt_identity()
        if identity.startswith('admin-'):
            admin_id = int(identity.split('-')[1])
            user = Administrador.query.get(admin_id)
            if not user or not user.ativo:
                return {'message': 'Acesso negado.'}, 403
        elif identity.startswith('editor-'):
            editor_id = int(identity.split('-')[1])
            user = Usuario.query.get(editor_id)
            if not user or not user.ativo:
                return {'message': 'Acesso negado.'}, 403
        else:
            return {'message': 'Token inválido.'}, 401
        return fn(*args, **kwargs)
    return wrapper


def get_current_user_info():
    """Retorna (tipo, id, nome) do usuário autenticado pelo JWT."""
    identity = get_jwt_identity()
    if identity.startswith('admin-'):
        admin_id = int(identity.split('-')[1])
        admin = Administrador.query.get(admin_id)
        return 'ADMIN', admin_id, admin.nome if admin else 'Admin'
    elif identity.startswith('editor-'):
        editor_id = int(identity.split('-')[1])
        editor = Usuario.query.get(editor_id)
        return 'EDITOR', editor_id, editor.nome if editor else 'Editor'
    return None, None, None
