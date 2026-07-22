import json

import pytest

from app import create_app
from app.config.config import Config

FAKE_KEY = json.dumps({
    'private_key': '-----BEGIN PRIVATE KEY-----\nFAKE\n-----END PRIVATE KEY-----\n',
})


class ConfigSemOrigin(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'
    ARQUIVOS_PASTA_RAIZ = 'fake-root'
    GOOGLE_SERVICE_ACCOUNT_JSON = FAKE_KEY
    ARQUIVOS_ORIGIN_PERMITIDA = None


def test_falha_sem_origin_permitida():
    with pytest.raises(RuntimeError, match='ARQUIVOS_ORIGIN_PERMITIDA'):
        create_app(ConfigSemOrigin)


class ConfigSemPastaRaiz(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'
    ARQUIVOS_ORIGIN_PERMITIDA = 'https://intranet-teste.local'
    GOOGLE_SERVICE_ACCOUNT_JSON = FAKE_KEY
    ARQUIVOS_PASTA_RAIZ = None


def test_falha_sem_pasta_raiz():
    with pytest.raises(RuntimeError, match='ARQUIVOS_PASTA_RAIZ'):
        create_app(ConfigSemPastaRaiz)


class ConfigCredencialNaoJson(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'
    ARQUIVOS_ORIGIN_PERMITIDA = 'https://intranet-teste.local'
    ARQUIVOS_PASTA_RAIZ = 'fake-root'
    GOOGLE_SERVICE_ACCOUNT_JSON = 'isso nao e json'


def test_falha_com_credencial_nao_json():
    with pytest.raises(RuntimeError, match='GOOGLE_SERVICE_ACCOUNT_JSON'):
        create_app(ConfigCredencialNaoJson)


class ConfigCredencialSemPrivateKeyValida(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'
    ARQUIVOS_ORIGIN_PERMITIDA = 'https://intranet-teste.local'
    ARQUIVOS_PASTA_RAIZ = 'fake-root'
    GOOGLE_SERVICE_ACCOUNT_JSON = json.dumps({'private_key': 'sem quebras de linha nenhuma'})


def test_falha_com_private_key_sem_quebras_de_linha():
    with pytest.raises(RuntimeError, match='private_key'):
        create_app(ConfigCredencialSemPrivateKeyValida)
