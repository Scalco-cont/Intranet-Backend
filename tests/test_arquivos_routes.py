from app.services.drive_service import decodificar_token, mintar_token


def test_listar_raiz_sem_parametro(client, monkeypatch):
    monkeypatch.setattr('app.routes.arquivos_routes.listar_pasta', lambda id_real: [
        {'id': 'f1', 'name': 'Módulo 1', 'mimeType': 'application/vnd.google-apps.folder', 'modifiedTime': '2026-01-01T00:00:00Z'},
        {'id': 'f2', 'name': 'Aula 1.pdf', 'mimeType': 'application/pdf', 'modifiedTime': '2026-01-02T00:00:00Z'},
    ])
    resp = client.get('/api/arquivos-do-curso/listar')
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo['caminho'] == [{'token': None, 'nome': 'Arquivos do curso'}]
    assert [i['nome'] for i in corpo['itens']] == ['Módulo 1', 'Aula 1.pdf']
    assert [i['tipo'] for i in corpo['itens']] == ['pasta', 'pdf']


def test_listar_com_token_de_pasta_valido(app, client, monkeypatch):
    with app.app_context():
        token_pasta = mintar_token('pasta-real-1', 'pasta', 'Módulo 1', caminho=[{'token': None, 'nome': 'Arquivos do curso'}])

    monkeypatch.setattr('app.routes.arquivos_routes.listar_pasta', lambda id_real: [
        {'id': 'f3', 'name': 'Semana 1', 'mimeType': 'application/vnd.google-apps.folder', 'modifiedTime': '2026-01-01T00:00:00Z'},
    ])
    resp = client.get(f'/api/arquivos-do-curso/listar?pasta={token_pasta}')
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo['caminho'] == [
        {'token': None, 'nome': 'Arquivos do curso'},
        {'token': token_pasta, 'nome': 'Módulo 1'},
    ]

    # o token do filho mintado precisa ser independentemente válido e carregar o
    # caminho completo até ele mesmo, sem o front precisar reconstruir nada
    with app.app_context():
        payload_filho = decodificar_token(corpo['itens'][0]['token'])
    assert payload_filho['id'] == 'f3'
    assert payload_filho['caminho'] == corpo['caminho']


def test_listar_com_token_malformado(client):
    resp = client.get('/api/arquivos-do-curso/listar?pasta=token-invalido')
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'solicitacao_invalida'


def test_listar_com_token_de_pdf_como_pasta_e_rejeitado(app, client):
    with app.app_context():
        token_pdf = mintar_token('pdf-real-1', 'pdf', 'Aula.pdf')
    resp = client.get(f'/api/arquivos-do-curso/listar?pasta={token_pdf}')
    assert resp.status_code == 400


def test_profundidade_capada_em_20_niveis(app, client, monkeypatch):
    caminho_profundo = [{'token': f'tok{i}', 'nome': f'Pasta {i}'} for i in range(25)]
    with app.app_context():
        token_pasta_profunda = mintar_token('pasta-profunda', 'pasta', 'Pasta Atual', caminho=caminho_profundo)

    monkeypatch.setattr('app.routes.arquivos_routes.listar_pasta', lambda id_real: [
        {'id': 'filho1', 'name': 'Sub', 'mimeType': 'application/vnd.google-apps.folder', 'modifiedTime': '2026-01-01T00:00:00Z'},
    ])
    resp = client.get(f'/api/arquivos-do-curso/listar?pasta={token_pasta_profunda}')
    corpo = resp.get_json()
    with app.app_context():
        payload_filho = decodificar_token(corpo['itens'][0]['token'])
    assert len(payload_filho['caminho']) == 20
