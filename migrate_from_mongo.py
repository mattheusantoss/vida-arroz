"""
Script único: copia receitas do MongoDB para o SQLite (data/vidaarroz.db).
Use se você ainda tem o MongoDB com a coleção 'receitas' e quer recuperar as receitas.

Como usar:
  1. Tenha o MongoDB rodando (ou defina MONGODB_URI).
  2. pip install pymongo   (se ainda não tiver)
  3. python migrate_from_mongo.py

Variáveis de ambiente (opcionais):
  MONGODB_URI     - ex.: mongodb://localhost:27017 (padrão)
  MONGODB_DB_NAME - nome do banco; padrão: vidaarroz
"""
import os
import sys

def main():
    try:
        from pymongo import MongoClient
    except ImportError:
        print("Instale o pymongo: pip install pymongo")
        sys.exit(1)

    from database import init_db, insert_receita, get_all_receitas, DB_PATH

    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGODB_DB_NAME", "vidaarroz")

    print("Conectando ao MongoDB:", uri)
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as e:
        print("MongoDB não acessível:", e)
        print("Verifique se o MongoDB está rodando ou ajuste MONGODB_URI.")
        sys.exit(2)

    db = client[db_name]
    col = db.get_collection("receitas")
    docs = list(col.find({}))
    print("Receitas no MongoDB:", len(docs))

    if not docs:
        print("Nenhuma receita no MongoDB. Nada a migrar.")
        return

    init_db()
    existentes = len(get_all_receitas())
    print("Receitas já no SQLite (antes):", existentes)
    print("SQLite em:", DB_PATH)

    for i, doc in enumerate(docs):
        titulo = (doc.get("titulo") or "").strip() or "Receita sem título"
        slug = doc.get("slug") or ""
        ingredientes = doc.get("ingredientes") or ""
        conteudo = doc.get("conteudo") or ""
        modo_preparo = doc.get("modo_preparo") or ""
        imagem_destaque = doc.get("imagem_destaque") or ""
        video_url = doc.get("video_url") or ""
        video_arquivo = doc.get("video_arquivo") or ""
        created_at = doc.get("created_at")  # pode ser datetime ou str

        rid = insert_receita(
            titulo=titulo,
            ingredientes=ingredientes,
            conteudo=conteudo,
            modo_preparo=modo_preparo,
            imagem_destaque=imagem_destaque or None,
            video_url=video_url or None,
            video_arquivo=video_arquivo or None,
            created_at=created_at,
        )
        if rid:
            print("  Migrada:", titulo[:50], "-> id", rid)
        else:
            print("  Falha ao inserir:", titulo[:50])

    print("Migração concluída. Receitas no SQLite agora:", len(get_all_receitas()))


if __name__ == "__main__":
    main()
