"""
Esta área não tem controle de acesso próprio. A proteção depende da intranet
estar restrita à rede interna. Se ela for exposta à internet, adicionar um
código de acesso antes disso.
"""
import json


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
