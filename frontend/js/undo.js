// undo.js — pilha de "desfazer" (Ctrl+Z) para ações estruturais
// destrutivas: detectar, gerar áreas, dividir estufa, excluir estufa,
// excluir área. Edições de campo (nome, fase, etc.) não entram na
// pilha — cada uma já é uma alteração pequena e reversível manualmente.

const Undo = (() => {
  let pilha = [];
  let projetoIdAtual = null;
  let aoRestaurarCb = async () => {};
  const LIMITE = 20;

  function iniciar({ aoRestaurar }) {
    aoRestaurarCb = aoRestaurar;

    document.addEventListener("keydown", (evento) => {
      const combinacaoZ =
        (evento.ctrlKey || evento.metaKey) && !evento.shiftKey && evento.key.toLowerCase() === "z";
      if (!combinacaoZ) return;

      const alvo = evento.target;
      const ehCampoDeTexto =
        alvo && (alvo.tagName === "INPUT" || alvo.tagName === "TEXTAREA");
      if (ehCampoDeTexto) return; // deixa o undo nativo do campo funcionar

      evento.preventDefault();
      desfazer();
    });
  }

  // Chamar ANTES de qualquer ação destrutiva, passando o estado atual
  // de `estufas` (com áreas aninhadas) do projeto.
  function registrar(projetoId, estufasAtuais) {
    projetoIdAtual = projetoId;
    pilha.push(JSON.parse(JSON.stringify(estufasAtuais)));
    if (pilha.length > LIMITE) pilha.shift();
  }

  async function desfazer() {
    if (pilha.length === 0) return;
    const snapshot = pilha.pop();
    try {
      await aoRestaurarCb(projetoIdAtual, snapshot);
    } catch (erro) {
      alert("Não foi possível desfazer: " + erro.message);
    }
  }

  return { iniciar, registrar };
})();
