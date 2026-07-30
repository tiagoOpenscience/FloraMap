// api.js — camada única de comunicação com o backend do FloraMap.
// Nenhum outro módulo do frontend deve chamar fetch() diretamente.

const Api = {
  async listarProjetos() {
    const resp = await fetch("/api/projetos");
    return Api._tratarResposta(resp);
  },

  async criarProjeto(nome) {
    const resp = await fetch("/api/projetos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome }),
    });
    return Api._tratarResposta(resp);
  },

  async obterProjeto(projetoId) {
    const resp = await fetch(`/api/projetos/${projetoId}`);
    return Api._tratarResposta(resp);
  },

  async renomearProjeto(projetoId, nome) {
    return Api.atualizarProjeto(projetoId, { nome });
  },

  async atualizarProjeto(projetoId, campos) {
    const resp = await fetch(`/api/projetos/${projetoId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(campos),
    });
    return Api._tratarResposta(resp);
  },

  async obterResumoProjeto(projetoId) {
    const resp = await fetch(`/api/projetos/${projetoId}/resumo`);
    return Api._tratarResposta(resp);
  },

  async excluirProjeto(projetoId) {
    const resp = await fetch(`/api/projetos/${projetoId}`, { method: "DELETE" });
    return Api._tratarResposta(resp);
  },

  async enviarImagemProjeto(projetoId, arquivo) {
    const formData = new FormData();
    formData.append("imagem", arquivo);
    const resp = await fetch(`/api/projetos/${projetoId}/imagem`, {
      method: "POST",
      body: formData,
    });
    return Api._tratarResposta(resp);
  },

  async listarEstufas(projetoId) {
    const resp = await fetch(`/api/projetos/${projetoId}/estufas`);
    return Api._tratarResposta(resp);
  },

  async detectarEstufas(projetoId, pontos) {
    const resp = await fetch(`/api/projetos/${projetoId}/detectar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amostras: pontos || [] }),
    });
    return Api._tratarResposta(resp);
  },

  async criarEstufaManual(projetoId, poligono) {
    const resp = await fetch(`/api/projetos/${projetoId}/estufas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ poligono }),
    });
    return Api._tratarResposta(resp);
  },

  async atualizarEstufa(estufaId, campos) {
    const resp = await fetch(`/api/estufas/${estufaId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(campos),
    });
    return Api._tratarResposta(resp);
  },

  async dividirEstufa(estufaId, quantidade, orientacao) {
    const resp = await fetch(`/api/estufas/${estufaId}/dividir`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantidade, orientacao }),
    });
    return Api._tratarResposta(resp);
  },

  async excluirEstufa(estufaId) {
    const resp = await fetch(`/api/estufas/${estufaId}`, { method: "DELETE" });
    return Api._tratarResposta(resp);
  },

  async restaurarEstufas(projetoId, estufas) {
    const resp = await fetch(`/api/projetos/${projetoId}/estufas/restaurar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estufas }),
    });
    return Api._tratarResposta(resp);
  },

  urlExportarCsv(projetoId) {
    return `/api/projetos/${projetoId}/exportar/csv`;
  },

  urlExportarPdf(projetoId) {
    return `/api/projetos/${projetoId}/exportar/pdf`;
  },

  async gerarAreas(estufaId, quantidade, orientacao) {
    const resp = await fetch(`/api/estufas/${estufaId}/gerar-areas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantidade, orientacao }),
    });
    return Api._tratarResposta(resp);
  },

  async atualizarArea(areaId, campos) {
    const resp = await fetch(`/api/areas/${areaId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(campos),
    });
    return Api._tratarResposta(resp);
  },

  async excluirArea(areaId) {
    const resp = await fetch(`/api/areas/${areaId}`, { method: "DELETE" });
    return Api._tratarResposta(resp);
  },

  async listarVariedades() {
    const resp = await fetch("/api/variedades");
    return Api._tratarResposta(resp);
  },

  async criarVariedade(nome, cor) {
    const resp = await fetch("/api/variedades", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, cor }),
    });
    return Api._tratarResposta(resp);
  },

  async atualizarVariedade(variedadeId, campos) {
    const resp = await fetch(`/api/variedades/${variedadeId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(campos),
    });
    return Api._tratarResposta(resp);
  },

  async _tratarResposta(resp) {
    const dados = await resp.json().catch(() => null);
    if (!resp.ok) {
      const mensagem = (dados && dados.erro) || "Erro inesperado na API.";
      throw new Error(mensagem);
    }
    return dados;
  },
};
