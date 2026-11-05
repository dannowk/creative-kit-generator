# campaign-kit

Gere uma campanha completa a partir de uma pasta com **logo + referências + briefing**.
Roda na **sua máquina**, com o **seu agente de IA** (Claude, Codex, Qoder…). Não é um
serviço hospedado: nada de nuvem, login ou URL pública — os arquivos e o controle são
seus.

## Comece aqui (passo a passo)

### 1. Instale — escolha uma porta

> Preciso baixar os arquivos antes? **A1 não** — o próprio agente busca do GitHub.
> **A2, B e C sim**: você precisa da pasta do kit no seu computador primeiro
> (cada uma mostra como abaixo).

**A. Como extensão do seu agente (recomendado — roda junto com ele):**

Escolha o seu agente abaixo e siga os passos na ordem. O **A1 não precisa de terminal
nem de clone**: você cola comandos dentro do próprio Claude Code.

**A1 · Claude Code (plugin — o caminho mais fácil):**

1. Abra o Claude Code (digite `claude` no terminal, em qualquer pasta).
2. Cole o comando abaixo e dê Enter — ele registra a "loja" do kit:
   ```
   /plugin marketplace add dannowk/creative-kit-generator
   ```
3. Cole o próximo e dê Enter — ele instala o plugin:
   ```
   /plugin install campaign-kit@creative-kit-generator
   ```
4. Para começar uma campanha, digite:
   ```
   /campaign-kit:start
   ```
   A partir daí o agente faz tudo: instala o Python sozinho (sem admin), pergunta
   qual é a pasta da sua campanha e conduz até a revisão no navegador.

**A2 · Qoder ou Claude (skill — copiar uma pasta):**

1. Baixe o kit para o seu computador (uma vez só):
   ```
   git clone https://github.com/dannowk/creative-kit-generator ~/Documents/creative-kit-generator
   ```
2. Copie a pasta do skill para a pasta de skills do seu agente:
   - **Qoder:**
     ```
     cp -R ~/Documents/creative-kit-generator/skills/campaign-kit ~/.qoder/skills/
     ```
   - **Claude:**
     ```
     cp -R ~/Documents/creative-kit-generator/skills/campaign-kit ~/.claude/skills/
     ```
   - **Windows:** não tem `cp` — copie a pasta `skills\campaign-kit` pelo Explorer para
     `%USERPROFILE%\.qoder\skills\` (Qoder) ou `%USERPROFILE%\.claude\skills\` (Claude).
3. Abra (ou reinicie) o agente e peça para usar o skill **campaign-kit** — no Qoder
   ele aparece na lista de skills. O fluxo é o mesmo do A1: Python gerenciado →
   wizard → campanha → revisão no navegador.

**B. Duplo clique (sem agente ainda):**

1. Baixe a pasta do kit para o seu computador:
   - Abra `https://github.com/dannowk/creative-kit-generator` no navegador, clique no
     botão verde **Code → Download ZIP** e descompacte (ex.: em `~/Documents/`).
   - Ou, se você tem git:
     ```
     git clone https://github.com/dannowk/creative-kit-generator ~/Documents/creative-kit-generator
     ```
2. Entre na pasta e dê duplo clique no instalador do seu sistema:
   - **Mac:** `Instalar.command` — se avisar "desenvolvedor não identificado",
     clique com o botão direito → **Abrir** → **Abrir**.
   - **Windows:** `Instalar.bat`.
   - **Linux:** rode `./install.sh` no terminal, dentro da pasta.
3. Ele pergunta só a pasta da sua campanha (Enter = `~/Desktop/minha-campanha`),
   instala o Python sozinho e abre o wizard no navegador.

**C. Terminal manual:** baixe a pasta (clone, como no passo B1) e siga o
[Início rápido](#início-rápido-manual) — venv + `pip install` + comandos `kit.cli`.

Nas portas A e B o **Python vem junto**: o instalador baixa o `uv` para `.tools/` e o uv
cria um **Python 3.12 gerenciado dentro da pasta do kit** — sem admin, sem instalar nada
no sistema, sem tocar no Python que já existir. Só precisa de internet na primeira vez.

O código fica na pasta onde você clonou (ex.: `~/Documents/creative-kit-generator`) ou
na pasta de plugins do seu agente, no caso da porta A. Essa pasta **é o kit**: motor
(`kit/`), specs (`templates/`), exemplo (`brands/acme` + `campaigns/acme-launch`).
Tudo que ele gerar nasce **dentro dela**: `brands/<marca>/` e `campaigns/<campanha>/`.
O ffmpeg vem embutido (`imageio-ffmpeg`).

### 2. Preencha a SUA pasta (o inbox da campanha)

Sua pasta fica em qualquer lugar **fora do kit** — ex.: `~/Desktop/minha-marca`. Ela é
separada do código de propósito: o kit é a ferramenta; o inbox é o seu material.

**Se você veio pela porta A ou B, use o wizard no navegador** — na porta B ele abre
sozinho; na porta A o agente te passa o link. É nele que você prepara tudo, sem digitar
comando: suba ou arraste os arquivos em cada slot e preencha o briefing na tela.

O wizard cria exatamente esta estrutura dentro da pasta que você escolheu:

```
minha-marca/
  logo/        ← logo png, de preferência fundo transparente (obrigatório)
  photos/      ← fotos que podem virar peça
  videos/      ← clipes fonte
  refs/        ← 2–6 referências do look desejado
  fonts/       ← .ttf / .otf da marca (opcional; há substitutas)
  briefing.md  ← o briefing que você preencheu na tela (ou editado à mão)
```

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

(Quem instalou pela porta C manual usa `python3` com o venv ativado.)

### 3. Entregue ao agente

> **Porta A:** o agente já está conduzindo (você deu `/campaign-kit:start` ou chamou o
> skill) — este passo é só para quem preparou a pasta na mão (portas B/C).

Abra a **pasta do kit** no seu agente — Claude Code (`claude` no terminal dentro dela),
Qoder (abrir a pasta no app), Codex (`codex`) — e diga:

> "leia o AGENTS.md e rode a campanha de `~/Desktop/minha-marca`"

O agente conduz `intake (ou brief --apply) → plan → assets → render → video` e cria:

- `brands/minha-marca/` — `brand.yaml` (paleta, fontes, voz), `assets/logo.png`;
- `campaigns/minha-marca-<slug>/` — `campaign.json`, `templates/` (direção de arte),
  `assets/`, `out/`, `review/`.

Faltou informação? Vira **uma rodada única** de perguntas (no wizard ou no terminal).
Antes de gerar qualquer asset pago, o agente mostra o aviso de ≈ créditos.

### 4. Aprove no navegador

O `review` **abre o navegador sozinho** em `http://127.0.0.1:8765` (ou a próxima porta
livre). Na tela: aprovar / rejeitar por peça; **refazer** enfileira seu motivo em
`requests.json` e o agente executa.

- Perdeu o link? Atalho clicável **`ABRIR-REVISAO.html`** dentro da pasta da campanha;
  o endereço também fica no topo da tela e no fim de `render` / `video` no terminal.
- Peças aprovadas: `campaigns/<campanha>/out/<conceito>/` (png/mp4 por formato) +
  contact sheet `review/sheet_<conceito>.png`.

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
| código do kit | onde você clonou (ex.: `~/Documents/creative-kit-generator`) |
| seus arquivos | inbox que você escolheu (ex.: `~/Desktop/minha-marca`) |
| marca derivada | `<kit>/brands/<id>/` |
| peças finais | `<kit>/campaigns/<id>-<slug>/out/<conceito>/` |
| revisão | navegador `127.0.0.1:8765+` · atalho `ABRIR-REVISAO.html` |
| pedidos de refazer | `<kit>/campaigns/<id>-<slug>/requests.json` |
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
```

## O que vem no repo

- `kit/` — motor de render declarativo + compliance + providers + UI local.
- `templates/` — biblioteca de specs de conceito (sobrescrevível por campanha).
- `brands/acme` + `campaigns/acme-launch` — exemplo genérico para você seguir.

O design **segue o briefing e as referências** — não herda o visual de outro cliente.
Regras completas e contrato de providers em **[AGENTS.md](AGENTS.md)**.