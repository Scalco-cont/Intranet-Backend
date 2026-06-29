from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.extensions import db
from app.models import Comunicado, Comentario, Reacao
from app.middleware.auth_middleware import editor_or_admin_required, admin_required, get_current_user_info

comunicados_bp = Blueprint('comunicados', __name__, url_prefix='/api/comunicados')


@comunicados_bp.route('', methods=['GET'])
def listar_comunicados():
    """
    Lista comunicados ativos — fixados primeiro, depois mais recentes
    ---
    tags:
      - Comunicação
    responses:
      200:
        description: Lista de comunicados
    """
    comunicados = (
        Comunicado.query
        .filter_by(ativo=True)
        .order_by(Comunicado.fixado.desc(), Comunicado.criado_em.desc())
        .all()
    )
    return jsonify([c.to_dict() for c in comunicados]), 200


@comunicados_bp.route('/<int:id>', methods=['GET'])
def buscar_comunicado(id):
    """
    Retorna um comunicado com comentários
    ---
    tags:
      - Comunicação
    """
    comunicado = Comunicado.query.get_or_404(id)
    return jsonify(comunicado.to_dict(include_comentarios=True)), 200


@comunicados_bp.route('', methods=['POST'])
@editor_or_admin_required
def criar_comunicado():
    """
    Cria um novo comunicado (Editor ou Admin)
    ---
    tags:
      - Comunicação
    security:
      - Bearer: []
    """
    data = request.get_json()
    if not data or not data.get('titulo') or not data.get('conteudo'):
        return jsonify({'message': 'Título e conteúdo são obrigatórios.'}), 400

    tipo, user_id, _ = get_current_user_info()

    # autor_id só é preenchível para Usuarios (Editores); Admins usam a tabela separada
    autor_id = user_id if tipo == 'EDITOR' else None

    comunicado = Comunicado(
        titulo=data['titulo'],
        conteudo=data['conteudo'],
        categoria=data.get('categoria', 'Geral'),
        prioridade=data.get('prioridade', 'normal'),
        autor_id=autor_id,
        fixado=False,
    )
    # Admins: guardar nome manualmente se necessário (via campo `autor` virtual no to_dict)
    db.session.add(comunicado)
    db.session.commit()
    return jsonify(comunicado.to_dict()), 201


@comunicados_bp.route('/<int:id>', methods=['PUT'])
@editor_or_admin_required
def editar_comunicado(id):
    """
    Edita um comunicado (Editor próprio ou Admin)
    ---
    tags:
      - Comunicação
    security:
      - Bearer: []
    """
    comunicado = Comunicado.query.get_or_404(id)
    tipo, user_id, _ = get_current_user_info()

    # Editor só edita os próprios comunicados
    if tipo == 'EDITOR' and comunicado.autor_id != user_id:
        return jsonify({'message': 'Sem permissão para editar este comunicado.'}), 403

    data = request.get_json()
    comunicado.titulo = data.get('titulo', comunicado.titulo)
    comunicado.conteudo = data.get('conteudo', comunicado.conteudo)
    comunicado.categoria = data.get('categoria', comunicado.categoria)
    comunicado.prioridade = data.get('prioridade', comunicado.prioridade)
    db.session.commit()
    return jsonify(comunicado.to_dict()), 200


@comunicados_bp.route('/<int:id>', methods=['DELETE'])
@editor_or_admin_required
def excluir_comunicado(id):
    """
    Exclui (desativa) um comunicado
    ---
    tags:
      - Comunicação
    security:
      - Bearer: []
    """
    comunicado = Comunicado.query.get_or_404(id)
    tipo, user_id, _ = get_current_user_info()

    if tipo == 'EDITOR' and comunicado.autor_id != user_id:
        return jsonify({'message': 'Sem permissão para excluir este comunicado.'}), 403

    comunicado.ativo = False
    db.session.commit()
    return jsonify({'message': 'Comunicado removido.'}), 200


@comunicados_bp.route('/<int:id>/fixar', methods=['PATCH'])
@editor_or_admin_required
def fixar_comunicado(id):
    """
    Alterna o status de fixado de um comunicado (Admin ou Editor)
    ---
    tags:
      - Comunicação
    security:
      - Bearer: []
    """
    comunicado = Comunicado.query.get_or_404(id)
    comunicado.fixado = not comunicado.fixado
    db.session.commit()
    return jsonify({'fixado': comunicado.fixado}), 200


# ─── Comentários ──────────────────────────────────────────────────────────────

@comunicados_bp.route('/<int:id>/comentarios', methods=['GET'])
def listar_comentarios(id):
    """
    Lista comentários de um comunicado (público)
    ---
    tags:
      - Comunicação
    """
    Comunicado.query.get_or_404(id)
    comentarios = Comentario.query.filter_by(comunicado_id=id).order_by(Comentario.criado_em).all()
    return jsonify([c.to_dict() for c in comentarios]), 200

@comunicados_bp.route('/<int:id>/comentarios/<int:comentario_id>', methods=['DELETE'])
@admin_required
def deletar_comentario(id, comentario_id):
    """
    Deleta um comentário de um comunicado (Apenas Admin)
    """
    Comunicado.query.get_or_404(id)
    comentario = Comentario.query.get_or_404(comentario_id)
    if comentario.comunicado_id != id:
        return jsonify({'message': 'Comentário não pertence a este comunicado'}), 400
        
    db.session.delete(comentario)
    db.session.commit()
    
    return jsonify({'message': 'Comentário deletado com sucesso'}), 200


@comunicados_bp.route('/<int:id>/comentarios', methods=['POST'])
def criar_comentario(id):
    """
    Adiciona um comentário anônimo a um comunicado (público)
    ---
    tags:
      - Comunicação
    """
    Comunicado.query.get_or_404(id)
    data = request.get_json()
    if not data or not data.get('comentario'):
        return jsonify({'message': 'Comentário não pode estar vazio.'}), 400

    comentario = Comentario(
        comunicado_id=id,
        autor_nome=data.get('autor_nome', 'Anônimo').strip() or 'Anônimo',
        comentario=data['comentario'].strip(),
    )
    db.session.add(comentario)
    db.session.commit()
    return jsonify(comentario.to_dict()), 201


# ─── Reações ──────────────────────────────────────────────────────────────────

@comunicados_bp.route('/<int:id>/reacoes', methods=['POST'])
def reagir(id):
    """
    Adiciona ou altera uma reação a um comunicado (público, controlado por cliente_id)
    ---
    tags:
      - Comunicação
    """
    Comunicado.query.get_or_404(id)
    data = request.get_json()
    emoji = data.get('emoji', '') if data else ''
    cliente_id = data.get('cliente_id') if data else None

    if not cliente_id:
        return jsonify({'message': 'cliente_id é obrigatório para reagir.'}), 400

    if emoji not in Reacao.EMOJIS_VALIDOS:
        return jsonify({'message': f'Emoji inválido. Use: {", ".join(Reacao.EMOJIS_VALIDOS)}'}), 400

    reacao_existente = Reacao.query.filter_by(comunicado_id=id, cliente_id=cliente_id).first()

    if reacao_existente:
        if reacao_existente.emoji == emoji:
            # Clicou no mesmo emoji: remove a reação
            db.session.delete(reacao_existente)
        else:
            # Clicou em um diferente: atualiza a reação
            reacao_existente.emoji = emoji
    else:
        # Nova reação
        reacao = Reacao(comunicado_id=id, emoji=emoji, cliente_id=cliente_id)
        db.session.add(reacao)
        
    db.session.commit()

    # Retorna contagem atualizada
    comunicado = Comunicado.query.get(id)
    reacoes_agrupadas = {}
    for r in comunicado.reacoes:
        reacoes_agrupadas[r.emoji] = reacoes_agrupadas.get(r.emoji, 0) + 1
    return jsonify({'reacoes': reacoes_agrupadas}), 201
