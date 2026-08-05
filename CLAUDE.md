# CLAUDE.md

Você é o desenvolvedor responsável pelo FloraMap.

Este projeto é utilizado internamente pela Cooperflora.

Não desenvolva pensando em milhares de usuários.

Desenvolva pensando em simplicidade, facilidade de manutenção e boa experiência para os funcionários.

Este arquivo reflete o estado **atual** do projeto (já em uso, não mais uma proposta inicial). Para o comportamento funcional completo e detalhado, ver `SPEC.md` — mantenha os dois em sincronia sempre que alterar comportamento.

---

# Objetivos

O sistema:

- detecta automaticamente as estufas em uma imagem aérea, calibrado por amostra de cor clicada pelo usuário (ver seção "Decisões de projeto importantes")
- permite corrigir a detecção manualmente: dividir (split) uma estufa que a detecção juntou por engano, ou desenhar o contorno de uma estufa à mão
- permite selecionar, renomear, renumerar e excluir uma estufa
- permite informar quantas áreas ela possui e a orientação do corte (vertical/horizontal/automático)
- divide automaticamente a estufa em áreas iguais, recortadas para dentro do contorno real dela
- permite editar e excluir cada área
- salva automaticamente qualquer alteração (sem botão "Salvar")
- mostra uma Visão Geral do projeto (contadores, distribuição por variedade, observações, análise geral) como visão padrão da coluna direita
- exporta o projeto em PDF (com o mapa desenhado) e CSV
- permite desfazer (Ctrl+Z) ações estruturais destrutivas

---

# Arquitetura

Backend

- Python + Flask
- SQLite
- OpenCV (`cv2`) para detecção e geometria de polígonos
- Pillow para compor a imagem do mapa usada no PDF
- fpdf2 para gerar o PDF

Frontend

- HTML + CSS + JavaScript puro
- Nunca usar React, Vue ou Angular

---

# Modelo do Sistema

```
Projeto
  └── Estufa (N)
        └── Área (N)
              └── Variedade (referência opcional)
```

Cada Área possui: variedade (seleção), fase, vãos, canteiros, postinhos (todos texto livre, exceto variedade).

Cada Projeto possui, além do nome e imagem: observação e análise geral (texto livre, editados na Visão Geral).

Cada Estufa possui, além do polígono: nome, número, quantidade de áreas e orientação de corte das áreas (`auto` | `vertical` | `horizontal`).

---

# SVG

Toda estufa e toda área são representadas por um polígono SVG. Nunca usar Canvas como estrutura principal.

Rótulos no mapa:

- Estufa: mostra só o **nome** (sem o número), **sempre**, tenha ou não áreas geradas — é o único texto visível dentro da estufa, para o usuário sempre saber qual estufa é qual só olhando o mapa. O número continua existindo como campo (editável no painel, usado nas tabelas do PDF/CSV), só não aparece mais no rótulo do mapa.
- Área: **não mostra nenhum texto** — só a cor (da variedade, ou neutra se nenhuma). Os detalhes (`A{ordem}`, canteiros/vãos/postinhos, variedade) ficam só no painel lateral, ao clicar na área.

---

# Interface

Aplicação de uma tela só (SPA): mapa à esquerda, painel lateral à direita, toolbar superior. Nunca abrir novas páginas; toda interação acontece no mapa/painel.

**A Visão Geral é o estado padrão do painel lateral** (não é mais modal): aparece sozinha ao carregar o projeto, com contadores (estufas/áreas), distribuição de áreas por variedade, links de exportação (PDF/CSV) e os campos de Observações / Análise Geral, todos com salvamento automático.

Ao selecionar uma Estufa ou uma Área, o painel muda para o respectivo modo de edição e mostra, no topo, um botão "← Visão Geral" para voltar. O painel de Área também mostra "← Editar Estufa N" para voltar à estufa-mãe.

Variedades continuam em um modal separado (cadastro global, não é por projeto).

---

# Banco

SQLite. Persistência automática, sem botão "Salvar".

Migrações leves: `backend/banco.py` roda `CREATE TABLE IF NOT EXISTS` a partir de `schema.sql` e, em seguida, tenta `ALTER TABLE ... ADD COLUMN` para cada coluna adicionada depois do primeiro uso, ignorando o erro se a coluna já existir. Ao adicionar um campo novo a uma tabela existente, sempre:
1. Atualizar `schema.sql` (para bancos novos).
2. Adicionar a migração correspondente em `_migrar_colunas_novas` (para bancos já existentes).

---

# Organização

Backend (`backend/`):

- `app.py` — app factory Flask, registra blueprints, serve o frontend
- `banco.py` — conexão SQLite + migrações
- `schema.sql`
- `detector/detector.py` — detecção automática de estufas
- `rotas/` — blueprints: `projetos`, `estufas`, `areas`, `variedades`, `exportacao`, `pontos_acesso`, `auth`
- `servicos/` — regras de negócio: `projeto_servico`, `estufa_servico`, `area_servico`, `variedade_servico`, `resumo_servico`, `exportacao_servico`, `geometria`, `ponto_acesso_servico`

Frontend (`frontend/`):

- `index.html` — Home (listar/criar/renomear/excluir projeto)
- `projeto.html` — tela principal (SPA)
- `login.html` — tela de senha única compartilhada
- `css/style.css`
- `js/api.js` — única camada que chama `fetch()`; nenhum outro módulo deve chamar `fetch()` diretamente
- `js/home.js` — comportamento da Home
- `js/login.js` — comportamento da tela de login
- `js/mapa.js` — renderização SVG (estufas, áreas, rótulos) + modos interativos (amostra de cor, desenho manual)
- `js/sidebar.js` — painel lateral: Visão Geral (padrão), Estufa, Área
- `js/variedades.js` — modal de Variedades
- `js/undo.js` — pilha de desfazer (Ctrl+Z)
- `js/projeto.js` — orquestrador da tela principal, liga tudo

---

# Decisões de projeto importantes

Estas decisões vieram de problemas reais encontrados durante o desenvolvimento — não as reverta sem entender o motivo (documentado aqui e, com mais detalhe, no `SPEC.md` seção 7).

**Detector calibrado por amostra, nunca por cor fixa no código.** Fotos aéreas de propriedades diferentes têm estufas de cores muito diferentes (branco, cinza-azulado, rosa) e fundos diferentes (grama, solo exposto). Uma primeira versão cravava uma faixa de cor "branca" no código e funcionava só para uma foto específica. A versão atual pede que o usuário clique em um ou mais pontos de uma estufa conhecida na própria foto; o detector lê a cor (média ± desvio padrão em HSV) desses pontos — a união de vários pontos ajuda em coberturas listradas/ripadas — e usa isso como referência de cor. **Além disso, o tamanho do contorno amostrado vira a referência de escala** (em vez de um percentual fixo da imagem), o que resolve com naturalidade o caso de uma construção pequena (galpão, casa) ter cor parecida com a estufa mas tamanho muito menor.

**Geração de área usa recorte real do polígono, não bounding box.** A primeira versão dividia a caixa delimitadora (retângulo alinhado aos eixos) da estufa — isso "vazava" nos cantos sempre que a estufa detectada não era perfeitamente alinhada à imagem. A versão atual (`backend/servicos/geometria.py`) rasteriza o polígono real da estufa numa máscara e faz a interseção com cada faixa (vertical/horizontal/automática), garantindo que a área nunca ultrapasse o contorno verdadeiro. Essa mesma função é reaproveitada pelo split de estufa.

**Split de estufa reaproveita a função de divisão de área.** "Dividir estufa" e "Gerar áreas" usam a mesma lógica de corte (`geometria.dividir_poligono`), só que uma cria novas Estufas e a outra cria Áreas dentro de uma Estufa.

**Detector filtra por forma (solidez) e separa blobs fundidos (watershed).** A máscara de cor sozinha não distingue uma estufa (retangular, convexa) de uma mancha de vegetação/árvore (irregular, lobulada) com brilho parecido — por isso todo contorno candidato passa por um filtro de solidez (`área / área do fecho convexo`) antes de virar estufa. Além disso, o fechamento morfológico antigo (kernel 7×7, 3 iterações) chegava a colar estufas vizinhas numa única máscara; o fechamento atual é bem mais conservador (3×3, 1 iteração), e qualquer contorno que ainda assim fique anormalmente grande é testado com uma separação via `watershed` (núcleos pela transformada de distância) antes de aceitá-lo como uma única estufa. Ver `SPEC.md` seção 7.1 para os passos completos.

**Rótulo da estufa sempre visível; áreas não têm mais texto próprio.** A primeira versão escondia o rótulo da estufa quando ela já tinha áreas, porque ele podia cair visualmente em cima do rótulo de alguma área (três linhas: `A{ordem}`, dimensões, variedade) e bloquear o clique nela. A versão atual resolve isso na raiz: áreas não mostram mais nenhum texto no mapa (só a cor), então o rótulo da estufa pode ficar sempre visível sem colidir com nada. Os detalhes de uma área só aparecem ao clicar nela (painel lateral) — o botão "← Editar Estufa" continua existindo no painel de Área como atalho, mas agora clicar direto no rótulo da estufa no mapa também funciona.

**Desfazer (Ctrl+Z) cobre apenas mudanças estruturais**, não edições de campo isoladas (nome, fase, etc.): detectar, gerar áreas, dividir estufa, excluir estufa, excluir área. O mecanismo é simples de propósito — o frontend guarda uma cópia de `estufas` (com áreas aninhadas) antes da ação destrutiva, e Ctrl+Z manda essa cópia de volta para `POST /api/projetos/{id}/estufas/restaurar`, que apaga as estufas atuais do projeto e recria a partir da cópia (os IDs mudam, os dados não).

**Exportação em PDF sanitiza todo texto do usuário para Latin-1** antes de mandar para o fpdf2 (fontes core do PDF não suportam Unicode completo — um caractere como "—" derrubava a exportação inteira). Ver `_texto_seguro` em `exportacao_servico.py`.

---

# Desenvolvimento

Sempre escrever código limpo.

Utilizar type hints (Python) e nomes em português (consistente com o restante do código).

Seguir PEP8.

Evitar funções grandes.

Preferir código simples ao invés de soluções excessivamente sofisticadas.

Sempre que houver dúvida, escolher a solução mais simples que atenda ao requisito.

Ao alterar comportamento, atualizar o `SPEC.md` correspondente.

Antes de considerar uma mudança pronta, teste-a de verdade (subir o servidor e exercitar o fluxo, seja manualmente ou com um script) — várias correções neste projeto só apareceram testando de fato, não só lendo o código.
