"""Rotas de exportação (CSV e PDF) de um Projeto."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify

from backend.servicos import exportacao_servico

bp = Blueprint("exportacao", __name__, url_prefix="/api/projetos")


@bp.get("/<int:projeto_id>/exportar/csv")
def exportar_csv(projeto_id: int) -> Any:
    try:
        csv_texto = exportacao_servico.gerar_csv(projeto_id)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404

    return Response(
        csv_texto,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=floramap_projeto_{projeto_id}.csv"
        },
    )


@bp.get("/<int:projeto_id>/exportar/pdf")
def exportar_pdf(projeto_id: int) -> Any:
    try:
        pdf_bytes = exportacao_servico.gerar_pdf(projeto_id)
    except LookupError as erro:
        return jsonify({"erro": str(erro)}), 404

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=floramap_projeto_{projeto_id}.pdf"
        },
    )
