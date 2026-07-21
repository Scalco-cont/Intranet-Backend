"""
Script para popular o banco com dados iniciais.
Execute: python seed.py

As senhas padrão de Admin e Editor podem ser definidas via variáveis de
ambiente ADMIN_SEED_PASSWORD e EDITOR_SEED_PASSWORD. Se não definidas, uma
senha aleatória é gerada e impressa uma única vez — nunca fica hardcoded
no repositório.
"""
import secrets
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import Administrador, Sistema, LinkUtil, Usuario, Comunicado

app = create_app()

with app.app_context():
    db.create_all()

    # Administrador padrao
    if not Administrador.query.filter_by(email='admin@empresa.com').first():
        admin_password = os.getenv('ADMIN_SEED_PASSWORD')
        if not admin_password:
            admin_password = secrets.token_urlsafe(12)
            print(f'[AVISO] ADMIN_SEED_PASSWORD não definida — senha gerada automaticamente: {admin_password}')
        admin = Administrador(nome='Administrador', email='admin@empresa.com')
        admin.set_senha(admin_password)
        db.session.add(admin)
        print('[OK] Admin criado: admin@empresa.com')

    # Editor padrao
    if not Usuario.query.filter_by(email='editor@empresa.com').first():
        editor_password = os.getenv('EDITOR_SEED_PASSWORD')
        if not editor_password:
            editor_password = secrets.token_urlsafe(12)
            print(f'[AVISO] EDITOR_SEED_PASSWORD não definida — senha gerada automaticamente: {editor_password}')
        editor = Usuario(nome='Editor RH', email='editor@empresa.com', perfil='EDITOR')
        editor.set_senha(editor_password)
        db.session.add(editor)
        print('[OK] Editor criado: editor@empresa.com')

    db.session.flush()

    # Sistemas
    if Sistema.query.count() == 0:
        sistemas = [
            Sistema(nome='ERP', descricao='Sistema de gestao empresarial', icone='Building', url='https://erp.empresa.com', ordem_exibicao=1),
            Sistema(nome='Help Desk', descricao='Central de suporte e chamados', icone='Headset', url='https://helpdesk.empresa.com', ordem_exibicao=2),
            Sistema(nome='Financeiro', descricao='Controle financeiro e relatorios', icone='DollarSign', url='https://financeiro.empresa.com', ordem_exibicao=3),
            Sistema(nome='RH', descricao='Portal de Recursos Humanos', icone='Users', url='https://rh.empresa.com', ordem_exibicao=4),
            Sistema(nome='Monitoramento', descricao='Dashboards de infraestrutura', icone='Activity', url='https://monitoramento.empresa.com', ordem_exibicao=5),
            Sistema(nome='Controle de Tarefas', descricao='Gerenciamento de projetos', icone='CheckSquare', url='https://tarefas.empresa.com', ordem_exibicao=6),
            Sistema(nome='Sistema Fiscal', descricao='Gestao de notas fiscais', icone='FileText', url='https://fiscal.empresa.com', ordem_exibicao=7),
            Sistema(nome='CRM', descricao='Relacionamento com clientes', icone='PieChart', url='https://crm.empresa.com', ordem_exibicao=8),
        ]
        db.session.add_all(sistemas)
        print(f'[OK] {len(sistemas)} sistemas criados.')

    # Links
    if LinkUtil.query.count() == 0:
        links = [
            LinkUtil(nome='Receita Federal', descricao='Portal e-CAC e consultas', url='https://cav.receita.fazenda.gov.br', icone='Landmark', ordem_exibicao=1),
            LinkUtil(nome='Microsoft 365', descricao='Acesso ao pacote Office', url='https://www.office.com', icone='MonitorPlay', ordem_exibicao=2),
            LinkUtil(nome='WhatsApp Web', descricao='Comunicacao rapida via web', url='https://web.whatsapp.com', icone='MessageCircle', ordem_exibicao=3),
            LinkUtil(nome='Banco de Horas', descricao='Controle de ponto online', url='https://ponto.empresa.com', icone='Clock', ordem_exibicao=4),
            LinkUtil(nome='Wiki Interna', descricao='Base de conhecimento tecnica', url='https://wiki.empresa.com', icone='BookOpen', ordem_exibicao=5),
            LinkUtil(nome='Portal do Colaborador', descricao='Holerites e beneficios', url='https://colaborador.empresa.com', icone='UserCircle', ordem_exibicao=6),
        ]
        db.session.add_all(links)
        print(f'[OK] {len(links)} links criados.')

    # Comunicados de exemplo
    if Comunicado.query.count() == 0:
        editor = Usuario.query.filter_by(email='editor@empresa.com').first()
        comunicados = [
            Comunicado(
                titulo='Bem-vindo a nova Intranet!',
                conteudo='Estamos felizes em anunciar o lancamento da nossa nova Intranet Corporativa. Aqui voce encontra sistemas, links uteis e os comunicados da empresa. Explore e personalize seus favoritos!',
                categoria='Geral',
                autor_id=editor.id if editor else None,
                fixado=True,
            ),
            Comunicado(
                titulo='Nova politica de ferias 2026',
                conteudo='Informamos que a nova politica de ferias ja esta disponivel para consulta no Portal do Colaborador. Acesse e verifique as datas disponiveis para o seu departamento.',
                categoria='RH',
                autor_id=editor.id if editor else None,
                fixado=False,
            ),
            Comunicado(
                titulo='Manutencao programada dos servidores',
                conteudo='Neste sabado, das 22h as 02h, realizaremos manutencao nos servidores. Durante esse periodo, alguns sistemas podem ficar indisponiveis. Planeje-se!',
                categoria='TI',
                autor_id=editor.id if editor else None,
                fixado=False,
            ),
        ]
        db.session.add_all(comunicados)
        print(f'[OK] {len(comunicados)} comunicados de exemplo criados.')

    db.session.commit()
    print('[DONE] Banco populado com sucesso!')
