def test_criar_comunicado_remove_script_do_conteudo(client, editor_token):
    token, _ = editor_token
    resp = client.post(
        '/api/comunicados',
        json={
            'titulo': 'Aviso',
            'conteudo': '<p>Oi</p><script>alert(1)</script>',
        },
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == 201
    assert resp.get_json()['conteudo'] == '<p>Oi</p>'


def test_editar_comunicado_remove_script_do_conteudo(client, editor_token):
    token, _ = editor_token
    criado = client.post(
        '/api/comunicados',
        json={'titulo': 'Aviso', 'conteudo': '<p>original</p>'},
        headers={'Authorization': f'Bearer {token}'},
    ).get_json()

    resp = client.put(
        f"/api/comunicados/{criado['id']}",
        json={'conteudo': '<p>editado</p><img src=x onerror=alert(1)>'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == 200
    assert 'onerror' not in resp.get_json()['conteudo']
    assert '<img' not in resp.get_json()['conteudo']
