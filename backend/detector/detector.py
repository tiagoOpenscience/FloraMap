"""Detecção automática de estufas em imagens aéreas via OpenCV.

IMPORTANTE — por que a detecção é calibrada por amostra, e não por uma
cor fixa no código: estufas de propriedades diferentes têm coberturas
de cores muito diferentes (branco, cinza-azulado, até rosa), e o fundo
ao redor também varia (grama, solo exposto, barro). Cravar uma cor
"típica" no código funcionaria só para as fotos parecidas com as que
foram usadas para calibrar, e falharia silenciosamente para qualquer
produtor com um cenário diferente.

Por isso o fluxo é: o usuário clica em um ou mais pontos de uma (ou
mais) estufa conhecida na própria foto que ele enviou. O detector lê a
cor de cada ponto e usa a UNIÃO dessas faixas de cor como referência
para encontrar o resto das estufas. Permitir vários pontos é
importante para coberturas com textura listrada/ripada, onde um único
ponto captura só uma das cores da listra — clicar numa faixa clara e
noutra escura da mesma estufa cobre as duas.

Se nenhum ponto de amostra for informado, um heurístico genérico de
"área clara e pouco saturada" é usado como aproximação de baixa
confiança (mantido por compatibilidade), mas o resultado tende a ser
bem menos preciso do que com uma amostra.
"""

from __future__ import annotations

import statistics

import cv2
import numpy as np

AREA_MINIMA_RELATIVA = 0.001  # 0,1% da área total da imagem — descarta ruído
AREA_MAXIMA_RELATIVA = 0.5  # 50% da área total — descarta manchas grandes
# demais (clareira, sombra de nuvem, uma detecção que "engoliu" a
# imagem inteira), que não correspondem a uma única estufa.

LARGURA_MAXIMA_RELATIVA = 0.6  # uma estufa não deveria ocupar quase toda a
ALTURA_MAXIMA_RELATIVA = 0.6  # largura/altura da foto — isso costuma ser
# solo exposto, clareira ou estrada, não uma única estufa.

EPSILON_RELATIVO = 0.02  # tolerância da aproximação poligonal, em % do perímetro

RAIO_AMOSTRA_PX = 12  # vizinhança ao redor de cada ponto clicado usada para
# calcular a cor de referência (média + desvio padrão em HSV).

# Margem mínima de tolerância em cada canal HSV, usada mesmo quando a
# região amostrada é muito uniforme (desvio padrão baixo) — evita uma
# faixa de cor tão estreita que nem a própria estufa amostrada bata
# inteira nela.
MARGEM_MINIMA_H = 10
MARGEM_MINIMA_S = 30
MARGEM_MINIMA_V = 35
MULTIPLICADOR_DESVIO = 3.0

# Heurístico genérico (sem amostra): área clara e pouco saturada.
BRILHO_MINIMO_GENERICO = 140
SATURACAO_MAXIMA_GENERICA = 70

PontoAmostra = tuple[float, float]


def detectar_estufas(
    imagem_path: str, pontos_amostra: list[PontoAmostra] | None = None
) -> list[list[dict[str, float]]]:
    """Detecta estufas em uma imagem aérea.

    Args:
        imagem_path: caminho absoluto da imagem aérea no disco.
        pontos_amostra: lista de coordenadas (x, y), em pixels da
            imagem, de pontos que o usuário clicou sobre estufas
            conhecidas. Quando informado, a cor dessas regiões (a
            união delas) calibra a detecção. Quando ausente, um
            heurístico genérico é usado.

    Returns:
        Lista de polígonos (um por estufa detectada), já ordenados de
        cima para baixo e da esquerda para a direita. Cada polígono é
        uma lista de pontos {"x": float, "y": float}.

    Raises:
        ValueError: se a imagem não puder ser lida.
    """
    imagem = cv2.imread(imagem_path)
    if imagem is None:
        raise ValueError("Não foi possível ler a imagem enviada.")

    altura, largura = imagem.shape[:2]
    area_total = altura * largura
    area_minima = area_total * AREA_MINIMA_RELATIVA
    area_maxima = area_total * AREA_MAXIMA_RELATIVA
    largura_maxima = largura * LARGURA_MAXIMA_RELATIVA
    altura_maxima = altura * ALTURA_MAXIMA_RELATIVA

    suavizada = cv2.GaussianBlur(imagem, (5, 5), 0)
    hsv = cv2.cvtColor(suavizada, cv2.COLOR_BGR2HSV)

    pontos_amostra = pontos_amostra or []
    if pontos_amostra:
        mascara = _mascara_por_amostras(hsv, pontos_amostra, largura, altura)
    else:
        mascara = cv2.inRange(
            hsv, (0, 0, BRILHO_MINIMO_GENERICO), (180, SATURACAO_MAXIMA_GENERICA, 255)
        )

    kernel = np.ones((7, 7), np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel, iterations=1)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=3)

    contornos, _ = cv2.findContours(
        mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Quando há amostras, o tamanho e as dimensões dos contornos que
    # contêm os pontos clicados viram a referência de escala: só
    # aceitamos formas de porte parecido com as estufas que o usuário
    # efetivamente apontou. Isso é bem mais preciso — e mais robusto a
    # diferenças de imagem para imagem — do que um percentual fixo da
    # imagem inteira, e resolve de forma natural o caso de uma
    # construção pequena (galpão, casa) ter uma cor parecida com a da
    # estufa, mas um tamanho muito menor.
    if pontos_amostra:
        referencia = _referencia_das_amostras(contornos, pontos_amostra)
        if referencia is not None:
            area_ref, largura_ref, altura_ref = referencia
            area_minima = max(area_ref * 0.15, area_total * 0.0002)
            area_maxima = min(area_ref * 8, area_total * AREA_MAXIMA_RELATIVA)
            largura_maxima = min(largura_ref * 5, largura * 0.9)
            altura_maxima = min(altura_ref * 5, altura * 0.9)

    poligonos: list[list[dict[str, float]]] = []
    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if area < area_minima or area > area_maxima:
            continue

        _, _, largura_contorno, altura_contorno = cv2.boundingRect(contorno)
        if largura_contorno > largura_maxima or altura_contorno > altura_maxima:
            continue

        perimetro = cv2.arcLength(contorno, True)
        aproximado = cv2.approxPolyDP(contorno, EPSILON_RELATIVO * perimetro, True)

        if len(aproximado) < 3:
            continue

        pontos = [{"x": float(p[0][0]), "y": float(p[0][1])} for p in aproximado]
        poligonos.append(pontos)

    poligonos.sort(key=_chave_ordenacao_espacial)
    return poligonos


def _referencia_das_amostras(
    contornos: list[np.ndarray], pontos_amostra: list[PontoAmostra]
) -> tuple[float, float, float] | None:
    """Área e dimensões "típicas" de uma estufa real, a partir das amostras.

    Usa a mediana entre os contornos que contêm cada ponto amostrado,
    para não deixar um contorno anormalmente grande (ex.: duas estufas
    coladas na máscara) distorcer sozinho a referência.
    """
    areas = []
    larguras = []
    alturas = []
    for ponto in pontos_amostra:
        for contorno in contornos:
            if cv2.pointPolygonTest(contorno, ponto, False) >= 0:
                _, _, w, h = cv2.boundingRect(contorno)
                areas.append(cv2.contourArea(contorno))
                larguras.append(w)
                alturas.append(h)
                break
    if not areas:
        return None
    return statistics.median(areas), statistics.median(larguras), statistics.median(alturas)


def _mascara_por_amostras(
    hsv: np.ndarray,
    pontos_amostra: list[PontoAmostra],
    largura: int,
    altura: int,
) -> np.ndarray:
    """Máscara de cor a partir da UNIÃO de várias amostras clicadas.

    Cada ponto contribui com sua própria faixa de cor (média ± desvio
    da vizinhança); a máscara final é a união (OR) de todas elas. Isso
    é o que permite cobrir coberturas listradas/ripadas: um clique na
    parte clara e outro na escura da mesma estufa juntam as duas faixas
    de cor num só resultado, em vez de uma média que não bate com
    nenhuma das duas.
    """
    mascara_uniao = None

    for ponto in pontos_amostra:
        x, y = ponto
        x0 = max(0, int(x - RAIO_AMOSTRA_PX))
        x1 = min(largura, int(x + RAIO_AMOSTRA_PX))
        y0 = max(0, int(y - RAIO_AMOSTRA_PX))
        y1 = min(altura, int(y + RAIO_AMOSTRA_PX))

        regiao = hsv[y0:y1, x0:x1]
        if regiao.size == 0:
            continue

        h_medio, s_medio, v_medio = (
            float(c) for c in regiao.reshape(-1, 3).mean(axis=0)
        )
        h_desvio, s_desvio, v_desvio = (
            float(c) for c in regiao.reshape(-1, 3).std(axis=0)
        )

        margem_h = max(MARGEM_MINIMA_H, h_desvio * MULTIPLICADOR_DESVIO)
        margem_s = max(MARGEM_MINIMA_S, s_desvio * MULTIPLICADOR_DESVIO)
        margem_v = max(MARGEM_MINIMA_V, v_desvio * MULTIPLICADOR_DESVIO)

        limite_inferior = (
            max(0, h_medio - margem_h),
            max(0, s_medio - margem_s),
            max(0, v_medio - margem_v),
        )
        limite_superior = (
            min(180, h_medio + margem_h),
            min(255, s_medio + margem_s),
            min(255, v_medio + margem_v),
        )

        mascara_ponto = cv2.inRange(hsv, limite_inferior, limite_superior)
        mascara_uniao = (
            mascara_ponto
            if mascara_uniao is None
            else cv2.bitwise_or(mascara_uniao, mascara_ponto)
        )

    if mascara_uniao is None:
        raise ValueError("Nenhum ponto de amostra válido foi informado.")

    return mascara_uniao


def _chave_ordenacao_espacial(poligono: list[dict[str, float]]) -> tuple[int, float]:
    """Ordena estufas por linha (topo->base) e depois por coluna (esq->dir).

    Agrupa centros verticais em "faixas" de 100px para lidar com pequenas
    variações de altura entre estufas visualmente na mesma linha.
    """
    centro_x = sum(p["x"] for p in poligono) / len(poligono)
    centro_y = sum(p["y"] for p in poligono) / len(poligono)
    faixa = int(centro_y // 100)
    return (faixa, centro_x)
