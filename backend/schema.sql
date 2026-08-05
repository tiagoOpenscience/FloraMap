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

-- Um ponto de acesso é uma aresta da borda de uma Estufa (o segmento
-- entre poligono[indice_aresta] e poligono[(indice_aresta+1) % N]),
-- marcada como entrada ou saída. Não tem coordenadas próprias — segue
-- o polígono da estufa automaticamente.
CREATE TABLE IF NOT EXISTS ponto_acesso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estufa_id INTEGER NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    indice_aresta INTEGER NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (estufa_id) REFERENCES estufa (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_estufa_projeto ON estufa (projeto_id);
CREATE INDEX IF NOT EXISTS idx_area_estufa ON area (estufa_id);
CREATE INDEX IF NOT EXISTS idx_ponto_acesso_estufa ON ponto_acesso (estufa_id);
