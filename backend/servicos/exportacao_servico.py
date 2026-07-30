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
from PIL import Image, ImageDraw

from backend.servicos import estufa_servico, projeto_servico, resumo_servico, variedade_servico

LARGURA_MAXIMA_IMAGEM_PDF = 1800  # px — evita PDFs enormes com fotos muito grandes

# Largura mínima de trabalho para compor o mapa. Fotos de propriedades
# menores costumam ter poucas centenas de pixels de largura — desenhar o
# texto dos rótulos nessa resolução nativa (fontes de ~11-16px) e depois
# esticar a imagem para a largura da página do PDF deixa as letras
# borradas/pixeladas. Ampliar a imagem antes de desenhar os rótulos (e
# só then reduzir, se preciso, no limite acima) mantém o texto nítido.
RESOLUCAO_MINIMA_RENDER = 1600  # px


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
            imagem_mapa, rotulos = _gerar_imagem_mapa(str(caminho_absoluto), estufas)
            largura_disponivel = pdf.w - 2 * pdf.l_margin
            x_imagem, y_imagem = pdf.l_margin, pdf.get_y()
            pdf.image(imagem_mapa, x=x_imagem, y=y_imagem, w=largura_disponivel)
            altura_imagem = largura_disponivel * imagem_mapa.height / imagem_mapa.width

            # Os rótulos são desenhados como texto vetorial de verdade do
            # PDF (não "assados" no bitmap) — assim continuam nítidos em
            # qualquer nível de zoom, igual ao resto do texto do
            # documento. Ver CLAUDE.md / SPEC.md para o racional.
            px_para_pt = (largura_disponivel * 72 / 25.4) / imagem_mapa.width
            _desenhar_rotulos_vetoriais(
                pdf, rotulos, x_imagem, y_imagem, largura_disponivel, altura_imagem, px_para_pt
            )
            pdf.set_xy(pdf.l_margin, y_imagem + altura_imagem + 4)

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


def _desenhar_rotulos_vetoriais(
    pdf: FPDF,
    rotulos: list[dict[str, Any]],
    x0: float,
    y0: float,
    largura_mm: float,
    altura_mm: float,
    px_para_pt: float,
) -> None:
    """Desenha os rótulos de estufa/área como texto vetorial real do PDF,
    posicionados por cima da imagem do mapa já embutida.

    Ao contrário de texto desenhado com Pillow dentro de um bitmap, texto
    vetorial do fpdf2 continua nítido em qualquer nível de zoom no leitor
    de PDF. Para legibilidade sobre a foto, em vez de uma caixa de fundo
    (que ficava com aspecto de "blocão" branco), o texto é desenhado com
    contorno branco ao redor das letras — a mesma técnica usada no SVG do
    mapa no navegador (`paint-order: stroke` + `stroke` branco em
    `frontend/css/style.css`).
    """
    largura_linha_original = pdf.line_width
    pdf.set_draw_color(255, 255, 255)
    pdf.set_text_color(25, 35, 20)
    pdf.text_mode = "FILL_STROKE"

    for rotulo in rotulos:
        cx = x0 + rotulo["centro_frac"][0] * largura_mm
        cy = y0 + rotulo["centro_frac"][1] * altura_mm
        tamanho_pt = max(6.0, rotulo["tamanho_fonte_px"] * px_para_pt)
        pdf.set_font("Helvetica", "B", tamanho_pt)
        pdf.set_line_width(tamanho_pt * 0.35276 * 0.18)  # contorno proporcional ao tamanho da fonte

        linhas = [_texto_seguro(linha) for linha in rotulo["linhas"]]
        altura_linha = tamanho_pt * 0.4
        largura_caixa = max(pdf.get_string_width(linha) for linha in linhas) + 4
        y_atual = cy - (len(linhas) * altura_linha) / 2

        for linha in linhas:
            pdf.set_xy(cx - largura_caixa / 2, y_atual)
            pdf.cell(largura_caixa, altura_linha, linha, align="C")
            y_atual += altura_linha

    pdf.text_mode = "FILL"
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(largura_linha_original)


def _gerar_imagem_mapa(
    caminho_imagem: str, estufas: list[dict[str, Any]]
) -> tuple[Image.Image, list[dict[str, Any]]]:
    base = Image.open(caminho_imagem).convert("RGBA")

    fator_render = max(1.0, RESOLUCAO_MINIMA_RENDER / base.width)
    if fator_render > 1.0:
        base = base.resize(
            (round(base.width * fator_render), round(base.height * fator_render)),
            Image.LANCZOS,
        )

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    escala = max(1, base.width // 800)
    espessura_estufa = max(2, escala)
    espessura_area = max(1, escala)
    cor_neutra = (207, 214, 199, 150)

    for estufa in estufas:
        pontos_estufa = [(p["x"] * fator_render, p["y"] * fator_render) for p in estufa["poligono"]]
        if len(pontos_estufa) >= 2:
            draw_overlay.polygon(pontos_estufa, outline=(47, 111, 78, 255), width=espessura_estufa)

        for area in estufa.get("areas") or []:
            pontos_area = [(p["x"] * fator_render, p["y"] * fator_render) for p in area["poligono"]]
            if len(pontos_area) < 2:
                continue
            if area.get("variedade_cor"):
                r, g, b = _hex_para_rgb(area["variedade_cor"])
                cor = (r, g, b, 150)
            else:
                cor = cor_neutra
            draw_overlay.polygon(pontos_area, fill=cor, outline=(255, 255, 255, 255), width=espessura_area)

    composta = Image.alpha_composite(base, overlay).convert("RGB")

    # Os rótulos não são desenhados na imagem — só a posição/texto/tamanho
    # são calculados aqui; o desenho em si acontece depois como texto
    # vetorial do PDF (`_desenhar_rotulos_vetoriais`), com contorno branco
    # ao redor das letras para legibilidade (em vez de uma caixa de
    # fundo), continuando nítido em qualquer nível de zoom.
    tamanho_fonte_estufa = max(14, 16 * escala)
    tamanho_fonte_area = max(10, 11 * escala)

    rotulos: list[dict[str, Any]] = []
    largura_final = base.width
    altura_final = base.height

    for estufa in estufas:
        cx, cy = _centro(estufa["poligono"])
        centro_estufa = (cx * fator_render, cy * fator_render)
        rotulos.append(
            {
                "centro_frac": (centro_estufa[0] / largura_final, centro_estufa[1] / altura_final),
                "linhas": [f"{estufa['numero']} · {estufa['nome']}"],
                "tamanho_fonte_px": tamanho_fonte_estufa,
            }
        )

        for area in estufa.get("areas") or []:
            cx, cy = _centro(area["poligono"])
            centro_area = (cx * fator_render, cy * fator_render)
            rotulos.append(
                {
                    "centro_frac": (centro_area[0] / largura_final, centro_area[1] / altura_final),
                    "linhas": [
                        f"A{area['ordem']}",
                        f"{area.get('canteiros') or '-'}x{area.get('vaos') or '-'}x{area.get('postinhos') or '-'}",
                        area.get("variedade_nome") or "Sem variedade",
                    ],
                    "tamanho_fonte_px": tamanho_fonte_area,
                }
            )

    if composta.width > LARGURA_MAXIMA_IMAGEM_PDF:
        proporcao = LARGURA_MAXIMA_IMAGEM_PDF / composta.width
        nova_altura = int(composta.height * proporcao)
        composta = composta.resize((LARGURA_MAXIMA_IMAGEM_PDF, nova_altura), Image.LANCZOS)

    return composta, rotulos
