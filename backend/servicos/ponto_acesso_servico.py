"""Regras de negócio relacionadas a Ponto de Acesso (entrada/saída).

Um ponto de acesso é uma aresta da borda de uma Estufa — não um ponto
solto — identificada por `indice_aresta` (o segmento entre
`poligono[indice_aresta]` e o próximo vértice, com wrap-around). Isso
faz a marcação seguir o contorno real da estufa automaticamente.
"""

from __future__ import annotations

from typing import Any

from backend import banco
from backend.servicos import estufa_servico

TIPOS_VALIDOS = {"entrada", "saida"}


def listar_pontos_acesso(projeto_id: int) -> list[dict[str, Any]]:
    with banco.get_conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT ponto_acesso.id, ponto_acesso.estufa_id, ponto_acesso.tipo,
                   ponto_acesso.indice_aresta
            FROM ponto_acesso
            JOIN estufa ON estufa.id = ponto_acesso.estufa_id
            WHERE estufa.projeto_id = ?
            ORDER BY ponto_acesso.id ASC
            """,
            (projeto_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def criar_ponto_acesso(estufa_id: int, tipo: str, indice_aresta: int) -> dict[str, Any]:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError("Tipo inválido (use 'entrada' ou 'saida').")

    estufa = estufa_servico.obter_estufa(estufa_id)
    if estufa is None:
        raise LookupError("Estufa não encontrada.")

    total_arestas = len(estufa["poligono"])
    if not (0 <= indice_aresta < total_arestas):
        raise ValueError("Índice de aresta inválido para o contorno desta estufa.")

    with banco.get_conexao() as conexao:
        cursor = conexao.execute(
            "INSERT INTO ponto_acesso (estufa_id, tipo, indice_aresta) VALUES (?, ?, ?)",
            (estufa_id, tipo, indice_aresta),
        )
        conexao.commit()
        ponto_id = cursor.lastrowid

    return {
        "id": ponto_id,
        "estufa_id": estufa_id,
        "tipo": tipo,
        "indice_aresta": indice_aresta,
    }


def excluir_ponto_acesso(ponto_id: int) -> None:
    with banco.get_conexao() as conexao:
        existe = conexao.execute(
            "SELECT id FROM ponto_acesso WHERE id = ?", (ponto_id,)
        ).fetchone()
        if existe is None:
            raise LookupError("Ponto de acesso não encontrado.")

        conexao.execute("DELETE FROM ponto_acesso WHERE id = ?", (ponto_id,))
        conexao.commit()
