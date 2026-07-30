-- Schema do FloraMap
-- SQLite

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projeto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    imagem_path TEXT,
    observacao TEXT,
    analise_geral TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS variedade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS estufa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projeto_id INTEGER NOT NULL,
    numero INTEGER NOT NULL,
    nome TEXT NOT NULL,
    poligono TEXT NOT NULL DEFAULT '[]',
    quantidade_areas INTEGER NOT NULL DEFAULT 0,
    orientacao_areas TEXT NOT NULL DEFAULT 'auto',
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (projeto_id) REFERENCES projeto (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS area (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estufa_id INTEGER NOT NULL,
    variedade_id INTEGER,
    fase TEXT,
    vaos TEXT,
    canteiros TEXT,
    postinhos TEXT,
    poligono TEXT NOT NULL DEFAULT '[]',
    ordem INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (estufa_id) REFERENCES estufa (id) ON DELETE CASCADE,
    FOREIGN KEY (variedade_id) REFERENCES variedade (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_estufa_projeto ON estufa (projeto_id);
CREATE INDEX IF NOT EXISTS idx_area_estufa ON area (estufa_id);
