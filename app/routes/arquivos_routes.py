"""
Esta área não tem controle de acesso próprio. A proteção depende da intranet
estar restrita à rede interna. Se ela for exposta à internet, adicionar um
código de acesso antes disso.
"""
from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from googleapiclient.errors import HttpError

from app.services.drive_service import (
    ArquivosDoCursoError,
    DRIVE_MEDIA_URL_TEMPLATE,
    MAX_PROFUNDIDADE,
    decodificar_token,
    listar_pasta,
    mapear_erro_http,
    mintar_token,
    obter_client,
    obter_sessao_autorizada,
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
        nome_atual = 'Biblioteca de Cursos'
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


@arquivos_bp.route('/arquivo/<token>', methods=['GET'])
def arquivo(token):
    try:
        payload = decodificar_token(token)
    except ArquivosDoCursoError as erro:
        return jsonify({'error': erro.codigo, 'message': erro.mensagem}), erro.status

    if payload['tipo'] != 'pdf':
        return jsonify({'error': 'solicitacao_invalida', 'message': 'Token não é de um PDF.'}), 400

    id_real = payload['id']
    nome_arquivo = payload['nome']

    try:
        metadados = obter_client().files().get(
            fileId=id_real, fields='id,name,mimeType,size', supportsAllDrives=True,
        ).execute()
    except HttpError as exc:
        erro = mapear_erro_http(exc)
        return jsonify({'error': erro.codigo, 'message': erro.mensagem}), erro.status

    if metadados.get('mimeType') != 'application/pdf':
        return jsonify({'error': 'solicitacao_invalida', 'message': 'Arquivo não é mais um PDF na origem.'}), 400

    # Decisão consciente: não repassamos o Range do cliente pro Drive. Nesta rede, cada
    # requisição ao Drive carrega uma latência fixa (~1,5-2s) independente do tamanho
    # pedido — e o pdf.js chega a abrir 10+ requisições Range concorrentes por PDF. Com
    # gunicorn rodando poucos workers/threads em produção, isso é capaz de saturar o
    # backend inteiro por uma única pessoa abrindo um PDF. Sempre servimos o arquivo
    # inteiro numa única chamada.
    resposta_drive = obter_sessao_autorizada().get(
        DRIVE_MEDIA_URL_TEMPLATE.format(id=id_real),
        params={'alt': 'media', 'supportsAllDrives': 'true'},
        stream=True,
    )

    if resposta_drive.status_code != 200:
        current_app.logger.exception(
            'Drive respondeu %s ao baixar o arquivo: %s', resposta_drive.status_code, nome_arquivo
        )
        return jsonify({'error': 'indisponivel', 'message': 'Google Drive indisponível no momento.'}), 502

    current_app.logger.info(
        'Acesso a arquivo do curso: ip=%s arquivo=%s', obter_ip_cliente(), nome_arquivo
    )

    def gerar():
        try:
            for pedaco in resposta_drive.iter_content(chunk_size=1024 * 1024):
                if pedaco:
                    yield pedaco
        except Exception:
            current_app.logger.exception('Falha no meio do streaming do arquivo: %s', nome_arquivo)

    headers = {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline',
        'Cache-Control': 'no-store',
    }
    # O tamanho vem do metadado (files().get), não do header da resposta de mídia — em
    # download de arquivo inteiro (sem Range), o Drive costuma responder em
    # Transfer-Encoding: chunked sem Content-Length algum, o que quebraria a barra de
    # progresso do frontend sem essa alternativa.
    tamanho = metadados.get('size')
    if tamanho is not None:
        headers['Content-Length'] = str(tamanho)
    elif 'Content-Length' in resposta_drive.headers:
        headers['Content-Length'] = resposta_drive.headers['Content-Length']

    return Response(stream_with_context(gerar()), headers=headers)
