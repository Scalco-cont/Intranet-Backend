from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.extensions import db
from app.models import LinkUtil
from app.middleware.auth_middleware import admin_required
from app.utils.audit import registrar_log

links_bp = Blueprint('links', __name__, url_prefix='/api/links')


@links_bp.route('', methods=['GET'])
def listar_links():
    """
    Lista todos os links ativos (rota pública)
    ---
    tags:
      - Links Úteis
    responses:
      200:
        description: Lista de links
    """
    links = LinkUtil.query.filter_by(ativo=True).order_by(LinkUtil.ordem_exibicao).all()
    return jsonify([l.to_dict() for l in links]), 200


@links_bp.route('/<int:id>', methods=['GET'])
def buscar_link(id):
    """
    Busca um link por ID (rota pública)
    ---
    tags:
      - Links Úteis
    """
    link = LinkUtil.query.get_or_404(id)
    return jsonify(link.to_dict()), 200


@links_bp.route('', methods=['POST'])
@admin_required
def criar_link():
    """
    Cria um novo link útil (Admin)
    ---
    tags:
      - Links Úteis
    security:
      - Bearer: []
    """
    data = request.get_json()
    if not data or not data.get('nome') or not data.get('url'):
        return jsonify({'message': 'Nome e URL são obrigatórios.'}), 400

    # Tags recebidas como lista, salvas como string separada por vírgulas
    tags_raw = data.get('tags', [])
    tags_str = ','.join([t.strip().lower() for t in tags_raw if t.strip()]) if isinstance(tags_raw, list) else ''

    link = LinkUtil(
        nome=data['nome'],
        descricao=data.get('descricao', ''),
        url=data['url'],
        icone=data.get('icone', 'Link'),
        ativo=data.get('ativo', True),
        ordem_exibicao=data.get('ordem_exibicao', 0),
        tags=tags_str,
    )
    db.session.add(link)
    db.session.commit()

    registrar_log(get_jwt_identity(), 'CREATE', 'link', link.id, f'Criou: {link.nome}')

    return jsonify(link.to_dict()), 201


@links_bp.route('/<int:id>', methods=['PUT'])
@admin_required
def editar_link(id):
    """
    Edita um link útil (Admin)
    ---
    tags:
      - Links Úteis
    security:
      - Bearer: []
    """
    link = LinkUtil.query.get_or_404(id)
    data = request.get_json()

    link.nome = data.get('nome', link.nome)
    link.descricao = data.get('descricao', link.descricao)
    link.url = data.get('url', link.url)
    link.icone = data.get('icone', link.icone)
    link.ativo = data.get('ativo', link.ativo)
    link.ordem_exibicao = data.get('ordem_exibicao', link.ordem_exibicao)

    # Atualiza tags se enviadas (lista -> string separada por vírgulas)
    if 'tags' in data:
        tags_raw = data['tags']
        if isinstance(tags_raw, list):
            link.tags = ','.join([t.strip().lower() for t in tags_raw if t.strip()])
        else:
            link.tags = link.tags  # mantém o valor atual se não for lista

    db.session.commit()
    registrar_log(get_jwt_identity(), 'UPDATE', 'link', link.id, f'Editou: {link.nome}')

    return jsonify(link.to_dict()), 200


@links_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def excluir_link(id):
    """
    Exclui um link útil (Admin)
    ---
    tags:
      - Links Úteis
    security:
      - Bearer: []
    """
    link = LinkUtil.query.get_or_404(id)
    registrar_log(get_jwt_identity(), 'DELETE', 'link', link.id, f'Excluiu: {link.nome}')
    db.session.delete(link)
    db.session.commit()
    return jsonify({'message': 'Link excluído com sucesso.'}), 200
