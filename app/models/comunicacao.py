from datetime import datetime, timezone
from app.extensions import db

CATEGORIAS_VALIDAS = ['Geral', 'RH', 'TI', 'Financeiro', 'Diretoria', 'Aviso Importante']


class Comunicado(db.Model):
    __tablename__ = 'comunicados'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False, default='Geral')
    autor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    fixado = db.Column(db.Boolean, default=False)
    prioridade = db.Column(db.String(20), nullable=False, default='normal')  # normal | importante | urgente
    ativo = db.Column(db.Boolean, default=True)
    anexo_url = db.Column(db.String(500), nullable=True)  # Reservado para implementação futura
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))

    comentarios = db.relationship('Comentario', backref='comunicado', lazy=True, cascade='all, delete-orphan')
    reacoes = db.relationship('Reacao', backref='comunicado', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_comentarios=False):
        # Agrupa reações por emoji com contagem
        reacoes_agrupadas = {}
        for r in self.reacoes:
            reacoes_agrupadas[r.emoji] = reacoes_agrupadas.get(r.emoji, 0) + 1

        data = {
            'id': self.id,
            'titulo': self.titulo,
            'conteudo': self.conteudo,
            'categoria': self.categoria,
            'autor': self.autor.nome if self.autor else 'Administrador',
            'fixado': self.fixado,
            'prioridade': self.prioridade,
            'ativo': self.ativo,
            'reacoes': reacoes_agrupadas,
            'total_comentarios': len(self.comentarios),
            'criado_em': self.criado_em.isoformat(),
            'atualizado_em': self.atualizado_em.isoformat(),
        }
        if include_comentarios:
            data['comentarios'] = [c.to_dict() for c in self.comentarios]
        return data


class Comentario(db.Model):
    __tablename__ = 'comentarios'

    id = db.Column(db.Integer, primary_key=True)
    comunicado_id = db.Column(db.Integer, db.ForeignKey('comunicados.id'), nullable=False)
    autor_nome = db.Column(db.String(100), nullable=False, default='Anônimo')
    comentario = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'comunicado_id': self.comunicado_id,
            'autor_nome': self.autor_nome,
            'comentario': self.comentario,
            'criado_em': self.criado_em.isoformat(),
        }


class Reacao(db.Model):
    __tablename__ = 'reacoes'

    EMOJIS_VALIDOS = ['👍', '❤️', '🎉', '👏', '🚀', '💡']

    id = db.Column(db.Integer, primary_key=True)
    comunicado_id = db.Column(db.Integer, db.ForeignKey('comunicados.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    cliente_id = db.Column(db.String(50), nullable=False)  # Para controlar 1 reacao por pessoa anônima
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
