# Vida Arroz - Aplicação Flask

Aplicação web desenvolvida com Flask, utilizando templates Jinja2 e estrutura organizada.

## 🚀 Estrutura do Projeto

```
.
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências do projeto
├── templates/            # Templates Jinja2
│   ├── base.html         # Template base
│   ├── index.html        # Página inicial
│   └── sobre.html        # Página sobre
├── static/               # Arquivos estáticos
│   ├── css/              # Estilos CSS
│   │   └── style.css
│   ├── js/               # JavaScript
│   │   └── main.js
│   └── images/           # Imagens
└── venv/                 # Ambiente virtual (não versionado)
```

## 📦 Instalação

1. Clone o repositório ou navegue até a pasta do projeto

2. Ative o ambiente virtual:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. Instale as dependências (se necessário):
   ```powershell
   pip install -r requirements.txt
   ```

## ▶️ Executando a Aplicação

Com o ambiente virtual ativado, execute:

```powershell
python app.py
```

A aplicação estará disponível em: `http://localhost:5000`

## 🛠️ Tecnologias Utilizadas

- **Flask 3.1.3** - Framework web
- **Jinja2 3.1.6** - Engine de templates
- **Werkzeug 3.1.6** - WSGI utilities
- **Pillow 12.1.1** - Processamento de imagens

## 📝 Desenvolvimento

### Adicionar uma nova rota

Edite `app.py` e adicione:

```python
@app.route('/nova-rota')
def nova_rota():
    return render_template('nova_pagina.html', title='Nova Página')
```

### Criar um novo template

1. Crie um arquivo em `templates/` (ex: `nova_pagina.html`)
2. Estenda o template base:

```html
{% extends "base.html" %}

{% block content %}
<h1>Conteúdo da nova página</h1>
{% endblock %}
```

### Adicionar arquivos estáticos

- **CSS**: Adicione em `static/css/` e referencie no template base
- **JavaScript**: Adicione em `static/js/` e referencie no template base
- **Imagens**: Adicione em `static/images/` e use `url_for('static', filename='images/nome.jpg')`

## 📄 Licença

Este projeto é de uso pessoal/educacional.
