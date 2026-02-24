"""
Aplicação Flask principal - Vida Arroz
"""
import os
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database import init_db, insert_lead, get_all_leads, get_admin_by_username, create_admin_if_empty

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui-altere-em-producao')

# Senha padrão do admin (altere em produção via ADMIN_PASSWORD)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'vidaarroz2026')


_db_initialized = False

@app.before_request
def setup_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        create_admin_if_empty(ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD, method='scrypt'))
        _db_initialized = True


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
                session['admin_logged_in'] = True
                session['admin_username'] = username
                return redirect(url_for('admin_leads'))
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
    return render_template('admin/dashboards.html')


@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    return render_template('admin/usuarios.html')


@app.route('/admin/leads')
@admin_required
def admin_leads():
    leads = get_all_leads()
    return render_template('admin/leads.html', leads=leads)


@app.route('/admin/blog')
@admin_required
def admin_blog():
    return render_template('admin/blog.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
