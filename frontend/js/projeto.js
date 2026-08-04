// projeto.js — orquestra a tela principal: carrega o projeto, liga a
// toolbar, o módulo Mapa, o módulo Sidebar (Visão Geral é o estado
// padrão), o modal de Variedades e o sistema de desfazer (Ctrl+Z).

document.addEventListener("DOMContentLoaded", async () => {
  const params = new URLSearchParams(window.location.search);
  const projetoId = params.get("id");

  const elNomeProjeto = document.getElementById("nome-projeto");
  const inputImagem = document.getElementById("input-imagem");
  const botaoDetectar = document.getElementById("botao-detectar");
  const botaoDesenhar = document.getElementById("botao-desenhar");
  const botaoAdicionarEntrada = document.getElementById("botao-adicionar-entrada");
  const botaoAdicionarSaida = document.getElementById("botao-adicionar-saida");

  const bannerAmostra = document.getElementById("banner-amostra");
  const textoBanner = document.getElementById("texto-banner-amostra");
  const botaoConcluirAmostra = document.getElementById("botao-concluir-amostra");
  const botaoCancelarAmostra = document.getElementById("botao-cancelar-amostra");
  const legendaAcessos = document.getElementById("legenda-acessos");
  const legendaVariedades = document.getElementById("legenda-variedades");

  // Deixa o banner de amostra/desenho arrastável: por padrão ele fica
  // centralizado no topo do mapa e pode acabar bloqueando a visualização
  // da estufa que o usuário está tentando clicar.
  function _tornarArrastavel(elemento) {
    let arrastando = false;
    let offsetX = 0;
    let offsetY = 0;

    elemento.addEventListener("mousedown", (evento) => {
      if (evento.target.closest("button")) return;
      const pai = elemento.offsetParent.getBoundingClientRect();
      const rect = elemento.getBoundingClientRect();
      arrastando = true;
      offsetX = evento.clientX - rect.left;
      offsetY = evento.clientY - rect.top;
      elemento.style.left = `${rect.left - pai.left}px`;
      elemento.style.top = `${rect.top - pai.top}px`;
      elemento.style.transform = "none";
      evento.preventDefault();
    });

    document.addEventListener("mousemove", (evento) => {
      if (!arrastando) return;
      const pai = elemento.offsetParent.getBoundingClientRect();
      const novoLeft = Math.max(
        0,
        Math.min(evento.clientX - pai.left - offsetX, pai.width - elemento.offsetWidth)
      );
      const novoTop = Math.max(
        0,
        Math.min(evento.clientY - pai.top - offsetY, pai.height - elemento.offsetHeight)
      );
      elemento.style.left = `${novoLeft}px`;
      elemento.style.top = `${novoTop}px`;
    });

    document.addEventListener("mouseup", () => {
      arrastando = false;
    });
  }

  _tornarArrastavel(bannerAmostra);

  let projetoAtual = null;

  function encontrarEstufa(estufaId) {
    return (projetoAtual?.estufas || []).find((e) => e.id === Number(estufaId));
  }

  function mostrarVisaoGeral() {
    Sidebar.mostrarVisaoGeral(projetoId);
  }

  // Legenda de variedades (canto inferior direito do mapa): mostra só
  // as variedades realmente em uso em alguma área deste projeto, para
  // não listar o cadastro global inteiro sem relação com o mapa atual.
  function atualizarLegendaVariedades() {
    const vistos = new Map();
    for (const estufa of projetoAtual?.estufas || []) {
      for (const area of estufa.areas || []) {
        if (area.variedade_id && area.variedade_cor) {
          vistos.set(area.variedade_id, { nome: area.variedade_nome, cor: area.variedade_cor });
        }
      }
    }

    const itens = Array.from(vistos.values()).sort((a, b) => a.nome.localeCompare(b.nome));

    legendaVariedades.innerHTML = "";
    if (itens.length === 0) {
      legendaVariedades.hidden = true;
      return;
    }

    const titulo = document.createElement("div");
    titulo.className = "legenda-variedades__titulo";
    titulo.textContent = "Variedades";
    legendaVariedades.appendChild(titulo);

    for (const item of itens) {
      const linha = document.createElement("div");
      linha.className = "legenda-variedades__item";

      const cor = document.createElement("span");
      cor.className = "legenda-variedades__cor";
      cor.style.background = item.cor;
      linha.appendChild(cor);

      const nome = document.createElement("span");
      nome.className = "legenda-variedades__nome";
      nome.textContent = item.nome;
      linha.appendChild(nome);

      legendaVariedades.appendChild(linha);
    }

    legendaVariedades.hidden = !projetoAtual?.imagem_path;
  }

  async function selecionarEstufa(estufa) {
    Mapa.marcarEstufaSelecionada(estufa.id);
    Sidebar.mostrarEstufa(estufa, {
      aoVoltarGeral: mostrarVisaoGeral,
      aoAtualizar: async (estufaId, campos) => {
        const atualizada = await Api.atualizarEstufa(estufaId, campos);
        Mapa.atualizarRotulo(estufaId, atualizada.numero, atualizada.nome);
        Object.assign(estufa, atualizada);
        return atualizada;
      },
      aoGerarAreas: async (estufaId, quantidade, orientacao) => {
        Undo.registrar(projetoId, projetoAtual.estufas);
        await Api.gerarAreas(estufaId, quantidade, orientacao);
        await carregarProjeto({ manterSidebar: true });
        const estufaAtualizada = encontrarEstufa(estufaId);
        if (estufaAtualizada) {
          await selecionarEstufa(estufaAtualizada);
        }
      },
      aoDividir: async (estufaId, quantidade, orientacao) => {
        Undo.registrar(projetoId, projetoAtual.estufas);
        await Api.dividirEstufa(estufaId, quantidade, orientacao);
        await carregarProjeto({ manterSidebar: true });
        mostrarVisaoGeral(); // a estufa original deixou de existir
      },
      aoExcluir: async (estufaId) => {
        Undo.registrar(projetoId, projetoAtual.estufas);
        await Api.excluirEstufa(estufaId);
        await carregarProjeto({ manterSidebar: true });
        mostrarVisaoGeral();
      },
    });
  }

  async function selecionarArea(area, estufa) {
    Mapa.marcarAreaSelecionada(area.id);
    const variedades = await Api.listarVariedades();
    Sidebar.mostrarArea(area, estufa, {
      variedades,
      aoVoltarGeral: mostrarVisaoGeral,
      aoAtualizar: async (areaId, campos) => {
        const atualizada = await Api.atualizarArea(areaId, campos);
        Mapa.atualizarCorArea(areaId, atualizada.variedade_cor);
        Mapa.atualizarRotuloArea(areaId, atualizada);
        Object.assign(area, atualizada);
        atualizarLegendaVariedades();
        return atualizada;
      },
      aoVoltarParaEstufa: (estufaDaArea) => {
        const estufaAtual = encontrarEstufa(estufaDaArea.id) || estufaDaArea;
        selecionarEstufa(estufaAtual);
      },
      aoExcluir: async (areaId, estufaDaArea) => {
        Undo.registrar(projetoId, projetoAtual.estufas);
        await Api.excluirArea(areaId);
        await carregarProjeto({ manterSidebar: true });
        const estufaAtualizada = encontrarEstufa(estufaDaArea.id);
        if (estufaAtualizada) {
          await selecionarEstufa(estufaAtualizada);
        } else {
          mostrarVisaoGeral();
        }
      },
    });
  }

  async function excluirPontoAcesso(ponto) {
    const rotulo = ponto.tipo === "entrada" ? "entrada" : "saída";
    const confirmado = confirm(`Remover esta marcação de ${rotulo}?`);
    if (!confirmado) return;

    try {
      await Api.excluirPontoAcesso(ponto.id);
      Mapa.removerMarcadorAcesso(ponto.id);
      if (projetoAtual) {
        projetoAtual.pontos_acesso = (projetoAtual.pontos_acesso || []).filter(
          (p) => p.id !== ponto.id
        );
      }
    } catch (erro) {
      alert(erro.message);
    }
  }

  Mapa.iniciar({
    vazio: document.getElementById("mapa-vazio"),
    palco: document.getElementById("mapa-palco"),
    imagem: document.getElementById("mapa-imagem"),
    svg: document.getElementById("mapa-svg"),
    aoSelecionarEstufa: selecionarEstufa,
    aoSelecionarArea: selecionarArea,
    aoClicarAcesso: excluirPontoAcesso,
  });

  Sidebar.iniciar({
    conteudo: document.getElementById("sidebar-conteudo"),
  });

  Variedades.iniciar({
    modal: document.getElementById("modal-variedades"),
    botaoAbrir: document.getElementById("botao-variedades"),
    botaoFechar: document.getElementById("botao-fechar-variedades"),
    lista: document.getElementById("lista-variedades"),
    form: document.getElementById("form-nova-variedade"),
    inputNome: document.getElementById("input-nome-variedade"),
    inputCor: document.getElementById("input-cor-variedade"),
    erro: document.getElementById("erro-variedade"),
    aoMudar: async () => {
      // Cores de variedades podem ter mudado; recarrega para refletir
      // imediatamente nas áreas já pintadas no mapa.
      await carregarProjeto({ manterSidebar: true });
    },
  });

  document.getElementById("botao-visao-geral").addEventListener("click", mostrarVisaoGeral);

  document.getElementById("botao-sair").addEventListener("click", async () => {
    await Api.logout();
    window.location.href = "/login.html";
  });

  Undo.iniciar({
    aoRestaurar: async (idDoProjeto, snapshot) => {
      await Api.restaurarEstufas(idDoProjeto, snapshot);
      await carregarProjeto({ manterSidebar: true });
      mostrarVisaoGeral();
    },
  });

  if (!projetoId) {
    elNomeProjeto.textContent = "Projeto não encontrado";
    return;
  }

  async function carregarProjeto({ manterSidebar = false } = {}) {
    try {
      projetoAtual = await Api.obterProjeto(projetoId);
    } catch (erro) {
      elNomeProjeto.textContent = "Projeto não encontrado";
      return;
    }

    elNomeProjeto.textContent = projetoAtual.nome;
    botaoDetectar.disabled = !projetoAtual.imagem_path;
    botaoDesenhar.disabled = !projetoAtual.imagem_path;
    botaoAdicionarEntrada.disabled = !projetoAtual.imagem_path;
    botaoAdicionarSaida.disabled = !projetoAtual.imagem_path;
    legendaAcessos.hidden = !projetoAtual.imagem_path;

    if (projetoAtual.imagem_path) {
      Mapa.carregar({
        imagemUrl: projetoAtual.imagem_path,
        estufas: projetoAtual.estufas || [],
        pontosAcesso: projetoAtual.pontos_acesso || [],
      });
    } else {
      Mapa.mostrarVazio();
    }

    if (!manterSidebar) {
      mostrarVisaoGeral();
    }

    atualizarLegendaVariedades();
  }

  inputImagem.addEventListener("change", async () => {
    const arquivo = inputImagem.files[0];
    if (!arquivo) return;

    try {
      await Api.enviarImagemProjeto(projetoId, arquivo);
      await carregarProjeto();
    } catch (erro) {
      alert(erro.message);
    } finally {
      inputImagem.value = "";
    }
  });

  // ---------- Modo de amostra (detecção calibrada por clique) ----------

  let finalizarModoAtual = null; // função para remover overlay/marcadores do modo ativo

  function _encerrarBanner() {
    bannerAmostra.hidden = true;
    if (finalizarModoAtual) {
      finalizarModoAtual();
      finalizarModoAtual = null;
    }
  }

  botaoDetectar.addEventListener("click", () => {
    if (!projetoAtual?.imagem_path) return;

    if ((projetoAtual.estufas || []).length > 0) {
      const confirmado = confirm(
        "Detectar estufas novamente? Isso substitui as estufas atuais deste projeto (e suas áreas) pelo resultado da nova detecção. (Ctrl+Z desfaz depois, se precisar.)"
      );
      if (!confirmado) return;
    }

    const pontos = [];
    textoBanner.textContent =
      "Clique em um ou mais pontos de estufas conhecidas (se a cobertura for listrada, clique numa parte clara e noutra escura). Depois clique em Concluir.";
    botaoConcluirAmostra.hidden = false;
    botaoConcluirAmostra.textContent = "Concluir (0 pontos)";
    botaoConcluirAmostra.disabled = true;
    bannerAmostra.hidden = false;

    finalizarModoAtual = Mapa.iniciarModoAmostra((x, y) => {
      pontos.push({ x, y });
      botaoConcluirAmostra.textContent = `Concluir (${pontos.length} ponto${pontos.length > 1 ? "s" : ""})`;
      botaoConcluirAmostra.disabled = false;
    });

    botaoConcluirAmostra.onclick = async () => {
      if (pontos.length === 0) return;
      _encerrarBanner();

      const textoOriginal = botaoDetectar.textContent;
      botaoDetectar.disabled = true;
      botaoDetectar.textContent = "Detectando...";

      Undo.registrar(projetoId, projetoAtual.estufas);
      try {
        await Api.detectarEstufas(projetoId, pontos);
        await carregarProjeto();
      } catch (erro) {
        alert(erro.message);
      } finally {
        botaoDetectar.textContent = textoOriginal;
        botaoDetectar.disabled = !projetoAtual?.imagem_path;
      }
    };
  });

  // ---------- Modo de desenho manual de uma nova estufa ----------

  botaoDesenhar.addEventListener("click", () => {
    if (!projetoAtual?.imagem_path) return;

    textoBanner.textContent =
      "Clique nos cantos da estufa para desenhar o contorno (mínimo 3 pontos). Depois clique em Concluir.";
    botaoConcluirAmostra.hidden = false;
    botaoConcluirAmostra.textContent = "Concluir (0 pontos)";
    botaoConcluirAmostra.disabled = true;
    bannerAmostra.hidden = false;

    const modo = Mapa.iniciarModoDesenho((quantidadePontos) => {
      botaoConcluirAmostra.textContent = `Concluir (${quantidadePontos} ponto${quantidadePontos > 1 ? "s" : ""})`;
      botaoConcluirAmostra.disabled = quantidadePontos < 3;
    });
    finalizarModoAtual = modo.finalizar;

    botaoConcluirAmostra.onclick = async () => {
      const pontos = modo.obterPontos();
      if (pontos.length < 3) return;
      _encerrarBanner();

      Undo.registrar(projetoId, projetoAtual.estufas);
      try {
        await Api.criarEstufaManual(projetoId, pontos);
        await carregarProjeto();
      } catch (erro) {
        alert(erro.message);
      }
    };
  });

  // ---------- Modo de posicionar entrada/saída (marcador único) ----------

  function ativarModoAcesso(tipo, rotulo) {
    if (!projetoAtual?.imagem_path) return;

    textoBanner.textContent = `Clique no mapa para marcar a ${rotulo}.`;
    botaoConcluirAmostra.hidden = true;
    bannerAmostra.hidden = false;

    finalizarModoAtual = Mapa.iniciarModoPonto(async (x, y) => {
      _encerrarBanner();
      try {
        const ponto = await Api.criarPontoAcesso(projetoId, tipo, x, y);
        projetoAtual.pontos_acesso = projetoAtual.pontos_acesso || [];
        projetoAtual.pontos_acesso.push(ponto);
        Mapa.adicionarMarcadorAcesso(ponto);
      } catch (erro) {
        alert(erro.message);
      }
    });
  }

  botaoAdicionarEntrada.addEventListener("click", () => ativarModoAcesso("entrada", "entrada"));
  botaoAdicionarSaida.addEventListener("click", () => ativarModoAcesso("saida", "saída"));

  botaoCancelarAmostra.addEventListener("click", () => {
    _encerrarBanner();
  });

  await carregarProjeto();
});
