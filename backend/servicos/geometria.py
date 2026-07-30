"""Funções de geometria compartilhadas entre Estufa e Área.

A divisão de um polígono em N partes é usada tanto para gerar Áreas
dentro de uma Estufa quanto para dividir (split) uma Estufa detectada
por engano como um único bloco (quando duas estufas reais ficaram
coladas na detecção automática).

Diferente de uma divisão por bounding box "cru", aqui cada parte é
recortada (via máscara/interseção) para respeitar o contorno real do
polígono original — importante porque estufas detectadas em fotos
aéreas raramente são retângulos perfeitamente alinhados aos eixos da
imagem; usar só o bounding box faria as partes "vazarem" para fora do
contorno real nos cantos.
"""

from __future__ import annotations

import cv2
import numpy as np

Ponto = dict[str, float]
Poligono = list[Ponto]


def dividir_poligono(
    poligono: Poligono, quantidade: int, orientacao: str = "auto"
) -> list[Poligono]:
    """Divide um polígono em `quantidade` partes de tamanho igual.

    Args:
        poligono: lista de pontos {"x","y"} em coordenadas da imagem.
        quantidade: número de partes desejado (mínimo 1).
        orientacao: "vertical" (cortes verticais, lado a lado),
            "horizontal" (cortes horizontais, empilhados) ou "auto"
            (escolhe o eixo mais longo do polígono automaticamente).

    Returns:
        Lista de polígonos (uma por parte), já recortados para dentro
        do contorno do polígono original. Pode retornar menos itens
        que `quantidade` se alguma faixa não interceptar o polígono.
    """
    xs = [p["x"] for p in poligono]
    ys = [p["y"] for p in poligono]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    largura_total = max_x - min_x
    altura_total = max_y - min_y

    if orientacao == "vertical":
        eixo = "x"
    elif orientacao == "horizontal":
        eixo = "y"
    else:
        eixo = "x" if largura_total >= altura_total else "y"

    largura_canvas = max(1, int(round(largura_total)) + 2)
    altura_canvas = max(1, int(round(altura_total)) + 2)

    mascara_poligono = np.zeros((altura_canvas, largura_canvas), dtype=np.uint8)
    pontos_locais = np.array(
        [[int(round(p["x"] - min_x)), int(round(p["y"] - min_y))] for p in poligono],
        dtype=np.int32,
    )
    cv2.fillPoly(mascara_poligono, [pontos_locais], 255)

    partes: list[Poligono] = []

    if eixo == "x":
        passo = largura_total / quantidade
        for i in range(quantidade):
            x0 = int(round(i * passo))
            x1 = int(round((i + 1) * passo))
            faixa = np.zeros_like(mascara_poligono)
            cv2.rectangle(faixa, (x0, 0), (x1, altura_canvas), 255, -1)
            intersecao = cv2.bitwise_and(mascara_poligono, faixa)
            parte = _extrair_poligono(intersecao, min_x, min_y)
            if parte is not None:
                partes.append(parte)
    else:
        passo = altura_total / quantidade
        for i in range(quantidade):
            y0 = int(round(i * passo))
            y1 = int(round((i + 1) * passo))
            faixa = np.zeros_like(mascara_poligono)
            cv2.rectangle(faixa, (0, y0), (largura_canvas, y1), 255, -1)
            intersecao = cv2.bitwise_and(mascara_poligono, faixa)
            parte = _extrair_poligono(intersecao, min_x, min_y)
            if parte is not None:
                partes.append(parte)

    return partes


def _extrair_poligono(
    mascara: np.ndarray, offset_x: float, offset_y: float
) -> Poligono | None:
    """Extrai o maior contorno de uma máscara binária como polígono."""
    contornos, _ = cv2.findContours(
        mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contornos:
        return None

    maior = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(maior) < 4:
        return None

    perimetro = cv2.arcLength(maior, True)
    aproximado = cv2.approxPolyDP(maior, 0.01 * perimetro, True)
    if len(aproximado) < 3:
        return None

    return [
        {"x": float(p[0][0] + offset_x), "y": float(p[0][1] + offset_y)}
        for p in aproximado
    ]
