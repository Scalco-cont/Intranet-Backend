"""
Script de migração segura: adiciona a coluna 'tags' à tabela 'links_uteis'
sem apagar dados existentes.

Execute com:
    python migrate_add_tags.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        # Verifica se a coluna já existe antes de tentar criar
        try:
            result = conn.execute(text("SELECT tags FROM links_uteis LIMIT 1"))
            print("✅ Coluna 'tags' já existe em 'links_uteis'. Nenhuma alteração necessária.")
        except Exception:
            # Coluna não existe — adicionar com valor padrão vazio
            print("➕ Adicionando coluna 'tags' à tabela 'links_uteis'...")
            conn.execute(text("ALTER TABLE links_uteis ADD COLUMN tags VARCHAR(500) DEFAULT ''"))
            conn.commit()
            print("✅ Coluna 'tags' adicionada com sucesso!")
    print("Migração concluída.")
