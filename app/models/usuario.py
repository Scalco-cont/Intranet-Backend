from datetime import datetime, timezone
from app.extensions import db


class Usuario(db.Model):
    """Representa Editores e pode futuramente absorver Admins."""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default='EDITOR')  # ADMIN | EDITOR
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    comunicados = db.relationship('Comunicado', backref='autor', lazy=True)

    def set_senha(self, senha: str):
        import bcrypt
        self.senha_hash = bcrypt.hashpw(
            senha.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def verificar_senha(self, senha: str) -> bool:
        import bcrypt
        return bcrypt.checkpw(
            senha.encode('utf-8'),
            self.senha_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'perfil': self.perfil,
            'ativo': self.ativo,
        }
