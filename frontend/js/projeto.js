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

  const bannerAmostra = document.getElementById("banner-amostra");
  const textoBanner = document.getElementById("texto-banner-amostra");
  const botaoConcluirAmostra = document.getElementById("botao-concluir-amostra");
  const botaoCancelarAmostra = document.getElementById("botao-cancelar-amostra");

  let projetoAtual = null;

  function encontrarEstufa(estufaId) {
    return (projetoAtual?.estufas || []).find((e) => e.id === Number(estufaId));
  }

  function mostrarVisaoGeral() {
    Sidebar.mostrarVisaoGeral(projetoId);
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

  Mapa.iniciar({
    vazio: document.getElementById("mapa-vazio"),
    palco: document.getElementById("mapa-palco"),
    imagem: document.getElementById("mapa-imagem"),
    svg: document.getElementById("mapa-svg"),
    aoSelecionarEstufa: selecionarEstufa,
    aoSelecionarArea: selecionarArea,
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

    if (projetoAtual.imagem_path) {
      Mapa.carregar({ imagemUrl: projetoAtual.imagem_path, estufas: projetoAtual.estufas || [] });
    } else {
      Mapa.mostrarVazio();
    }

    if (!manterSidebar) {
      mostrarVisaoGeral();
    }
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

  botaoCancelarAmostra.addEventListener("click", () => {
    _encerrarBanner();
  });

  await carregarProjeto();
});
