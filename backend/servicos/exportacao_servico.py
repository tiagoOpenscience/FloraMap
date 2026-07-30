"""Exportação de um Projeto em CSV e PDF.

O PDF inclui a imagem aérea com os contornos de estufas/áreas
desenhados por cima (áreas coloridas pela variedade, com o número da
área e suas dimensões), a legenda de variedades, o resumo do projeto,
uma tabela detalhada por área e os campos de Observações / Análise
Geral.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from backend.servicos import estufa_servico, projeto_servico, resumo_servico, variedade_servico

LARGURA_MAXIMA_IMAGEM_PDF = 1800  # px — evita PDFs enormes com fotos muito grandes


def gerar_csv(projeto_id: int) -> str:
    estufas = estufa_servico.listar_estufas(projeto_id)

    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(
        ["Estufa", "Número", "Área", "Variedade", "Fase", "Vãos", "Canteiros", "Postinhos"]
    )

    for estufa in estufas:
        for area in estufa.get("areas") or []:
            escritor.writerow(
                [
                    estufa["nome"],
                    estufa["numero"],
                    f"A{area['ordem']}",
                    area.get("variedade_nome") or "",
                    area.get("fase") or "",
                    area.get("vaos") or "",
                    area.get("canteiros") or "",
                    area.get("postinhos") or "",
                ]
            )

    return buffer.getvalue()


def _texto_seguro(texto: Any) -> str:
    """Garante que o texto caiba na codificação Latin-1 usada pelas fontes
    padrão do PDF, substituindo qualquer caractere fora dela.

    Sem isso, qualquer texto do usuário (nome do projeto, observações,
    campos de área etc.) com um caractere fora do Latin-1 — como "—"
    ou emojis — derrubaria a exportação inteira com uma exceção.
    """
    if texto is None:
        return ""
    return str(texto).encode("latin-1", errors="replace").decode("latin-1")


def gerar_pdf(projeto_id: int) -> bytes:
    projeto = projeto_servico.obter_projeto(projeto_id)
    if projeto is None:
        raise LookupError("Projeto não encontrado.")

    estufas = estufa_servico.listar_estufas(projeto_id)
    resumo = resumo_servico.obter_resumo(projeto_id)
    variedades = variedade_servico.listar_variedades()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _texto_seguro(projeto["nome"]), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(
        0, 6,
        f"Exportado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    if projeto["imagem_path"]:
        nome_arquivo = Path(projeto["imagem_path"]).name
        caminho_absoluto = projeto_servico.UPLOADS_DIR / nome_arquivo
        if caminho_absoluto.exists():
            imagem_mapa = _gerar_imagem_mapa(str(caminho_absoluto), estufas)
            largura_disponivel = pdf.w - 2 * pdf.l_margin
            pdf.image(imagem_mapa, w=largura_disponivel)
            pdf.ln(4)

    _secao_resumo(pdf, resumo)
    _secao_legenda_variedades(pdf, variedades)
    _secao_tabela_areas(pdf, estufas)
    _secao_texto(pdf, "Observações", projeto.get("observacao"))
    _secao_texto(pdf, "Análise Geral", projeto.get("analise_geral"))

    return bytes(pdf.output())


def _secao_resumo(pdf: FPDF, resumo: dict[str, Any]) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Resumo do Projeto", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Total de estufas: {resumo['total_estufas']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Total de áreas: {resumo['total_areas']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _secao_legenda_variedades(pdf: FPDF, variedades: list[dict[str, Any]]) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Legenda de Variedades", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    if not variedades:
        pdf.cell(0, 6, "Nenhuma variedade cadastrada.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        return

    for variedade in variedades:
        r, g, b = _hex_para_rgb(variedade["cor"])
        pdf.set_fill_color(r, g, b)
        pdf.cell(6, 6, "", border=1, fill=True)
        pdf.cell(0, 6, f"  {_texto_seguro(variedade['nome'])}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)


def _secao_tabela_areas(pdf: FPDF, estufas: list[dict[str, Any]]) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Áreas por Estufa", new_x="LMARGIN", new_y="NEXT")

    larguras = [45, 15, 35, 20, 20, 22, 22]
    cabecalhos = ["Estufa", "Área", "Variedade", "Fase", "Vãos", "Canteiros", "Postinhos"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 238, 230)
    for largura, cabecalho in zip(larguras, cabecalhos):
        pdf.cell(largura, 7, cabecalho, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for estufa in estufas:
        areas = estufa.get("areas") or []
        if not areas:
            valores = [f"{estufa['numero']} - {estufa['nome']}", "-", "-", "-", "-", "-", "-"]
            for largura, valor in zip(larguras, valores):
                pdf.cell(largura, 6, _texto_seguro(valor)[:22], border=1)
            pdf.ln()
            continue

        for area in areas:
            valores = [
                f"{estufa['numero']} - {estufa['nome']}",
                f"A{area['ordem']}",
                area.get("variedade_nome") or "-",
                area.get("fase") or "-",
                area.get("vaos") or "-",
                area.get("canteiros") or "-",
                area.get("postinhos") or "-",
            ]
            for largura, valor in zip(larguras, valores):
                pdf.cell(largura, 6, _texto_seguro(valor)[:22], border=1)
            pdf.ln()

    pdf.ln(3)


def _secao_texto(pdf: FPDF, titulo: str, texto: str | None) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, _texto_seguro(texto) or "-")
    pdf.ln(2)


def _hex_para_rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return int(cor_hex[0:2], 16), int(cor_hex[2:4], 16), int(cor_hex[4:6], 16)


def _centro(poligono: list[dict[str, float]]) -> tuple[float, float]:
    x = sum(p["x"] for p in poligono) / len(poligono)
    y = sum(p["y"] for p in poligono) / len(poligono)
    return x, y


def _fonte(tamanho: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:
        return ImageFont.load_default()


def _desenhar_texto_com_fundo(
    draw: ImageDraw.ImageDraw,
    centro: tuple[float, float],
    linhas: list[str],
    fonte: ImageFont.ImageFont,
) -> None:
    """Desenha linhas de texto centralizadas, com um fundo branco translúcido
    atrás para garantir legibilidade sobre qualquer cor da foto."""
    alturas_linha = []
    larguras_linha = []
    for linha in linhas:
        caixa = draw.textbbox((0, 0), linha, font=fonte)
        larguras_linha.append(caixa[2] - caixa[0])
        alturas_linha.append(caixa[3] - caixa[1])

    largura_total = max(larguras_linha) if larguras_linha else 0
    altura_total = sum(alturas_linha) + 2 * (len(linhas) - 1)

    x0 = centro[0] - largura_total / 2 - 4
    y0 = centro[1] - altura_total / 2 - 3
    x1 = centro[0] + largura_total / 2 + 4
    y1 = centro[1] + altura_total / 2 + 3
    draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255, 210))

    y_atual = centro[1] - altura_total / 2
    for linha, altura in zip(linhas, alturas_linha):
        draw.text((centro[0], y_atual), linha, font=fonte, fill=(25, 35, 20, 255), anchor="ma")
        y_atual += altura + 2


def _gerar_imagem_mapa(
    caminho_imagem: str, estufas: list[dict[str, Any]]
) -> Image.Image:
    base = Image.open(caminho_imagem).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    escala = max(1, base.width // 800)
    espessura_estufa = max(2, escala)
    espessura_area = max(1, escala)
    cor_neutra = (207, 214, 199, 150)

    for estufa in estufas:
        pontos_estufa = [(p["x"], p["y"]) for p in estufa["poligono"]]
        if len(pontos_estufa) >= 2:
            draw_overlay.polygon(pontos_estufa, outline=(47, 111, 78, 255), width=espessura_estufa)

        for area in estufa.get("areas") or []:
            pontos_area = [(p["x"], p["y"]) for p in area["poligono"]]
            if len(pontos_area) < 2:
                continue
            if area.get("variedade_cor"):
                r, g, b = _hex_para_rgb(area["variedade_cor"])
                cor = (r, g, b, 150)
            else:
                cor = cor_neutra
            draw_overlay.polygon(pontos_area, fill=cor, outline=(255, 255, 255, 255), width=espessura_area)

    composta = Image.alpha_composite(base, overlay).convert("RGB")
    draw_final = ImageDraw.Draw(composta)

    fonte_estufa = _fonte(max(14, 16 * escala))
    fonte_area = _fonte(max(10, 11 * escala))

    for estufa in estufas:
        centro_estufa = _centro(estufa["poligono"])
        _desenhar_texto_com_fundo(
            draw_final, centro_estufa, [f"{estufa['numero']} · {estufa['nome']}"], fonte_estufa
        )

        for area in estufa.get("areas") or []:
            centro_area = _centro(area["poligono"])
            linhas = [
                f"A{area['ordem']}",
                f"{area.get('canteiros') or '-'}x{area.get('vaos') or '-'}x{area.get('postinhos') or '-'}",
                area.get("variedade_nome") or "Sem variedade",
            ]
            _desenhar_texto_com_fundo(draw_final, centro_area, linhas, fonte_area)

    if composta.width > LARGURA_MAXIMA_IMAGEM_PDF:
        proporcao = LARGURA_MAXIMA_IMAGEM_PDF / composta.width
        nova_altura = int(composta.height * proporcao)
        composta = composta.resize((LARGURA_MAXIMA_IMAGEM_PDF, nova_altura), Image.LANCZOS)

    return composta
