// mapa.js — renderização da imagem aérea e dos polígonos SVG de
// estufas e áreas, além dos modos interativos de amostra de cor
// (multi-ponto) e de desenho manual de uma nova estufa.

const Mapa = (() => {
  let elVazio;
  let elPalco;
  let elImagem;
  let elSvg;
  let aoSelecionarEstufaCb = () => {};
  let aoSelecionarAreaCb = () => {};

  function iniciar({ vazio, palco, imagem, svg, aoSelecionarEstufa, aoSelecionarArea }) {
    elVazio = vazio;
    elPalco = palco;
    elImagem = imagem;
    elSvg = svg;
    aoSelecionarEstufaCb = aoSelecionarEstufa || (() => {});
    aoSelecionarAreaCb = aoSelecionarArea || (() => {});
  }

  function mostrarVazio() {
    elVazio.style.display = "block";
    elPalco.classList.remove("visivel");
  }

  function _limparSvg() {
    while (elSvg.firstChild) {
      elSvg.removeChild(elSvg.firstChild);
    }
  }

  function _pontosParaAtributo(pontos) {
    return pontos.map((p) => `${p.x},${p.y}`).join(" ");
  }

  function _centro(pontos) {
    return pontos.reduce(
      (acc, p) => ({ x: acc.x + p.x / pontos.length, y: acc.y + p.y / pontos.length }),
      { x: 0, y: 0 }
    );
  }

  function _textoRotulo(estufa) {
    return `${estufa.numero} · ${estufa.nome}`;
  }

  function _linhasRotuloArea(area) {
    const dimensoes = `${area.canteiros || "-"}x${area.vaos || "-"}x${area.postinhos || "-"}`;
    const variedade = area.variedade_nome || "Sem variedade";
    return [`A${area.ordem}`, dimensoes, variedade];
  }

  function _desenharArea(ns, grupo, area, estufa) {
    const poligono = document.createElementNS(ns, "polygon");
    poligono.setAttribute("points", _pontosParaAtributo(area.poligono));
    poligono.setAttribute("class", "poligono-area");
    poligono.dataset.areaId = area.id;
    poligono.dataset.estufaId = estufa.id;
    if (area.variedade_cor) {
      poligono.style.fill = area.variedade_cor;
    }
    poligono.addEventListener("click", (evento) => {
      evento.stopPropagation();
      aoSelecionarAreaCb(area, estufa);
    });
    grupo.appendChild(poligono);

    const centro = _centro(area.poligono);
    const rotulo = document.createElementNS(ns, "text");
    rotulo.setAttribute("x", centro.x);
    rotulo.setAttribute("y", centro.y);
    rotulo.setAttribute("text-anchor", "middle");
    rotulo.setAttribute("class", "rotulo-area");
    rotulo.dataset.areaId = area.id;

    const linhas = _linhasRotuloArea(area);
    linhas.forEach((linha, indice) => {
      const tspan = document.createElementNS(ns, "tspan");
      tspan.setAttribute("x", centro.x);
      tspan.setAttribute("dy", indice === 0 ? "-1em" : "1.1em");
      tspan.setAttribute("class", indice === 0 ? "rotulo-area__titulo" : "");
      tspan.textContent = linha;
      rotulo.appendChild(tspan);
    });

    grupo.appendChild(rotulo);
  }

  function _desenharEstufa(estufa) {
    const ns = "http://www.w3.org/2000/svg";
    const grupo = document.createElementNS(ns, "g");
    const temAreas = (estufa.areas || []).length > 0;

    const poligono = document.createElementNS(ns, "polygon");
    poligono.setAttribute("points", _pontosParaAtributo(estufa.poligono));
    poligono.setAttribute("class", "poligono-estufa");
    poligono.dataset.estufaId = estufa.id;
    if (temAreas) {
      poligono.style.fill = "none";
    }
    poligono.addEventListener("click", () => aoSelecionarEstufaCb(estufa));
    grupo.appendChild(poligono);

    if (temAreas) {
      for (const area of estufa.areas) {
        _desenharArea(ns, grupo, area, estufa);
      }
    }

    if (!temAreas && estufa.poligono.length > 0) {
      const centro = _centro(estufa.poligono);
      const rotulo = document.createElementNS(ns, "text");
      rotulo.setAttribute("x", centro.x);
      rotulo.setAttribute("y", centro.y);
      rotulo.setAttribute("text-anchor", "middle");
      rotulo.setAttribute("class", "rotulo-estufa");
      rotulo.dataset.estufaId = estufa.id;
      rotulo.textContent = _textoRotulo(estufa);
      rotulo.addEventListener("click", (evento) => {
        evento.stopPropagation();
        aoSelecionarEstufaCb(estufa);
      });
      grupo.appendChild(rotulo);
    }

    elSvg.appendChild(grupo);
  }

  function carregar({ imagemUrl, estufas }) {
    elVazio.style.display = "none";
    elPalco.classList.add("visivel");

    elImagem.src = imagemUrl;
    elImagem.onload = () => {
      elSvg.setAttribute("width", elImagem.naturalWidth);
      elSvg.setAttribute("height", elImagem.naturalHeight);
      elSvg.setAttribute("viewBox", `0 0 ${elImagem.naturalWidth} ${elImagem.naturalHeight}`);
    };

    _limparSvg();
    for (const estufa of estufas || []) {
      _desenharEstufa(estufa);
    }
  }

  function marcarEstufaSelecionada(estufaId) {
    elSvg.querySelectorAll(".poligono-estufa").forEach((p) => {
      p.classList.toggle("selecionada", Number(p.dataset.estufaId) === Number(estufaId));
    });
    elSvg.querySelectorAll(".poligono-area").forEach((p) => {
      p.classList.remove("selecionada");
    });
  }

  function marcarAreaSelecionada(areaId) {
    elSvg.querySelectorAll(".poligono-area").forEach((p) => {
      p.classList.toggle("selecionada", Number(p.dataset.areaId) === Number(areaId));
    });
    elSvg.querySelectorAll(".poligono-estufa").forEach((p) => {
      p.classList.remove("selecionada");
    });
  }

  function atualizarRotulo(estufaId, numero, nome) {
    const rotulo = elSvg.querySelector(`text[data-estufa-id="${estufaId}"]`);
    if (rotulo) {
      rotulo.textContent = _textoRotulo({ numero, nome });
    }
  }

  function atualizarCorArea(areaId, cor) {
    const poligono = elSvg.querySelector(`polygon.poligono-area[data-area-id="${areaId}"]`);
    if (poligono) {
      poligono.style.fill = cor || "";
    }
  }

  function atualizarRotuloArea(areaId, area) {
    const rotulo = elSvg.querySelector(`text.rotulo-area[data-area-id="${areaId}"]`);
    if (!rotulo) return;
    const tspans = rotulo.querySelectorAll("tspan");
    const linhas = _linhasRotuloArea(area);
    tspans.forEach((tspan, indice) => {
      if (linhas[indice] !== undefined) tspan.textContent = linhas[indice];
    });
  }

  function _pontoDoEvento(evento) {
    const ponto = elSvg.createSVGPoint();
    ponto.x = evento.clientX;
    ponto.y = evento.clientY;
    return ponto.matrixTransform(elSvg.getScreenCTM().inverse());
  }

  function _criarOverlayClicavel() {
    const ns = "http://www.w3.org/2000/svg";
    const overlay = document.createElementNS(ns, "rect");
    overlay.setAttribute("x", 0);
    overlay.setAttribute("y", 0);
    overlay.setAttribute("width", elSvg.getAttribute("width") || "100%");
    overlay.setAttribute("height", elSvg.getAttribute("height") || "100%");
    overlay.setAttribute("fill", "transparent");
    overlay.style.cursor = "crosshair";
    elSvg.appendChild(overlay);
    return overlay;
  }

  // Modo de amostra: o usuário pode clicar em UM OU MAIS pontos de
  // estufas conhecidas (útil para coberturas listradas/ripadas, onde
  // um único ponto não representa toda a variação de cor). Cada
  // clique adiciona um marcador visual e dispara aoAdicionarPonto.
  // O modo continua ativo até finalizarModoInterativo() ser chamado.
  function iniciarModoAmostra(aoAdicionarPonto) {
    const ns = "http://www.w3.org/2000/svg";
    const overlay = _criarOverlayClicavel();
    const marcadores = [];

    overlay.addEventListener("click", (evento) => {
      const { x, y } = _pontoDoEvento(evento);
      const marcador = document.createElementNS(ns, "circle");
      marcador.setAttribute("cx", x);
      marcador.setAttribute("cy", y);
      marcador.setAttribute("r", 5);
      marcador.setAttribute("class", "marcador-amostra");
      elSvg.appendChild(marcador);
      marcadores.push(marcador);
      aoAdicionarPonto(x, y);
    });

    return function finalizar() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      marcadores.forEach((m) => m.parentNode && m.parentNode.removeChild(m));
    };
  }

  // Modo de desenho manual: o usuário clica nos cantos de uma estufa
  // para desenhar seu contorno à mão. Mostra uma linha (polyline) em
  // tempo real ligando os pontos já clicados.
  function iniciarModoDesenho(aoAdicionarPonto) {
    const ns = "http://www.w3.org/2000/svg";
    const overlay = _criarOverlayClicavel();
    const pontos = [];

    const linha = document.createElementNS(ns, "polyline");
    linha.setAttribute("class", "linha-desenho");
    linha.setAttribute("points", "");
    elSvg.appendChild(linha);

    function _atualizarLinha() {
      linha.setAttribute("points", _pontosParaAtributo(pontos));
    }

    overlay.addEventListener("click", (evento) => {
      const bruto = _pontoDoEvento(evento);
      const ponto = { x: bruto.x, y: bruto.y };
      pontos.push(ponto);

      const marcador = document.createElementNS(ns, "circle");
      marcador.setAttribute("cx", ponto.x);
      marcador.setAttribute("cy", ponto.y);
      marcador.setAttribute("r", 5);
      marcador.setAttribute("class", "marcador-amostra");
      elSvg.appendChild(marcador);

      _atualizarLinha();
      aoAdicionarPonto(pontos.length);
    });

    return {
      obterPontos: () => pontos.slice(),
      finalizar: () => {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        elSvg.querySelectorAll(".marcador-amostra").forEach((m) => m.remove());
        linha.remove();
      },
    };
  }

  return {
    iniciar,
    mostrarVazio,
    carregar,
    marcarEstufaSelecionada,
    marcarAreaSelecionada,
    atualizarRotulo,
    atualizarCorArea,
    atualizarRotuloArea,
    iniciarModoAmostra,
    iniciarModoDesenho,
  };
})();
