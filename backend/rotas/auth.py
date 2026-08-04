"""Rotas da API relacionadas à autenticação (senha única compartilhada).

Não há contas por usuário — todo o time compartilha a mesma senha,
configurada no servidor via variável de ambiente `FLORAMAP_SENHA_HASH`
(hash gerado com `werkzeug.security.generate_password_hash`). Ver
DEPLOY.md para como gerar e configurar esse hash.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/login")
def login() -> Any:
    dados = request.get_json(silent=True) or {}
    senha = dados.get("senha", "")

    hash_configurado = os.environ.get("FLORAMAP_SENHA_HASH", "")
    if not hash_configurado:
        return jsonify({"erro": "Senha de acesso não configurada no servidor."}), 500

    if not senha or not check_password_hash(hash_configurado, senha):
        return jsonify({"erro": "Senha incorreta."}), 401

    session.permanent = True
    session["autenticado"] = True
    return jsonify({"ok": True})


@bp.post("/logout")
def logout() -> Any:
    session.clear()
    return jsonify({"ok": True})
