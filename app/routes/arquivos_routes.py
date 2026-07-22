"""
Esta área não tem controle de acesso próprio. A proteção depende da intranet
estar restrita à rede interna. Se ela for exposta à internet, adicionar um
código de acesso antes disso.
"""
from flask import Blueprint, current_app, jsonify, request

from app.services.drive_service import (
    ArquivosDoCursoError,
    MAX_PROFUNDIDADE,
    decodificar_token,
    listar_pasta,
    mintar_token,
)

arquivos_bp = Blueprint('arquivos', __name__, url_prefix='/api/arquivos-do-curso')


@arquivos_bp.after_request
def aplicar_cors_escopado(response):
    response.headers['Access-Control-Allow-Origin'] = current_app.config['ARQUIVOS_ORIGIN_PERMITIDA']
    response.headers['Vary'] = 'Origin'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def obter_ip_cliente():
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        partes = [p.strip() for p in xff.split(',') if p.strip()]
        if partes:
            return partes[-1]  # Traefik acrescenta o IP real por último
    return request.remote_addr


@arquivos_bp.route('/listar', methods=['GET'])
def listar():
    token = request.args.get('pasta')

    if token:
        try:
            payload = decodificar_token(token)
        except ArquivosDoCursoError as erro:
            return jsonify({'error': erro.codigo, 'message': erro.mensagem}), erro.status
        if payload['tipo'] != 'pasta':
            return jsonify({'error': 'solicitacao_invalida', 'message': 'Token não é de uma pasta.'}), 400
        id_real = payload['id']
        ancestrais = payload.get('caminho', [])
        nome_atual = payload['nome']
    else:
        id_real = current_app.config['ARQUIVOS_PASTA_RAIZ']
        ancestrais = []
        nome_atual = 'Arquivos do curso'
        token = None

    caminho_atual = ancestrais + [{'token': token, 'nome': nome_atual}]
    if len(caminho_atual) > MAX_PROFUNDIDADE:
        caminho_atual = caminho_atual[-MAX_PROFUNDIDADE:]

    try:
        arquivos_drive = listar_pasta(id_real)
    except ArquivosDoCursoError as erro:
        return jsonify({'error': erro.codigo, 'message': erro.mensagem}), erro.status

    itens = []
    for item in arquivos_drive:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            tipo = 'pasta'
            token_filho = mintar_token(item['id'], 'pasta', item['name'], caminho=caminho_atual)
        else:
            tipo = 'pdf'
            token_filho = mintar_token(item['id'], 'pdf', item['name'])
        itens.append({
            'token': token_filho,
            'nome': item['name'],
            'tipo': tipo,
            'modificado_em': item.get('modifiedTime'),
        })

    return jsonify({'caminho': caminho_atual, 'itens': itens}), 200
