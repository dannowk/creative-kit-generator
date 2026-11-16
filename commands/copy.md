---
description: Gera só o COPY da campanha (texto para PPC + overlay) a partir de briefing + textos de exemplo, com aprovação linha a linha numa tabela no navegador. Independente do visual — sem logo/brandbook. Sem o usuário abrir terminal.
---

O usuário **não abre terminal nem digita comando**. Você (agente) roda tudo; ele só
conversa no chat e usa o navegador. Este comando é o **copy kit** (independente do
`/campaign-kit:start`, que é o visual). Siga a skill `copy-kit` nesta ordem:

1. Ache a raiz do kit (a pasta com `AGENTS.md` + `install.sh`).
2. **Crie a pasta automaticamente**, sem perguntar caminho: default
   `~/Desktop/minha-campanha-copy` (ou `~/Desktop/<marca>-copy` se o usuário já disse o nome).
3. Rode `./install.sh <inbox> --copy` (Mac/Linux) ou `Instalar.bat <inbox> --copy`
   (Windows) em **background**. Baixa `uv` + Python 3.12 gerenciado (sem admin), instala
   as deps e **abre o wizard de copy no navegador**, criando só `briefing.md` +
   `examples.txt` (sem logo/brandbook/refs). Se `.venv/` já existe, só reabre o wizard.
4. Diga no chat: *"Abri o wizard de copy no navegador. Preencha o briefing (objetivo,
   público, tom, oferta, conceitos) e cole textos de exemplo no campo de exemplos.
   Me avise quando terminar."* Espere o OK.
5. `copy plan <pasta>` → leia briefing + exemplos → **autore `copy.json`** (concepts +
   rows: id, destination ppc/overlay, concept, axis, kind, text, lang, status pending,
   origin agent, updated_at/by). PPC: headline/description/primary_text. Overlay:
   hook/kicker/program/cta. **Nunca invente copy** fora do briefing+exemplos; **nunca
   marque approved** (é do usuário).
6. `copy validate <pasta>` → corrija erros (nada gravado se erro).
7. `copy review <pasta>` → abre a **tabela** (atalho `ABRIR-COPY-REVISAO.html`). O usuário
   aprova/rejeita/refazer+nota por linha. Cumpra rejected/redo reescrevendo o text,
   voltando a pending e recarimbando updated_at/by; a tabela atualiza sozinha.
8. Tudo aprovado → o usuário clica **Exportar aprovadas** (ou você roda `copy deliver
   <pasta>`): planilhas CSV+XLSX (Meta / Google RSA / overlay / manifest) em
   `~/Desktop/Copy Kit/<pasta>/`, só aprovadas, com download + **Abrir pasta**. Limites
   RSA (≤30/≤90) viram aviso. URL/orçamento/IDs em branco pro time de PPC — não invente.

**Um fluxo por vez na UI:** não suba o wizard/review visual e o de copy na mesma sessão.
Independente do visual: não toca campaign/render/ppc visual.