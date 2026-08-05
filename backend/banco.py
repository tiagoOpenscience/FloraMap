"""Gerenciamento da conexão com o banco SQLite do FloraMap."""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "floramap.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_conexao() -> sqlite3.Connection:
    """Cria uma conexão nova com o banco, com row_factory em dict-like."""
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_banco() -> None:
    """Cria as tabelas do banco caso ainda não existam."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conexao() as conexao:
        _migrar_ponto_acesso_para_aresta(conexao)
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conexao.executescript(sql)
        _migrar_colunas_novas(conexao)


def _migrar_ponto_acesso_para_aresta(conexao: sqlite3.Connection) -> None:
    """Derruba a `ponto_acesso` antiga (formato por ponto solto x/y).

    A primeira versão da tabela guardava um ponto solto (x, y) por
    projeto; a versão atual guarda uma aresta (estufa_id + índice) da
    borda de uma Estufa. É uma mudança estrutural (não só coluna nova),
    então não dá pra usar só ALTER TABLE ADD COLUMN. Precisa rodar
    ANTES do executescript do schema.sql, porque o CREATE INDEX de lá
    já assume a coluna `estufa_id` — com a tabela antiga ainda no
    lugar, esse índice falharia. Depois do DROP, o próprio
    `CREATE TABLE IF NOT EXISTS` do schema.sql recria a tabela certa.
    """
    colunas = {
        linha["name"] for linha in conexao.execute("PRAGMA table_info(ponto_acesso)")
    }
    if "x" in colunas:
        conexao.execute("DROP TABLE ponto_acesso")
        conexao.commit()


def _migrar_colunas_novas(conexao: sqlite3.Connection) -> None:
    """Adiciona colunas novas a bancos criados antes delas existirem.

    CREATE TABLE IF NOT EXISTS não altera tabelas já existentes, então
    colunas adicionadas ao schema.sql depois do primeiro uso precisam
    ser adicionadas aqui também (ALTER TABLE ... ADD COLUMN), ignorando
    o erro caso a coluna já exista.
    """
    migracoes = [
        ("projeto", "observacao", "TEXT"),
        ("projeto", "analise_geral", "TEXT"),
        ("estufa", "orientacao_areas", "TEXT NOT NULL DEFAULT 'auto'"),
    ]
    for tabela, coluna, tipo in migracoes:
        try:
            conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
            conexao.commit()
        except sqlite3.OperationalError:
            pass  # coluna já existe
