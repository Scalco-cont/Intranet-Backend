import pytest

from app.services.drive_service import (
    ArquivosDoCursoError,
    decodificar_token,
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
