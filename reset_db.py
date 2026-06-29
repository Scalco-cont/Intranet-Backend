import os
import sys

# Adiciona o diretório atual ao path para garantir as importações
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    print("Deletando o banco de dados...")
    db.drop_all()
    print("Recriando o banco de dados...")
    db.create_all()
    print("Concluído!")
