"""Aplicação Flask do FloraMap."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, request, send_from_directory, session

from backend import banco
from backend.rotas.areas import bp as areas_bp
from backend.rotas.auth import bp as auth_bp
from backend.rotas.estufas import bp as estufas_bp
from backend.rotas.exportacao import bp as exportacao_bp
from backend.rotas.pontos_acesso import bp as pontos_acesso_bp
from backend.rotas.projetos import bp as projetos_bp
from backend.rotas.variedades import bp as variedades_bp

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = BASE_DIR / "uploads"

# Únicas rotas acessíveis sem sessão autenticada: a própria tela/API de
# login e os arquivos estáticos que ela precisa para carregar.
CAMINHOS_PUBLICOS = {"/login.html", "/api/login"}
PREFIXOS_PUBLICOS = ("/css/", "/js/")


def criar_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = os.environ.get(
        "FLORAMAP_SECRET_KEY", "chave-de-desenvolvimento-nao-usar-em-producao"
    )
    app.permanent_session_lifetime = timedelta(days=30)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLORAMAP_COOKIE_SECURE") == "1"

    banco.inicializar_banco()

    app.register_blueprint(auth_bp)
    app.register_blueprint(projetos_bp)
    app.register_blueprint(estufas_bp)
    app.register_blueprint(areas_bp)
    app.register_blueprint(variedades_bp)
    app.register_blueprint(exportacao_bp)
    app.register_blueprint(pontos_acesso_bp)

    @app.before_request
    def exigir_autenticacao() -> Any:  # noqa: ANN401
        if request.path in CAMINHOS_PUBLICOS or request.path.startswith(PREFIXOS_PUBLICOS):
            return None
        if session.get("autenticado"):
            return None
        if request.path.startswith("/api/"):
            return jsonify({"erro": "Não autenticado."}), 401
        return redirect("/login.html")

    @app.get("/login.html")
    def tela_login() -> Any:  # noqa: ANN401
        return send_from_directory(FRONTEND_DIR, "login.html")

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
