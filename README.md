# campaign-kit

Gere uma campanha completa a partir de uma pasta com **logo + referências + briefing**.
Roda na **sua máquina**, com o **seu agente de IA** (Claude, Codex, Qoder…). Não é um
serviço hospedado: nada de nuvem, login ou URL pública — os arquivos e o controle são
seus.

## Comece aqui (passo a passo)

### 1. Instale — escolha uma porta

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
3. Abra (ou reinicie) o agente e peça para usar o skill **campaign-kit** — no Qoder
   ele aparece na lista de skills. O fluxo é o mesmo do A1: Python gerenciado →
   wizard → campanha → revisão no navegador.

**B. Duplo clique (sem agente ainda):** `Instalar.command` no Mac, `Instalar.bat` no
Windows, `./install.sh` no Linux. Ele pergunta só a pasta da campanha e abre o wizard.

**C. Terminal manual:** clone + venv, como no [Início rápido](#início-rápido-manual).

Nas portas A e B o **Python vem junto**: o instalador baixa o `uv` para `.tools/` e o uv
cria um **Python 3.12 gerenciado dentro da pasta do kit** — sem admin, sem instalar nada
no sistema, sem tocar no Python que já existir. Só precisa de internet na primeira vez.

O código fica na pasta onde você clonou (ex.: `~/Documents/creative-kit-generator`) ou
na pasta de plugins do seu agente, no caso da porta A. Essa pasta **é o kit**: motor
(`kit/`), specs (`templates/`), exemplo (`brands/acme` + `campaigns/acme-launch`).
Tudo que ele gerar nasce **dentro dela**: `brands/<marca>/` e `campaigns/<campanha>/`.
O ffmpeg vem embutido (`imageio-ffmpeg`).

### 2. Onde fica a SUA pasta (o inbox da campanha)

Em qualquer lugar **fora do kit** — ex.: `~/Desktop/minha-marca`. Dois caminhos:

- **Wizard:** dentro da pasta do kit, rode
  `python3 -m kit.cli onboard ~/Desktop/minha-marca` — o navegador abre com o checklist;
  você sobe ou arrasta os arquivos em cada slot e preenche o briefing na tela.
- **Na mão:** crie a pasta com esta estrutura (o wizard cria exatamente ela):

```
minha-marca/
  logo/        ← logo png, de preferência fundo transparente (obrigatório)
  photos/      ← fotos que podem virar peça
  videos/      ← clipes fonte
  refs/        ← 2–6 referências do look desejado
  fonts/       ← .ttf / .otf da marca (opcional; há substitutas)
  briefing.md  ← modelo preenchido (python3 -m kit.cli brief --template)
```

### 3. Entregue ao agente

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

### 5. Conecte o seu MCP de assets (só p/ o que faltar)

O kit **não guarda conexão MCP**: quem tem o MCP instalado é o **seu agente**.

1. **No agente**, instale o MCP do provider como qualquer outro: Claude Code
   (`claude mcp add …` conforme a doc do provider), Qoder (Settings → MCP),
   Codex (`~/.codex/config.toml`). Ex.: Magnific MCP. O kit nunca vê suas credenciais.
2. **No briefing**, declare o contrato e o custo do aviso:

   ```yaml
   provider:
     nome: magnific-mcp        # manual | magnific-mcp | http
     creditos_imagem: 4        # alimenta o aviso "≈ X créditos"
     creditos_video: 20
     drop_dir: ~/Downloads     # onde o agente solta os arquivos gerados
   ```

3. `assets` prepara `campaigns/<campanha>/assets/jobs.json` e para (`NeedsAgent`).
4. O agente cumpre cada job pelo **MCP dele** (imagem ou vídeo) e salva no `drop_dir`
   com o **prefixo do id do job** (ex.: `acme-hero_….png`).
5. Rode `assets` de novo: o kit coleta do `drop_dir`, copia para `assets/` da campanha
   e grava `manifest.json` (tipo + créditos).

Alternativas: `manual` (sem MCP — você mesmo dropa os arquivos no `drop_dir`) e
`http` (API genérica: `api_url` + `api_key_env`, ex. `MAGNIFIC_API_KEY`; **a chave fica
em variável de ambiente, nunca no briefing**). Custo é aviso, não porteiro.

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
#  ou, pelo modelo canônico de briefing:
python3 -m kit.cli brief --template           # modelo markdown gerado do schema
python3 -m kit.cli brief ~/inbox/briefing.yaml --apply   # valida e escreve marca + campanha
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