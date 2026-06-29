from datetime import datetime, timezone
from flask import request
from app.extensions import db
from app.models import Log


def registrar_log(admin_id, acao, entidade=None, entidade_id=None, detalhes=None):
    """Utilitário para gravar um log de auditoria."""
    log = Log(
        administrador_id=admin_id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
        ip=request.remote_addr,
        data_hora=datetime.now(timezone.utc)
    )
    db.session.add(log)
    db.session.commit()
