from datetime import datetime, timezone
from app.extensions import db


class Sistema(db.Model):
    __tablename__ = 'sistemas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    icone = db.Column(db.String(50), nullable=False, default='AppWindow')
    url = db.Column(db.String(500), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    ordem_exibicao = db.Column(db.Integer, default=0)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'icone': self.icone,
            'url': self.url,
            'ativo': self.ativo,
            'ordem_exibicao': self.ordem_exibicao,
            'criado_em': self.criado_em.isoformat(),
        }


class LinkUtil(db.Model):
    __tablename__ = 'links_uteis'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    icone = db.Column(db.String(50), nullable=False, default='Link')
    ativo = db.Column(db.Boolean, default=True)
    ordem_exibicao = db.Column(db.Integer, default=0)
    # Tags armazenadas como string separada por vírgulas, ex: "fiscal,contabilidade"
    tags = db.Column(db.String(500), nullable=True, default='')
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'url': self.url,
            'icone': self.icone,
            'ativo': self.ativo,
            'ordem_exibicao': self.ordem_exibicao,
            'tags': [t.strip() for t in self.tags.split(',') if t.strip()] if self.tags else [],
            'criado_em': self.criado_em.isoformat(),
        }
