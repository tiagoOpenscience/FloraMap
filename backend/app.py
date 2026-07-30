"""Aplicação Flask do FloraMap."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, send_from_directory

from backend import banco
from backend.rotas.areas import bp as areas_bp
from backend.rotas.estufas import bp as estufas_bp
from backend.rotas.exportacao import bp as exportacao_bp
from backend.rotas.projetos import bp as projetos_bp
from backend.rotas.variedades import bp as variedades_bp

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"


def criar_app() -> Flask:
    app = Flask(__name__)

    banco.inicializar_banco()

    app.register_blueprint(projetos_bp)
    app.register_blueprint(estufas_bp)
    app.register_blueprint(areas_bp)
    app.register_blueprint(variedades_bp)
    app.register_blueprint(exportacao_bp)

    @app.get("/")
    def home() -> Any:  # noqa: ANN401
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/projeto.html")
    def tela_projeto() -> Any:  # noqa: ANN401
        return send_from_directory(FRONTEND_DIR, "projeto.html")

    @app.get("/css/<path:caminho>")
    def servir_css(caminho: str) -> Any:  # noqa: ANN401
        return send_from_directory(FRONTEND_DIR / "css", caminho)

    @app.get("/js/<path:caminho>")
    def servir_js(caminho: str) -> Any:  # noqa: ANN401
        return send_from_directory(FRONTEND_DIR / "js", caminho)

    @app.get("/uploads/<path:caminho>")
    def servir_uploads(caminho: str) -> Any:  # noqa: ANN401
        return send_from_directory(UPLOADS_DIR, caminho)

    return app


if __name__ == "__main__":
    aplicacao = criar_app()
    aplicacao.run(debug=True, port=5000)
