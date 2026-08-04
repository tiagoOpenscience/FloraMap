# DEPLOY.md — Publicar o FloraMap na nuvem (PythonAnywhere, grátis)

Este guia coloca o FloraMap acessível por um link da internet, pro time todo usar, protegido por uma senha única compartilhada. Usa o plano **gratuito** do [PythonAnywhere](https://www.pythonanywhere.com/) — não pede cartão de crédito e mantém o banco SQLite e as imagens enviadas persistidos entre reinícios (diferente da maioria dos free tiers de outros provedores, que apagam o disco a cada deploy).

Limitações do plano grátis, pra você já saber:
- O link fica em `SEUUSUARIO.pythonanywhere.com` — **use um usuário genérico** (ex.: `floramap`, `cooperflora`) ao criar a conta, não seu nome pessoal, já que ele aparece na URL (ver Passo 3).
- **512 MB de disco no total**, contando o próprio ambiente Python instalado. Só `opencv-python-headless` + `numpy` + `Pillow` (dependências do FloraMap) já usam uns 150–250 MB, sobrando de fato uns 250–350 MB pra código + banco + fotos. Pra caber mais propriedades nesse espaço, o FloraMap já recomprime toda imagem enviada (redimensiona pra no máximo 2000px de largura e salva como JPEG) — o suficiente pra dezenas de projetos, mas vale de olho na cota (aba "Files" do PythonAnywhere mostra o uso atual).
- Cota diária de CPU baixa — de sobra pro uso interno do time, mas não serve pra tráfego alto.
- Acesso de saída à internet é restrito a uma whitelist — não afeta o FloraMap, que não faz chamadas para fora.
- Se a conta ficar 3 meses sem login algum na plataforma, o app é desativado (basta entrar de novo pra reativar).

Se um dia isso virar um problema, dá pra migrar pra um plano pago do próprio PythonAnywhere (~US$5/mês, mais disco e domínio próprio) ou outro provedor — o código não muda, só a hospedagem.

---

## Passo 1 — Enviar o código pro GitHub

O PythonAnywhere vai clonar o repositório de lá, não da sua máquina Windows. Rode isto na pasta do projeto:

```
git add -A
git commit -m "Adiciona senha de acesso e pontos de entrada/saída"
git push
```

## Passo 2 — Gerar o hash da senha compartilhada

**Antes de mexer no PythonAnywhere**, decida a senha que o time vai usar e gere o hash dela localmente (o servidor nunca guarda a senha em texto puro, só o hash):

```
"./.venv/Scripts/python.exe" -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('COLOQUE_A_SENHA_AQUI'))"
```

Guarde o resultado (algo como `scrypt:32768:8:1$...`) — você vai colar ele no Passo 6.

Também gere uma chave de sessão aleatória (qualquer string longa e única serve):

```
"./.venv/Scripts/python.exe" -c "import secrets; print(secrets.token_hex(32))"
```

## Passo 3 — Criar a conta no PythonAnywhere

1. Acesse pythonanywhere.com e crie uma conta gratuita ("Beginner" account).
2. **No campo de usuário, escolha um nome genérico** (ex.: `floramap`, `cooperflora`) em vez do seu nome pessoal — esse é o nome que vai aparecer pra sempre na URL pública (`SEUUSUARIO.pythonanywhere.com`), e não dá pra trocar depois sem criar outra conta.
3. Confirme o e-mail se for pedido.

## Passo 4 — Clonar o repositório

No dashboard do PythonAnywhere, abra um **Bash console** (menu "Consoles" → "Bash") e rode:

```
git clone https://github.com/tiagoOpenscience/FloraMap.git
```

## Passo 5 — Instalar as dependências

Ainda no Bash console:

```
mkvirtualenv --python=python3.11 floramap-venv
cd FloraMap
pip install -r requirements.txt
```

(Se `mkvirtualenv` pedir pra reabrir o console, feche e abra outro — o comando `workon floramap-venv` reativa o virtualenv depois.)

## Passo 6 — Criar o Web App

1. Vá na aba **"Web"** → **"Add a new web app"**.
2. Escolha **"Manual configuration"** (não "Flask", pra usar nosso `criar_app()` diretamente) e a mesma versão de Python do virtualenv (3.11).
3. Na seção **"Virtualenv"** da página do Web App, aponte para o caminho do virtualenv criado (algo como `/home/SEUUSUARIO/.virtualenvs/floramap-venv`).
4. Na seção **"Code"**, defina:
   - **Source code**: `/home/SEUUSUARIO/FloraMap`
   - **Working directory**: `/home/SEUUSUARIO/FloraMap`
5. Clique no link do **arquivo WSGI** (algo como `/var/www/seuusuario_pythonanywhere_com_wsgi.py`) para editá-lo. Apague o conteúdo padrão e coloque:

```python
import sys
import os

caminho_projeto = "/home/SEUUSUARIO/FloraMap"
if caminho_projeto not in sys.path:
    sys.path.insert(0, caminho_projeto)

os.environ["FLORAMAP_SECRET_KEY"] = "COLE_AQUI_A_CHAVE_GERADA_NO_PASSO_2"
os.environ["FLORAMAP_SENHA_HASH"] = "COLE_AQUI_O_HASH_GERADO_NO_PASSO_2"
os.environ["FLORAMAP_COOKIE_SECURE"] = "1"

from backend.app import criar_app

application = criar_app()
```

Troque `SEUUSUARIO` pelo seu usuário do PythonAnywhere em todas as ocorrências deste guia.

## Passo 7 — Recarregar e acessar

1. Volte pra aba "Web" e clique no botão verde **"Reload"**.
2. Acesse `https://SEUUSUARIO.pythonanywhere.com/login.html` e entre com a senha escolhida no Passo 2.

Pronto — qualquer pessoa do time com o link e a senha já consegue usar o FloraMap.

---

## Trocar a senha compartilhada depois

1. Gere um novo hash (Passo 2).
2. Edite o arquivo WSGI (Passo 6) trocando o valor de `FLORAMAP_SENHA_HASH`.
3. Clique em "Reload" na aba "Web".

## Atualizar o código depois de uma mudança

No Bash console do PythonAnywhere:

```
cd ~/FloraMap
git pull
workon floramap-venv
pip install -r requirements.txt
```

Depois, volte na aba "Web" e clique em "Reload".
