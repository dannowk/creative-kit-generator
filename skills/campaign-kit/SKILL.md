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
   e **abre o wizard no navegador**, criando `logo/ refs/ brandbook/ fonts/ photos/
   videos/ briefing/ briefing.md`. Cada slot aceita botão + arrastar-e-soltar (o briefing também).
   `.venv/` já existe → só reabre o wizard.
4. **Avise no chat** que o onboarding abriu; peça o logo (obrigatório) + fotos/refs +
   briefing (brandbook é opcional) e espere o "pronto" do usuário. Na área de briefing há
   **"Documentos de apoio"** (vários, acumulam): copy dos anúncios, regras de layout, safe
   areas, segurança do logo — texto/PDF/Word/imagem/planilha. O `plan` lista todos; leia e
   aplique (copy → campaign.json.copy; regras → geometry/safe_zones/compliance).
5. **Siga o `AGENTS.md`**: `intake (ou brief --apply) → plan → assets → render →
   video`. A direção de arte vem do briefing + refs + brandbook (se houver), não de
   outro cliente. Briefing
   livre (prosa/PDF/docx)? `brief --normalize <fonte>` → preencha o skeleton (visão
   p/ PDF; o que faltar fica vazio, vira gap) → `brief <out> --apply`.
6. **Custo é aviso**: mostre ≈ créditos antes de jobs de provider e siga.
7. **Revisão + entrega (etapa 6)**: suba `review` (abre o navegador sozinho; atalho
   `ABRIR-REVISAO.html` na pasta da campanha). Aprovar/rejeitar/refazer só **marcam** a peça;
   o usuário clica **Continuar** (ou você roda `deliver`) para exportar as aprovadas em
   `delivery/` e enfileirar rejeitadas (recriar) + refazer (com a nota) em `requests.json`.
   **Cumpra o lote**: ajuste template/asset/copy (recrie de fato — o render é determinístico),
   rode `render --ids <ids>` (preserva as aprovadas) e a revisão atualiza sozinha. Repita até fechar.
   **Ajuste de estilo por conceito**: se o usuário usou **Ajustar estilo** na revisão, há um
   `styles/<concept>.yaml` (cores/fontes) que o **próprio render aplica** — para esse lote basta
   `render --ids`, sem editar template. Ver "Ajuste de estilo por conceito" no AGENTS.md.
8. **Planilhas de PPC (Meta + Google)**: o Continuar/`deliver` já gera `delivery/ppc/` com o
   bulk upload de cada plataforma em CSV + XLSX (Meta Ads Manager, Google Search RSA, Google
   Display) + manifesto. Ou rode `ppc <campanha>` (`--all` p/ não-aprovadas). Nomes/copy/CTA/
   placements/tamanho vêm preenchidos; **URL, orçamento, targeting e IDs ficam em branco para
   o time de tráfego** — não invente. Tudo sai pausado. Ver "Etapa 6b" no AGENTS.md.

Provider de assets (MCP do usuário, ex. Magnific) vive no agente, não no kit:
seção `provider` do briefing + `assets/jobs.json` → MCP → `drop_dir` → coleta.