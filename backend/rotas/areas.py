"""Rotas da API relacionadas a Área."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.servicos import area_servico

bp = Blueprint("areas", __name__, url_prefix="/api")


@bp.get("/estufas/<int:estufa_id>/areas")
def listar(estufa_id: int) -> Any:
    areas = area_servico.listar_areas(estufa_id)
    return jsonify(areas)


@bp.post("/estufas/<int:estufa_id>/gerar-areas")
def gerar(estufa_id: int) -> Any:
    dados = request.get_json(silent=True) or {}
    quantidade = dados.get("quantidade")
    orientacao = dados.get("orientacao", "auto")

    try:
        quantidade_int = int(quantidade)
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe uma quantidade de áreas válida."}), 400

    try:
        areas = area_servico.gerar_areas(estufa_id, quantidade_int, orientacao)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(areas)


@bp.patch("/areas/<int:area_id>")
def atualizar(area_id: int) -> Any:
    dados = request.get_json(silent=True) or {}

    try:
        area = area_servico.atualizar_area(area_id, dados)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(area)


@bp.delete("/areas/<int:area_id>")
def excluir(area_id: int) -> Any:
    try:
        area_servico.excluir_area(area_id)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404

    return "", 204
