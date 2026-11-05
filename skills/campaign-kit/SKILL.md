---
name: campaign-kit
description: Use quando o usuário quiser criar ou rodar uma campanha de marketing (imagens e vídeos em vários formatos) a partir de uma pasta com logo, referências e briefing, com aprovação peça por peça no navegador.
---

# campaign-kit

Gera a campanha localmente: specs declarativos, compliance (nunca cobrir rostos),
vídeo editado com ffmpeg embutido e revisão no navegador com aprovar/rejeitar/refazer.

## Passos

1. **Ache a raiz do kit**: pasta com `AGENTS.md` + `install.sh`. Se este skill foi
   copiado para fora do repo, pergunte ao usuário onde ele clonou o
   `creative-kit-generator` (ou ofereça clonar de
   `https://github.com/dannowk/creative-kit-generator`).
2. **Bootstrap sem admin**: se `.venv/` não existir, rode
   `./install.sh <inbox> --no-open` em background — ele baixa `uv` para `.tools/`,
   cria Python 3.12 gerenciado dentro da pasta e instala as dependências.
   `<inbox>` = pasta da campanha (default `~/Desktop/minha-campanha`); o wizard
   (`onboard`) cria a estrutura `logo/ photos/ videos/ refs/ fonts/ briefing.md`.
3. **Siga o `AGENTS.md` da raiz**: `intake (ou brief --apply) → plan → assets →
   render → video`. A direção de arte vem do briefing + refs, não de outro cliente.
4. **Custo é aviso**: mostre ≈ créditos antes de jobs de provider e siga.
5. **Revisão**: suba `review` (abre o navegador sozinho; atalho
   `ABRIR-REVISAO.html` na pasta da campanha). Conduza aprovar/rejeitar/refazer;
   refazer chega em `requests.json` com o motivo do usuário.

Provider de assets (MCP do usuário, ex. Magnific) vive no agente, não no kit:
seção `provider` do briefing + `assets/jobs.json` → MCP → `drop_dir` → coleta.