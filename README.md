# campaign-kit

**Idioma:** Português · [English](README.en.md)

Gere uma campanha completa a partir de uma pasta com **logo + referências + briefing**.
Roda na **sua máquina**, com o **seu agente de IA** (Claude, Codex, Qoder…). Não é um
serviço hospedado: nada de nuvem, login ou URL pública — os arquivos e o controle são
seus.

## Comece aqui (passo a passo)

### 1. Comece — sem terminal

**Você não precisa abrir terminal nem digitar comando.** O agente faz tudo por você:
cria a pasta da campanha, instala o Python sozinho (sem admin), abre o onboarding no
navegador e conduz até a revisão. Você só **conversa com ele no chat** e **usa o
navegador**. Escolha como colocar o agente para rodar:

**Porta 1 · Claude Code (plugin — sem baixar nada):**

1. Abra o Claude Code.
2. Peça para ele instalar o repositorio - https://github.com/dannowk/creative-kit-generator
   ```
   /plugin marketplace add dannowk/creative-kit-generator
   ```
   ```
   /plugin install campaign-kit@creative-kit-generator
   ```
3. Para começar, digite:
   ```
   /campaign-kit:start
   ```

### 2. Preencha a SUA pasta (o inbox da campanha)

Sua pasta fica **fora do kit** (ex.: `~/Desktop/minha-campanha`) — o kit é a
ferramenta; o inbox é o seu material. **O agente cria essa pasta e abre o wizard no
navegador para você.** É nele que você prepara tudo, sem digitar comando: suba ou
arraste os arquivos em cada slot e preencha o briefing na tela.

O wizard cria exatamente esta estrutura dentro da pasta que o agente criou:

```
minha-marca/
  logo/        ← logo png, de preferência fundo transparente (obrigatório)
  photos/      ← fotos que podem virar peça
  videos/      ← clipes fonte
  refs/        ← 2–6 referências de anúncios/posts do look desejado
  brandbook/   ← manual da marca em PDF/imagens/docx (opcional)
  fonts/       ← .ttf / .otf da marca (opcional; há substitutas)
  briefing/    ← documentos de apoio: copy dos anúncios, regras de layout, safe areas, segurança do logo (opcional, vários)
  briefing.md  ← o briefing que você preencheu na tela (ou editado à mão)
```

Cada slot aceita **botão ou arrastar-e-soltar** — e o briefing também: arraste um
`.md/.txt/.rtf/.pdf/.docx` para a área de briefing, ou escreva/cole na tela. Se você
anexar um **brandbook**, o agente lê as regras da marca (cores, tipografia, uso do logo,
voz) e as segue junto com o briefing e as referências.

**Documentos de apoio (vários arquivos):** na área de briefing há uma zona **"Documentos
de apoio"** para anexar quantos arquivos quiser — o **conteúdo/copy dos anúncios** (quando
está em arquivos separados), **regras de layout**, **safe areas** e **segurança do logo**
do brandbook. Aceita texto, PDF/Word, imagens (diagramas) e planilha (`.csv/.xlsx`, ex.:
tabela de copy). Eles **se somam** (não substituem o briefing) e aparecem numa lista com
botão de remover. O agente lê tudo no `plan`: o copy vira o texto das peças (e dos anúncios
de search no PPC), e as regras de layout/safe area/logo viram geometria e compliance.

**Já tem um briefing pronto em qualquer formato** (Word, PDF, texto, e-mail)? Não
precisa reescrever nada: o agente **normaliza** para o modelo do kit e te pergunta só
o que faltar (uma rodada única). É só dizer: *"normalize este briefing"* e apontar o
arquivo. Quem preenche o modelo na tela (acima) já está no formato certo.

**Prefere criar na mão, ou reabrir o wizard depois?** Dentro da pasta do kit, use o
Python que o instalador deixou (não o `python3` do sistema, que não tem as dependências):

```
.venv/bin/python -m kit.cli onboard ~/Desktop/minha-marca       # Mac / Linux
.venv\Scripts\python -m kit.cli onboard ~/Desktop/minha-marca   # Windows
```

(No fluxo manual do [Início rápido](#início-rápido-manual), use `python3` com o venv ativado.)

### 3. Entregue ao agente

> **No fluxo sem terminal (Portas 1 e 2)** o agente já está conduzindo — este passo é
> só para quem preparou a pasta na mão (alternativas com terminal).

Abra a **pasta do kit** no seu agente — Claude Code (`claude` no terminal dentro dela),
Qoder (abrir a pasta no app), Codex (`codex`) — e diga:

> "leia o AGENTS.md e rode a campanha de `~/Desktop/minha-marca`"

O agente conduz `intake (ou brief --apply) → plan → assets → render → video` e cria:

- `brands/minha-marca/` — `brand.yaml` (paleta, fontes, voz), `assets/logo.png`;
- `campaigns/minha-marca-<slug>/` — `campaign.json`, `templates/` (direção de arte),
  `assets/`, `out/`, `review/`.

Faltou informação? Vira **uma rodada única** de perguntas (no wizard ou no terminal).
Antes de gerar qualquer asset pago, o agente mostra o aviso de ≈ créditos.

### 4. Aprove no navegador — e clique Continuar para entregar

O `review` **abre o navegador sozinho** em `http://127.0.0.1:8765` (ou a próxima porta
livre). Na tela você decide peça por peça — **cada clique só marca, nada executa na hora**:

- **✓ aprovar** → a peça fica marcada para ir para a pasta de entrega e sai da grade de
  trabalho (vai só para a lista **Aprovadas**).
- **✕ rejeitar** → marcada para o sistema **recriar** outra automaticamente.
- **↻ refazer** → você escreve o que ajustar; a nota fica guardada.

Quando terminar de marcar, clique no botão **Continuar** (etapa 6). Aí sim tudo executa de
uma vez: as aprovadas são **exportadas para a pasta de entrega** e as rejeitadas/refazer
entram na fila de regeneração. O **agente recria/refaz** essas peças e elas **atualizam
nesta mesma página** sozinhas, prontas para revisar de novo. As aprovadas continuam só na
lista de aprovadas. Repita até fechar a campanha.

- Perdeu o link? Atalho clicável **`ABRIR-REVISAO.html`** dentro da pasta da campanha;
  o endereço também fica no topo da tela e no fim de `render` / `video` no terminal.
- Peças entregues (aprovadas): `campaigns/<campanha>/delivery/<conceito>/` (png/mp4). O
  render de trabalho fica em `out/<conceito>/` + contact sheet `review/sheet_<conceito>.png`.
- **Planilhas p/ o time de PPC (Meta + Google):** o Continuar também gera
  `campaigns/<campanha>/delivery/ppc/` com o bulk upload de cada plataforma em **CSV + XLSX**
  (Meta Ads Manager, Google Search RSA e Google Display) + um manifesto dos criativos. Já
  vem com nomes, copy, CTA, placements e tamanho; o time de tráfego completa URL, orçamento
  e IDs. Tudo sai pausado para revisão. Veja [Planilhas de PPC](#planilhas-de-ppc-meta--google).
- **Idioma da interface:** o wizard e a revisão têm toggle **PT | EN** no topo (fica
  gravado no navegador). No terminal, `--lang en` ou `KIT_LANG=en` traduz as mensagens.

### 5. Gerar imagem/vídeo com IA (opcional — só p/ o que faltar)

**Precisa disso?** Só se quiser que a IA **crie** imagem ou vídeo que está faltando.
Se o seu inbox já tem `photos/` e `videos/`, o kit renderiza a partir deles e você
**pula este passo**.

**Quem faz?** O **agente**, sozinho — você não edita YAML nem roda comando duas vezes.
Seu único trabalho é ter o MCP do provider instalado no agente (ex.: Magnific):
Claude Code (`claude mcp add …`), Qoder (Settings → MCP), Codex (`~/.codex/config.toml`).
Aí diga ao agente: *"gere os assets que faltam"*. Ele mostra o aviso de ≈ créditos
antes de gerar (é aviso, não porteiro) e cuida do resto.

**Por que o agente e não o kit?** O kit é Python local e **não guarda conexão MCP** —
de propósito, ele nunca vê suas credenciais. Quem tem o MCP é o agente; por isso é ele
quem gera, e o kit só coleta os arquivos prontos.

<details>
<summary>Por baixo do capô (avançado / manual)</summary>

O contrato vive na seção `provider` do briefing:

```yaml
provider:
  nome: magnific-mcp        # manual | magnific-mcp | http
  creditos_imagem: 4        # alimenta o aviso "≈ X créditos"
  creditos_video: 20
  drop_dir: ~/Downloads     # onde o agente solta os arquivos gerados
```

1. `assets` prepara `campaigns/<campanha>/assets/jobs.json` e para (`NeedsAgent`).
2. O agente cumpre cada job pelo MCP dele e salva no `drop_dir` com o **prefixo do id
   do job** (ex.: `acme-hero_….png`).
3. `assets` de novo coleta do `drop_dir`, copia para `assets/` da campanha e grava
   `manifest.json` (tipo + créditos).

Alternativas: `manual` (sem MCP — você mesmo dropa os arquivos no `drop_dir`) e `http`
(API genérica: `api_url` + `api_key_env`, ex. `MAGNIFIC_API_KEY`; **a chave fica em
variável de ambiente, nunca no briefing**).

</details>

### 6. Campanha nova

- **Mesma marca:** só um briefing novo (objetivo, oferta, CTA, canais, conceitos, copy);
  o agente reusa `brands/<id>` e cria `campaigns/<id>-<novo-slug>/`.
- **Marca nova:** novo inbox (passo 2) e repita do passo 3.

### Onde cada coisa fica

| O quê | Onde |
| --- | --- |
| código do kit | onde você baixou/abriu (ex.: `~/Documents/creative-kit-generator`) |
| seus arquivos | inbox que o agente criou (ex.: `~/Desktop/minha-campanha`) |
| marca derivada | `<kit>/brands/<id>/` |
| peças entregues (aprovadas) | `<kit>/campaigns/<id>-<slug>/delivery/<conceito>/` |
| render de trabalho | `<kit>/campaigns/<id>-<slug>/out/<conceito>/` + `review/sheet_<conceito>.png` |
| revisão | navegador `127.0.0.1:8765+` · atalho `ABRIR-REVISAO.html` |
| lote de regeneração | `<kit>/campaigns/<id>-<slug>/requests.json` (rejeitadas + refazer) |
| gerados pelo MCP | `drop_dir` (ex.: `~/Downloads`) → coletados p/ `assets/` da campanha |

## Início rápido (manual)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 -m kit.cli onboard ~/inbox/acme        # prepara a pasta; wizard abre no navegador
python3 -m kit.cli intake  ~/inbox/acme acme   # deriva a marca
#  ou, pelo modelo canônico de briefing (avançado):
python3 -m kit.cli brief --template           # só IMPRIME um checklist markdown (não salva arquivo)
#  preencha um briefing.yaml/.json com esses campos e então:
python3 -m kit.cli brief ~/inbox/briefing.yaml --apply   # valida e escreve marca + campanha
#  ou normalize um briefing livre (prosa/PDF/docx) — emite skeleton + contrato p/ o agente:
python3 -m kit.cli brief --normalize ~/inbox/briefing.pdf   # agente preenche → brief <out> --apply
python3 -m kit.cli plan    campaigns/acme-launch
python3 -m kit.cli assets  campaigns/acme-launch
python3 -m kit.cli render  campaigns/acme-launch
python3 -m kit.cli video   campaigns/acme-launch   # trim/reframe/overlay/concat/legenda
python3 -m kit.cli review  campaigns/acme-launch   # abre o navegador sozinho; atalho ABRIR-REVISAO.html na pasta
python3 -m kit.cli deliver campaigns/acme-launch   # etapa 6: o "Continuar" — exporta aprovadas + enfileira recriação/refazer
#  o agente cumpre requests.json e re-renderiza só as peças do lote (preserva as aprovadas):
python3 -m kit.cli render  campaigns/acme-launch --ids <id1> <id2>
python3 -m kit.cli ppc     campaigns/acme-launch   # planilhas de bulk upload (Meta + Google), CSV + XLSX, em delivery/ppc/
python3 -m kit.cli ppc     campaigns/acme-launch --all   # exporta todas as peças, não só as aprovadas
```

## Planilhas de PPC (Meta + Google)

Para campanhas com muitos anúncios, Meta e Google aceitam **importar em lote por planilha**.
O kit gera essas planilhas sozinho — o **Continuar** já cria, e você também pode rodar
`python3 -m kit.cli ppc <campanha>` a qualquer momento. Tudo cai em
`campaigns/<campanha>/delivery/ppc/`, em **CSV** (import direto) e **XLSX** (revisão no
Excel/Google Sheets):

| Arquivo | Onde importar | O que é |
|---|---|---|
| `meta_bulk_import` | Meta Ads Manager → Import/Export → **Import Ads in Bulk** | Uma linha por peça Meta (feed/story/reels), com placements, CTA, copy e nome do criativo. |
| `google_search_rsa` | Google Ads Editor (CSV) ou **Bulk actions → Uploads** | Responsive Search Ads: até 15 headlines (≤30 car.) + 4 descriptions (≤90) por conceito×eixo. |
| `google_display` | Google Ads Editor / Uploads | Responsive Display Ads: texto + referência ao arquivo de imagem/logo (o anexo é feito no Editor). |
| `creative_manifest` | — (referência humana) | Cada peça com plataforma, formato, tamanho, conceito, arquivo e copy. |
| `README.txt` | — | O que vem preenchido vs. o que o PPC completa, e os limites de caracteres. |

**Já preenchido:** nomes de campanha/ad set/anúncio, criativo (nome do arquivo), copy
(hook/primary text, headline, description), CTA, placements e tamanho — tudo derivado da
campanha renderizada, conforme a plataforma e o formato de cada peça.

**O time de PPC completa (colunas em branco):** URL final, Display Link, URL Tags (UTM),
objetivo, orçamento, targeting e IDs (Facebook Page, Instagram, Pixel). Nada disso é
inventado pelo kit. Todos os anúncios saem **pausados** para revisão antes de ativar.

<details>
<summary>Detalhes (avançado)</summary>

- O export é **determinístico**: peça aprovada → linha. Re-renderize/re-aprove e rode `ppc`
  de novo para atualizar. `--all` inclui peças ainda não aprovadas (útil para rascunho).
- O copy do Google RSA sai do `copy` da campanha (program/kicker/hook/CTA), truncado nos
  limites do Google e sem os `[colchetes]` de destaque. Melhore o `copy` no briefing se
  quiser headlines/descriptions melhores — não edite a planilha na mão.
- Se o briefing trouxer a landing page, grave `landing_url` no `campaign.json` para o kit
  pré-preencher `Link`/`Final URL`; senão ficam em branco para o PPC.
- XLSX exige `openpyxl` (já em `requirements.txt`). Sem ele, o kit exporta só CSV e avisa.
- Google Display não anexa imagem por CSV puro: a planilha lista `Image file`/`Logo file`
  para você anexar no Editor. Meta usa o nome do arquivo de criativo já exportado.

</details>

## O que vem no repo

- `kit/` — motor de render declarativo + compliance + providers + UI local.
- `templates/` — biblioteca de specs de conceito (sobrescrevível por campanha).
- `brands/acme` + `campaigns/acme-launch` — exemplo genérico para você seguir.

O design **segue o briefing e as referências** — não herda o visual de outro cliente.
Regras completas e contrato de providers em **[AGENTS.md](AGENTS.md)**.
