// variedades.js — modal de cadastro/edição de Variedades (nome + cor).
// É cadastro global (não pertence a um projeto específico).

const Variedades = (() => {
  let elModal, elLista, elForm, elInputNome, elInputCor, elErro;
  let aoMudarCb = () => {};

  function iniciar({ modal, botaoAbrir, botaoFechar, lista, form, inputNome, inputCor, erro, aoMudar }) {
    elModal = modal;
    elLista = lista;
    elForm = form;
    elInputNome = inputNome;
    elInputCor = inputCor;
    elErro = erro;
    aoMudarCb = aoMudar || (() => {});

    botaoAbrir.addEventListener("click", abrir);
    botaoFechar.addEventListener("click", fechar);
    elModal.addEventListener("click", (evento) => {
      if (evento.target === elModal) fechar();
    });

    elForm.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      elErro.textContent = "";

      const nome = elInputNome.value.trim();
      const cor = elInputCor.value;
      if (!nome) {
        elErro.textContent = "Informe um nome para a variedade.";
        return;
      }

      try {
        await Api.criarVariedade(nome, cor);
        elInputNome.value = "";
        await carregar();
        await aoMudarCb();
      } catch (erro) {
        elErro.textContent = erro.message;
      }
    });
  }

  async function abrir() {
    elModal.hidden = false;
    await carregar();
  }

  function fechar() {
    elModal.hidden = true;
  }

  async function carregar() {
    const variedades = await Api.listarVariedades();
    _renderizar(variedades);
  }

  function _renderizar(variedades) {
    elLista.innerHTML = "";

    if (variedades.length === 0) {
      const vazio = document.createElement("li");
      vazio.textContent = "Nenhuma variedade cadastrada ainda.";
      elLista.appendChild(vazio);
      return;
    }

    for (const variedade of variedades) {
      const item = document.createElement("li");

      const cor = document.createElement("input");
      cor.type = "color";
      cor.className = "lista-variedades__cor";
      cor.value = variedade.cor;
      cor.addEventListener("change", async () => {
        try {
          await Api.atualizarVariedade(variedade.id, { cor: cor.value });
          await aoMudarCb();
        } catch (erro) {
          alert(erro.message);
        }
      });

      const nome = document.createElement("input");
      nome.type = "text";
      nome.className = "lista-variedades__nome";
      nome.value = variedade.nome;
      nome.addEventListener("change", async () => {
        const nomeLimpo = nome.value.trim();
        if (!nomeLimpo || nomeLimpo === variedade.nome) {
          nome.value = variedade.nome;
          return;
        }
        try {
          await Api.atualizarVariedade(variedade.id, { nome: nomeLimpo });
          await aoMudarCb();
        } catch (erro) {
          alert(erro.message);
          nome.value = variedade.nome;
        }
      });

      item.appendChild(cor);
      item.appendChild(nome);
      elLista.appendChild(item);
    }
  }

  return { iniciar };
})();
