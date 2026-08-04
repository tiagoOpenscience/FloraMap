"""Rotas da API relacionadas a Ponto de Acesso (entrada/saída da propriedade)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.servicos import ponto_acesso_servico

bp = Blueprint("pontos_acesso", __name__, url_prefix="/api")


@bp.post("/projetos/<int:projeto_id>/pontos-acesso")
def criar(projeto_id: int) -> Any:
    dados = request.get_json(silent=True) or {}
    tipo = dados.get("tipo")

    try:
        x = float(dados.get("x"))
        y = float(dados.get("y"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Coordenadas inválidas."}), 400

    try:
        ponto = ponto_acesso_servico.criar_ponto_acesso(projeto_id, tipo, x, y)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(ponto), 201


@bp.delete("/pontos-acesso/<int:ponto_id>")
def excluir(ponto_id: int) -> Any:
    try:
        ponto_acesso_servico.excluir_ponto_acesso(ponto_id)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404

    return "", 204
