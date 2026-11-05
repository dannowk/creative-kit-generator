---
name: campaign-kit
description: Use quando o usuário quiser criar ou rodar uma campanha de marketing (imagens e vídeos em vários formatos) a partir de logo, referências e briefing, com aprovação peça por peça no navegador. Conduz tudo sem o usuário abrir terminal.
---

# campaign-kit

Gera a campanha localmente: specs declarativos, compliance (nunca cobrir rostos),
vídeo com ffmpeg embutido e revisão no navegador (aprovar/rejeitar/refazer).
**O usuário não abre terminal nem digita comando — você roda tudo; ele usa o chat
e o navegador.**

## Passos

1. **Ache a raiz do kit** (`AGENTS.md` + `install.sh`). Se não estiver no workspace,
   clone você mesmo de `https://github.com/dannowk/creative-kit-generator` para
   `~/Documents/creative-kit-generator` — não peça ao usuário para clonar.
2. **Crie a pasta da campanha automaticamente**: default `~/Desktop/minha-campanha`
   (ou `~/Desktop/<marca>` se ele já disse o nome no chat). Sem perguntar caminho.
3. **Bootstrap + onboarding num comando só**, em background: `./install.sh <inbox>`
   (sem `--no-open`). Baixa `uv` + Python 3.12 gerenciado sem admin, instala as deps
   e **abre o wizard no navegador**, criando `logo/ photos/ videos/ refs/ fonts/
   briefing.md`. `.venv/` já existe → só reabre o wizard.
4. **Avise no chat** que o onboarding abriu; peça o logo (obrigatório) + fotos/refs +
   briefing e espere o "pronto" do usuário.
5. **Siga o `AGENTS.md`**: `intake (ou brief --apply) → plan → assets → render →
   video`. A direção de arte vem do briefing + refs, não de outro cliente. Briefing
   livre (prosa/PDF/docx)? `brief --normalize <fonte>` → preencha o skeleton (visão
   p/ PDF; o que faltar fica vazio, vira gap) → `brief <out> --apply`.
6. **Custo é aviso**: mostre ≈ créditos antes de jobs de provider e siga.
7. **Revisão**: suba `review` (abre o navegador sozinho; atalho `ABRIR-REVISAO.html`
   na pasta da campanha). Conduza aprovar/rejeitar/refazer; refazer chega em
   `requests.json` com o motivo do usuário.

Provider de assets (MCP do usuário, ex. Magnific) vive no agente, não no kit:
seção `provider` do briefing + `assets/jobs.json` → MCP → `drop_dir` → coleta.