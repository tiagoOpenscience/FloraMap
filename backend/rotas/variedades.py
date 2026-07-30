"""Rotas da API relacionadas a Variedade."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.servicos import variedade_servico

bp = Blueprint("variedades", __name__, url_prefix="/api/variedades")


@bp.get("")
def listar() -> Any:
    variedades = variedade_servico.listar_variedades()
    return jsonify(variedades)


@bp.post("")
def criar() -> Any:
    dados = request.get_json(silent=True) or {}
    nome = dados.get("nome", "")
    cor = dados.get("cor", "")

    try:
        variedade = variedade_servico.criar_variedade(nome, cor)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(variedade), 201


@bp.patch("/<int:variedade_id>")
def atualizar(variedade_id: int) -> Any:
    dados = request.get_json(silent=True) or {}

    try:
        variedade = variedade_servico.atualizar_variedade(variedade_id, dados)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(variedade)
