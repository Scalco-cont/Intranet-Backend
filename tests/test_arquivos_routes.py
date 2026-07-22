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
    assert corpo['caminho'] == [{'token': None, 'nome': 'Biblioteca de Cursos'}]
    assert [i['nome'] for i in corpo['itens']] == ['Módulo 1', 'Aula 1.pdf']
    assert [i['tipo'] for i in corpo['itens']] == ['pasta', 'pdf']


def test_listar_com_token_de_pasta_valido(app, client, monkeypatch):
    with app.app_context():
        token_pasta = mintar_token('pasta-real-1', 'pasta', 'Módulo 1', caminho=[{'token': None, 'nome': 'Biblioteca de Cursos'}])

    monkeypatch.setattr('app.routes.arquivos_routes.listar_pasta', lambda id_real: [
        {'id': 'f3', 'name': 'Semana 1', 'mimeType': 'application/vnd.google-apps.folder', 'modifiedTime': '2026-01-01T00:00:00Z'},
    ])
    resp = client.get(f'/api/arquivos-do-curso/listar?pasta={token_pasta}')
    corpo = resp.get_json()
    assert resp.status_code == 200
    assert corpo['caminho'] == [
        {'token': None, 'nome': 'Biblioteca de Cursos'},
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


class FakeDriveClientConteudo:
    def __init__(self, metadados):
        self._files = FakeFilesResourceConteudo(metadados)

    def files(self):
        return self._files


class FakeRespostaDrive:
    def __init__(self, status_code, headers, pedacos):
        self.status_code = status_code
        self.headers = headers
        self._pedacos = pedacos

    def iter_content(self, chunk_size=None):
        yield from self._pedacos


class FakeRespostaDriveComFalha(FakeRespostaDrive):
    def iter_content(self, chunk_size=None):
        yield b'PARTE-UM-'
        raise RuntimeError('falha simulada no meio do download')


class FakeSessaoAutorizada:
    def __init__(self, resposta):
        self._resposta = resposta
        self.ultima_chamada_headers = None

    def get(self, url, params=None, headers=None, stream=None):
        self.ultima_chamada_headers = headers
        return self._resposta


def test_arquivo_pdf_streaming_ok(app, client, monkeypatch):
    with app.app_context():
        token = mintar_token('pdf-real-1', 'pdf', 'Aula 1.pdf')

    metadados = {'id': 'pdf-real-1', 'name': 'Aula 1.pdf', 'mimeType': 'application/pdf', 'size': '19'}
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    resposta_fake = FakeRespostaDrive(200, {'Content-Length': '19'}, [b'PARTE-UM-', b'PARTE-DOIS'])
    monkeypatch.setattr(arquivos_routes, 'obter_sessao_autorizada', lambda: FakeSessaoAutorizada(resposta_fake))

    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'application/pdf'
    assert resp.headers['Content-Disposition'] == 'inline'
    assert resp.headers['Cache-Control'] == 'no-store'
    assert 'Accept-Ranges' not in resp.headers
    assert resp.headers['Content-Length'] == '19'
    assert resp.get_data() == b'PARTE-UM-PARTE-DOIS'


def test_arquivo_ignora_range_do_cliente_e_devolve_arquivo_inteiro(app, client, monkeypatch):
    # Decisão consciente: não repassamos Range pro Drive (ver design doc, trade-off T2
    # revisado). Mesmo que o navegador peça um pedaço, sempre servimos o arquivo inteiro
    # com 200 — evita multiplicar chamadas concorrentes à API do Drive por abertura de PDF.
    with app.app_context():
        token = mintar_token('pdf-real-5', 'pdf', 'Aula 5.pdf')

    metadados = {'id': 'pdf-real-5', 'name': 'Aula 5.pdf', 'mimeType': 'application/pdf'}
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    resposta_fake = FakeRespostaDrive(200, {'Content-Length': '1000'}, [b'X' * 1000])
    sessao_fake = FakeSessaoAutorizada(resposta_fake)
    monkeypatch.setattr(arquivos_routes, 'obter_sessao_autorizada', lambda: sessao_fake)

    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}', headers={'Range': 'bytes=0-99'})
    assert resp.status_code == 200
    assert resp.headers['Content-Length'] == '1000'
    assert sessao_fake.ultima_chamada_headers is None


def test_arquivo_usa_size_do_metadado_mesmo_sem_content_length_na_resposta(app, client, monkeypatch):
    # O tamanho vem do metadado, não do header da resposta de mídia — em download de
    # arquivo inteiro o Drive costuma responder em Transfer-Encoding: chunked sem
    # Content-Length algum, então não dá pra confiar só na resposta de mídia.
    with app.app_context():
        token = mintar_token('pdf-real-2', 'pdf', 'Aula 2.pdf')

    metadados = {'id': 'pdf-real-2', 'name': 'Aula 2.pdf', 'mimeType': 'application/pdf', 'size': '8'}
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    resposta_fake = FakeRespostaDrive(200, {}, [b'conteudo'])  # sem Content-Length na resposta
    monkeypatch.setattr(arquivos_routes, 'obter_sessao_autorizada', lambda: FakeSessaoAutorizada(resposta_fake))

    resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
    assert resp.status_code == 200
    assert resp.headers['Content-Length'] == '8'


def test_arquivo_sem_size_e_sem_content_length_omite_o_header(app, client, monkeypatch):
    with app.app_context():
        token = mintar_token('pdf-real-6', 'pdf', 'Aula 6.pdf')

    metadados = {'id': 'pdf-real-6', 'name': 'Aula 6.pdf', 'mimeType': 'application/pdf'}  # sem 'size'
    monkeypatch.setattr(arquivos_routes, 'obter_client', lambda: FakeDriveClientConteudo(metadados))
    resposta_fake = FakeRespostaDrive(200, {}, [b'conteudo'])  # sem Content-Length na resposta
    monkeypatch.setattr(arquivos_routes, 'obter_sessao_autorizada', lambda: FakeSessaoAutorizada(resposta_fake))

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
    resposta_fake = FakeRespostaDriveComFalha(200, {'Content-Length': '19'}, [])
    monkeypatch.setattr(arquivos_routes, 'obter_sessao_autorizada', lambda: FakeSessaoAutorizada(resposta_fake))

    with caplog.at_level('ERROR'):
        resp = client.get(f'/api/arquivos-do-curso/arquivo/{token}')
        dados = resp.get_data()  # força o consumo do generator

    assert resp.status_code == 200  # headers já foram enviados
    assert dados == b'PARTE-UM-'  # truncado
    assert any('Falha no meio do streaming' in r.message for r in caplog.records)
