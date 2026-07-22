def test_sistemas_cors_continua_curinga(client):
    resp = client.get('/api/sistemas')
    assert resp.headers.get('Access-Control-Allow-Origin') == '*'
