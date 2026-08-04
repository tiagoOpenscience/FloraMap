"""Regras de negócio relacionadas a Projeto."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend import banco

UPLOADS_DIR = banco.BASE_DIR / "uploads"
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg"}

# Fotos aéreas de drone costumam vir com vários MB e resolução muito
# maior do que o necessário pra visualização no mapa/exportação em PDF
# (ver RESOLUCAO_MINIMA_RENDER em exportacao_servico.py). Recomprimir
# no upload reduz drasticamente o espaço em disco usado por projeto —
# importante em hospedagens com cota de disco apertada.
LARGURA_MAXIMA_UPLOAD_PX = 2000
QUALIDADE_JPEG_UPLOAD = 85


def _extensao_valida(nome_arquivo: str) -> bool:
    partes = nome_arquivo.rsplit(".", 1)
    return len(partes) == 2 and partes[1].lower() in EXTENSOES_PERMITIDAS


CAMPOS_EDITAVEIS = {"nome", "observacao", "analise_geral"}


def listar_projetos() -> list[dict[str, Any]]:
    with banco.get_conexao() as conexao:
        linhas = conexao.execute(
            "SELECT id, nome, imagem_path, criado_em FROM projeto ORDER BY criado_em DESC"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def obter_projeto(projeto_id: int) -> dict[str, Any] | None:
    with banco.get_conexao() as conexao:
        linha = conexao.execute(
            """
            SELECT id, nome, imagem_path, observacao, analise_geral, criado_em
            FROM projeto WHERE id = ?
            """,
            (projeto_id,),
        ).fetchone()
    return dict(linha) if linha else None


def criar_projeto(nome: str) -> dict[str, Any]:
    nome_limpo = nome.strip()
    if not nome_limpo:
        raise ValueError("O nome do projeto é obrigatório.")

    with banco.get_conexao() as conexao:
        cursor = conexao.execute(
            "INSERT INTO projeto (nome) VALUES (?)", (nome_limpo,)
        )
        conexao.commit()
        projeto_id = cursor.lastrowid

    projeto = obter_projeto(projeto_id)
    assert projeto is not None
    return projeto


def atualizar_projeto(projeto_id: int, campos: dict[str, Any]) -> dict[str, Any]:
    """Atualiza nome, observação e/ou análise geral do projeto."""
    projeto = obter_projeto(projeto_id)
    if projeto is None:
        raise LookupError("Projeto não encontrado.")

    dados_validos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS}
    if not dados_validos:
        raise ValueError("Nenhum campo válido para atualizar.")

    if "nome" in dados_validos:
        dados_validos["nome"] = dados_validos["nome"].strip()
        if not dados_validos["nome"]:
            raise ValueError("O nome do projeto é obrigatório.")

    set_clause = ", ".join(f"{campo} = ?" for campo in dados_validos)
    valores = list(dados_validos.values()) + [projeto_id]

    with banco.get_conexao() as conexao:
        conexao.execute(f"UPDATE projeto SET {set_clause} WHERE id = ?", valores)
        conexao.commit()

    projeto_atualizado = obter_projeto(projeto_id)
    assert projeto_atualizado is not None
    return projeto_atualizado


def excluir_projeto(projeto_id: int) -> None:
    projeto = obter_projeto(projeto_id)
    if projeto is None:
        raise LookupError("Projeto não encontrado.")

    with banco.get_conexao() as conexao:
        conexao.execute("DELETE FROM projeto WHERE id = ?", (projeto_id,))
        conexao.commit()

    if projeto["imagem_path"]:
        caminho = UPLOADS_DIR / Path(projeto["imagem_path"]).name
        caminho.unlink(missing_ok=True)


def salvar_imagem_projeto(projeto_id: int, arquivo: FileStorage) -> str:
    if not arquivo.filename or not _extensao_valida(arquivo.filename):
        raise ValueError("Formato de imagem inválido. Utilize PNG ou JPEG.")

    projeto = obter_projeto(projeto_id)
    if projeto is None:
        raise ValueError("Projeto não encontrado.")

    try:
        imagem = Image.open(arquivo.stream)
        imagem.load()
    except Exception as erro:
        raise ValueError("Não foi possível ler o arquivo de imagem enviado.") from erro

    if imagem.mode != "RGB":
        imagem = imagem.convert("RGB")

    if imagem.width > LARGURA_MAXIMA_UPLOAD_PX:
        nova_altura = round(imagem.height * LARGURA_MAXIMA_UPLOAD_PX / imagem.width)
        imagem = imagem.resize((LARGURA_MAXIMA_UPLOAD_PX, nova_altura), Image.LANCZOS)

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    nome_arquivo = secure_filename(f"projeto_{projeto_id}.jpg")
    caminho_destino = UPLOADS_DIR / nome_arquivo
    imagem.save(caminho_destino, format="JPEG", quality=QUALIDADE_JPEG_UPLOAD)

    # Se a imagem anterior tinha outra extensão (ex.: reenvio de um PNG
    # depois que este projeto já tinha uma foto), remove o arquivo
    # antigo pra não deixar lixo ocupando espaço em disco.
    imagem_anterior = projeto.get("imagem_path")
    if imagem_anterior and Path(imagem_anterior).name != nome_arquivo:
        (UPLOADS_DIR / Path(imagem_anterior).name).unlink(missing_ok=True)

    imagem_path = f"/uploads/{nome_arquivo}"
    with banco.get_conexao() as conexao:
        conexao.execute(
            "UPDATE projeto SET imagem_path = ? WHERE id = ?",
            (imagem_path, projeto_id),
        )
        conexao.commit()

    return imagem_path
