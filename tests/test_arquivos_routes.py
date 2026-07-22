from app.routes import arquivos_routes
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


class FakeExecutavel:
    def __init__(self, resultado):
        self._resultado = resultado

    def execute(self):
        return self._resultado


class FakeFilesResourceConteudo:
    def __init__(self, metadados):
        self._metadados = metadados

    def get(self, fileId, fields=None, supportsAllDrives=None):
        return FakeExecutavel(self._metadados)

    def get_media(self, fileId, supportsAllDrives=None):
        return object()


class FakeDriveClientConteudo:
    def __init__(self, metadados):
        self._files = FakeFilesResourceConteudo(metadados)

    def files(self):
        return self._files


class FakeDownloaderOk:
    def __init__(self, buffer, requisicao, chunksize):
        self.buffer = buffer
        self._chamadas = 0

    def next_chunk(self):
        self._chamadas += 1
        if self._chamadas == 1:
            self.buffer.write(b'PARTE-UM-')
            return (None, False)
        self.buffer.write(b'PARTE-DOIS')
        return (None, True)


class FakeDownloaderComFalha:
    def __init__(self, buffer, requisicao, chunksize):
        self.buffer = buffer
        self._chamadas = 0

    def next_chunk(self):
        self._chamadas += 1
        if self._chamadas == 1:
            self.buffer.write(b'PARTE-UM-')
            return (None, False)
        raise RuntimeError('falha simulada no meio do download')


def test_arquivo_pdf_streaming_ok(app, client, monkeypatch):
    with app.app_context():
        token = mintar_token('pdf-real-1', 'pdf', 'Aula 1.pdf')

    metadados = {'id': 'pdf-real-1', 'name': 'Aula 1.pdf', 'mimeType': 'application/pdf', 'size': '19'}
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    monkeypatch.setattr(arquivos_routes, 'MediaIoBaseDownload', FakeDownloaderOk)

    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/pdf'
    assert resp.headers['Content-Disposition'] == 'inline'
    assert resp.headers['Cache-Control'] == 'no-store'
    assert resp.headers['Content-Length'] == '19'
    assert resp.get_data() == b'PARTE-UM-PARTE-DOIS'


def test_arquivo_sem_size_omite_content_length(app, client, monkeypatch):
    with app.app_context():
        token = mintar_token('pdf-real-2', 'pdf', 'Aula 2.pdf')

    metadados = {'id': 'pdf-real-2', 'name': 'Aula 2.pdf', 'mimeType': 'application/pdf'}  # sem 'size'
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    monkeypatch.setattr(arquivos_routes, 'MediaIoBaseDownload', FakeDownloaderOk)

    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
    assert resp.status_code == 200
    assert 'Content-Length' not in resp.headers


def test_arquivo_mimetype_mudou_na_origem_e_rejeitado(app, client, monkeypatch):
    with app.app_context():
        token = mintar_token('pdf-real-3', 'pdf', 'Aula 3.pdf')

    metadados = {'id': 'pdf-real-3', 'name': 'Aula 3.pdf', 'mimeType': 'image/png', 'size': '10'}
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))

    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'solicitacao_invalida'


def test_arquivo_token_de_pasta_e_rejeitado(app, client):
    with app.app_context():
        token_pasta = mintar_token('pasta-real-1', 'pasta', 'Módulo 1', caminho=[])
    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token_pasta}')
    assert resp.status_code == 400


def test_arquivo_falha_no_meio_do_stream_e_logada(app, client, monkeypatch, caplog):
    with app.app_context():
        token = mintar_token('pdf-real-4', 'pdf', 'Aula 4.pdf')

    metadados = {'id': 'pdf-real-4', 'name': 'Aula 4.pdf', 'mimeType': 'application/pdf', 'size': '19'}
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    monkeypatch.setattr(arquivos_routes, 'MediaIoBaseDownload', FakeDownloaderComFalha)

    with caplog.at_level('ERROR'):
        resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
        dados = resp.get_data()  # força o consumo do generator

    assert resp.status_code == 200  # headers já foram enviados
    assert dados == b'PARTE-UM-'  # truncado
    assert any('Falha no meio do streaming' in r.message for r in caplog.records)
