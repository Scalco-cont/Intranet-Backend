import json

import pytest
from googleapiclient.errors import HttpError

from app.services import drive_service
from app.services.drive_service import (
    ArquivosDoCursoError,
    decodificar_token,
    listar_pasta,
    mapear_erro_http,
    mintar_token,
)


def test_mint_e_decode_pasta(app):
    with app.app_context():
        token = mintar_token('id-real-123', 'pasta', 'Módulo 1', caminho=[{'id': 'raiz', 'nome': 'Arquivos do curso'}])
        payload = decodificar_token(token)
    assert payload['id'] == 'id-real-123'
    assert payload['tipo'] == 'pasta'
    assert payload['nome'] == 'Módulo 1'
    assert payload['caminho'] == [{'id': 'raiz', 'nome': 'Arquivos do curso'}]


def test_mint_e_decode_pdf_sem_caminho(app):
    with app.app_context():
        token = mintar_token('id-pdf-456', 'pdf', 'Aula 1.pdf')
        payload = decodificar_token(token)
    assert payload['id'] == 'id-pdf-456'
    assert payload['tipo'] == 'pdf'
    assert 'caminho' not in payload


def test_token_com_assinatura_adulterada_e_rejeitado(app):
    with app.app_context():
        token = mintar_token('id-real-123', 'pasta', 'Módulo 1', caminho=[])
    token_adulterado = token[:-2] + 'xx'
    with app.app_context():
        with pytest.raises(ArquivosDoCursoError) as erro:
            decodificar_token(token_adulterado)
    assert erro.value.codigo == 'solicitacao_invalida'
    assert erro.value.status == 400


class RespostaFalsa:
    def __init__(self, status):
        self.status = status
        self.reason = 'motivo-falso'


def _http_error(status, razao=None):
    corpo = {'error': {'errors': [{'reason': razao}]}} if razao else {}
    return HttpError(RespostaFalsa(status), json.dumps(corpo).encode('utf-8'))


def test_mapear_erro_404():
    erro = mapear_erro_http(_http_error(404))
    assert erro.codigo == 'nao_encontrado'
    assert erro.status == 404


def test_mapear_erro_403_sem_permissao():
    erro = mapear_erro_http(_http_error(403, razao='forbidden'))
    assert erro.codigo == 'sem_permissao'
    assert erro.status == 403


def test_mapear_erro_403_cota_excedida():
    erro = mapear_erro_http(_http_error(403, razao='userRateLimitExceeded'))
    assert erro.codigo == 'cota_excedida'
    assert erro.status == 429


def test_mapear_erro_generico_indisponivel():
    erro = mapear_erro_http(_http_error(500))
    assert erro.codigo == 'indisponivel'
    assert erro.status == 502


class FakeListaExecutavel:
    def __init__(self, resultado):
        self._resultado = resultado

    def execute(self):
        return self._resultado


class FakeFilesResource:
    chamadas = 0

    def __init__(self, resultado):
        self._resultado = resultado

    def list(self, **kwargs):
        FakeFilesResource.chamadas += 1
        return FakeListaExecutavel(self._resultado)


class FakeClient:
    def __init__(self, resultado):
        self._files = FakeFilesResource(resultado)

    def files(self):
        return self._files


def test_listar_pasta_filtra_e_ordena(app, monkeypatch):
    resultado = {'files': [
        {'id': 'f1', 'name': 'Pasta A', 'mimeType': 'application/vnd.google-apps.folder', 'modifiedTime': '2026-01-01T00:00:00Z'},
        {'id': 'f2', 'name': 'Aula.pdf', 'mimeType': 'application/pdf', 'modifiedTime': '2026-01-02T00:00:00Z'},
        {'id': 'f3', 'name': 'planilha.xlsx', 'mimeType': 'application/vnd.ms-excel', 'modifiedTime': '2026-01-03T00:00:00Z'},
    ]}
    FakeFilesResource.chamadas = 0
    monkeypatch.setattr(drive_service, 'obter_client', lambda: FakeClient(resultado))
    drive_service._cache.clear()

    with app.app_context():
        itens = listar_pasta('pasta-x')

    assert [i['name'] for i in itens] == ['Pasta A', 'Aula.pdf']
    assert FakeFilesResource.chamadas == 1


def test_listar_pasta_usa_cache_dentro_do_ttl(app, monkeypatch):
    resultado = {'files': [{'id': 'f1', 'name': 'Pasta A', 'mimeType': 'application/vnd.google-apps.folder', 'modifiedTime': '2026-01-01T00:00:00Z'}]}
    FakeFilesResource.chamadas = 0
    monkeypatch.setattr(drive_service, 'obter_client', lambda: FakeClient(resultado))
    drive_service._cache.clear()

    with app.app_context():
        listar_pasta('pasta-y')
        listar_pasta('pasta-y')

    assert FakeFilesResource.chamadas == 1
