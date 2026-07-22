import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///intranet.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 8))
    )
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

    ARQUIVOS_PASTA_RAIZ = os.getenv('ARQUIVOS_PASTA_RAIZ')
    ARQUIVOS_ORIGIN_PERMITIDA = os.getenv('ARQUIVOS_ORIGIN_PERMITIDA')
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    ARQUIVOS_CACHE_TTL_SEGUNDOS = int(os.getenv('ARQUIVOS_CACHE_TTL_SEGUNDOS', 300))
