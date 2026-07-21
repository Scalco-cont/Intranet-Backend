from app.utils.sanitize import sanitize_html


def test_remove_tag_script():
    assert sanitize_html('<p>oi</p><script>alert(1)</script>') == '<p>oi</p>'


def test_remove_atributo_onerror_e_tag_nao_permitida():
    result = sanitize_html('<img src=x onerror="alert(1)">')
    assert 'onerror' not in result
    assert '<img' not in result


def test_mantem_formatacao_permitida():
    html = '<p>Texto <strong>negrito</strong> e <em>itálico</em></p>'
    assert sanitize_html(html) == html


def test_remove_link_javascript():
    result = sanitize_html('<a href="javascript:alert(1)">clique</a>')
    assert 'javascript:' not in result


def test_mantem_link_http_valido():
    html = '<a href="https://empresa.com">link</a>'
    assert sanitize_html(html) == html


def test_string_vazia_retorna_vazia():
    assert sanitize_html('') == ''
