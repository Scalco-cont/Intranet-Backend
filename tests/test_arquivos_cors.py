def test_listar_arquivos_cors_origin_exato(client, monkeypatch):
    # Mocka o caminho de sucesso — sem isso, a credencial fake quebra ao construir
    # o client do Drive, o teste passa pelo caminho de erro (que também carrega os
    # headers de CORS via after_request) e fica verde sem exercitar o que importa.
    monkeypatch.setattr('app.routes.arquivos_routes.listar_pasta', lambda id_real: [])
    resp = client.get('/api/arquivos-do-curso/listar')
    assert resp.status_code == 200
    assert resp.headers.get('Access-Control-Allow-Origin') == 'https://intranet-teste.local'
    assert resp.headers.get('Access-Control-Allow-Origin') != '*'


def test_sistemas_cors_continua_curinga(client):
    resp = client.get('/api/sistemas')
    assert resp.headers.get('Access-Control-Allow-Origin') == '*'
