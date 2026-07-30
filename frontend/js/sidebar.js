// sidebar.js — painel lateral contextual. Visão Geral é o estado
// padrão (mostrado quando nada está selecionado); ao selecionar uma
// Estufa ou Área, aparece um link "← Visão Geral" no topo para voltar.

const Sidebar = (() => {
  let elConteudo;

  function iniciar({ conteudo }) {
    elConteudo = conteudo;
  }

  function _escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto ?? "";
    return div.innerHTML;
  }

  function _criarStatusSalvamento(idStatus, idTexto) {
    const statusEl = document.getElementById(idStatus);
    const statusTexto = document.getElementById(idTexto);
    const temporizadores = {};

    return function agendarSalvar(chave, salvarFn, { imediato = false } = {}) {
      statusEl.classList.add("salvando");
      statusTexto.textContent = "Salvando...";
      clearTimeout(temporizadores[chave]);
      const executar = async () => {
        try {
          await salvarFn();
          statusEl.classList.remove("salvando");
          statusTexto.textContent = "Salvo automaticamente";
        } catch (erro) {
          statusEl.classList.remove("salvando");
          statusTexto.textContent = erro.message || "Erro ao salvar";
        }
      };
      if (imediato) {
        executar();
      } else {
        temporizadores[chave] = setTimeout(executar, 500);
      }
    };
  }

  // ---------- Visão Geral (estado padrão) ----------

  async function mostrarVisaoGeral(projetoId) {
    elConteudo.innerHTML = `
      <p class="sidebar__titulo">Visão Geral</p>
      <p class="sidebar__subtitulo">Clique em uma estufa no mapa (ou no rótulo dela) para editar.</p>

      <div class="resumo-contadores">
        <div class="resumo-contador">
          <span class="resumo-contador__numero" id="resumo-total-estufas">…</span>
          <span class="resumo-contador__rotulo">Estufas</span>
        </div>
        <div class="resumo-contador">
          <span class="resumo-contador__numero" id="resumo-total-areas">…</span>
          <span class="resumo-contador__rotulo">Áreas</span>
        </div>
      </div>

      <p class="sidebar__subtitulo" style="margin-top:18px;">Áreas por variedade</p>
      <ul id="resumo-variedades" class="lista-variedades"></ul>

      <div class="exportar-acoes">
        <a href="${Api.urlExportarPdf(projetoId)}" target="_blank" rel="noopener">Exportar PDF</a>
        <a href="${Api.urlExportarCsv(projetoId)}" target="_blank" rel="noopener">Exportar CSV</a>
      </div>

      <label for="resumo-observacao">Observações</label>
      <textarea id="resumo-observacao" rows="3" placeholder="Anotações rápidas sobre este projeto..."></textarea>

      <label for="resumo-analise">Análise geral</label>
      <textarea id="resumo-analise" rows="4" placeholder="Uma análise mais completa da situação do projeto..."></textarea>

      <div class="status-salvamento" id="status-salvamento">
        <span class="status-salvamento__ponto"></span>
        <span id="status-salvamento-texto">Salvo automaticamente</span>
      </div>
    `;

    const elObservacao = document.getElementById("resumo-observacao");
    const elAnalise = document.getElementById("resumo-analise");
    const agendarSalvar = _criarStatusSalvamento("status-salvamento", "status-salvamento-texto");

    elObservacao.addEventListener("input", () => {
      agendarSalvar("observacao", () => Api.atualizarProjeto(projetoId, { observacao: elObservacao.value }));
    });
    elAnalise.addEventListener("input", () => {
      agendarSalvar("analise_geral", () => Api.atualizarProjeto(projetoId, { analise_geral: elAnalise.value }));
    });

    try {
      const [projeto, resumo] = await Promise.all([
        Api.obterProjeto(projetoId),
        Api.obterResumoProjeto(projetoId),
      ]);
      document.getElementById("resumo-total-estufas").textContent = resumo.total_estufas;
      document.getElementById("resumo-total-areas").textContent = resumo.total_areas;
      elObservacao.value = projeto.observacao || "";
      elAnalise.value = projeto.analise_geral || "";
      _renderizarVariedadesResumo(resumo.areas_por_variedade);
    } catch (erro) {
      // painel simplesmente fica com os contadores em "…" se falhar
    }
  }

  function _renderizarVariedadesResumo(itens) {
    const lista = document.getElementById("resumo-variedades");
    if (!lista) return;
    lista.innerHTML = "";

    if (!itens || itens.length === 0) {
      const vazio = document.createElement("li");
      vazio.textContent = "Nenhuma área com dados ainda.";
      lista.appendChild(vazio);
      return;
    }

    for (const item of itens) {
      const li = document.createElement("li");

      const cor = document.createElement("span");
      cor.className = "lista-variedades__cor";
      cor.style.background = item.variedade_cor || "var(--cor-neutra-area)";
      cor.style.border = "1px solid var(--cor-borda)";

      const nome = document.createElement("span");
      nome.style.flex = "1";
      nome.textContent = item.variedade_nome;

      const contagem = document.createElement("span");
      contagem.className = "lista-variedades__contagem";
      contagem.textContent = `${item.quantidade} área(s)`;

      li.appendChild(cor);
      li.appendChild(nome);
      li.appendChild(contagem);
      lista.appendChild(li);
    }
  }

  function _botaoVoltarGeral(aoVoltarGeral) {
    return `<button type="button" id="botao-voltar-geral" class="link-voltar">← Visão Geral</button>`;
  }

  // ---------- Estufa ----------

  function _opcoesOrientacao(selecionada) {
    const opcoes = [
      ["auto", "Automático (eixo mais longo)"],
      ["vertical", "Vertical (colunas lado a lado)"],
      ["horizontal", "Horizontal (linhas empilhadas)"],
    ];
    return opcoes
      .map(([valor, rotulo]) => {
        const sel = valor === selecionada ? "selected" : "";
        return `<option value="${valor}" ${sel}>${rotulo}</option>`;
      })
      .join("");
  }

  function mostrarEstufa(estufa, { aoAtualizar, aoGerarAreas, aoDividir, aoExcluir, aoVoltarGeral }) {
    elConteudo.innerHTML = `
      ${_botaoVoltarGeral()}
      <p class="sidebar__titulo">Estufa</p>
      <p class="sidebar__subtitulo">Selecionada no mapa</p>

      <label for="campo-numero">Número</label>
      <input type="number" id="campo-numero" min="1" value="${estufa.numero}" />

      <label for="campo-nome">Nome</label>
      <input type="text" id="campo-nome" value="${_escaparHtml(estufa.nome)}" />

      <label for="campo-qtd-areas">Quantidade de áreas</label>
      <input type="number" id="campo-qtd-areas" min="1" value="${estufa.quantidade_areas || 1}" />

      <label for="campo-orientacao-areas">Direção das áreas</label>
      <select id="campo-orientacao-areas">
        ${_opcoesOrientacao(estufa.orientacao_areas || "auto")}
      </select>

      <button type="button" id="botao-gerar-areas" class="primario" style="margin-top:10px; width:100%;">Gerar áreas</button>
      <p id="erro-gerar-areas" style="color: var(--cor-perigo); font-size: 12px; margin: 4px 0 0;"></p>

      <hr style="border:none; border-top:1px solid var(--cor-borda); margin:18px 0;" />

      <p class="sidebar__subtitulo" style="margin-bottom:6px;">
        A detecção juntou duas estufas vizinhas por engano? Divida esta estufa em partes separadas.
      </p>
      <label for="campo-qtd-divisao">Dividir em quantas partes</label>
      <input type="number" id="campo-qtd-divisao" min="2" value="2" />
      <label for="campo-orientacao-divisao">Direção do corte</label>
      <select id="campo-orientacao-divisao">
        ${_opcoesOrientacao("auto")}
      </select>
      <button type="button" id="botao-dividir" style="margin-top:10px; width:100%;">Dividir estufa</button>
      <p id="erro-dividir" style="color: var(--cor-perigo); font-size: 12px; margin: 4px 0 0;"></p>

      <div class="status-salvamento" id="status-salvamento">
        <span class="status-salvamento__ponto"></span>
        <span id="status-salvamento-texto">Salvo automaticamente</span>
      </div>

      <hr style="border:none; border-top:1px solid var(--cor-borda); margin:18px 0;" />
      <button type="button" id="botao-excluir-estufa" class="botao-perigo" style="width:100%;">Excluir estufa</button>
    `;

    document.getElementById("botao-voltar-geral").addEventListener("click", aoVoltarGeral);

    const campoNumero = document.getElementById("campo-numero");
    const campoNome = document.getElementById("campo-nome");
    const campoQtdAreas = document.getElementById("campo-qtd-areas");
    const campoOrientacaoAreas = document.getElementById("campo-orientacao-areas");
    const botaoGerarAreas = document.getElementById("botao-gerar-areas");
    const erroGerarAreas = document.getElementById("erro-gerar-areas");

    const campoQtdDivisao = document.getElementById("campo-qtd-divisao");
    const campoOrientacaoDivisao = document.getElementById("campo-orientacao-divisao");
    const botaoDividir = document.getElementById("botao-dividir");
    const erroDividir = document.getElementById("erro-dividir");
    const botaoExcluir = document.getElementById("botao-excluir-estufa");

    const agendarSalvar = _criarStatusSalvamento("status-salvamento", "status-salvamento-texto");

    campoNumero.addEventListener("change", () => {
      const numero = Number(campoNumero.value);
      if (Number.isInteger(numero) && numero > 0) {
        agendarSalvar("numero", async () => {
          const atualizado = await aoAtualizar(estufa.id, { numero });
          Object.assign(estufa, atualizado);
        });
      }
    });

    campoNome.addEventListener("input", () => {
      agendarSalvar("nome", async () => {
        const atualizado = await aoAtualizar(estufa.id, { nome: campoNome.value });
        Object.assign(estufa, atualizado);
      });
    });

    botaoGerarAreas.addEventListener("click", async () => {
      erroGerarAreas.textContent = "";
      const quantidade = Number(campoQtdAreas.value);
      const orientacao = campoOrientacaoAreas.value;

      if (!Number.isInteger(quantidade) || quantidade < 1) {
        erroGerarAreas.textContent = "Informe uma quantidade válida (mínimo 1).";
        return;
      }

      if ((estufa.areas || []).length > 0) {
        const confirmado = confirm(
          "Esta estufa já tem áreas geradas. Gerar novamente substitui todas as áreas e os dados preenchidos nelas. Continuar? (Ctrl+Z desfaz depois, se precisar.)"
        );
        if (!confirmado) return;
      }

      botaoGerarAreas.disabled = true;
      try {
        await aoGerarAreas(estufa.id, quantidade, orientacao);
      } catch (erro) {
        erroGerarAreas.textContent = erro.message;
      } finally {
        botaoGerarAreas.disabled = false;
      }
    });

    botaoDividir.addEventListener("click", async () => {
      erroDividir.textContent = "";
      const quantidade = Number(campoQtdDivisao.value);
      const orientacao = campoOrientacaoDivisao.value;

      if (!Number.isInteger(quantidade) || quantidade < 2) {
        erroDividir.textContent = "Informe pelo menos 2 partes.";
        return;
      }

      const avisoAreas = (estufa.areas || []).length > 0
        ? " As áreas já geradas nela serão perdidas."
        : "";
      const confirmado = confirm(
        `Dividir esta estufa em ${quantidade} novas estufas separadas?${avisoAreas} (Ctrl+Z desfaz depois, se precisar.)`
      );
      if (!confirmado) return;

      botaoDividir.disabled = true;
      try {
        await aoDividir(estufa.id, quantidade, orientacao);
      } catch (erro) {
        erroDividir.textContent = erro.message;
        botaoDividir.disabled = false;
      }
    });

    botaoExcluir.addEventListener("click", async () => {
      const confirmado = confirm(
        `Excluir a Estufa ${estufa.numero} (${estufa.nome}) e todas as suas áreas? (Ctrl+Z desfaz depois, se precisar.)`
      );
      if (!confirmado) return;
      botaoExcluir.disabled = true;
      try {
        await aoExcluir(estufa.id);
      } catch (erro) {
        alert(erro.message);
        botaoExcluir.disabled = false;
      }
    });
  }

  // ---------- Área ----------

  function mostrarArea(area, estufa, { variedades, aoAtualizar, aoVoltarParaEstufa, aoExcluir, aoVoltarGeral }) {
    const opcoesVariedade = variedades
      .map((v) => {
        const selecionada = area.variedade_id === v.id ? "selected" : "";
        return `<option value="${v.id}" ${selecionada}>${_escaparHtml(v.nome)}</option>`;
      })
      .join("");

    elConteudo.innerHTML = `
      ${_botaoVoltarGeral()}
      <button type="button" id="botao-voltar-estufa" style="margin: 8px 0 12px; width:100%;">← Editar Estufa ${estufa.numero}</button>
      <p class="sidebar__titulo">Área ${area.ordem} (Estufa ${estufa.numero})</p>
      <p class="sidebar__subtitulo">Selecionada no mapa</p>

      <label for="campo-variedade">Variedade</label>
      <select id="campo-variedade">
        <option value="">— Selecione —</option>
        ${opcoesVariedade}
      </select>

      <label for="campo-fase">Fase</label>
      <input type="text" id="campo-fase" value="${_escaparHtml(area.fase)}" />

      <label for="campo-vaos">Vãos</label>
      <input type="text" id="campo-vaos" value="${_escaparHtml(area.vaos)}" />

      <label for="campo-canteiros">Canteiros</label>
      <input type="text" id="campo-canteiros" value="${_escaparHtml(area.canteiros)}" />

      <label for="campo-postinhos">Postinhos</label>
      <input type="text" id="campo-postinhos" value="${_escaparHtml(area.postinhos)}" />

      <div class="status-salvamento" id="status-salvamento">
        <span class="status-salvamento__ponto"></span>
        <span id="status-salvamento-texto">Salvo automaticamente</span>
      </div>

      <hr style="border:none; border-top:1px solid var(--cor-borda); margin:18px 0;" />
      <button type="button" id="botao-excluir-area" class="botao-perigo" style="width:100%;">Excluir área</button>
    `;

    document.getElementById("botao-voltar-geral").addEventListener("click", aoVoltarGeral);
    document.getElementById("botao-voltar-estufa").addEventListener("click", () => {
      aoVoltarParaEstufa(estufa);
    });

    const campoVariedade = document.getElementById("campo-variedade");
    const campoFase = document.getElementById("campo-fase");
    const campoVaos = document.getElementById("campo-vaos");
    const campoCanteiros = document.getElementById("campo-canteiros");
    const campoPostinhos = document.getElementById("campo-postinhos");
    const botaoExcluir = document.getElementById("botao-excluir-area");
    const agendarSalvar = _criarStatusSalvamento("status-salvamento", "status-salvamento-texto");

    campoVariedade.addEventListener("change", () => {
      const variedadeId = campoVariedade.value ? Number(campoVariedade.value) : null;
      agendarSalvar("variedade_id", async () => {
        const atualizada = await aoAtualizar(area.id, { variedade_id: variedadeId });
        Object.assign(area, atualizada);
      }, { imediato: true });
    });

    campoFase.addEventListener("input", () => {
      agendarSalvar("fase", async () => {
        const atualizada = await aoAtualizar(area.id, { fase: campoFase.value });
        Object.assign(area, atualizada);
      });
    });

    campoVaos.addEventListener("input", () => {
      agendarSalvar("vaos", async () => {
        const atualizada = await aoAtualizar(area.id, { vaos: campoVaos.value });
        Object.assign(area, atualizada);
      });
    });

    campoCanteiros.addEventListener("input", () => {
      agendarSalvar("canteiros", async () => {
        const atualizada = await aoAtualizar(area.id, { canteiros: campoCanteiros.value });
        Object.assign(area, atualizada);
      });
    });

    campoPostinhos.addEventListener("input", () => {
      agendarSalvar("postinhos", async () => {
        const atualizada = await aoAtualizar(area.id, { postinhos: campoPostinhos.value });
        Object.assign(area, atualizada);
      });
    });

    botaoExcluir.addEventListener("click", async () => {
      const confirmado = confirm(
        `Excluir a Área ${area.ordem}? (Ctrl+Z desfaz depois, se precisar.)`
      );
      if (!confirmado) return;
      botaoExcluir.disabled = true;
      try {
        await aoExcluir(area.id, estufa);
      } catch (erro) {
        alert(erro.message);
        botaoExcluir.disabled = false;
      }
    });
  }

  return { iniciar, mostrarVisaoGeral, mostrarEstufa, mostrarArea };
})();
