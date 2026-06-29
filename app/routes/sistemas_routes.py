from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.extensions import db
from app.models import Sistema
from app.middleware.auth_middleware import admin_required
from app.utils.audit import registrar_log

sistemas_bp = Blueprint('sistemas', __name__, url_prefix='/api/sistemas')


@sistemas_bp.route('', methods=['GET'])
def listar_sistemas():
    """
    Lista todos os sistemas ativos (rota pública)
    ---
    tags:
      - Sistemas
    responses:
      200:
        description: Lista de sistemas
    """
    sistemas = Sistema.query.filter_by(ativo=True).order_by(Sistema.ordem_exibicao).all()
    return jsonify([s.to_dict() for s in sistemas]), 200


@sistemas_bp.route('/<int:id>', methods=['GET'])
def buscar_sistema(id):
    """
    Busca um sistema por ID (rota pública)
    ---
    tags:
      - Sistemas
    """
    sistema = Sistema.query.get_or_404(id)
    return jsonify(sistema.to_dict()), 200


@sistemas_bp.route('', methods=['POST'])
@admin_required
def criar_sistema():
    """
    Cria um novo sistema (Admin)
    ---
    tags:
      - Sistemas
    security:
      - Bearer: []
    """
    data = request.get_json()
    if not data or not data.get('nome') or not data.get('url'):
        return jsonify({'message': 'Nome e URL são obrigatórios.'}), 400

    sistema = Sistema(
        nome=data['nome'],
        descricao=data.get('descricao', ''),
        icone=data.get('icone', 'AppWindow'),
        url=data['url'],
        ativo=data.get('ativo', True),
        ordem_exibicao=data.get('ordem_exibicao', 0)
    )
    db.session.add(sistema)
    db.session.commit()

    registrar_log(get_jwt_identity(), 'CREATE', 'sistema', sistema.id, f'Criou: {sistema.nome}')

    return jsonify(sistema.to_dict()), 201


@sistemas_bp.route('/<int:id>', methods=['PUT'])
@admin_required
def editar_sistema(id):
    """
    Edita um sistema existente (Admin)
    ---
    tags:
      - Sistemas
    security:
      - Bearer: []
    """
    sistema = Sistema.query.get_or_404(id)
    data = request.get_json()

    sistema.nome = data.get('nome', sistema.nome)
    sistema.descricao = data.get('descricao', sistema.descricao)
    sistema.icone = data.get('icone', sistema.icone)
    sistema.url = data.get('url', sistema.url)
    sistema.ativo = data.get('ativo', sistema.ativo)
    sistema.ordem_exibicao = data.get('ordem_exibicao', sistema.ordem_exibicao)

    db.session.commit()
    registrar_log(get_jwt_identity(), 'UPDATE', 'sistema', sistema.id, f'Editou: {sistema.nome}')

    return jsonify(sistema.to_dict()), 200


@sistemas_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def excluir_sistema(id):
    """
    Exclui um sistema (Admin)
    ---
    tags:
      - Sistemas
    security:
      - Bearer: []
    """
    sistema = Sistema.query.get_or_404(id)
    registrar_log(get_jwt_identity(), 'DELETE', 'sistema', sistema.id, f'Excluiu: {sistema.nome}')
    db.session.delete(sistema)
    db.session.commit()
    return jsonify({'message': 'Sistema excluído com sucesso.'}), 200
