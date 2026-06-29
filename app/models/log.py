from datetime import datetime, timezone
from app.extensions import db


class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    administrador_id = db.Column(db.Integer, db.ForeignKey('administradores.id'), nullable=True)
    acao = db.Column(db.String(50), nullable=False)   # LOGIN, CREATE, UPDATE, DELETE
    entidade = db.Column(db.String(50), nullable=True) # sistema, link, administrador
    entidade_id = db.Column(db.Integer, nullable=True)
    detalhes = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    data_hora = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'administrador_id': self.administrador_id,
            'acao': self.acao,
            'entidade': self.entidade,
            'entidade_id': self.entidade_id,
            'detalhes': self.detalhes,
            'ip': self.ip,
            'data_hora': self.data_hora.isoformat(),
        }
