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
roda tudo. Em vez do venv manual acima, use `./install.sh <inbox>` em background (sem
`--no-open`): ele baixa `uv` + Python 3.12 gerenciado **sem admin**, instala as deps e
**abre o wizard de onboarding no navegador**. **Crie a pasta `<inbox>` automaticamente**
(default `~/Desktop/minha-campanha`, ou `~/Desktop/<marca>`), sem perguntar caminho ao
usuário; o `onboard` faz o scaffold (`logo/ photos/ videos/ refs/ fonts/ briefing.md`).
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
#    cria logo/ refs/ fonts/ photos/ videos/ + briefing.md; o usuário preenche.
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
#    imprime briefing, respostas do onboarding, refs, reference_analysis, os
#    conceitos pedidos e o vocabulário de OPS. Autorais os templates/<concept>.yaml
#    a partir DISSO — um por conceito pedido.

# 4. Assets de IA (imagem e vídeo) — aviso de custo informativo, sem porteiro
python3 -m kit.cli assets campaigns/acme-launch
#    imprime "≈ X créditos (N imagem(ns) + M vídeo(s))" e gera/coleta.

# 5. Renderizar a matriz de peças (conceitos × formatos × eixos)
python3 -m kit.cli render campaigns/acme-launch
#    --concepts clean cinema --formats Meta-Feed --limit 4 --dry

# 5b. Editar vídeo: trim, reframe por sujeito, overlay de marca, concat, legenda
python3 -m kit.cli video campaigns/acme-launch

# 6. Revisão local (127.0.0.1, porta livre a partir de 8765): aprovar / rejeitar / refazer por peça.
#    Abre o navegador sozinho e grava ABRIR-REVISAO.html na pasta da campanha (atalho clicável).
#    --no-open para headless. A URL também aparece no topo da tela e no fim de render/video.
python3 -m kit.cli review campaigns/acme-launch
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
  provider, asset_jobs) + `assets/` + `out/<concept>/` + `review/`.
- `brands/acme` + `campaigns/acme-launch` — exemplo genérico que acompanha o repo.

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
aprovar/rejeitar/refazer sem misturar.

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
4. **Revisão por peça:** aprovar / rejeitar / refazer, com filtros de status e achados
   de compliance no card. Mantenha esse formato.
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

## Limites honestos

O motor renderiza specs deterministicamente (PIL). A criatividade — autorais de
templates, copy, análise das refs, escolha de provider — é do agente. O kit não
"adivinha" a marca sozinho: `intake` deriva o que dá (paleta, logo) e o resto vem do
briefing + da sua direção de arte no `plan`. No `normalize`, você adapta a prosa ao
schema, mas o que falta continua virando pergunta — nunca chute silencioso.