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
    init_db,
    insert_lead,
    get_all_leads,
    get_admin_by_username,
    create_admin_if_empty,
    get_all_receitas,
    get_receita_by_id,
    get_receita_by_slug,
    insert_receita,
    update_receita,
    get_db_backend,
    get_all_admin_users,
    insert_admin_user,
    update_admin_user,
    set_admin_ativo,
    delete_admin_user,
    count_receitas_por_mes,
    count_leads_por_mes,
    get_all_produtos,
    get_produto_by_id,
    insert_produto,
    update_produto,
    set_produto_ativo,
    delete_produto,
    insert_visita,
    count_visitas_por_mes,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui-altere-em-producao')

# Upload de imagens e vídeos (receitas)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'receitas')
PRODUTOS_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'produtos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
# HEIC (fotos do iPhone) não é suportado na web; o usuário deve converter para JPG/PNG
UNSUPPORTED_IMAGE_EXTENSIONS = {'heic', 'heif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'ogg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB (para vídeos)

# Garantir que a pasta de upload existe desde o início (evita salvar em outro lugar)
for folder in (UPLOAD_FOLDER, PRODUTOS_UPLOAD_FOLDER):
    try:
        os.makedirs(folder, exist_ok=True)
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
    Também registra visita para rotas públicas.
    """
    global _db_initialized
    if not _db_initialized:
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

    # Registrar visita apenas para páginas públicas (não admin, não static)
    try:
        if (
            request.method == 'GET'
            and request.endpoint
            and not request.endpoint.startswith('admin_')
            and request.endpoint != 'static'
        ):
            insert_visita(request.path)
    except Exception:
        # Não impacta a navegação se contar visita falhar
        pass


# ---------- Rotas públicas ----------

@app.route('/')
def index():
    produtos_list = get_all_produtos(ativos_apenas=True)
    return render_template('index.html', title='Home', produtos_list=produtos_list)


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
    visitas_mes = count_visitas_por_mes(hoje.year, hoje.month)
    return render_template(
        'admin/dashboards.html',
        receitas_mes=receitas_mes,
        leads_mes=leads_mes,
        visitas_mes=visitas_mes,
        mes_nome=mes_nome,
        ano=hoje.year,
    )


@app.route('/admin/usuarios', methods=['GET', 'POST'])
@admin_required
def admin_usuarios():
    users = get_all_admin_users()
    error = None
    success = None

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'alterar_permissao':
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


@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@admin_required
def admin_usuarios_novo():
    error = None
    success = None
    editar_id = request.args.get('editar')
    usuario = None
    if editar_id and editar_id.isdigit():
        uid = int(editar_id)
        usuario = next((u for u in get_all_admin_users() if u.get('id') == uid), None)
    if request.method == 'POST':
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
        elif not usuario and (not password or len(password) < 6):
            error = 'A senha deve ter no mínimo 6 caracteres para novos usuários.'
        else:
            existing = get_admin_by_username(username)
            if existing and (not usuario or existing['id'] != usuario.get('id')):
                error = 'Já existe um usuário com este e-mail de acesso.'
            else:
                try:
                    if usuario:
                        # Atualizar usuário existente (sem alterar senha aqui)
                        update_admin_user(usuario['id'], nome=nome or username, email=email or None, ativo=ativo, permissao=permissao)
                        success = 'Usuário atualizado com sucesso.'
                    else:
                        password_hash = generate_password_hash(password, method='scrypt')
                        if insert_admin_user(username, password_hash, nome=nome or username, email=email or None, ativo=ativo, permissao=permissao):
                            success = 'Usuário criado com sucesso.'
                        else:
                            error = 'Não foi possível criar o usuário.'
                except Exception as e:
                    error = f'Não foi possível salvar o usuário. Tente novamente. ({e})'
    permissoes_list = [('admin', 'Administrador'), ('editor', 'Editor'), ('visualizador', 'Visualizador')]
    return render_template('admin/usuario_novo.html', error=error, success=success, usuario=usuario, permissoes_list=permissoes_list)


@app.route('/admin/produtos', methods=['GET', 'POST'])
@admin_required
def admin_produtos():
    produtos = get_all_produtos(ativos_apenas=False)
    error = None
    success = None

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_imagem':
            produto_id = request.form.get('id')
            f = request.files.get('imagem_destaque')
            if produto_id and produto_id.isdigit() and f and f.filename:
                if not allowed_file(f.filename):
                    error = 'Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.'
                else:
                    try:
                        ext = f.filename.rsplit('.', 1)[1].lower()
                        if ext in UNSUPPORTED_IMAGE_EXTENSIONS:
                            error = 'Formato HEIC/HEIF não é suportado. Converta para JPG ou PNG antes de enviar.'
                        else:
                            filename = f"{uuid.uuid4().hex}.{ext}"
                            filepath = os.path.join(PRODUTOS_UPLOAD_FOLDER, filename)
                            f.save(filepath)
                            imagem_path = f"uploads/produtos/{filename}"
                            if update_produto(int(produto_id), imagem_destaque=imagem_path):
                                success = 'Imagem atualizada.'
                                produtos = get_all_produtos(ativos_apenas=False)
                            else:
                                error = 'Não foi possível atualizar a imagem.'
                    except Exception as e:
                        error = f'Não foi possível salvar a nova imagem. Tente novamente. ({e})'
        elif action == 'toggle_ativo':
            produto_id = request.form.get('id')
            if produto_id and produto_id.isdigit():
                p = next((x for x in produtos if str(x.get('id')) == produto_id), None)
                if p:
                    novo_ativo = not bool(p.get('ativo'))
                    set_produto_ativo(int(produto_id), novo_ativo)
                    success = 'Status atualizado.'
                    produtos = get_all_produtos(ativos_apenas=False)
        elif action == 'delete':
            produto_id = request.form.get('id')
            if produto_id and produto_id.isdigit():
                if delete_produto(int(produto_id)):
                    success = 'Produto excluído.'
                    produtos = get_all_produtos(ativos_apenas=False)
                else:
                    error = 'Não foi possível excluir o produto.'

    return render_template('admin/produtos.html', produtos=produtos, error=error, success=success)


@app.route('/admin/produtos/novo', methods=['GET', 'POST'])
@admin_required
def admin_produtos_novo():
    error = None
    success = None
    editar_id = request.args.get('editar')
    produto = None
    if editar_id and editar_id.isdigit():
        produto = get_produto_by_id(int(editar_id))
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        descricao = (request.form.get('descricao') or '').strip()
        pagina = (request.form.get('pagina') or '').strip()
        ativo = request.form.get('ativo') == 'on'
        f = request.files.get('imagem_destaque')
        if not nome:
            error = 'Nome do produto é obrigatório.'
        elif not produto and (not f or not f.filename):
            error = 'Imagem de destaque é obrigatória.'
        elif f and f.filename and not allowed_file(f.filename):
            error = 'Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.'
        else:
            try:
                imagem_path = produto.get('imagem_destaque') if produto else None
                if f and f.filename:
                    ext = f.filename.rsplit('.', 1)[1].lower()
                    if ext in UNSUPPORTED_IMAGE_EXTENSIONS:
                        error = 'Formato HEIC/HEIF não é suportado. Converta para JPG ou PNG antes de enviar.'
                    else:
                        filename = f"{uuid.uuid4().hex}.{ext}"
                        filepath = os.path.join(PRODUTOS_UPLOAD_FOLDER, filename)
                        f.save(filepath)
                        imagem_path = f"uploads/produtos/{filename}"
                if not error:
                    if produto:
                        update_produto(produto['id'], nome=nome, descricao=descricao, imagem_destaque=imagem_path, ativo=ativo, pagina=pagina or None)
                        success = 'Produto atualizado com sucesso.'
                    else:
                        if insert_produto(nome, descricao, imagem_path, ativo=ativo, pagina=pagina or None):
                            success = 'Produto criado com sucesso.'
                        else:
                            error = 'Não foi possível criar o produto.'
            except Exception as e:
                error = f'Não foi possível salvar a imagem. Tente novamente. ({e})'
    return render_template('admin/produto_novo.html', error=error, success=success, produto=produto)


@app.route('/admin/leads')
@admin_required
def admin_leads():
    leads = get_all_leads()
    return render_template('admin/leads.html', leads=leads)


@app.route('/admin/receitas')
@admin_required
def admin_receitas():
    return render_template('admin/receitas.html', receitas_list=get_all_receitas())


@app.route('/admin/receitas/nova', methods=['GET', 'POST'])
@admin_required
def admin_receita_nova():
    error = None
    if request.method == 'POST':
        titulo = (request.form.get('titulo') or '').strip()
        ingredientes = (request.form.get('ingredientes') or '').strip()
        conteudo = (request.form.get('conteudo') or '').strip()
        modo_preparo = (request.form.get('modo_preparo') or '').strip()
        if not titulo:
            error = 'Título é obrigatório.'
        else:
            f = request.files.get('imagem_destaque')
            if not f or not f.filename:
                error = 'Imagem de destaque é obrigatória. Selecione uma imagem para publicar a receita.'
            else:
                ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
                if ext in UNSUPPORTED_IMAGE_EXTENSIONS:
                    error = 'Formato HEIC/HEIF (fotos do iPhone) não é suportado. Converta para JPG ou PNG antes de enviar.'
                elif not allowed_file(f.filename):
                    error = 'Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.'
                else:
                    try:
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        filename = f"{uuid.uuid4().hex}.{ext}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        f.save(filepath)
                        if not os.path.isfile(filepath):
                            error = 'A imagem não foi gravada no disco. Verifique permissões da pasta static/uploads/receitas.'
                        else:
                            imagem_path = f"uploads/receitas/{filename}"
                            video_url = (request.form.get('video_url') or '').strip() or None
                            video_arquivo = None
                            fvideo = request.files.get('video_destaque')
                            if fvideo and fvideo.filename and allowed_video_file(fvideo.filename):
                                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                                vext = fvideo.filename.rsplit('.', 1)[1].lower()
                                vname = f"{uuid.uuid4().hex}.{vext}"
                                vpath = os.path.join(app.config['UPLOAD_FOLDER'], vname)
                                fvideo.save(vpath)
                                video_arquivo = f"uploads/receitas/{vname}"
                            insert_receita(titulo, ingredientes, conteudo, modo_preparo, imagem_path, video_url, video_arquivo)
                            return redirect(url_for('admin_receitas'))
                    except Exception as e:
                        error = f'Não foi possível salvar a imagem. Tente novamente. ({e})'
    return render_template('admin/receita_nova.html', error=error)


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
