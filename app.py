"""
Aplicação Flask principal - Vida Arroz
"""
import os
import json
import uuid
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from database import (
    init_db, insert_lead, get_all_leads, get_admin_by_username, create_admin_if_empty,
    get_all_receitas, get_receita_by_id, get_receita_by_slug, insert_receita, update_receita, get_db_backend,
    get_all_admin_users, insert_admin_user, update_admin_user, set_admin_ativo, delete_admin_user,
    count_receitas_por_mes, count_leads_por_mes,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui-altere-em-producao')

# Upload de imagens e vídeos (receitas)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'receitas')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
# HEIC (fotos do iPhone) não é suportado na web; o usuário deve converter para JPG/PNG
UNSUPPORTED_IMAGE_EXTENSIONS = {'heic', 'heif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'ogg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB (para vídeos)

# Garantir que a pasta de upload existe desde o início (evita salvar em outro lugar)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except OSError:
    pass


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

# Senha padrão do admin (altere em produção via ADMIN_PASSWORD)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'vidaarroz2026')


_db_initialized = False

@app.before_request
def setup_db():
    """
    Inicializa o banco UMA vez por processo.
    Só marca como inicializado quando der certo, para novas requisições tentarem de novo se falhar.
    """
    global _db_initialized
    if _db_initialized:
        return
    try:
        init_db()
        create_admin_if_empty(
            ADMIN_USERNAME,
            generate_password_hash(ADMIN_PASSWORD, method='scrypt'),
        )
        _db_initialized = True
    except Exception:
        # Não derruba o site; na próxima requisição tenta init_db de novo
        pass


# ---------- Rotas públicas ----------

@app.route('/')
def index():
    return render_template('index.html', title='Home')


@app.route('/sobre')
def sobre():
    return render_template('sobre.html', title='Sobre')


@app.route('/quem-somos')
def quem_somos():
    return render_template('quem_somos.html', title='Quem somos')


@app.route('/contato')
def contato():
    return render_template('contato.html', title='Contato')


@app.route('/sustentavel')
def sustentavel():
    return render_template('sustentavel.html', title='Linha Sustentável')


@app.route('/classico')
def classico():
    return render_template('classico.html', title='Linha Clássico')


@app.route('/gold')
def gold():
    return render_template('gold.html', title='Linha Gold')


@app.route('/receitas')
def receitas():
    receitas_list = get_all_receitas()
    return render_template('receitas.html', title='Receitas', receitas_list=receitas_list)


@app.route('/receitas/<slug_or_id>')
def receita_detail(slug_or_id):
    receita = get_receita_by_slug(slug_or_id)
    if not receita and slug_or_id.isdigit():
        receita = get_receita_by_id(slug_or_id)
    if not receita:
        return render_template('receitas.html', title='Receitas', receitas_list=get_all_receitas(), not_found=True), 404
    return render_template('receita_detail.html', title=receita.get('titulo') or 'Receita', receita=receita)


# ---------- Status do banco (diagnóstico) ----------

@app.route('/api/db-status')
def api_db_status():
    """Retorna status do banco (sqlite). Útil para validar ambiente."""
    try:
        backend = get_db_backend()
        return jsonify({'ok': True, 'backend': backend})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/uploads-status')
def api_uploads_status():
    """Diagnóstico: pasta de upload de receitas e arquivos existentes."""
    folder = app.config['UPLOAD_FOLDER']
    exists = os.path.isdir(folder)
    try:
        files = os.listdir(folder) if exists else []
    except OSError:
        files = []
    # URL base que o Flask usa para static (ex.: /static/uploads/receitas/xxx)
    static_url_example = url_for('static', filename='uploads/receitas/x.jpg').rstrip('x.jpg') if exists else None
    return jsonify({
        'upload_folder': folder,
        'folder_exists': exists,
        'file_count': len(files),
        'files': files[:20],
        'static_url_prefix': static_url_example,
    })


# ---------- API Leads (formulário WhatsApp) ----------

@app.route('/api/leads', methods=['POST'])
def api_leads():
    data = request.get_json() or request.form
    nome = (data.get('nome') or '').strip()
    telefone = (data.get('telefone') or '').strip()
    email = (data.get('email') or '').strip()
    mensagem = (data.get('mensagem') or '').strip()
    origem = (data.get('origem') or 'whatsapp').strip() or 'whatsapp'

    if not nome or not telefone or not email:
        return jsonify({'ok': False, 'error': 'Nome, telefone e e-mail são obrigatórios.'}), 400

    try:
        lead_id = insert_lead(nome, telefone, email, mensagem, origem)
        return jsonify({'ok': True, 'id': lead_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ---------- Admin (login e listagem de leads) ----------

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin', methods=['GET'])
def admin_index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return redirect(url_for('admin_leads'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_leads'))

    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if not username or not password:
            error = 'Usuário e senha são obrigatórios.'
        else:
            admin = get_admin_by_username(username)
            if admin and check_password_hash(admin['password_hash'], password):
                if admin.get('ativo', 1) == 0:
                    error = 'Este usuário está inativo. Entre em contato com o administrador.'
                else:
                    session['admin_logged_in'] = True
                    session['admin_username'] = username
                    return redirect(url_for('admin_leads'))
            if not error:
                error = 'Usuário ou senha incorretos.'

    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboards')
@admin_required
def admin_dashboards():
    hoje = date.today()
    receitas_mes = count_receitas_por_mes(hoje.year, hoje.month)
    leads_mes = count_leads_por_mes(hoje.year, hoje.month)
    mes_nome = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')[hoje.month - 1]
    return render_template('admin/dashboards.html', receitas_mes=receitas_mes, leads_mes=leads_mes, mes_nome=mes_nome, ano=hoje.year)


@app.route('/admin/usuarios', methods=['GET', 'POST'])
@admin_required
def admin_usuarios():
    users = get_all_admin_users()
    error = None
    success = None

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            nome = (request.form.get('nome') or '').strip()
            username = (request.form.get('username') or '').strip().lower()
            email = (request.form.get('email') or '').strip()
            password = request.form.get('password') or ''
            ativo = request.form.get('ativo') == 'on'
            permissao = (request.form.get('permissao') or 'editor').strip().lower()
            if permissao not in ('admin', 'editor', 'visualizador'):
                permissao = 'editor'
            if not username:
                error = 'E-mail de acesso (usuário) é obrigatório.'
            elif not password or len(password) < 6:
                error = 'A senha deve ter no mínimo 6 caracteres.'
            else:
                existing = get_admin_by_username(username)
                if existing:
                    error = 'Já existe um usuário com este e-mail de acesso.'
                else:
                    password_hash = generate_password_hash(password, method='scrypt')
                    if insert_admin_user(username, password_hash, nome=nome or username, email=email, ativo=ativo, permissao=permissao):
                        success = 'Usuário criado com sucesso.'
                        users = get_all_admin_users()
                    else:
                        error = 'Não foi possível criar o usuário.'
        elif action == 'alterar_permissao':
            uid = request.form.get('id')
            permissao = (request.form.get('permissao') or 'editor').strip().lower()
            if permissao not in ('admin', 'editor', 'visualizador'):
                permissao = 'editor'
            if uid and uid.isdigit():
                update_admin_user(int(uid), permissao=permissao)
                success = 'Permissão atualizada.'
                users = get_all_admin_users()
        elif action == 'toggle_ativo':
            uid = request.form.get('id')
            if uid and uid.isdigit():
                u = next((x for x in users if str(x.get('id')) == uid), None)
                if u:
                    new_ativo = not (u.get('ativo', 1) == 1)
                    set_admin_ativo(int(uid), new_ativo)
                    success = 'Status atualizado.'
                    users = get_all_admin_users()
        elif action == 'delete':
            uid = request.form.get('id')
            if uid and uid.isdigit():
                if delete_admin_user(int(uid)):
                    success = 'Usuário excluído.'
                    users = get_all_admin_users()
                else:
                    error = 'Não é possível excluir o último usuário do painel.'
            else:
                error = 'Usuário não encontrado.'

    permissoes_list = [('admin', 'Administrador'), ('editor', 'Editor'), ('visualizador', 'Visualizador')]
    return render_template('admin/usuarios.html', users=users, error=error, success=success, permissoes_list=permissoes_list)


@app.route('/admin/leads')
@admin_required
def admin_leads():
    leads = get_all_leads()
    return render_template('admin/leads.html', leads=leads)


@app.route('/admin/receitas', methods=['GET', 'POST'])
@admin_required
def admin_receitas():
    if request.method == 'POST':
        titulo = (request.form.get('titulo') or '').strip()
        ingredientes = (request.form.get('ingredientes') or '').strip()
        conteudo = (request.form.get('conteudo') or '').strip()
        modo_preparo = (request.form.get('modo_preparo') or '').strip()
        if not titulo:
            return render_template('admin/receitas.html', receitas_list=get_all_receitas(), error='Título é obrigatório.')
        f = request.files.get('imagem_destaque')
        if not f or not f.filename:
            return render_template('admin/receitas.html', receitas_list=get_all_receitas(), error='Imagem de destaque é obrigatória. Selecione uma imagem para publicar a receita.')
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext in UNSUPPORTED_IMAGE_EXTENSIONS:
            return render_template('admin/receitas.html', receitas_list=get_all_receitas(), error='Formato HEIC/HEIF (fotos do iPhone) não é suportado. Converta para JPG ou PNG no celular (Configurações > Câmera > Formatos > Mais compatível) ou use um conversor online antes de enviar.')
        if not allowed_file(f.filename):
            return render_template('admin/receitas.html', receitas_list=get_all_receitas(), error='Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.')
        imagem_path = None
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(filepath)
            if not os.path.isfile(filepath):
                return render_template('admin/receitas.html', receitas_list=get_all_receitas(), error='A imagem não foi gravada no disco. Verifique permissões da pasta static/uploads/receitas.')
            imagem_path = "uploads/receitas/" + filename
        except Exception as e:
            return render_template('admin/receitas.html', receitas_list=get_all_receitas(), error=f'Não foi possível salvar a imagem. Tente novamente. ({e})')
        video_url = (request.form.get('video_url') or '').strip() or None
        video_arquivo = None
        fvideo = request.files.get('video_destaque')
        if fvideo and fvideo.filename and allowed_video_file(fvideo.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            ext = fvideo.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            fvideo.save(filepath)
            video_arquivo = f"uploads/receitas/{filename}"
        insert_receita(titulo, ingredientes, conteudo, modo_preparo, imagem_path, video_url, video_arquivo)
        return redirect(url_for('admin_receitas'))
    return render_template('admin/receitas.html', receitas_list=get_all_receitas())


@app.route('/admin/receitas/editar/<receita_id>', methods=['GET', 'POST'])
@admin_required
def admin_receita_editar(receita_id):
    receita = get_receita_by_id(receita_id)
    if not receita:
        return redirect(url_for('admin_receitas'))
    if request.method == 'POST':
        titulo = (request.form.get('titulo') or '').strip()
        ingredientes = (request.form.get('ingredientes') or '').strip()
        conteudo = (request.form.get('conteudo') or '').strip()
        modo_preparo = (request.form.get('modo_preparo') or '').strip()
        if not titulo:
            receita_json = json.dumps({'conteudo': receita.get('conteudo') or '', 'modo_preparo': receita.get('modo_preparo') or ''}).replace('</script>', '<\\/script>')
            return render_template('admin/receita_editar.html', receita=receita, receita_json=receita_json, error='Título é obrigatório.')
        imagem_path = request.form.get('imagem_destaque_atual') or receita.get('imagem_destaque')
        f = request.files.get('imagem_destaque')
        if f and f.filename:
            ext_edit = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
            if ext_edit in UNSUPPORTED_IMAGE_EXTENSIONS:
                receita_json = json.dumps({'conteudo': receita.get('conteudo') or '', 'modo_preparo': receita.get('modo_preparo') or ''}).replace('</script>', '<\\/script>')
                return render_template('admin/receita_editar.html', receita=receita, receita_json=receita_json, error='Formato HEIC/HEIF não é suportado. Converta a imagem para JPG ou PNG antes de enviar.')
        if f and f.filename and allowed_file(f.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(filepath)
            if os.path.isfile(filepath):
                imagem_path = f"uploads/receitas/{filename}"
        video_url = (request.form.get('video_url') or '').strip() or None
        video_arquivo = request.form.get('video_arquivo_atual') or receita.get('video_arquivo')
        if not video_arquivo:
            video_arquivo = None
        fvideo = request.files.get('video_destaque')
        if fvideo and fvideo.filename and allowed_video_file(fvideo.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            ext = fvideo.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            fvideo.save(filepath)
            video_arquivo = f"uploads/receitas/{filename}"
        update_receita(receita_id, titulo, ingredientes, conteudo, modo_preparo, imagem_path, video_url, video_arquivo)
        return redirect(url_for('admin_receitas'))
    receita_json = json.dumps({
        'conteudo': receita.get('conteudo') or '',
        'modo_preparo': receita.get('modo_preparo') or '',
    }).replace('</script>', '<\\/script>')
    return render_template('admin/receita_editar.html', receita=receita, receita_json=receita_json)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
