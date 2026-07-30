"""Regras de negócio relacionadas a Área.

Geração automática de áreas: divide o polígono real da estufa (não
apenas seu bounding box) em N partes iguais, recortadas para dentro do
contorno — ver backend/servicos/geometria.py para o algoritmo.
"""

from __future__ import annotations

import json
from typing import Any

from backend import banco
from backend.servicos import estufa_servico, geometria

CAMPOS_EDITAVEIS = {"variedade_id", "fase", "vaos", "canteiros", "postinhos"}

_SQL_AREA_COM_VARIEDADE = """
    SELECT
        area.id, area.estufa_id, area.variedade_id, area.fase, area.vaos,
        area.canteiros, area.postinhos, area.poligono, area.ordem,
        variedade.nome AS variedade_nome, variedade.cor AS variedade_cor
    FROM area
    LEFT JOIN variedade ON variedade.id = area.variedade_id
"""


def _linha_para_dict(linha: Any) -> dict[str, Any]:
    area = dict(linha)
    area["poligono"] = json.loads(area["poligono"])
    return area


def listar_areas(estufa_id: int) -> list[dict[str, Any]]:
    with banco.get_conexao() as conexao:
        linhas = conexao.execute(
            f"{_SQL_AREA_COM_VARIEDADE} WHERE area.estufa_id = ? ORDER BY area.ordem ASC",
            (estufa_id,),
        ).fetchall()
    return [_linha_para_dict(linha) for linha in linhas]


def obter_area(area_id: int) -> dict[str, Any] | None:
    with banco.get_conexao() as conexao:
        linha = conexao.execute(
            f"{_SQL_AREA_COM_VARIEDADE} WHERE area.id = ?", (area_id,)
        ).fetchone()
    return _linha_para_dict(linha) if linha else None


def gerar_areas(
    estufa_id: int, quantidade: int, orientacao: str = "auto"
) -> list[dict[str, Any]]:
    if quantidade < 1:
        raise ValueError("A quantidade de áreas deve ser pelo menos 1.")
    if orientacao not in ("auto", "vertical", "horizontal"):
        raise ValueError("Orientação inválida (use auto, vertical ou horizontal).")

    estufa = estufa_servico.obter_estufa(estufa_id)
    if estufa is None:
        raise LookupError("Estufa não encontrada.")

    poligonos = geometria.dividir_poligono(estufa["poligono"], quantidade, orientacao)
    if not poligonos:
        raise ValueError("Não foi possível gerar áreas para esta estufa.")

    with banco.get_conexao() as conexao:
        conexao.execute("DELETE FROM area WHERE estufa_id = ?", (estufa_id,))
        for indice, poligono in enumerate(poligonos, start=1):
            conexao.execute(
                "INSERT INTO area (estufa_id, poligono, ordem) VALUES (?, ?, ?)",
                (estufa_id, json.dumps(poligono), indice),
            )
        conexao.execute(
            "UPDATE estufa SET quantidade_areas = ?, orientacao_areas = ? WHERE id = ?",
            (len(poligonos), orientacao, estufa_id),
        )
        conexao.commit()

    return listar_areas(estufa_id)


def excluir_area(area_id: int) -> None:
    area = obter_area(area_id)
    if area is None:
        raise LookupError("Área não encontrada.")

    with banco.get_conexao() as conexao:
        conexao.execute("DELETE FROM area WHERE id = ?", (area_id,))
        conexao.commit()


def atualizar_area(area_id: int, campos: dict[str, Any]) -> dict[str, Any]:
    area_existente = obter_area(area_id)
    if area_existente is None:
        raise LookupError("Área não encontrada.")

    dados_validos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS}
    if not dados_validos:
        raise ValueError("Nenhum campo válido para atualizar.")

    if "variedade_id" in dados_validos and dados_validos["variedade_id"] is not None:
        with banco.get_conexao() as conexao:
            existe = conexao.execute(
                "SELECT id FROM variedade WHERE id = ?",
                (dados_validos["variedade_id"],),
            ).fetchone()
        if existe is None:
            raise ValueError("Variedade não encontrada.")

    set_clause = ", ".join(f"{campo} = ?" for campo in dados_validos)
    valores = list(dados_validos.values()) + [area_id]

    with banco.get_conexao() as conexao:
        conexao.execute(f"UPDATE area SET {set_clause} WHERE id = ?", valores)
        conexao.commit()

    area_atualizada = obter_area(area_id)
    assert area_atualizada is not None
    return area_atualizada
