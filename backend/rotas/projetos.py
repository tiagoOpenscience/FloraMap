"""Rotas da API relacionadas a Projeto."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.servicos import estufa_servico, projeto_servico, resumo_servico

bp = Blueprint("projetos", __name__, url_prefix="/api/projetos")


@bp.get("")
def listar() -> Any:
    projetos = projeto_servico.listar_projetos()
    return jsonify(projetos)


@bp.post("")
def criar() -> Any:
    dados = request.get_json(silent=True) or {}
    nome = dados.get("nome", "")

    try:
        projeto = projeto_servico.criar_projeto(nome)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(projeto), 201


@bp.get("/<int:projeto_id>")
def obter(projeto_id: int) -> Any:
    projeto = projeto_servico.obter_projeto(projeto_id)
    if projeto is None:
        return jsonify({"erro": "Projeto não encontrado."}), 404

    projeto["estufas"] = estufa_servico.listar_estufas(projeto_id)
    return jsonify(projeto)


@bp.post("/<int:projeto_id>/imagem")
def enviar_imagem(projeto_id: int) -> Any:
    arquivo = request.files.get("imagem")
    if arquivo is None:
        return jsonify({"erro": "Nenhum arquivo de imagem enviado."}), 400

    try:
        imagem_path = projeto_servico.salvar_imagem_projeto(projeto_id, arquivo)
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify({"imagem_path": imagem_path})


@bp.patch("/<int:projeto_id>")
def atualizar(projeto_id: int) -> Any:
    dados = request.get_json(silent=True) or {}

    try:
        projeto = projeto_servico.atualizar_projeto(projeto_id, dados)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404
    except ValueError as erro:
        return jsonify({"erro": str(erro)}), 400

    return jsonify(projeto)


@bp.get("/<int:projeto_id>/resumo")
def resumo(projeto_id: int) -> Any:
    projeto = projeto_servico.obter_projeto(projeto_id)
    if projeto is None:
        return jsonify({"erro": "Projeto não encontrado."}), 404

    return jsonify(resumo_servico.obter_resumo(projeto_id))


@bp.delete("/<int:projeto_id>")
def excluir(projeto_id: int) -> Any:
    try:
        projeto_servico.excluir_projeto(projeto_id)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404

    return "", 204
