// home.js — comportamento da tela inicial (lista/criação de projetos).

document.addEventListener("DOMContentLoaded", () => {
  const lista = document.getElementById("lista-projetos");
  const form = document.getElementById("form-novo-projeto");
  const inputNome = document.getElementById("input-nome-projeto");
  const erroEl = document.getElementById("erro-novo-projeto");

  function formatarData(isoString) {
    const data = new Date(isoString.replace(" ", "T") + "Z");
    if (Number.isNaN(data.getTime())) return "";
    return data.toLocaleDateString("pt-BR");
  }

  function renderizarProjetos(projetos) {
    lista.innerHTML = "";

    if (projetos.length === 0) {
      const vazio = document.createElement("div");
      vazio.className = "estado-vazio";
      vazio.textContent = "Nenhum projeto ainda. Crie o primeiro acima.";
      lista.appendChild(vazio);
      return;
    }

    for (const projeto of projetos) {
      const item = document.createElement("li");

      const link = document.createElement("a");
      link.href = `/projeto.html?id=${projeto.id}`;

      const nome = document.createElement("span");
      nome.className = "nome-projeto";
      nome.textContent = projeto.nome;

      const data = document.createElement("span");
      data.className = "data-projeto";
      data.textContent = projeto.criado_em ? formatarData(projeto.criado_em) : "";

      link.appendChild(nome);
      link.appendChild(data);

      const acoes = document.createElement("div");
      acoes.className = "item-projeto__acoes";

      const botaoRenomear = document.createElement("button");
      botaoRenomear.type = "button";
      botaoRenomear.textContent = "Renomear";
      botaoRenomear.addEventListener("click", () => renomearProjeto(projeto));

      const botaoExcluir = document.createElement("button");
      botaoExcluir.type = "button";
      botaoExcluir.textContent = "Excluir";
      botaoExcluir.addEventListener("click", () => excluirProjeto(projeto));

      acoes.appendChild(botaoRenomear);
      acoes.appendChild(botaoExcluir);

      item.appendChild(link);
      item.appendChild(acoes);
      lista.appendChild(item);
    }
  }

  async function renomearProjeto(projeto) {
    const novoNome = prompt("Novo nome do projeto:", projeto.nome);
    if (novoNome === null) return;

    const nomeLimpo = novoNome.trim();
    if (!nomeLimpo || nomeLimpo === projeto.nome) return;

    try {
      await Api.renomearProjeto(projeto.id, nomeLimpo);
      await carregarProjetos();
    } catch (erro) {
      alert(erro.message);
    }
  }

  async function excluirProjeto(projeto) {
    const confirmado = confirm(
      `Excluir o projeto "${projeto.nome}"? Todas as estufas e áreas dele também serão apagadas. Esta ação não pode ser desfeita.`
    );
    if (!confirmado) return;

    try {
      await Api.excluirProjeto(projeto.id);
      await carregarProjetos();
    } catch (erro) {
      alert(erro.message);
    }
  }

  async function carregarProjetos() {
    try {
      const projetos = await Api.listarProjetos();
      renderizarProjetos(projetos);
    } catch (erro) {
      lista.innerHTML = "";
      const vazio = document.createElement("div");
      vazio.className = "estado-vazio";
      vazio.textContent = "Não foi possível carregar os projetos.";
      lista.appendChild(vazio);
    }
  }

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erroEl.textContent = "";

    const nome = inputNome.value.trim();
    if (!nome) {
      erroEl.textContent = "Informe um nome para o projeto.";
      return;
    }

    try {
      const projeto = await Api.criarProjeto(nome);
      window.location.href = `/projeto.html?id=${projeto.id}`;
    } catch (erro) {
      erroEl.textContent = erro.message;
    }
  });

  carregarProjetos();
});
