---
name: copy-kit
description: Use quando o usuário quiser gerar só o COPY de uma campanha (texto para PPC e overlay) a partir de um briefing + textos de exemplo, com aprovação linha a linha numa tabela no navegador. Independente do kit visual — sem logo, brandbook ou imagens. Conduz tudo sem o usuário abrir terminal.
---

# copy-kit

Gera o copy localmente: o agente escreve a partir do briefing + exemplos, o kit valida
a forma e exporta **só o aprovado** (planilhas Meta / Google RSA / overlay). Revisão em
**tabela** no navegador (aprovar/rejeitar/refazer+nota por linha). **O usuário não abre
terminal nem digita comando — você roda tudo; ele usa o chat e o navegador.**

Independente do `campaign-kit` (visual): não toca campaign/render/ppc visual, não pede
logo/brandbook/refs. **Um fluxo por vez na UI** — wizard visual 8766/review 8765; copy
usa 8767 (wizard) / 8768 (tabela). Não suba os dois na mesma sessão.

## Passos

1. **Ache a raiz do kit** (`AGENTS.md` + `install.sh`). Se não estiver no workspace,
   clone você mesmo de `https://github.com/dannowk/creative-kit-generator` para
   `~/Documents/creative-kit-generator` — não peça ao usuário para clonar.
2. **Crie a pasta automaticamente**: default `~/Desktop/minha-campanha-copy` (ou
   `~/Desktop/<marca>-copy` se ele já disse o nome no chat). Sem perguntar caminho.
3. **Bootstrap + wizard de copy num comando só**, em background: `./install.sh <inbox> --copy`
   (Mac/Linux) ou `Instalar.bat <inbox> --copy` (Windows). Baixa `uv` + Python 3.12
   gerenciado sem admin, instala as deps e **abre o wizard de copy no navegador**,
   criando só `briefing.md` + `examples.txt` (sem logo/brandbook/refs/fotos/vídeos).
   `.venv/` já existe → só reabre o wizard.
4. **Avise no chat** que o wizard de copy abriu; peça o **briefing** (objetivo, público,
   tom de voz, oferta/produto, conceitos, eixos, restrições, idiomas) e os **textos de
   exemplo** (campo de texto onde ele cola copy que gosta / quer usar como modelo).
   Espere o "pronto" do usuário.
5. **`copy plan <pasta>`** imprime briefing + exemplos + o vocabulário de destinos/kinds.
   **SEU TRABALHO:** autore `<pasta>/copy.json` = `{"concepts":[...], "rows":[...]}`.
   Cada row: `id` (`k01`…, próximo livre), `destination` (`ppc`/`overlay`), `concept`,
   `axis` (opcional), `kind`, `text`, `lang` (`pt`/`en`), `status:"pending"`,
   `origin:"agent"`, `updated_at` (ISO UTC agora), `updated_by` (seu nome/usuário).
   - **ppc kinds:** `headline` (≤30 p/ Google RSA), `description` (≤90), `primary_text`.
   - **overlay kinds:** `hook`, `kicker`, `program`, `cta`.
   Volume alto: conceitos × eixos × destinos × versões. **Nunca invente copy** fora do
   briefing + exemplos; **nunca marque `approved`** — a decisão é do usuário na tabela.
6. **`copy validate <pasta>`** checa a forma (destinos/kinds/status/lang válidos, text
   não-vazio, ids únicos, conceito declarado). Erro → nada gravado; corrija e revalide.
7. **`copy review <pasta>`** abre a **tabela** no navegador (atalho `ABRIR-COPY-REVISAO.html`
   na pasta). Cada linha tem aprovar / rejeitar / refazer+nota; filtros por status,
   destino (PPC/overlay) e conceito. Só **marca** a linha (intenção). **Cumpra o lote:**
   `rejected` → reescreva o copy (nova direção a partir do briefing/exemplos); `redo` →
   aplique a `note`. Mude o `text`, volte `status:"pending"`, limpe `note`, recarimbe
   `updated_at`/`updated_by`. A tabela atualiza sozinha (poll de 4 s). Repita até fechar.
8. **Entrega:** tudo aprovado → o usuário clica **Exportar aprovadas** na tabela (ou você
   roda **`copy deliver <pasta>`**). Gera planilhas **CSV + XLSX** em
   `~/Desktop/Copy Kit/<pasta>/`: `meta_bulk_import`, `google_search_rsa`, `overlay`
   (conceito × eixo × kind), `copy_manifest` + README. **Só as aprovadas saem.** Limites
   RSA (headline ≤30 / description ≤90) viram **aviso + truncamento**, não porteiro.
   URL/orçamento/targeting/IDs ficam **em branco para o time de PPC** — não invente.
   Tudo sai PAUSED. O botão **Abrir pasta** abre a pasta no computador do usuário; os
   arquivos também ficam disponíveis para **download** na própria tabela.

O copy é independente: entrega o arquivo dele. Não há import automático pelo kit visual
(handoff = passo futuro, se o usuário quiser). A voz vem do briefing + exemplos colados,
não de logo/brandbook.