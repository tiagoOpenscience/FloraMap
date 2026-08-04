// login.js — comportamento da tela de login (senha única compartilhada).

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form-login");
  const inputSenha = document.getElementById("input-senha");
  const erroEl = document.getElementById("erro-login");

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erroEl.textContent = "";

    try {
      await Api.login(inputSenha.value);
      window.location.href = "/";
    } catch (erro) {
      erroEl.textContent = erro.message;
    }
  });
});
