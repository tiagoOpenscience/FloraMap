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
MARGEM_MINIMA_S = 25
MARGEM_MINIMA_V = 30
MULTIPLICADOR_DESVIO = 2.2

# Heurístico genérico (sem amostra): área clara e pouco saturada.
BRILHO_MINIMO_GENERICO = 140
SATURACAO_MAXIMA_GENERICA = 70

# Solidez mínima (área do contorno / área do seu fecho convexo) para um
# contorno ser aceito como estufa. Estufas são estruturas retangulares e
# convexas; árvores e manchas de vegetação são tipicamente irregulares e
# lobuladas, com fecho convexo bem maior que a área real — esse filtro
# descarta esse tipo de falso positivo tanto na detecção automática
# quanto na semiautomática.
SOLIDEZ_MINIMA = 0.75

# Quando a área de um contorno aceito ultrapassa este múltiplo da área de
# referência (amostras, ou mediana dos próprios contornos sem amostra),
# ele é candidato a ser duas ou mais estufas coladas pela morfologia —
# tentamos separá-lo via watershed antes de aceitá-lo como está.
MULTIPLICADOR_AREA_SUSPEITA = 1.6

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

    # A abertura usa um kernel um pouco maior para de fato *quebrar*
    # pontes finas entre estufas vizinhas que a máscara de cor colou
    # (ex.: uma faixa estreita de grama/sombra parecida em brilho). O
    # fechamento é bem mais conservador — só fecha ruído/buracos
    # pequenos dentro de uma mesma estufa, sem voltar a "colar" duas
    # estruturas separadas (um kernel 7×7 com 3 iterações, usado antes,
    # preenchia vãos de até ~21px entre estufas próximas).
    kernel_abertura = np.ones((5, 5), np.uint8)
    kernel_fechamento = np.ones((3, 3), np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel_abertura, iterations=2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel_fechamento, iterations=1)

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
    area_ref: float | None = None
    if pontos_amostra:
        referencia = _referencia_das_amostras(contornos, pontos_amostra)
        if referencia is not None:
            area_ref, largura_ref, altura_ref = referencia
            area_minima = max(area_ref * 0.15, area_total * 0.0002)
            area_maxima = min(area_ref * 8, area_total * AREA_MAXIMA_RELATIVA)
            largura_maxima = min(largura_ref * 5, largura * 0.9)
            altura_maxima = min(altura_ref * 5, altura * 0.9)

    candidatos = [
        c
        for c in contornos
        if _contorno_valido(c, area_minima, area_maxima, largura_maxima, altura_maxima)
    ]

    # Sem amostra, usamos a mediana dos próprios contornos aceitos como
    # referência de tamanho "típico" — mesma ideia de detectar um blob
    # anormalmente grande (provável fusão de duas estufas vizinhas).
    if area_ref is None and candidatos:
        area_ref = statistics.median(cv2.contourArea(c) for c in candidatos)

    poligonos: list[list[dict[str, float]]] = []
    for contorno in candidatos:
        area = cv2.contourArea(contorno)
        partes = [contorno]

        if area_ref and area > area_ref * MULTIPLICADOR_AREA_SUSPEITA:
            separados = _separar_por_watershed(mascara, contorno, area_ref)
            if separados:
                partes = separados

        for parte in partes:
            if not _contorno_valido(
                parte, area_minima, area_maxima, largura_maxima, altura_maxima
            ):
                continue
            poligono = _aproximar_poligono(parte)
            if poligono is not None:
                poligonos.append(poligono)

    poligonos.sort(key=_chave_ordenacao_espacial)
    return poligonos


def _contorno_valido(
    contorno: np.ndarray,
    area_minima: float,
    area_maxima: float,
    largura_maxima: float,
    altura_maxima: float,
) -> bool:
    """Verifica área, dimensões e solidez (forma) de um contorno.

    A solidez (área do contorno / área do seu fecho convexo) é o que
    descarta manchas irregulares de vegetação: uma estufa é retangular
    e praticamente convexa, enquanto copas de árvores e vegetação têm
    contornos lobulados, com fecho convexo bem maior que a área real.
    """
    area = cv2.contourArea(contorno)
    if area < area_minima or area > area_maxima:
        return False

    _, _, largura_contorno, altura_contorno = cv2.boundingRect(contorno)
    if largura_contorno > largura_maxima or altura_contorno > altura_maxima:
        return False

    area_fecho = cv2.contourArea(cv2.convexHull(contorno))
    if area_fecho <= 0 or (area / area_fecho) < SOLIDEZ_MINIMA:
        return False

    return True


def _aproximar_poligono(contorno: np.ndarray) -> list[dict[str, float]] | None:
    perimetro = cv2.arcLength(contorno, True)
    aproximado = cv2.approxPolyDP(contorno, EPSILON_RELATIVO * perimetro, True)
    if len(aproximado) < 3:
        return None
    return [{"x": float(p[0][0]), "y": float(p[0][1])} for p in aproximado]


def _separar_por_watershed(
    mascara: np.ndarray, contorno: np.ndarray, area_ref: float
) -> list[np.ndarray] | None:
    """Tenta separar um contorno anormalmente grande em vários sub-contornos.

    Um contorno bem maior que a referência de tamanho esperada costuma
    ser duas (ou mais) estufas vizinhas que a máscara de cor + morfologia
    colaram numa única forma. Em vez de simplesmente descartar esse blob
    fundido, usamos a transformada de distância para achar um "núcleo"
    por estufa dentro dele e watershed para dividir a região ambígua
    entre esses núcleos — devolvendo N contornos separados.

    Retorna None quando só existe um núcleo (nada a separar).
    """
    x, y, w, h = cv2.boundingRect(contorno)
    margem = 2
    x0, y0 = max(0, x - margem), max(0, y - margem)
    x1 = min(mascara.shape[1], x + w + margem)
    y1 = min(mascara.shape[0], y + h + margem)

    mascara_local = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    cv2.drawContours(
        mascara_local, [contorno - (x0, y0)], -1, 255, thickness=cv2.FILLED
    )

    distancia = cv2.distanceTransform(mascara_local, cv2.DIST_L2, 5)
    if distancia.max() <= 0:
        return None

    _, nucleos = cv2.threshold(
        distancia, 0.5 * distancia.max(), 255, cv2.THRESH_BINARY
    )
    nucleos = nucleos.astype(np.uint8)

    n_marcadores, marcadores = cv2.connectedComponents(nucleos)
    n_nucleos = n_marcadores - 1
    if n_nucleos < 2:
        return None

    marcadores = marcadores + 1  # núcleos: 2..n_nucleos+1; resto vira "fundo" (1)
    desconhecido = cv2.subtract(mascara_local, nucleos)
    marcadores[desconhecido == 255] = 0  # zona ambígua, watershed decide
    marcadores[mascara_local == 0] = 1  # fora do blob = fundo certo

    imagem_vazia = np.zeros((*mascara_local.shape, 3), dtype=np.uint8)
    cv2.watershed(imagem_vazia, marcadores)

    partes = []
    for rotulo in range(2, n_marcadores + 1):
        sub_mascara = np.uint8(marcadores == rotulo) * 255
        sub_contornos, _ = cv2.findContours(
            sub_mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not sub_contornos:
            continue
        maior = max(sub_contornos, key=cv2.contourArea)
        partes.append(maior + (x0, y0))

    return partes if len(partes) > 1 else None


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
