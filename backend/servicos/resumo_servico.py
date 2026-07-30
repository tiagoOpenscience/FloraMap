"""Regras de negócio para o resumo (Visão Geral) de um Projeto.

Reúne contagens agregadas — total de estufas, total de áreas e a
distribuição de áreas por variedade — usadas no painel de Visão Geral.
"""

from __future__ import annotations

from typing import Any

from backend import banco


def obter_resumo(projeto_id: int) -> dict[str, Any]:
    with banco.get_conexao() as conexao:
        total_estufas = conexao.execute(
            "SELECT COUNT(*) AS total FROM estufa WHERE projeto_id = ?",
            (projeto_id,),
        ).fetchone()["total"]

        total_areas = conexao.execute(
            """
            SELECT COUNT(*) AS total
            FROM area
            JOIN estufa ON estufa.id = area.estufa_id
            WHERE estufa.projeto_id = ?
            """,
            (projeto_id,),
        ).fetchone()["total"]

        linhas = conexao.execute(
            """
            SELECT
                area.variedade_id,
                variedade.nome AS variedade_nome,
                variedade.cor AS variedade_cor,
                COUNT(area.id) AS quantidade
            FROM area
            JOIN estufa ON estufa.id = area.estufa_id
            LEFT JOIN variedade ON variedade.id = area.variedade_id
            WHERE estufa.projeto_id = ?
            GROUP BY area.variedade_id
            ORDER BY quantidade DESC
            """,
            (projeto_id,),
        ).fetchall()

    areas_por_variedade = []
    for linha in linhas:
        item = dict(linha)
        if item["variedade_id"] is None:
            item["variedade_nome"] = "Sem variedade definida"
            item["variedade_cor"] = None
        areas_por_variedade.append(item)

    return {
        "total_estufas": total_estufas,
        "total_areas": total_areas,
        "areas_por_variedade": areas_por_variedade,
    }
