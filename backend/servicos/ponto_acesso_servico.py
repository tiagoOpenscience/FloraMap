"""Regras de negócio relacionadas a Ponto de Acesso (entrada/saída da propriedade)."""

from __future__ import annotations

from typing import Any

from backend import banco

TIPOS_VALIDOS = {"entrada", "saida"}


def listar_pontos_acesso(projeto_id: int) -> list[dict[str, Any]]:
    with banco.get_conexao() as conexao:
        linhas = conexao.execute(
            "SELECT id, projeto_id, tipo, x, y FROM ponto_acesso WHERE projeto_id = ? ORDER BY id ASC",
            (projeto_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def criar_ponto_acesso(projeto_id: int, tipo: str, x: float, y: float) -> dict[str, Any]:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError("Tipo inválido (use 'entrada' ou 'saida').")

    with banco.get_conexao() as conexao:
        projeto = conexao.execute(
            "SELECT id FROM projeto WHERE id = ?", (projeto_id,)
        ).fetchone()
        if projeto is None:
            raise LookupError("Projeto não encontrado.")

        cursor = conexao.execute(
            "INSERT INTO ponto_acesso (projeto_id, tipo, x, y) VALUES (?, ?, ?, ?)",
            (projeto_id, tipo, x, y),
        )
        conexao.commit()
        ponto_id = cursor.lastrowid

    return {"id": ponto_id, "projeto_id": projeto_id, "tipo": tipo, "x": x, "y": y}


def excluir_ponto_acesso(ponto_id: int) -> None:
    with banco.get_conexao() as conexao:
        existe = conexao.execute(
            "SELECT id FROM ponto_acesso WHERE id = ?", (ponto_id,)
        ).fetchone()
        if existe is None:
            raise LookupError("Ponto de acesso não encontrado.")

        conexao.execute("DELETE FROM ponto_acesso WHERE id = ?", (ponto_id,))
        conexao.commit()
