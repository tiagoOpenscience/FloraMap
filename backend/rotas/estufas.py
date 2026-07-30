"""Rotas da API relacionadas a Estufa."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.servicos import estufa_servico

bp = Blueprint("estufas", __name__, url_prefix="/api")


def _converter_pontos(lista_bruta: Any) -> list[tuple[float, float]]:
    """Converte uma lista de {"x":..,"y":..} em tuplas (x, y) float."""
    pontos = []
    for item in lista_bruta or []:
        pontos.append((float(item["x"]), float(item["y"])))
    return pontos


@bp.get("/projetos/<int:projeto_id>/estufas")
def listar(projeto_id: int) -> Any:
    estufas = estufa_servico.listar_estufas(projeto_id)
    return jsonify(estufas)


@bp.post("/projetos/<int:projeto_id>/estufas")
def criar_manual(projeto_id: int) -> Any:
    """Cria uma Estufa a partir de um contorno desenhado manualmente."""
    dados = request.get_json(silent=True) or {}

    try:
        pontos = _converter_pontos(dados.get("poligono"))
    except (TypeError, ValueError, KeyError):
        return jsonify({"erro": "Polígono inválido."}), 400

    poligono = [{"x": x, "y": y} for x, y in pontos]

    try:
        estufa = estufa_servico.criar_estufa_manual(projeto_id, poligono)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(estufa), 201


@bp.post("/projetos/<int:projeto_id>/detectar")
def detectar(projeto_id: int) -> Any:
    dados = request.get_json(silent=True) or {}

    try:
        pontos_amostra = _converter_pontos(dados.get("amostras"))
    except (TypeError, ValueError, KeyError):
        return jsonify({"erro": "Coordenadas de amostra inválidas."}), 400

    try:
        estufas = estufa_servico.detectar_estufas_projeto(projeto_id, pontos_amostra)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(estufas)


@bp.patch("/estufas/<int:estufa_id>")
def atualizar(estufa_id: int) -> Any:
    dados = request.get_json(silent=True) or {}

    try:
        estufa = estufa_servico.atualizar_estufa(estufa_id, dados)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(estufa)


@bp.delete("/estufas/<int:estufa_id>")
def excluir(estufa_id: int) -> Any:
    try:
        estufa_servico.excluir_estufa(estufa_id)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404

    return "", 204


@bp.post("/projetos/<int:projeto_id>/estufas/restaurar")
def restaurar(projeto_id: int) -> Any:
    dados = request.get_json(silent=True) or {}
    estufas_snapshot = dados.get("estufas")

    if not isinstance(estufas_snapshot, list):
        return jsonify({"erro": "Envie a lista de estufas a restaurar."}), 400

    try:
        estufas = estufa_servico.restaurar_estufas(projeto_id, estufas_snapshot)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except (KeyError, TypeError):
        return jsonify({"erro": "Dados de restauração inválidos."}), 400

    return jsonify(estufas)


@bp.post("/estufas/<int:estufa_id>/dividir")
def dividir(estufa_id: int) -> Any:
    """Divide (split) uma estufa detectada por engano como um bloco só."""
    dados = request.get_json(silent=True) or {}
    quantidade = dados.get("quantidade")
    orientacao = dados.get("orientacao", "auto")

    try:
        quantidade_int = int(quantidade)
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe uma quantidade de partes válida."}), 400

    try:
        estufas = estufa_servico.dividir_estufa(estufa_id, quantidade_int, orientacao)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(estufas)
