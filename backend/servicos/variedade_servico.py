"""Regras de negócio relacionadas a Variedade."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from backend import banco

_REGEX_COR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _validar_cor(cor: str) -> str:
    if not _REGEX_COR_HEX.match(cor or ""):
        raise ValueError("A cor deve estar no formato hexadecimal, ex.: #E91E63.")
    return cor


def listar_variedades() -> list[dict[str, Any]]:
    with banco.get_conexao() as conexao:
        linhas = conexao.execute(
            "SELECT id, nome, cor FROM variedade ORDER BY nome ASC"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def obter_variedade(variedade_id: int) -> dict[str, Any] | None:
    with banco.get_conexao() as conexao:
        linha = conexao.execute(
            "SELECT id, nome, cor FROM variedade WHERE id = ?", (variedade_id,)
        ).fetchone()
    return dict(linha) if linha else None


def criar_variedade(nome: str, cor: str) -> dict[str, Any]:
    nome_limpo = (nome or "").strip()
    if not nome_limpo:
        raise ValueError("O nome da variedade é obrigatório.")
    cor_validada = _validar_cor(cor)

    try:
        with banco.get_conexao() as conexao:
            cursor = conexao.execute(
                "INSERT INTO variedade (nome, cor) VALUES (?, ?)",
                (nome_limpo, cor_validada),
            )
            conexao.commit()
            variedade_id = cursor.lastrowid
    except sqlite3.IntegrityError as erro:
        raise ValueError(f'Já existe uma variedade chamada "{nome_limpo}".') from erro

    variedade = obter_variedade(variedade_id)
    assert variedade is not None
    return variedade


def atualizar_variedade(variedade_id: int, campos: dict[str, Any]) -> dict[str, Any]:
    variedade_existente = obter_variedade(variedade_id)
    if variedade_existente is None:
        raise LookupError("Variedade não encontrada.")

    campos_permitidos = {"nome", "cor"}
    dados_validos = {k: v for k, v in campos.items() if k in campos_permitidos}
    if not dados_validos:
        raise ValueError("Nenhum campo válido para atualizar.")

    if "nome" in dados_validos:
        dados_validos["nome"] = dados_validos["nome"].strip()
        if not dados_validos["nome"]:
            raise ValueError("O nome da variedade é obrigatório.")

    if "cor" in dados_validos:
        dados_validos["cor"] = _validar_cor(dados_validos["cor"])

    set_clause = ", ".join(f"{campo} = ?" for campo in dados_validos)
    valores = list(dados_validos.values()) + [variedade_id]

    try:
        with banco.get_conexao() as conexao:
            conexao.execute(f"UPDATE variedade SET {set_clause} WHERE id = ?", valores)
            conexao.commit()
    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe uma variedade com esse nome.") from erro

    variedade_atualizada = obter_variedade(variedade_id)
    assert variedade_atualizada is not None
    return variedade_atualizada
