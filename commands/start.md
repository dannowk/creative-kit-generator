---
description: Conduz uma campanha do zero sem o usuário abrir terminal — cria a pasta, instala o Python gerenciado, abre o onboarding no navegador e segue até a revisão.
---

O usuário **não abre terminal nem digita comando**. Você (agente) roda tudo; ele só
conversa com você no chat e usa o navegador. Conduza nesta ordem:

1. Ache a raiz do kit (a pasta com `AGENTS.md` + `install.sh`).
2. **Crie a pasta da campanha automaticamente**, sem perguntar caminho: default
   `~/Desktop/minha-campanha` (ou `~/Desktop/<marca>` se o usuário já disse o nome
   da marca no chat). Não peça para ele criar pasta nem digitar path.
3. Rode `./install.sh <inbox>` (Mac/Linux, sem `--no-open`) ou `Instalar.bat <inbox>`
   (Windows) em **background**. Ele baixa `uv` +
   Python 3.12 gerenciado (sem admin), instala as dependências e **abre o wizard de
   onboarding no navegador** do usuário, criando `logo/ refs/ brandbook/ fonts/
   photos/ videos/ briefing/ briefing.md`. Cada slot aceita botão + arrastar-e-soltar (o briefing
   também). Se `.venv/` já existe, só reabre o wizard.
4. Diga no chat: *"Abri o onboarding no navegador. Suba o logo (obrigatório), fotos
   e referências, e preencha o briefing; se tiver um brandbook, pode anexar também
   (opcional). Na área de briefing há 'Documentos de apoio' para anexar vários arquivos:
   copy dos anúncios, regras de layout, safe areas, segurança do logo. Me avise quando terminar."*
   Espere o OK.
5. Leia `AGENTS.md` e siga o pipeline: `intake (ou brief --apply) → plan → assets →
   render → video`. Briefing livre (prosa/PDF/docx)? `brief --normalize <fonte>` →
   preencha o skeleton (visão p/ PDF; o que faltar fica vazio, vira gap) → `brief --apply`.
6. Avise o ≈ custo antes de jobs de provider (é aviso, não porteiro).
7. Suba `review` (abre o navegador sozinho). Aprovar/rejeitar/refazer só **marcam**; o usuário
   clica **Continuar** (etapa 6) — ou você roda `deliver` — para exportar as aprovadas na pasta
   de entrega do Desktop (`~/Desktop/Campaign Kit/<campanha>/`) e enfileirar rejeitadas/refazer
   em `requests.json`. O botão **Abrir pasta** abre essa pasta no computador do usuário. Cumpra
   o lote (recrie/refaça de fato, mudando template/asset/copy), rode `render --ids <ids>` e a
   revisão atualiza sozinha.
   Se o usuário usou **Ajustar estilo** (cores/fontes de um conceito inteiro), o `styles/<concept>.yaml`
   já é aplicado pelo render — para esse lote basta `render --ids`. Ver AGENTS.md.
8. O Continuar/`deliver` também gera as **planilhas de PPC** (Meta + Google) em `ppc/` na pasta
   de entrega (Desktop), CSV + XLSX, p/ o time de tráfego importar em lote. Ou rode `ppc <campanha>`. URL/orçamento/
   targeting/IDs ficam em branco para o PPC — não invente. Ver "Etapa 6b" no AGENTS.md.

Não pule o compliance (nunca cobrir rostos) e não hardcode visual de marca.