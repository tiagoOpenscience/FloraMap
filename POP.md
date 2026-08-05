# POP — Procedimento Operacional Padrão

## Uso do Sistema FloraMap

| | |
|---|---|
| **Setor** | Cooperflora |
| **Sistema** | FloraMap |
| **Objetivo** | Padronizar o passo a passo para mapear estufas de uma propriedade a partir de uma foto aérea, dividir em áreas de cultivo e gerar os relatórios de exportação. |
| **Aplicável a** | Funcionários responsáveis pelo cadastro e acompanhamento de projetos no FloraMap. |

---

## 1. Objetivo

Orientar o funcionário, passo a passo, sobre como usar o FloraMap para:
- criar um projeto de uma propriedade;
- mapear as estufas a partir de uma imagem aérea;
- dividir cada estufa em áreas de cultivo e preencher seus dados;
- marcar a entrada e a saída de cada estufa;
- exportar o resultado em PDF e CSV.

## 2. Antes de Começar

- Tenha em mãos uma **imagem aérea** da propriedade (foto de drone, por exemplo), em PNG ou JPEG, com as estufas visíveis.
- Acesse o FloraMap pelo navegador, no endereço informado pela equipe responsável.
- Tenha em mãos a **senha de acesso** compartilhada do time (peça à equipe responsável pelo FloraMap se não tiver).
- Nenhuma etapa deste procedimento precisa ser "salva" manualmente — o sistema salva tudo automaticamente conforme você preenche os campos.

## 3. Passo a Passo

### 3.0 Entrar no sistema

1. Abra o endereço do FloraMap no navegador — se ainda não estiver logado, você cai automaticamente na tela de login.
2. Digite a senha de acesso compartilhada e clique em **Entrar**.
3. Para sair, clique em **Sair** (no topo da Home ou da barra superior do projeto) — por exemplo, ao usar um computador compartilhado.

> A sessão fica válida por 30 dias no navegador usado para entrar; não é preciso logar de novo a cada acesso.

### 3.1 Criar o projeto

1. Na tela inicial, digite o nome da propriedade no campo indicado.
2. Clique em **Criar**.
3. Clique no nome do projeto criado para abri-lo.

### 3.2 Enviar a imagem aérea

1. Dentro do projeto, clique em **Enviar imagem**.
2. Selecione o arquivo da foto aérea (PNG ou JPEG).
3. Aguarde a imagem aparecer no mapa.

### 3.3 Detectar as estufas automaticamente

1. Clique em **Detectar estufas**.
2. Um aviso amarelo aparece pedindo para clicar em um ou mais pontos de estufas conhecidas na foto.
   - Se a cobertura da estufa tiver listras/ripas (partes claras e escuras), clique em um ponto de cada tonalidade — isso melhora a detecção.
3. Clique em **Concluir**.
4. O sistema desenha automaticamente o contorno de cada estufa encontrada.

> Se já existiam estufas mapeadas nesse projeto, o sistema avisa que elas serão substituídas. Se isso acontecer por engano, use **Ctrl+Z** logo em seguida para desfazer (ver seção 3.7).

### 3.4 Corrigir a detecção (quando necessário)

A detecção automática é uma ajuda, não é perfeita. Corrija manualmente quando:

**Duas estufas foram detectadas como uma só:**
1. Clique na estufa (o contorno fica destacado).
2. No painel à direita, informe em quantas partes ela deve ser dividida e a direção do corte.
3. Clique em **Dividir estufa**.

**Uma estufa não foi detectada:**
1. Clique em **Desenhar estufa**.
2. Clique nos cantos da estufa, na imagem, para desenhar o contorno (mínimo 3 pontos).
3. Clique em **Concluir**.

### 3.5 Dividir uma estufa em áreas de cultivo

1. Clique na estufa desejada.
2. No painel à direita, informe:
   - **Quantidade de áreas**;
   - **Orientação do corte** (Automático, Vertical ou Horizontal).
3. Clique em **Gerar áreas**.
4. O sistema divide a estufa em áreas iguais, sempre dentro do contorno real dela.

### 3.6 Preencher os dados de cada área

1. Clique na área desejada (dentro da estufa já dividida).
2. Preencha os campos disponíveis:
   - **Variedade** (selecionar da lista; ver seção 3.8 para cadastrar uma nova);
   - **Fase**, **Vãos**, **Canteiros**, **Postinhos** (texto livre).
3. Não é preciso clicar em nada para salvar — cada campo salva sozinho ao sair dele.

### 3.7 Desfazer uma ação por engano

Se você excluiu uma estufa/área, dividiu uma estufa ou rodou a detecção por engano:
- Pressione **Ctrl+Z** logo em seguida.
- Isso desfaz a última ação desse tipo. Não funciona para desfazer a edição de um campo de texto isolado (nome, fase, etc.) — nesses casos, corrija o campo manualmente.

### 3.8 Cadastrar uma variedade

1. Clique em **Variedades**, na barra superior.
2. Preencha o nome e escolha uma cor.
3. Clique em **Adicionar**.
4. A variedade passa a aparecer na lista de seleção de qualquer área, em qualquer projeto.

### 3.9 Marcar a entrada e a saída de uma estufa

1. Clique em **Adicionar entrada** e depois clique numa das bordas da estufa — aquela borda fica bem mais grossa e **verde**, com a palavra "Entrada" escrita ao longo dela, marcando a entrada.
2. Clique em **Adicionar saída** e depois clique noutra borda — ela fica bem mais grossa e **vermelha**, com a palavra "Saída" escrita ao longo dela, marcando a saída.
3. A legenda no canto inferior esquerdo do mapa sempre mostra o que cada cor significa.
4. Para remover uma marcação colocada errado: clique na borda marcada (ela fica com um contorno tracejado, indicando que foi selecionada) e pressione a tecla **Delete** (ou **Backspace**) do teclado.

> No canto inferior direito do mapa aparece outra legenda, com a cor e o nome de cada variedade já usada em alguma área do projeto — ela é preenchida automaticamente, sem nenhuma ação extra.

### 3.10 Ver o resumo do projeto

1. Clique em **Visão Geral**, na barra superior (ou é a tela que já aparece ao abrir o projeto).
2. Veja o total de estufas e áreas, e a distribuição de áreas por variedade.
3. Preencha, se quiser, os campos **Observações** e **Análise Geral** (texto livre, salva sozinho).

### 3.11 Exportar o relatório

Na tela de **Visão Geral**:
- Clique em **Exportar PDF** para baixar o mapa com as estufas/áreas desenhadas, a legenda, o resumo e a tabela de áreas.
- Clique em **Exportar CSV** para baixar a tabela de áreas em planilha.

## 4. Pontos de Atenção

- Rodar **Detectar estufas** novamente **substitui** todas as estufas e áreas já cadastradas no projeto. Use com cuidado, e lembre do Ctrl+Z se for engano.
- Excluir uma estufa remove também todas as áreas dela e suas marcações de entrada/saída. O sistema sempre pede confirmação antes.
- Excluir um projeto (na tela inicial) remove também suas estufas, áreas, imagem e marcações de entrada/saída — não tem volta.
- O sistema é de uso interno da Cooperflora; não há login por usuário nem histórico de quem alterou o quê.

## 5. Responsabilidades

- **Funcionário de campo/escritório:** seguir este procedimento ao cadastrar cada nova propriedade e manter os dados de área atualizados.
- **Equipe responsável pelo FloraMap:** manter o sistema disponível e este documento atualizado sempre que uma funcionalidade mudar (ver `SPEC.md` para o comportamento técnico detalhado).

---

*Este documento descreve o uso do sistema do ponto de vista do funcionário. Para detalhes técnicos de arquitetura e comportamento do sistema, ver `SPEC.md`.*
