# AGENTS.md — campaign-kit

Ponto de entrada para o agente (Claude, Codex, Qoder, etc.). Leia isto primeiro e
execute o pipeline abaixo. Tudo roda **na máquina do usuário**, com os arquivos e o
controle locais. **Não é um serviço hospedado** — não há backend, login, nuvem nem URL
pública. Você (agente) é quem faz a direção de arte e a geração de IA; o motor Python é
determinístico e só renderiza o que você especificou.

## O que é

Um kit que transforma uma pasta (logo + referências + briefing) em uma campanha
completa: variações visuais, vários formatos/aspect ratios, pastas de saída separadas,
copy gerada e regras de compliance. Genérico para qualquer empresa — o design **segue o
briefing e as referências fornecidas**, nunca um visual fixo herdado.

## Bootstrap (uma vez)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Dependências: **Pillow, numpy, PyYAML, imageio-ffmpeg, faster-whisper**. Python 3.9+.
Rode todos os comandos da raiz como `python3 -m kit.cli ...`.

**Fluxo sem terminal (padrão):** o usuário não abre terminal nem digita comando — você
roda tudo. Em vez do venv manual acima, use `./install.sh <inbox>` (Mac/Linux, sem
`--no-open`) ou `Instalar.bat <inbox>` (Windows) em background: ele baixa `uv` + Python 3.12 gerenciado **sem admin**, instala as deps e
**abre o wizard de onboarding no navegador**. **Crie a pasta `<inbox>` automaticamente**
(default `~/Desktop/minha-campanha`, ou `~/Desktop/<marca>`), sem perguntar caminho ao
usuário; o `onboard` faz o scaffold (`logo/ refs/ brandbook/ fonts/ photos/ videos/ briefing/ briefing.md`).
Avise no chat que o onboarding abriu, espere o "pronto" e siga o pipeline. Os comandos
`python3` abaixo são o equivalente manual (porta C); no fluxo gerenciado use
`.venv/bin/python -m kit.cli ...` (Mac/Linux) ou `.venv\Scripts\python ...` (Windows).

**ffmpeg / codecs:** não instale ffmpeg de sistema nem codecs. O `imageio-ffmpeg` embute
o binário ffmpeg (usado pelo módulo de vídeo para trim/reframe/overlay/concat/legenda).
O `faster-whisper` só é importado/baixado (modelo) quando você pede legenda **automática**;
legenda manual ou `captions:"off"` não toca nele.

**Fontes:** não baixe fontes licenciadas por conta própria. Se a fonte da marca não veio
na pasta, o intake pergunta (rodada única) e o render degrada com fallback do SO
(macOS/Windows/Linux), avisando exatamente quais foram substituídas (`font_warnings`).
Para apontar uma pasta de fontes, use a env `CAMPAIGN_FONTS`. Só estoura se não houver
nem fallback de sistema (raro).

## Pipeline

```bash
# 1. Preparar a pasta da campanha (scaffold + UI guiada em 127.0.0.1:8766)
python3 -m kit.cli onboard ~/inbox/acme
#    cria logo/ refs/ brandbook/ fonts/ photos/ videos/ briefing/ + briefing.md; o usuário preenche.
#    No wizard, cada slot aceita botão + arrastar-e-soltar; o briefing também (arraste
#    .md/.txt/.rtf/.pdf/.docx). Cada arquivo enviado tem um ✕ para remover só aquele arquivo.
#    brandbook/ é opcional (manual da marca em PDF/imagens/docx).
#    briefing/ = documentos de apoio (vários, acumulam): copy dos anúncios, regras de layout,
#    safe areas, segurança do logo — texto/PDF/Word/imagem/planilha (.csv/.xlsx). O plan lista todos.
#    --no-ui = só scaffold + checklist, sem servidor.

# 2. Derivar a marca da pasta jogada (paleta, logo, análise das refs, gaps)
python3 -m kit.cli intake ~/inbox/acme acme
#    grava brands/acme/brand.yaml + intake.json. Gaps viram perguntas de 1 rodada;
#    as respostas (brands/acme/answers.json) são aplicadas no brand.yaml nesta rodada.

# 2-alt. Briefing canônico (schema + validate + apply), quando o usuário preenche
#        o modelo ou pede para adaptar um briefing existente a ele:
python3 -m kit.cli brief --template            # markdown gerado DO schema (nunca diverge)
python3 -m kit.cli brief ~/inbox/briefing.yaml          # valida: gaps + erros estruturais
python3 -m kit.cli brief ~/inbox/briefing.yaml --apply  # escreve brand.yaml + campaign.json
#    apply é determinístico: copia logo/fontes/fotos/vídeos/refs, mapeia canais→formatos,
#    conceitos→concepts+copy, compliance→checks, provider→créditos, e o bloco video.
#    Sem paleta declarada, deriva proposta do logo (palette_proposed=true → confirme).

# 2-alt-normalize. Briefing LIVRE (prosa .md/.txt, PDF, docx) → schema canônico:
python3 -m kit.cli brief --normalize ~/inbox/briefing.pdf   # [--out ~/inbox/briefing.yaml]
#    Emite um skeleton YAML do schema (campos vazios + a pergunta de cada um) e um
#    contrato <out>.normalize.md. SEU TRABALHO: ler a fonte (visão p/ PDF/docx),
#    mapear a prosa nos campos e preencher o skeleton. O que não souber fica VAZIO
#    (vira gap na rodada única) — nunca chute valor, cor, canal, conceito ou copy.
#    Depois: brief <out> --apply. A garantia determinística é o validate, não a leitura.

# 3. Direção de arte a partir do briefing + referências  ← SEU TRABALHO CRIATIVO
python3 -m kit.cli plan campaigns/acme-launch
#    imprime briefing, respostas do onboarding, refs, brandbook (se houver),
#    reference_analysis, os conceitos pedidos e o vocabulário de OPS. Autorais os
#    templates/<concept>.yaml a partir DISSO — um por conceito pedido. LEIA o brandbook
#    com visão (PDF/imagem): as regras dele (cores, tipografia, uso do logo, voz)
#    prevalecem sobre a paleta proposta do logo; conflito com o briefing vira pergunta.

# 4. Assets de IA (imagem e vídeo) — aviso de custo informativo, sem porteiro
python3 -m kit.cli assets campaigns/acme-launch
#    imprime "≈ X créditos (N imagem(ns) + M vídeo(s))" e gera/coleta.

# 5. Renderizar a matriz de peças (conceitos × formatos × eixos)
python3 -m kit.cli render campaigns/acme-launch
#    --concepts clean cinema --formats Meta-Feed --limit 4 --dry
#    --ids <id> ...  re-renderiza SÓ essas peças (etapa 6: recriar/refazer) sem perder as decisões

# 5b. Editar vídeo: trim, reframe por sujeito, overlay de marca, concat, legenda
python3 -m kit.cli video campaigns/acme-launch

# 6. Revisão local (127.0.0.1, porta livre a partir de 8765): aprovar / rejeitar / refazer por peça.
#    Cada clique só MARCA a peça (intenção); nada executa até o botão "Continuar" (etapa 6 da UI).
#    Abre o navegador sozinho e grava ABRIR-REVISAO.html na pasta da campanha (atalho clicável).
#    --no-open para headless. A URL também aparece no topo da tela e no fim de render/video.
python3 -m kit.cli review campaigns/acme-launch

# 7. Entrega — equivalent headless do "Continuar". Exporta as aprovadas para a pasta de entrega
#    no Desktop (~/Desktop/Campaign Kit/<campanha>/<conceito>/) e enfileira rejeitadas (recriar) +
#    refazer (com a nota) em requests.json. A regeneração é SUA (agente): cumpra o lote e rode
#    `render --ids`. Ver "Etapa 6 — Entrega e regeneração". Com as aprovadas exportadas, gera
#    também as planilhas de PPC em ppc/ na mesma pasta de entrega (Meta + Google).
python3 -m kit.cli deliver campaigns/acme-launch

# 8. Planilhas de bulk upload p/ o time de PPC (Meta + Google), CSV + XLSX, em ppc/ na pasta de entrega (Desktop).
#    Determinístico: cada peça aprovada vira linha nas colunas de import de cada plataforma.
#    --all exporta todas as peças (não só as aprovadas). Ver "Etapa 6b — Planilhas de PPC".
python3 -m kit.cli ppc campaigns/acme-launch
```

`campaign` é sempre um **caminho** (ex.: `campaigns/acme-launch`), não um slug.

## Estrutura

- `kit/` — motor (render declarativo, primitives PIL, compliance, intake, onboard,
  providers, UI). Não hardcode visual de marca aqui.
- `templates/` — biblioteca global de specs de conceito (`cinema.yaml`, `editorial.yaml`,
  `poster.yaml`, `typographic.yaml`). Cada campanha pode sobrescrever em
  `campaigns/<slug>/templates/<concept>.yaml`.
- `brands/<id>/` — `brand.yaml` (paleta, papéis tipográficos com fallback de SO, voz,
  eixos, naming, compliance, safe zones, locales) + `assets/logo.png` + `intake.json`.
- `campaigns/<slug>/` — `campaign.json` (brand, channels, concepts, axes, cta, copy,
  provider, asset_jobs) + `assets/` + `out/<concept>/` (render de trabalho) + `review/`
  + `styles/<concept>.yaml` (ajuste de cores/fontes do conceito, opcional)
  + `state.json` (decisões) + `requests.json` (lote de regeneração).
- `~/Desktop/Campaign Kit/<campanha>/` — **pasta de entrega final**, fora do kit, no Desktop
  do usuário: `<concept>/` com as aprovadas exportadas pelo Continuar + `ppc/` (planilhas de
  bulk upload Meta + Google, CSV + XLSX). O botão **Abrir pasta** na revisão abre esta pasta.
- `brands/acme` + `campaigns/acme-launch` — exemplo genérico que acompanha o repo.

## Documentos de apoio do briefing (`<inbox>/briefing/`)

Além do `briefing.md` (o texto estruturado) e do `brandbook/` (manual da marca), o usuário
pode anexar **vários documentos de apoio** na pasta `briefing/` — pelo wizard (botão ou
arrastar-e-soltar, área "Documentos de apoio") ou soltando os arquivos direto na pasta.
Eles **acumulam** (não substituem o briefing) e aceitam texto (.md/.txt/.rtf), PDF/Word,
imagens (.png/.jpg/.webp — diagramas de safe area/logo) e planilha (.csv/.xlsx — tabela de
copy). Exemplos: conteúdo/copy dos anúncios em arquivos separados, regras de layout, safe
areas por formato, segurança/clearspace do logo extraída do brandbook.

O `intake` recolhe tudo em `brief_docs` no `intake.json` e o `plan` lista cada arquivo.
**SEU TRABALHO como agente:** leia todos (visão para PDF/imagem; texto/planilha direto) e
aplique — o copy/conteúdo dos anúncios alimenta `campaign.json.copy` (hook/kicker/program/
CTA por conceito×eixo, e o copy do RSA no export de PPC); regras de layout, safe areas e
segurança do logo viram `geometry`/`safe_zones` e `compliance` no `brand.yaml` e nos
templates. As regras do brandbook e destes documentos prevalecem sobre a paleta proposta;
conflito com o briefing vira pergunta — nunca chute silencioso.

## Specs de template (declarativo)

Um template é uma lista de `layers`; cada layer tem um `op` que é uma primitiva PIL
(`paper`, `photo`, `text`, `rule`, `logo`, ...). Expressões usam um avaliador de AST
restrito (variáveis como `w`, `h`, `scale`, `top`, `m`). Knobs por layer de texto:
`underline`, `accent_upper`, `accent_scale`, `max_h`, ancoragem. Autorais a partir do
briefing + refs — não copie o visual de outro cliente.

## Vários conceitos

O briefing pede os conceitos na **seção 7** (lista separada por vírgula, ex.:
`clean, editorial, cinema`). O `intake` extrai isso em `concepts_requested` (e pergunta
na rodada única se ficar em branco); o `plan` imprime. Para cada conceito pedido:

1. Autorei `campaigns/<slug>/templates/<concept>.yaml` (o local vence a biblioteca global).
2. Liste-o em `campaign.json.concepts`.
3. Dê um `copy.hook` por conceito (ou um bloco de voz `copy.<eixo>.<concept>`). **Sem
   hook, o conceito é pulado no render** com aviso.

A matriz é `conceitos × formatos × eixos`. Cada conceito entrega em pasta própria
`out/<concept>/` e ganha um contact sheet próprio `review/sheet_<concept>[_<eixo>].png`.
Na revisão, os chips de **conceito** (além dos de status) isolam uma direção por vez para
aprovar/rejeitar/refazer sem misturar. Com um conceito filtrado, o botão **Ajustar estilo**
muda cores/fontes de **todas** as peças daquele conceito de uma vez (ver "Ajuste de estilo
por conceito").

## Vídeo

O módulo `kit/video.py` edita localmente com o ffmpeg embutido (sem ffmpeg de sistema):

- **Trim** por duração (`durations` por formato, ou `default`).
- **Reframe** por aspect ratio com crop centrado no sujeito (`subject_center`), então o
  rosto fica no centro do corte — nunca cortado fora.
- **Overlay de marca** reaproveitando o spec declarativo do conceito em modo
  transparente (`render.render(..., transparent=True)`): logo, kicker, hook, CTA nos
  safe zones, igual aos PNG.
- **Concat** de clipes de mesma geometria (`video.concat`, copy sem re-encode).
- **Legenda queimada**: `"auto"` (faster-whisper, modelo baixado no 1º uso) ou uma lista
  manual `[{start,end,text}]`. Vira PNG do PIL sobreposto por janela de tempo — não
  depende de libass/fontconfig. Com legenda, o `bottom` do overlay sobe para a copy/CTA
  não colidir com a faixa de legenda.

Config em `campaign.json.video`:
```json
{"source": "assets/clip.mp4", "durations": {"meta_story": 15, "default": 6},
 "captions": "auto", "concepts": ["clean"], "formats": ["meta_story", "meta_feed_square"]}
```
`source` pode ser um mapping por eixo; `concat: [paths]` gera um master antes. As peças
saem em `out/<concept>/<name>.mp4`, entram no `state.json` com `kind:"video"` e aparecem
na revisão como player com aprovar/rejeitar/refazer. O compliance de rosto roda sobre um
frame composto (overlay + frame do meio), igual às imagens.

## Regras (invioláveis)

1. **Nunca cobrir rostos.** O check `subject_safe` compara o centro do sujeito com os
   elementos; respeite as safe zones. Se bloquear, reposicione — não desligue o check.
2. **Custo é aviso, não porteiro.** O usuário já espera ser cobrado pela geração
   contratada. Mostre `≈ X créditos` (estimativa do provider) e siga. Não bloqueie.
3. **Vídeo é job de provider** (`kind:"video"`), gerado via MCP do usuário (ex.:
   Magnific) — não há render local de vídeo. `credits_per_video` é separado de
   `credits_per_image`.
4. **Revisão por peça, em lote:** aprovar / rejeitar / refazer apenas **marcam** a peça
   (intenção no `state.json`); nada executa até o **Continuar** (etapa 6). Filtros de status
   e achados de compliance no card. As **aprovadas ficam só na lista de aprovadas** (saem da
   grade de trabalho); rejeitadas/refazer atualizam **na mesma página** após a regeneração.
   Mantenha esse formato.
5. **Arquivos e controle locais.** Nada de criar URL pública, remote ou deploy sem
   pedir explicitamente ao usuário.
6. **Design segue o briefing/refs.** `plan` te dá a matéria-prima; a direção de arte é
   sua, não um template fixo.

## Providers (contrato = pasta + manifest, não API)

`campaign.json.provider.name`:
- `manual` — você/agente deposita os arquivos em `drop_dir`; o kit coleta.
- `magnific-mcp` (ou `mcp`) — **mediado pelo agente**. `assets` prepara
  `campaigns/<slug>/assets/jobs.json` e levanta `NeedsAgent`; o CLI imprime os jobs.
  Você cumpre cada job pelo seu MCP (imagem ou vídeo), salva no `drop_dir`, e roda
  `assets` de novo para coletar + gravar `manifest.json` (com `kind` e créditos).
- `http_api` — POST genérico configurável (`credits_per_image`, `credits_per_video`,
  `{duration}` no body; `.mp4` para vídeo, `.png` para imagem).

`estimate()` é obrigatório em todo provider e retorna o aviso informativo.

## Normalize (briefing livre → schema, mediado pelo agente)

Mesma lógica dos providers: o Python prepara, o agente cumpre, o Python valida.
`brief --normalize <fonte>` emite um **skeleton YAML** do schema (campos vazios, a
pergunta de cada um em comentário) + um contrato `<out>.normalize.md` com a fonte
(o texto, se `.md/.txt/.rtf`; senão a instrução de extrair).

Seu trabalho como agente:
1. Ler a fonte — **visão** para PDF/imagem, leitor de docx para `.docx`.
2. Mapear a prosa nos campos do skeleton, respeitando enums e chaves de mapa.
3. **Não souber → deixe vazio** (`null/[]/{}`). Vazio vira pergunta na rodada única
   do `validate`; nunca invente valor, cor, canal, conceito, copy ou caminho.
4. Paths de arquivo relativos à base do contrato (a pasta do `--out`).
5. `brief <out>` (valida) → `brief <out> --apply` (escreve marca + campanha).

A garantia determinística é o **validate + apply**, não a sua leitura da prosa.

## Etapa 6 — Entrega (Continuar) e regeneração

Mesma lógica dos providers/normalize: o Python prepara e exporta, o agente regenera, o
Python re-renderiza e a UI atualiza. A revisão é **em lote** — decidir não executa nada.

**O que cada clique faz (só marca, no `state.json`):**
- **Aprovar** → `status:"approved"`. A peça sai da grade de trabalho e fica **só na lista
  de aprovadas**, marcada para ir para a pasta de entrega (Desktop).
- **Rejeitar** → `status:"rejected"`. Marcada para **recriar** (sem nota).
- **Refazer** → `status:"redo"` + `note` (o que ajustar). Marcada para **refazer com a nota**.
- **Ajustar estilo** (por conceito, ao filtrar um conceito) → grava `styles/<concept>.yaml`
  (cores/fontes/nota) e marca **todas** as peças daquele conceito como `redo`. Ver abaixo.

**O botão "Continuar" (ou `kit.cli deliver`) executa o lote:**
1. **Exporta** as aprovadas de `out/` para `~/Desktop/Campaign Kit/<campanha>/<conceito>/`
   (cópia local, imediata) e marca `delivered:true` + `delivery_path` (caminho absoluto).
2. **Enfileira** rejeitadas + refazer em `requests.json` — um lote com
   `{id, concept, format, axes, path, kind, asset, reason:"rejected"|"redo", note}`.
3. A UI avisa o que foi exportado/enfileirado, mostra o botão **Abrir pasta** (abre a pasta de
   entrega no Desktop) e avança o stepper para a etapa 6 (Entregar).

**SEU TRABALHO como agente — cumprir o lote `requests.json`:**
1. Para cada peça: `reason:"redo"` → aplique a `note` (ajuste o template/copy/asset);
   `reason:"rejected"` → **recrie** (nova direção, asset novo via MCP, ou variação de layout).
   O render é **determinístico**: re-renderizar o mesmo spec dá a mesma imagem — para mudar
   o resultado você **precisa** mudar um insumo (template, asset, copy ou fx).
2. Rode `render <campaign> --ids <id1> <id2> ...` para re-renderizar **só** essas peças.
   O `run` faz **merge** com o `state.json` anterior: aprovadas/entregues são preservadas,
   as peças re-renderizadas voltam a `pending` (sem `note`/`queued`) para nova revisão, e as
   demais ficam intactas. **Nunca** re-renderize a matriz inteira depois de aprovar — use `--ids`.
3. A revisão **atualiza sozinha** (poll de 4 s no `state.json`): as rejeitadas/refazer
   reaparecem como pendentes com a imagem nova, na mesma página; as aprovadas seguem só na
   lista de aprovadas. O usuário revisa de novo e clica Continuar outra vez até fechar.

A pasta de entrega final (aprovadas + PPC) fica em `~/Desktop/Campaign Kit/<campanha>/`, no
Desktop do usuário — o botão **Abrir pasta** na revisão a abre. `out/` (dentro de
`campaigns/<slug>/`) continua sendo o render de trabalho. Nada no kit lê a entrega de volta:
o merge e o PPC usam `state.json`/`out/`, então a entrega no Desktop não afeta a regeneração.

## Ajuste de estilo por conceito (`styles/<concept>.yaml`)

Para mudar **cores, fontes etc. de todas as peças de um conceito de uma vez**, o usuário
filtra o conceito na revisão e clica **Ajustar estilo**: mexe nos papéis da paleta
(`primary/accent/ink/paper/dark`), nos papéis tipográficos (`display/text/accent`) e numa
nota livre. Isso grava `campaigns/<slug>/styles/<concept>.yaml` e marca todas as peças do
conceito como `redo` (as aprovadas voltam a `pending`). **Nada renderiza na hora** — igual
ao refazer, o lote sai no **Continuar** (`requests.json`).

**O override é aplicado pelo próprio render**, por conceito: `campaign.run` mescla
`styles/<concept>.yaml` sobre a paleta/tipografia da marca base (`styled_brand`) antes de
renderizar e checar compliance. Ou seja:

- Para cumprir um lote de restyle, **basta rodar `render --ids <ids>`** — o novo estilo já
  entra sozinho; você **não** precisa editar template nem `brand.yaml` para cor/fonte.
- O ajuste **persiste**: vale para essa e para as próximas renderizações daquele conceito.
- A `note` do restyle é orientação extra (ex.: "mais contraste"); se pedir algo além de
  cor/fonte (layout, safe area), aí sim ajuste o template/`brand.yaml` como no refazer normal.
- Conflito entre o override e o briefing/brandbook vira pergunta — não chute.

```yaml
# campaigns/<slug>/styles/cinema.yaml (exemplo)
palette: {dark: "#040D0B", accent: "#FC6C54"}
type: {display: DINPro-Bold.otf}
note: mais contraste
```

## Etapa 6b — Planilhas de PPC (bulk upload Meta + Google)

Quando a demanda é alta, Meta e Google aceitam importar anúncios em lote por planilha. O
`kit.cli ppc` (e o **Continuar**, que já chama o export) gera essas planilhas em
`ppc/` na pasta de entrega (`~/Desktop/Campaign Kit/<campanha>/ppc/`), **uma por plataforma**,
em **CSV** (import direto) e **XLSX** (revisão no
Excel/Sheets). É determinístico: cada peça aprovada (criativo + copy) vira uma linha nas
colunas de import da plataforma, conforme formato/tamanho/canal.

**Arquivos gerados:**
- `meta_bulk_import` → Meta Ads Manager → Import/Export → **Import Ads in Bulk**. Uma linha
  por peça Meta (feed/story/reels), com placements por formato, CTA, copy e nome do criativo.
- `google_search_rsa` → Google Ads Editor (CSV) ou **Bulk actions → Uploads**. Responsive
  Search Ads: até 15 headlines (≤30 car.) + 4 descriptions (≤90) derivados do copy por
  conceito×eixo (não por peça — o RSA é texto, não imagem).
- `google_display` → Google Ads Editor / Uploads. Responsive Display Ads: texto + **referência
  ao arquivo de imagem/logo** (o anexo da imagem é feito no Editor, não por CSV puro).
- `creative_manifest` → referência humana: cada peça com plataforma, formato, tamanho,
  conceito, eixos, arquivo, caminho de entrega e copy (hook/kicker/program/CTA).
- `README.txt` → o que já vem preenchido vs. o que o time de PPC completa, e os limites.

**Já preenchido pelo kit:** nomes de campanha/ad set/ad, criativo (nome do arquivo), copy
(hook/primary text, headline, description), CTA (enum do Meta), placements e tamanho.
**Fica em branco (coluna rotulada) para o time de PPC:** URL final (`Link`/`Final URL`),
Display Link, URL Tags (UTM), objetivo, orçamento, optimization goal, billing event,
países/targeting e IDs (Facebook Page/`Link Object ID`, Instagram Account ID, Pixel). Tudo
sai **PAUSED/Paused** para revisão antes de ativar.

**SEU TRABALHO como agente:** o export é mecânico e não inventa URL nem orçamento. Se o
briefing trouxer a landing page, você pode gravar `landing_url` no `campaign.json` para o
kit pré-preencher `Link`/`Final URL`; caso contrário, deixe em branco e sinalize ao usuário
que o PPC completa. Não preencha IDs de Page/Pixel/Instagram nem verba — são do time de
tráfego. O copy do RSA sai do `copy` da campanha; se faltar headline/description, melhore o
`copy` no briefing e re-renderize/exporte, não hardcode na planilha.

## Idioma (PT/EN)

A UI (wizard + revisão) tem toggle **PT | EN** no topo, gravado em cookie, e o CLI aceita
`--lang en` ou a env `KIT_LANG=en` (default PT). Slots, perguntas do briefing, gaps e
achados de compliance saem localizados. **Este AGENTS.md, as skills e a saída do `plan`
ficam em PT** — são o contrato do agente, não UI. Ao conversar com o usuário, responda no
idioma dele; o idioma da interface é independente e o usuário escolhe no toggle.

## Limites honestos

O motor renderiza specs deterministicamente (PIL). A criatividade — autorais de
templates, copy, análise das refs, escolha de provider — é do agente. O kit não
"adivinha" a marca sozinho: `intake` deriva o que dá (paleta, logo) e o resto vem do
briefing + da sua direção de arte no `plan`. No `normalize`, você adapta a prosa ao
schema, mas o que falta continua virando pergunta — nunca chute silencioso.