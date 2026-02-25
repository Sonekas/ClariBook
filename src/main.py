import os
import logging

from flask import Flask, send_from_directory
from flask_cors import CORS

from src.models.user import db
from src.routes.user import user_bp
from src.routes.epub_processor import epub_bp


def create_app() -> Flask:
    base_dir = os.path.dirname(__file__)
    app = Flask(__name__, static_folder=os.path.join(base_dir, 'static'))

    # Secret key should come from environment in production; keep fallback for local dev
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    # Habilitar CORS para todas as rotas
    CORS(app)

    # Registrar blueprints
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(epub_bp, url_prefix='/api/epub')

    # Configuração de banco de dados SQLite (fallback local)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(base_dir, 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app


app = create_app()


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path: str):
    static_folder_path = app.static_folder
    if not static_folder_path:
        return "Static folder not configured", 404

    requested = os.path.join(static_folder_path, path)
    if path and os.path.exists(requested):
        return send_from_directory(static_folder_path, path)

    index_path = os.path.join(static_folder_path, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(static_folder_path, 'index.html')

    return "index.html not found", 404


@app.route('/api/health')
def health():
    return {
        "status": "ok",
        "backend": "hf",
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
