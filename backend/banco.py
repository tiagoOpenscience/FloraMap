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
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conexao.executescript(sql)
        _migrar_colunas_novas(conexao)


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
