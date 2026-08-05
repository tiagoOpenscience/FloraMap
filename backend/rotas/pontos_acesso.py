"""Rotas da API relacionadas a Ponto de Acesso (entrada/saída, por aresta de estufa)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.servicos import ponto_acesso_servico

bp = Blueprint("pontos_acesso", __name__, url_prefix="/api")


@bp.post("/estufas/<int:estufa_id>/pontos-acesso")
def criar(estufa_id: int) -> Any:
    dados = request.get_json(silent=True) or {}
    tipo = dados.get("tipo")

    try:
        indice_aresta = int(dados.get("indice_aresta"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Índice de aresta inválido."}), 400

    try:
        ponto = ponto_acesso_servico.criar_ponto_acesso(estufa_id, tipo, indice_aresta)
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
