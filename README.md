# campaign-kit

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
2. Cole no chat e Enter — registra a "loja" do kit:
   ```
   /plugin marketplace add dannowk/creative-kit-generator
   ```
3. Cole e Enter — instala o plugin:
   ```
   /plugin install campaign-kit@creative-kit-generator
   ```
4. Para começar, digite:
   ```
   /campaign-kit:start
   ```

**Porta 2 · Qoder ou Claude Code (pela pasta):**

1. Baixe o kit **pelo navegador**: abra
   `https://github.com/dannowk/creative-kit-generator`, clique no botão verde
   **Code → Download ZIP** e descompacte (ex.: em `~/Documents/`).
2. Abra a pasta descompactada no **Qoder** (ou no Claude Code).
3. Diga no chat: **"leia o AGENTS.md e execute"** (ou peça o skill `campaign-kit`).

> Preciso baixar antes? **Porta 1 não** (o agente busca do GitHub). **Porta 2 sim**
> (o ZIP pelo navegador — sem terminal).

**Em qualquer porta, o agente então:**

- **cria a pasta da campanha automaticamente** (ex.: `~/Desktop/minha-campanha`) —
  você não cria pasta nem digita caminho;
- instala o **Python 3.12 gerenciado dentro do kit** (via `uv`, sem admin, sem tocar
  no Python do sistema; só precisa de internet na primeira vez);
- **abre o onboarding no navegador** com a estrutura `logo/ photos/ videos/ refs/
  fonts/ briefing.md` — você sobe os arquivos e preenche o briefing na tela;
- segue o pipeline e **abre a revisão no navegador** para aprovar / rejeitar / refazer.

O ffmpeg vem embutido (`imageio-ffmpeg`). O código do kit fica na pasta que você
baixou/abriu (ou na pasta de plugins, na Porta 1); tudo que ele gerar nasce dentro
dela: `brands/<marca>/` e `campaigns/<campanha>/`.

<details>
<summary>Alternativas com terminal (opcional)</summary>

- **Duplo clique:** `Instalar.command` (Mac) / `Instalar.bat` (Windows) / `./install.sh`
  (Linux) — instala o Python e abre o wizard. No Mac, se avisar "desenvolvedor não
  identificado": botão direito → **Abrir** → **Abrir**.
- **Manual:** clone + venv + `pip install`, como no [Início rápido](#início-rápido-manual).
- **Skill copiável:** a pasta `skills/campaign-kit/` pode ir para `~/.qoder/skills/`
  ou `~/.claude/skills/` — mas o próprio agente faz essa cópia se você pedir; não
  precisa fazer na mão.

</details>

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
| código do kit | onde você baixou/abriu (ex.: `~/Documents/creative-kit-generator`) |
| seus arquivos | inbox que o agente criou (ex.: `~/Desktop/minha-campanha`) |
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