from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity
from app.extensions import db
from app.models import Administrador, Usuario
from app.utils.audit import registrar_log
from app.middleware.auth_middleware import admin_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login unificado — Admin ou Editor
    ---
    tags:
      - Autenticação
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, senha]
          properties:
            email:
              type: string
            senha:
              type: string
    responses:
      200:
        description: Login realizado com sucesso
      401:
        description: Credenciais inválidas
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('senha'):
        return jsonify({'message': 'Email e senha são obrigatórios.'}), 400

    email = data['email']
    senha = data['senha']

    # Tenta autenticar como Administrador
    admin = Administrador.query.filter_by(email=email, ativo=True).first()
    if admin and admin.verificar_senha(senha):
        admin.ultimo_login = datetime.now(timezone.utc)
        db.session.commit()
        token = create_access_token(identity=f'admin-{admin.id}')
        registrar_log(admin.id, 'LOGIN')
        return jsonify({
            'token': token,
            'usuario': {'id': admin.id, 'nome': admin.nome, 'email': admin.email, 'perfil': 'ADMIN'}
        }), 200

    # Tenta autenticar como Editor
    editor = Usuario.query.filter_by(email=email, ativo=True).first()
    if editor and editor.verificar_senha(senha):
        token = create_access_token(identity=f'editor-{editor.id}')
        return jsonify({
            'token': token,
            'usuario': {'id': editor.id, 'nome': editor.nome, 'email': editor.email, 'perfil': 'EDITOR'}
        }), 200

    return jsonify({'message': 'Credenciais inválidas.'}), 401

@auth_bp.route('/usuarios', methods=['GET'])
@admin_required
def listar_usuarios():
    """
    Lista todos os usuários (Apenas Admin)
    """
    usuarios = Usuario.query.all()
    return jsonify([{
        'id': u.id,
        'nome': u.nome,
        'email': u.email,
        'perfil': u.perfil
    } for u in usuarios]), 200

@auth_bp.route('/usuarios/<int:id>', methods=['PUT'])
@admin_required
def atualizar_usuario(id):
    """
    Atualiza dados do usuário (nome, email, senha) (Apenas Admin)
    """
    usuario = Usuario.query.get_or_404(id)
    data = request.get_json()
    
    if 'nome' in data and data['nome']:
        usuario.nome = data['nome']
    if 'email' in data and data['email']:
        usuario.email = data['email']
    if 'senha' in data and data['senha']:
        usuario.set_senha(data['senha'])
        
    db.session.commit()
    
    return jsonify({
        'id': usuario.id,
        'nome': usuario.nome,
        'email': usuario.email,
        'perfil': usuario.perfil
    }), 200


@auth_bp.route('/me', methods=['GET'])
def me():
    """
    Retorna dados do usuário autenticado
    ---
    tags:
      - Autenticação
    security:
      - Bearer: []
    responses:
      200:
        description: Dados do usuário
    """
    from flask_jwt_extended import verify_jwt_in_request
    verify_jwt_in_request()
    identity = get_jwt_identity()

    if identity.startswith('admin-'):
        admin_id = int(identity.split('-')[1])
        admin = Administrador.query.get(admin_id)
        if not admin:
            return jsonify({'message': 'Não encontrado.'}), 404
        return jsonify({'id': admin.id, 'nome': admin.nome, 'email': admin.email, 'perfil': 'ADMIN'}), 200

    if identity.startswith('editor-'):
        editor_id = int(identity.split('-')[1])
        editor = Usuario.query.get(editor_id)
        if not editor:
            return jsonify({'message': 'Não encontrado.'}), 404
        return jsonify(editor.to_dict()), 200

    return jsonify({'message': 'Token inválido.'}), 401
