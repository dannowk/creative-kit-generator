---
description: Conduz uma campanha do zero sem o usuário abrir terminal — cria a pasta, instala o Python gerenciado, abre o onboarding no navegador e segue até a revisão.
---

O usuário **não abre terminal nem digita comando**. Você (agente) roda tudo; ele só
conversa com você no chat e usa o navegador. Conduza nesta ordem:

1. Ache a raiz do kit (a pasta com `AGENTS.md` + `install.sh`).
2. **Crie a pasta da campanha automaticamente**, sem perguntar caminho: default
   `~/Desktop/minha-campanha` (ou `~/Desktop/<marca>` se o usuário já disse o nome
   da marca no chat). Não peça para ele criar pasta nem digitar path.
3. Rode `./install.sh <inbox>` em **background, sem `--no-open`**. Ele baixa `uv` +
   Python 3.12 gerenciado (sem admin), instala as dependências e **abre o wizard de
   onboarding no navegador** do usuário, criando `logo/ photos/ videos/ refs/
   fonts/ briefing.md`. Se `.venv/` já existe, só reabre o wizard.
4. Diga no chat: *"Abri o onboarding no navegador. Suba o logo (obrigatório), fotos
   e referências, e preencha o briefing; me avise quando terminar."* Espere o OK.
5. Leia `AGENTS.md` e siga o pipeline: `intake (ou brief --apply) → plan → assets →
   render → video`. Briefing livre (prosa/PDF/docx)? `brief --normalize <fonte>` →
   preencha o skeleton (visão p/ PDF; o que faltar fica vazio, vira gap) → `brief --apply`.
6. Avise o ≈ custo antes de jobs de provider (é aviso, não porteiro).
7. Suba `review` (abre o navegador sozinho) e conduza aprovar / rejeitar / refazer;
   pedidos de refazer chegam em `requests.json`.

Não pule o compliance (nunca cobrir rostos) e não hardcode visual de marca.