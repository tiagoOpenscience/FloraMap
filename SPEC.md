# SPEC.md — FloraMap

Especificação funcional completa do sistema FloraMap, ferramenta interna da Cooperflora para gerenciamento visual de estufas e áreas produtivas a partir de imagens aéreas.

Versão: 2.0 — reflete o sistema **em funcionamento**, não mais uma proposta inicial. Ver `CLAUDE.md` para diretrizes de arquitetura/desenvolvimento e o racional resumido das decisões mais importantes.

---

# 1. Visão Geral

## 1.1 Descrição

FloraMap é um sistema web interno, de uso exclusivo da Cooperflora, que permite visualizar estufas de uma propriedade a partir de uma imagem aérea, detectar automaticamente essas estufas (calibrado por amostra de cor), corrigir a detecção manualmente quando necessário, dividi-las em áreas produtivas e registrar informações de cultivo. O projeto também produz uma Visão Geral com contadores e distribuição por variedade, e exporta tudo em PDF (com o mapa desenhado) e CSV.

Não é um ERP. Não é um SIG completo.

## 1.2 Escopo

Dentro do escopo:
- Um projeto por propriedade/imagem aérea.
- Detecção automática de estufas via OpenCV, calibrada por um ou mais pontos de cor que o usuário clica sobre estufas conhecidas na própria foto.
- Correção manual: desenhar o contorno de uma estufa à mão, ou dividir (split) uma estufa que a detecção juntou por engano.
- Edição manual de estufas e áreas via SVG, incluindo exclusão.
- Cadastro global de variedades (nome + cor).
- Visão Geral do projeto (contadores, distribuição por variedade, observações, análise geral).
- Exportação em PDF (mapa + tabelas) e CSV (tabela).
- Desfazer (Ctrl+Z) de ações estruturais destrutivas.
- Persistência em SQLite, sem necessidade de ação explícita de salvar.
- Acesso protegido por uma senha única compartilhada por todo o time (sem contas por pessoa).

Fora do escopo:
- Contas por usuário, permissões e múltiplos níveis de acesso (o que existe é uma senha única compartilhada — ver seção 3.13).
- Histórico/auditoria completo (o undo cobre só a sessão atual, em memória no navegador).
- Refazer (redo).
- Aplicativo mobile.
- Qualquer framework frontend (React, Vue, Angular).

## 1.3 Fluxo Geral

1. Usuário cria um novo projeto (e pode renomeá-lo ou excluí-lo depois, na Home).
2. Usuário envia uma imagem aérea da propriedade.
3. Usuário clica em "Detectar estufas": um banner pede para clicar em um ou mais pontos de estufas conhecidas na foto (mais de um ponto ajuda em coberturas listradas/ripadas — clicar numa parte clara e noutra escura da mesma estufa). Ao confirmar, o sistema detecta as estufas com cor e porte semelhantes aos pontos clicados.
4. Se a detecção juntar duas estufas vizinhas por engano, o usuário pode selecioná-la e usar "Dividir estufa" para separá-la em N novas estufas. Se preferir, pode desenhar o contorno de uma estufa manualmente ("Desenhar estufa").
5. Usuário pode renomear, renumerar ou excluir cada estufa.
6. Usuário informa quantas áreas existem dentro de uma estufa e a orientação do corte; o sistema divide automaticamente a estufa em áreas iguais, recortadas para dentro do contorno real dela.
7. Cada área pode receber seus dados (variedade, fase, vãos, canteiros, postinhos) ou ser excluída.
8. As alterações são salvas automaticamente.
9. A qualquer momento, o usuário pode desfazer (Ctrl+Z) a última ação estrutural destrutiva (detectar, gerar áreas, dividir estufa, excluir estufa, excluir área).
10. A Visão Geral (padrão da coluna direita) mostra o resumo do projeto e permite exportar em PDF/CSV.

---

# 2. Modelo de Dados

## 2.1 Entidades

### Projeto
- id
- nome
- imagem (caminho do arquivo)
- observação (texto livre)
- análise geral (texto livre)
- data de criação

### Estufa
- id
- projeto_id (FK)
- numero (gerado automaticamente na detecção/criação manual, editável)
- nome (editável)
- poligono (coordenadas SVG)
- quantidade_areas
- orientacao_areas (`auto` | `vertical` | `horizontal` — última orientação usada para gerar áreas)

### Área
- id
- estufa_id (FK)
- variedade_id (FK, opcional)
- fase (texto)
- vaos (texto)
- canteiros (texto)
- postinhos (texto)
- poligono (coordenadas SVG)
- ordem (posição dentro da estufa — usada como "A{ordem}" no rótulo)

### Variedade
- id
- nome
- cor (hexadecimal)

### Ponto de Acesso
- id
- estufa_id (FK)
- tipo (`entrada` | `saida`)
- indice_aresta (posição da aresta na borda da estufa — o segmento entre `poligono[indice_aresta]` e o próximo vértice, com wrap-around; não tem coordenadas próprias, segue o polígono da estufa)

## 2.2 Relacionamentos

```
Projeto (1) ──< Estufa (N) ──< Área (N) >── Variedade (opcional)
```

Exclusão em cascata: excluir um Projeto remove suas Estufas, Áreas e Pontos de Acesso (e o arquivo de imagem no disco); excluir uma Estufa remove suas Áreas e seus Pontos de Acesso; excluir uma Variedade em uso apenas desvincula as Áreas (`variedade_id` vira `NULL`).

---

# 3. Fluxo do Usuário

## 3.1 Projeto
Criar (Home), abrir, renomear (Home), excluir (Home, com confirmação — remove estufas/áreas/imagem em cascata).

## 3.2 Importar Imagem
Upload de PNG/JPEG; fica associada ao projeto e é exibida como plano de fundo do mapa. Ao salvar, a imagem é redimensionada (largura máxima de 2000px, mantendo proporção) e recomprimida como JPEG (qualidade ~85), independente do formato original — reduz bastante o espaço em disco por projeto (relevante em hospedagens com cota apertada, ver `DEPLOY.md`) sem perda perceptível, já que o mapa e o PDF exportado já usam resolução menor que a maioria das fotos aéreas originais. Reenviar uma imagem substitui a anterior (inclusive removendo o arquivo antigo do disco se a extensão mudou).

## 3.3 Detectar Estufas (calibrado por amostra)
1. Usuário clica em "Detectar estufas". Se já existirem estufas no projeto, é pedida confirmação (a detecção substitui todas as estufas e áreas atuais).
2. Um banner aparece: "Clique em um ou mais pontos de estufas conhecidas...". O botão "Concluir" fica desabilitado até o primeiro clique, e mostra a contagem de pontos.
3. Cada clique no mapa adiciona um marcador visual e um ponto à lista.
4. Ao clicar "Concluir", os pontos são enviados para `POST /projetos/{id}/detectar`; o detector calibra cor e porte a partir deles e retorna as estufas.
5. Botão "Cancelar" a qualquer momento aborta o modo sem chamar a API.

## 3.4 Corrigir a Detecção

**Dividir (split) uma estufa:** dentro do painel de uma Estufa, informar em quantas partes dividir e a orientação do corte; confirma (há aviso se a estufa já tinha áreas, que serão perdidas); a estufa original é substituída por N novas estufas.

**Desenhar estufa manualmente:** botão "Desenhar estufa" na toolbar entra em um modo onde cada clique no mapa adiciona um ponto do contorno (mínimo 3), com uma linha tracejada mostrando o polígono em progresso; "Concluir" cria a estufa.

## 3.5 Editar/Excluir Estufa
Painel da Estufa: número, nome (salvamento automático), quantidade de áreas + orientação + botão "Gerar áreas", seção "Dividir estufa", e botão "Excluir estufa" (confirmação; Ctrl+Z desfaz).

## 3.6 Gerar Áreas
Informar quantidade e orientação (`auto` — eixo mais longo da estufa; `vertical` — colunas lado a lado; `horizontal` — linhas empilhadas). Se a estufa já tinha áreas, é pedida confirmação (substituem as anteriores). As áreas geradas são sempre recortadas para dentro do contorno real da estufa (nunca "vazam" para fora, mesmo em estufas não perfeitamente retangulares).

## 3.7 Editar/Excluir Área
Painel da Área: variedade (seleção), fase/vãos/canteiros/postinhos (texto, salvamento automático), botão "Excluir área" (confirmação; Ctrl+Z desfaz). A área não tem rótulo de texto no mapa — só a cor da variedade atualiza em tempo real; os demais dados só aparecem no painel.

## 3.8 Navegação no painel lateral
A Visão Geral é o estado padrão. Selecionar uma Estufa ou Área muda o painel para o modo de edição correspondente, sempre com um botão "← Visão Geral" no topo. O painel de Área também tem "← Editar Estufa N".

## 3.9 Desfazer (Ctrl+Z)
Funciona em qualquer lugar da tela principal (exceto com foco em campo de texto, onde o undo nativo do navegador tem prioridade). Desfaz a última ação estrutural destrutiva: detectar, gerar áreas, dividir estufa, excluir estufa, excluir área. Não desfaz edições de campo isoladas.

## 3.10 Marcar Entrada/Saída

Toolbar tem os botões "Adicionar entrada" e "Adicionar saída". Ao clicar em um deles, um banner pede pra clicar numa **aresta da borda de uma estufa** (não um ponto qualquer do mapa): durante esse modo, todas as arestas de todas as estufas ficam destacadas e clicáveis; ao clicar numa, ela vira a entrada/saída marcada — a linha da borda fica bem mais grossa e colorida (verde para entrada, vermelho para saída) — e salva automaticamente via API, sem confirmar nada. A marcação segue o contorno real da estufa (não é um ponto solto). A própria aresta marcada mostra o texto "Entrada" ou "Saída" escrito ao longo dela (mesmo estilo do título da estufa, porém menor, com tamanho proporcional ao comprimento da aresta e rotacionado para acompanhar sua inclinação — nunca de cabeça para baixo). Uma legenda fixa no canto inferior esquerdo do mapa (visível sempre que há uma imagem carregada) reforça que verde é entrada e vermelho é saída.

Pra remover uma marcação já existente: clique nela (a linha fica com um contorno tracejado indicando que está selecionada) e pressione **Delete** ou **Backspace** — sem diálogo de confirmação, igual a selecionar e apagar um objeto num editor gráfico. As arestas de entrada/saída também aparecem no PDF exportado, com a mesma legenda.

## 3.11 Exportar
Na Visão Geral: "Exportar PDF" (mapa com estufas/áreas desenhadas e rotuladas + legenda de variedades + resumo + tabela + observações/análise) e "Exportar CSV" (tabela: Estufa, Número, Área, Variedade, Fase, Vãos, Canteiros, Postinhos).

## 3.12 Salvar Automaticamente
Nunca há botão "Salvar". Toda alteração de campo dispara uma chamada à API (com debounce curto para campos de texto — cada campo tem seu próprio temporizador, para não perder edições em campos diferentes feitas em sequência rápida) que persiste imediatamente, com indicador "Salvando..." / "Salvo automaticamente".

## 3.13 Autenticação (senha única compartilhada)
O sistema fica atrás de uma senha única, compartilhada por todo o time (não há conta por pessoa). Ao acessar qualquer página sem sessão válida, o usuário é redirecionado para `/login.html`; chamadas de API sem sessão válida recebem `401`. Após informar a senha correta em `/login.html`, uma sessão é criada (cookie de sessão do Flask, válida por 30 dias) e todas as telas ficam acessíveis normalmente. O botão "Sair" (na Home e na barra superior da tela do projeto) encerra a sessão. A senha em si nunca é guardada em texto puro: o servidor guarda apenas o hash dela numa variável de ambiente (`FLORAMAP_SENHA_HASH`) — ver `DEPLOY.md` para como gerar e trocar esse hash.

---

# 4. Todas as Telas

## 4.1 Tela de Projetos (Home)

```
┌──────────────────────────────────────────────┐
│  FloraMap                                     │
│                                                │
│  [ Nome do novo projeto... ] [ Criar ]         │
│                                                │
│  Projetos existentes:                         │
│  ┌────────────────────────────────────────┐   │
│  │ Fazenda Sede      10/03  [Renomear][Excluir]│
│  │ Setor Norte       22/05  [Renomear][Excluir]│
│  └────────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

"Renomear" abre um `prompt()`; "Excluir" pede confirmação (avisa que estufas/áreas/imagem também são apagadas).

## 4.2 Tela Principal do Projeto

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Projetos   [Nome]   [Enviar Imagem][Detectar][Desenhar]        │
│                                        [Variedades][Visão Geral] │
├───────────────────────────────────────┬───────────────────────┐
│                                        │  Painel Lateral        │
│                                        │  (Visão Geral é        │
│              MAPA (SVG)                │   o estado padrão)     │
│      [banner de amostra/desenho        │                        │
│       quando ativo, com Concluir       │                        │
│       e Cancelar]                      │                        │
└───────────────────────────────────────┴───────────────────────┘
```

### 4.2.1 Toolbar
"Enviar Imagem" · "Detectar estufas" (desabilitado sem imagem) · "Desenhar estufa" (desabilitado sem imagem) · "Adicionar entrada" (desabilitado sem imagem) · "Adicionar saída" (desabilitado sem imagem) · "Variedades" (abre modal) · "Visão Geral" (atalho para o estado padrão do painel).

### 4.2.2 Mapa
Imagem aérea de fundo + SVG com um polígono por Estufa e, dentro dela, um polígono por Área (quando geradas). Área colorida pela variedade (ou cor neutra se nenhuma), sem nenhum texto. O nome/número da estufa fica sempre visível, centralizado nela. Clique numa Estufa (fora de uma área) seleciona a Estufa; clique numa Área seleciona a Área; clique no rótulo da estufa também seleciona a Estufa. Rótulos: ver seção 5 do `CLAUDE.md` ("Decisões de projeto importantes") e seção 8.4 abaixo. Entradas (verde) e saídas (vermelho) são arestas destacadas da borda de uma estufa, sem rótulo de texto; uma legenda fixa no canto inferior esquerdo explica as cores (ver seção 3.10). No canto inferior direito, uma segunda legenda lista as variedades em uso no projeto (cor + nome), calculada a partir das áreas já preenchidas — some automaticamente se nenhuma área tem variedade definida.

### 4.2.3 Painel Lateral — estados

**Visão Geral (padrão):**
```
┌───────────────────────┐
│ Visão Geral            │
│ Estufas: 3   Áreas: 12 │
│                        │
│ Áreas por variedade    │
│ ● Rosa        5 área(s)│
│ ● Lola        3 área(s)│
│   Sem var.    4 área(s)│
│                        │
│ [Exportar PDF][CSV]    │
│                        │
│ Observações            │
│ [textarea]             │
│ Análise geral          │
│ [textarea]             │
│ ● Salvo automaticamente│
└───────────────────────┘
```

**Estufa:**
```
┌───────────────────────┐
│ ← Visão Geral          │
│ Estufa                │
│ Número:  [ 3        ] │
│ Nome:    [ Estufa C ] │
│ Qtd áreas: [ 6 ]       │
│ Orientação: [Auto ▾]  │
│ [ Gerar áreas ]        │
│ ─────────────────      │
│ Dividir em: [ 2 ]      │
│ Direção:    [Auto ▾]  │
│ [ Dividir estufa ]     │
│ ● Salvo automaticamente│
│ ─────────────────      │
│ [ Excluir estufa ]     │
└───────────────────────┘
```

**Área:**
```
┌───────────────────────┐
│ ← Visão Geral          │
│ ← Editar Estufa 3      │
│ Área 2 (Estufa 3)      │
│ Variedade: [ Rosa ▾ ] │
│ Fase:      [ Muda    ]│
│ Vãos:      [ 4       ]│
│ Canteiros: [ 8       ]│
│ Postinhos: [ 120     ]│
│ ● Salvo automaticamente│
│ ─────────────────      │
│ [ Excluir área ]       │
└───────────────────────┘
```

## 4.3 Modal de Variedades
Lista (cor + nome, ambos editáveis inline) + formulário "+ Nova Variedade" (nome + seletor de cor). Alterar a cor de uma variedade em uso atualiza automaticamente todas as áreas que a usam.

---

# 5. Banco de Dados

Ver `backend/schema.sql` (fonte da verdade) e a seção 2 acima para os campos por entidade. Migrações incrementais em `backend/banco.py::_migrar_colunas_novas`.

Índices: `idx_estufa_projeto` (estufa.projeto_id), `idx_area_estufa` (area.estufa_id).

---

# 6. API

Todos os endpoints abaixo existem e estão implementados.

## Autenticação
- `POST /api/login` `{senha}` — valida contra `FLORAMAP_SENHA_HASH`; cria sessão (200) ou `401` se errada
- `POST /api/logout` — encerra a sessão

## Projetos
- `GET /api/projetos` — lista
- `POST /api/projetos` `{nome}` — cria
- `GET /api/projetos/{id}` — detalhe (inclui `estufas` com `areas` aninhadas)
- `PATCH /api/projetos/{id}` `{nome?, observacao?, analise_geral?}` — atualização genérica
- `DELETE /api/projetos/{id}` — exclui (cascade + apaga imagem do disco)
- `POST /api/projetos/{id}/imagem` — upload (multipart, campo `imagem`)
- `GET /api/projetos/{id}/resumo` — `{total_estufas, total_areas, areas_por_variedade: [{variedade_id, variedade_nome, variedade_cor, quantidade}]}`
- `GET /api/projetos/{id}/exportar/csv` — download CSV
- `GET /api/projetos/{id}/exportar/pdf` — download PDF

## Estufas
- `GET /api/projetos/{id}/estufas` — lista (com áreas aninhadas)
- `POST /api/projetos/{id}/estufas` `{poligono: [{x,y}, ...]}` — cria manualmente (desenho à mão)
- `POST /api/projetos/{id}/detectar` `{amostras: [{x,y}, ...]}` — detecção calibrada (lista pode ser vazia → heurístico genérico de baixa confiança)
- `PATCH /api/estufas/{id}` `{nome?, numero?}`
- `DELETE /api/estufas/{id}`
- `POST /api/estufas/{id}/dividir` `{quantidade, orientacao}` — substitui a estufa por N novas
- `POST /api/projetos/{id}/estufas/restaurar` `{estufas: [...]}` — restauração em lote (usada pelo undo do frontend)

## Áreas
- `GET /api/estufas/{id}/areas`
- `POST /api/estufas/{id}/gerar-areas` `{quantidade, orientacao}`
- `PATCH /api/areas/{id}` `{variedade_id?, fase?, vaos?, canteiros?, postinhos?}`
- `DELETE /api/areas/{id}`

## Variedades
- `GET /api/variedades`
- `POST /api/variedades` `{nome, cor}`
- `PATCH /api/variedades/{id}` `{nome?, cor?}`

## Pontos de Acesso (entrada/saída, por aresta de estufa)
- lista embutida em `GET /api/projetos/{id}` como `pontos_acesso`
- `POST /api/estufas/{id}/pontos-acesso` `{tipo: "entrada"|"saida", indice_aresta}` — cria
- `DELETE /api/pontos-acesso/{id}` — exclui

---

# 7. Detector

Implementado em `backend/detector/detector.py`. Ver `CLAUDE.md` para o racional de por que é calibrado por amostra em vez de cor fixa.

## 7.1 Algoritmo

1. Ler a imagem, suavizar (`GaussianBlur`), converter para HSV.
2. **Com amostra(s):** para cada ponto `(x,y)` clicado, calcular média e desvio padrão de HSV numa vizinhança (`RAIO_AMOSTRA_PX = 12`); construir uma máscara `inRange` por ponto com margem `max(mínimo, desvio × 2.2)`; a máscara final é a **união** (OR) de todas — importante para coberturas listradas, onde um único ponto não cobre toda a variação de cor.
   **Sem amostra:** heurístico genérico (`inRange` por brilho alto/saturação baixa), baixa confiança, mantido só por compatibilidade.
3. Morfologia assimétrica: abertura com kernel 5×5 (2 iterações) para *quebrar* pontes finas entre estufas vizinhas que a máscara de cor tenha colado; fechamento bem mais conservador, kernel 3×3 (1 iteração), só para fechar ruído/buracos pequenos — sem voltar a colar estruturas separadas (a versão anterior, com fechamento 7×7×3, chegava a preencher vãos de até ~21px entre estufas próximas).
4. `findContours` (RETR_EXTERNAL).
5. **Calibração de escala:** localizar, para cada ponto amostrado, o contorno que o contém; usar a **mediana** de área/largura/altura desses contornos como referência. Aceitar só contornos com área entre 15% e 800% da referência, e largura/altura até 5× a referência (com um teto absoluto de 90% da imagem). Sem amostra, a referência de área é a mediana dos próprios contornos já aceitos pelos filtros abaixo (e os limites de área/dimensão usam o percentual fixo da imagem como fallback).
6. **Filtro de forma (solidez):** para cada contorno candidato, calcular `solidez = área / área do fecho convexo (convex hull)` e rejeitar contornos com solidez abaixo de `SOLIDEZ_MINIMA = 0.75`. Estufas são estruturas retangulares/convexas; árvores e manchas de vegetação são tipicamente irregulares e lobuladas — esse filtro é o que impede a detecção automática (sem amostra) de marcar árvores como estufa, e também descarta um vazamento parcial da máscara para a vegetação ao lado de uma estufa real.
7. **Separação de blobs fundidos (watershed):** quando um contorno aceito tem área bem maior que a referência (`> 1.6×`), é candidato a ser duas ou mais estufas coladas pela máscara/morfologia. Nesse caso: recorta a máscara local do contorno, calcula a transformada de distância (`distanceTransform`) para achar um "núcleo" por estufa dentro do blob, e — se houver mais de um núcleo — roda `watershed` para dividir a região ambígua entre eles, gerando N sub-contornos separados (cada um passa de novo pelos filtros de área/dimensão/solidez).
8. `approxPolyDP` (epsilon 2% do perímetro) para reduzir a pontos de polígono.
9. Ordenar espacialmente (linha top→bottom em faixas de 100px, depois esquerda→direita) e numerar sequencialmente.

## 7.2 Divisão de Polígono (Área e Split de Estufa)

Implementado em `backend/servicos/geometria.py::dividir_poligono`, compartilhado entre geração de área e divisão de estufa:

1. Calcular bounding box do polígono; escolher eixo de corte (`vertical` = x, `horizontal` = y, `auto` = o eixo mais longo).
2. Rasterizar o polígono numa máscara local (coordenadas relativas ao bbox, para não depender do tamanho da imagem inteira).
3. Para cada uma das N faixas iguais ao longo do eixo escolhido, rasterizar um retângulo da faixa e fazer a **interseção** (`bitwise_and`) com a máscara do polígono.
4. Extrair o maior contorno de cada interseção (`approxPolyDP`, epsilon 1%) como o polígono daquela parte.

Isso garante que cada parte respeite o contorno real do polígono original, mesmo quando ele não é um retângulo perfeitamente alinhado aos eixos.

---

# 8. Interface

## 8.1 Estados da Aplicação
1. Projeto sem imagem — mapa vazio, botões de detecção/desenho desabilitados.
2. Projeto com imagem, sem estufas — botões habilitados.
3. Estufas detectadas/criadas, sem seleção — Visão Geral no painel.
4. Estufa selecionada, sem áreas — rótulo da estufa visível no mapa; painel de Estufa.
5. Estufa selecionada, com áreas — rótulo da estufa continua visível (centralizado); áreas visíveis só por cor; painel de Estufa também alcançável via "← Editar Estufa" a partir de uma Área.
6. Área selecionada — painel de Área com número/dimensões/variedade (o mapa mostra só a cor).
7. Modo de amostra ativo — banner visível, overlay de clique no mapa, marcador por ponto.
8. Modo de desenho ativo — banner visível, linha tracejada acompanhando os cliques.
9. Modo de escolher aresta ativo (entrada/saída) — banner visível, todas as arestas de todas as estufas destacadas e clicáveis.
10. Aresta de entrada/saída selecionada — linha com contorno tracejado; Delete/Backspace remove.

## 8.2 Fluxo de Navegação
SPA de tela única para o projeto; a única transição de página é Home ↔ Tela Principal. Modal de Variedades abre por cima sem perder a seleção atual do mapa.

---

# 9. Regras de Negócio

1. Uma Estufa pode ter qualquer quantidade de Áreas (inclusive zero).
2. Uma Área pertence a exatamente uma Estufa.
3. Apenas "Variedade" é campo de seleção; os demais campos de Área são texto livre.
4. Cada Variedade tem uma cor; a cor de uma Área no mapa reflete a Variedade escolhida (ou cor neutra, se nenhuma).
5. Alterar a cor de uma Variedade em uso atualiza automaticamente todas as Áreas que a usam.
6. Toda alteração é salva automaticamente; não há botão "Salvar".
7. Gerar áreas para uma Estufa que já tem áreas pede confirmação (substitui as anteriores).
8. Dividir uma Estufa pede confirmação (a estufa original é substituída por N novas; áreas dela são perdidas).
9. Excluir uma Estufa ou Área pede confirmação; ambas podem ser desfeitas com Ctrl+Z logo em seguida.
10. Excluir um Projeto remove suas Estufas/Áreas e o arquivo de imagem; pede confirmação.
11. O número de uma Estufa é gerado automaticamente (detecção, split ou desenho manual), mas pode ser editado manualmente a qualquer momento.
12. Rodar a detecção novamente **substitui todas** as Estufas e Áreas do projeto (não tenta reconciliar com edições manuais anteriores) — o usuário é avisado antes.
13. Nunca usar Canvas como estrutura principal de renderização do mapa; toda geometria é SVG.
14. Nunca usar frameworks frontend.
15. Desfazer (Ctrl+Z) cobre apenas ações estruturais destrutivas (detectar, gerar áreas, dividir, excluir estufa/área) — não cobre edições de campo isoladas, e não há refazer (redo).
16. Áreas geradas nunca ultrapassam o contorno real da Estufa (recorte via máscara, não bounding box).
17. O rótulo de uma Estufa no mapa fica sempre visível; Áreas nunca têm rótulo de texto no mapa, só cor.
18. Um Ponto de Acesso é uma aresta da borda de uma Estufa (não um ponto solto) — é removido excluindo a Estufa, ou individualmente selecionando a aresta no mapa e pressionando Delete/Backspace (sem confirmação).
