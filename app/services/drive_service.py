"""
Esta área não tem controle de acesso próprio. A proteção depende da intranet
estar restrita à rede interna. Se ela for exposta à internet, adicionar um
código de acesso antes disso.
"""
import json
import time

from flask import current_app
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from itsdangerous import BadData, URLSafeSerializer

SALT = 'arquivos-do-curso'
MAX_PROFUNDIDADE = 20
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TIPOS_ACEITOS = {'application/vnd.google-apps.folder', 'application/pdf'}
DRIVE_MEDIA_URL_TEMPLATE = 'https://www.googleapis.com/drive/v3/files/{id}'

_client = None
_sessao_autorizada = None
_cache = {}  # {id_real: (timestamp, itens)}


class ArquivosDoCursoError(Exception):
    def __init__(self, codigo, mensagem, status):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status


def _serializer():
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt=SALT)


def mintar_token(id_real, tipo, nome, caminho=None):
    payload = {'id': id_real, 'tipo': tipo, 'nome': nome}
    if tipo == 'pasta':
        payload['caminho'] = caminho if caminho is not None else []
    return _serializer().dumps(payload)


def decodificar_token(token):
    try:
        return _serializer().loads(token)
    except BadData as exc:
        raise ArquivosDoCursoError('solicitacao_invalida', 'Token inválido.', 400) from exc


def validar_credencial_google(raw_json):
    """Valida só o formato — não constrói client nem toca rede. Nunca loga o conteúdo."""
    if not raw_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON não definida.")
    try:
        info = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON não é um JSON válido. Verifique se a private_key "
            "mantém as quebras de linha como \\n escapado (duas caracteres: barra + n), "
            "não como quebra de linha real dentro do valor da variável de ambiente."
        ) from exc

    chave = info.get('private_key', '')
    if '\n' not in chave or not chave.startswith('-----BEGIN PRIVATE KEY-----'):
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON foi lida, mas private_key não parece uma chave PEM "
            "válida após o parse. Confira o valor da variável (nunca o conteúdo em si)."
        )


def obter_client():
    global _client
    if _client is None:
        info = json.loads(current_app.config['GOOGLE_SERVICE_ACCOUNT_JSON'])
        creds = service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
        _client = build('drive', 'v3', credentials=creds, cache_discovery=False, static_discovery=True)
    return _client


def obter_sessao_autorizada():
    """Sessão HTTP autenticada (não a wrapper alta-nível do googleapiclient) — usada só
    pra baixar o conteúdo do arquivo direto via REST, porque precisamos repassar o header
    Range do cliente ao Drive, o que a MediaIoBaseDownload não permite fazer facilmente."""
    global _sessao_autorizada
    if _sessao_autorizada is None:
        info = json.loads(current_app.config['GOOGLE_SERVICE_ACCOUNT_JSON'])
        creds = service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPES)
        _sessao_autorizada = AuthorizedSession(creds)
    return _sessao_autorizada


def mapear_erro_http(exc):
    status = exc.resp.status if exc.resp else 500
    razao = ''
    try:
        corpo = json.loads(exc.content.decode('utf-8'))
        razao = corpo.get('error', {}).get('errors', [{}])[0].get('reason', '')
    except Exception:
        pass

    if status == 404:
        return ArquivosDoCursoError('nao_encontrado', 'Pasta ou arquivo não encontrado.', 404)
    if status == 403 and razao in ('rateLimitExceeded', 'userRateLimitExceeded'):
        return ArquivosDoCursoError('cota_excedida', 'Cota da API do Google excedida. Tente novamente em instantes.', 429)
    if status == 403:
        return ArquivosDoCursoError('sem_permissao', 'Credencial inválida ou sem permissão.', 403)
    return ArquivosDoCursoError('indisponivel', 'Google Drive indisponível no momento.', 502)


def listar_pasta(id_real):
    agora = time.time()
    ttl = current_app.config.get('ARQUIVOS_CACHE_TTL_SEGUNDOS', 300)
    cache_hit = _cache.get(id_real)
    if cache_hit and agora - cache_hit[0] < ttl:
        return cache_hit[1]

    try:
        resposta = obter_client().files().list(
            q=f"'{id_real}' in parents and trashed = false",
            fields='files(id,name,mimeType,modifiedTime)',
            orderBy='folder,name',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
    except HttpError as exc:
        raise mapear_erro_http(exc)

    itens = [f for f in resposta.get('files', []) if f['mimeType'] in TIPOS_ACEITOS]
    _cache[id_real] = (agora, itens)
    return itens
