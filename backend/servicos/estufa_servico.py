"""Regras de negócio relacionadas a Estufa."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend import banco
from backend.detector.detector import detectar_estufas
from backend.servicos import geometria, projeto_servico

CAMPOS_EDITAVEIS = {"nome", "numero"}

_SQL_ESTUFA = """
    SELECT id, projeto_id, numero, nome, poligono, quantidade_areas,
           orientacao_areas, criado_em
    FROM estufa
"""

# Consulta duplicada intencionalmente aqui (em vez de reutilizar
# area_servico.listar_areas) para evitar import circular entre
# estufa_servico e area_servico — este módulo só precisa dos dados
# de área para compor a resposta de listar_estufas.
_SQL_AREAS_DA_ESTUFA = """
    SELECT
        area.id, area.estufa_id, area.variedade_id, area.fase, area.vaos,
        area.canteiros, area.postinhos, area.poligono, area.ordem,
        variedade.nome AS variedade_nome, variedade.cor AS variedade_cor
    FROM area
    LEFT JOIN variedade ON variedade.id = area.variedade_id
    WHERE area.estufa_id = ?
    ORDER BY area.ordem ASC
"""


def _areas_da_estufa(conexao: Any, estufa_id: int) -> list[dict[str, Any]]:
    linhas = conexao.execute(_SQL_AREAS_DA_ESTUFA, (estufa_id,)).fetchall()
    areas = []
    for linha in linhas:
        area = dict(linha)
        area["poligono"] = json.loads(area["poligono"])
        areas.append(area)
    return areas


def listar_estufas(projeto_id: int) -> list[dict[str, Any]]:
    with banco.get_conexao() as conexao:
        linhas = conexao.execute(
            f"{_SQL_ESTUFA} WHERE projeto_id = ? ORDER BY numero ASC",
            (projeto_id,),
        ).fetchall()

        estufas = []
        for linha in linhas:
            estufa = dict(linha)
            estufa["poligono"] = json.loads(estufa["poligono"])
            estufa["areas"] = _areas_da_estufa(conexao, estufa["id"])
            estufas.append(estufa)

    return estufas


def obter_estufa(estufa_id: int) -> dict[str, Any] | None:
    with banco.get_conexao() as conexao:
        linha = conexao.execute(f"{_SQL_ESTUFA} WHERE id = ?", (estufa_id,)).fetchone()

    if linha is None:
        return None

    estufa = dict(linha)
    estufa["poligono"] = json.loads(estufa["poligono"])
    return estufa


def detectar_estufas_projeto(
    projeto_id: int, pontos_amostra: list[tuple[float, float]] | None = None
) -> list[dict[str, Any]]:
    """Roda o detector sobre a imagem do projeto e substitui as estufas.

    Decisão de implementação (SPEC.md, regra de negócio 12): rodar a
    detecção novamente descarta as estufas atuais do projeto e as
    recria a partir do resultado do detector. Ajustes manuais feitos
    antes de uma nova detecção serão perdidos — o usuário é avisado
    disso na interface antes de confirmar a ação.

    Args:
        pontos_amostra: lista de coordenadas (x, y) em pixels da
            imagem, de pontos que o usuário clicou sobre estufas
            conhecidas (mais de um ponto ajuda em coberturas listradas
            ou com cor pouco uniforme), usados para calibrar a cor e o
            porte esperado das demais estufas.
    """
    projeto = projeto_servico.obter_projeto(projeto_id)
    if projeto is None:
        raise LookupError("Projeto não encontrado.")
    if not projeto["imagem_path"]:
        raise ValueError("Envie uma imagem antes de detectar as estufas.")

    nome_arquivo = Path(projeto["imagem_path"]).name
    caminho_absoluto = projeto_servico.UPLOADS_DIR / nome_arquivo
    poligonos = detectar_estufas(str(caminho_absoluto), pontos_amostra)

    with banco.get_conexao() as conexao:
        conexao.execute("DELETE FROM estufa WHERE projeto_id = ?", (projeto_id,))
        for indice, poligono in enumerate(poligonos, start=1):
            conexao.execute(
                """
                INSERT INTO estufa (projeto_id, numero, nome, poligono, quantidade_areas)
                VALUES (?, ?, ?, ?, 0)
                """,
                (projeto_id, indice, f"Estufa {indice}", json.dumps(poligono)),
            )
        conexao.commit()

    return listar_estufas(projeto_id)


def criar_estufa_manual(
    projeto_id: int, poligono: list[dict[str, float]]
) -> dict[str, Any]:
    """Cria uma Estufa a partir de um polígono desenhado manualmente."""
    projeto = projeto_servico.obter_projeto(projeto_id)
    if projeto is None:
        raise LookupError("Projeto não encontrado.")

    if len(poligono) < 3:
        raise ValueError("Um contorno de estufa precisa de pelo menos 3 pontos.")

    with banco.get_conexao() as conexao:
        maior_numero = conexao.execute(
            "SELECT COALESCE(MAX(numero), 0) AS maior FROM estufa WHERE projeto_id = ?",
            (projeto_id,),
        ).fetchone()["maior"]
        novo_numero = maior_numero + 1

        cursor = conexao.execute(
            """
            INSERT INTO estufa (projeto_id, numero, nome, poligono, quantidade_areas)
            VALUES (?, ?, ?, ?, 0)
            """,
            (projeto_id, novo_numero, f"Estufa {novo_numero}", json.dumps(poligono)),
        )
        conexao.commit()
        estufa_id = cursor.lastrowid

    estufa = obter_estufa(estufa_id)
    assert estufa is not None
    return estufa


def dividir_estufa(
    estufa_id: int, quantidade: int, orientacao: str = "auto"
) -> list[dict[str, Any]]:
    """Divide (split) uma Estufa detectada por engano como um bloco só.

    Substitui a Estufa original por `quantidade` novas Estufas, cada
    uma com uma fatia do polígono original. Útil quando a detecção
    automática juntou duas estufas vizinhas em um único contorno.

    As áreas já geradas para a Estufa original são perdidas (o
    polígono muda), assim como sua numeração — as novas Estufas
    recebem números sequenciais a partir do maior número já usado no
    projeto. O usuário é avisado disso na interface antes de confirmar.
    """
    if quantidade < 2:
        raise ValueError("Informe pelo menos 2 partes para dividir a estufa.")
    if orientacao not in ("auto", "vertical", "horizontal"):
        raise ValueError("Orientação inválida (use auto, vertical ou horizontal).")

    estufa = obter_estufa(estufa_id)
    if estufa is None:
        raise LookupError("Estufa não encontrada.")

    partes = geometria.dividir_poligono(estufa["poligono"], quantidade, orientacao)
    if len(partes) < 2:
        raise ValueError(
            "Não foi possível dividir esta estufa da forma solicitada."
        )

    projeto_id = estufa["projeto_id"]

    with banco.get_conexao() as conexao:
        maior_numero = conexao.execute(
            "SELECT COALESCE(MAX(numero), 0) AS maior FROM estufa WHERE projeto_id = ?",
            (projeto_id,),
        ).fetchone()["maior"]

        conexao.execute("DELETE FROM estufa WHERE id = ?", (estufa_id,))

        for indice, poligono in enumerate(partes, start=1):
            novo_numero = maior_numero + indice
            conexao.execute(
                """
                INSERT INTO estufa (projeto_id, numero, nome, poligono, quantidade_areas)
                VALUES (?, ?, ?, ?, 0)
                """,
                (projeto_id, novo_numero, f"Estufa {novo_numero}", json.dumps(poligono)),
            )
        conexao.commit()

    return listar_estufas(projeto_id)


def excluir_estufa(estufa_id: int) -> None:
    estufa = obter_estufa(estufa_id)
    if estufa is None:
        raise LookupError("Estufa não encontrada.")

    with banco.get_conexao() as conexao:
        conexao.execute("DELETE FROM estufa WHERE id = ?", (estufa_id,))
        conexao.commit()


def restaurar_estufas(
    projeto_id: int, estufas_snapshot: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Substitui as estufas do projeto por uma cópia salva anteriormente.

    Usada pelo Ctrl+Z do frontend: antes de qualquer ação que destrua
    estufas/áreas (detectar, dividir, gerar áreas, excluir), o
    frontend guarda uma cópia do estado atual (a própria resposta de
    `listar_estufas`, com as áreas aninhadas) e, se o usuário desfizer,
    manda essa cópia de volta aqui para restaurá-la.

    Os IDs originais não são preservados (novos IDs são gerados), mas
    número, nome, polígono e todos os dados de cada área são mantidos.
    """
    projeto = projeto_servico.obter_projeto(projeto_id)
    if projeto is None:
        raise LookupError("Projeto não encontrado.")

    with banco.get_conexao() as conexao:
        conexao.execute("DELETE FROM estufa WHERE projeto_id = ?", (projeto_id,))

        for estufa in estufas_snapshot:
            cursor = conexao.execute(
                """
                INSERT INTO estufa
                    (projeto_id, numero, nome, poligono, quantidade_areas, orientacao_areas)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    projeto_id,
                    estufa["numero"],
                    estufa["nome"],
                    json.dumps(estufa["poligono"]),
                    estufa.get("quantidade_areas", 0),
                    estufa.get("orientacao_areas", "auto"),
                ),
            )
            nova_estufa_id = cursor.lastrowid

            for area in estufa.get("areas", []):
                variedade_id = area.get("variedade_id")
                if variedade_id is not None:
                    existe = conexao.execute(
                        "SELECT id FROM variedade WHERE id = ?", (variedade_id,)
                    ).fetchone()
                    if existe is None:
                        variedade_id = None

                conexao.execute(
                    """
                    INSERT INTO area
                        (estufa_id, variedade_id, fase, vaos, canteiros, postinhos, poligono, ordem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nova_estufa_id,
                        variedade_id,
                        area.get("fase"),
                        area.get("vaos"),
                        area.get("canteiros"),
                        area.get("postinhos"),
                        json.dumps(area["poligono"]),
                        area.get("ordem", 0),
                    ),
                )

        conexao.commit()

    return listar_estufas(projeto_id)


def atualizar_estufa(estufa_id: int, campos: dict[str, Any]) -> dict[str, Any]:
    estufa_existente = obter_estufa(estufa_id)
    if estufa_existente is None:
        raise LookupError("Estufa não encontrada.")

    dados_validos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS}
    if not dados_validos:
        raise ValueError("Nenhum campo válido para atualizar.")

    if "nome" in dados_validos and not str(dados_validos["nome"]).strip():
        raise ValueError("O nome da estufa é obrigatório.")

    set_clause = ", ".join(f"{campo} = ?" for campo in dados_validos)
    valores = list(dados_validos.values()) + [estufa_id]

    with banco.get_conexao() as conexao:
        conexao.execute(f"UPDATE estufa SET {set_clause} WHERE id = ?", valores)
        conexao.commit()

    estufa_atualizada = obter_estufa(estufa_id)
    assert estufa_atualizada is not None
    return estufa_atualizada
