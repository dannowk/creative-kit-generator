# campaign-kit

Gere uma campanha completa a partir de uma pasta com **logo + referências + briefing**.
Roda na **sua máquina**, com o **seu agente de IA** (Claude, Codex, Qoder…). Não é um
serviço hospedado: nada de nuvem, login ou URL pública — os arquivos e o controle são
seus.

## Comece aqui

**1. Instale** (uma vez por máquina):

```bash
git clone https://github.com/dannowk/creative-kit-generator.git
cd creative-kit-generator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

O vídeo usa ffmpeg embutido (`imageio-ffmpeg`) — não precisa instalar nada no sistema.

**2. Abra esta pasta no seu agente** (Claude, Codex, Qoder…) e diga:

> "leia o AGENTS.md e rode a campanha da minha pasta `~/inbox/minha-marca`"

Ainda não tem pasta? Diga **"começar onboarding"**: o wizard **abre no navegador** e
mostra o checklist do que falta. O que entrar na pasta:

| Item | Obrigatório? |
| --- | --- |
| logo (png/svg) | sim |
| fotos e/ou vídeos do assunto | sim, em campanha com foto |
| referências visuais | recomendado |
| fontes (.ttf/.otf) | opcional (há substitutas) |
| briefing (wizard ou `brief --template`) | sim |

**3. O agente conduz o pipeline**
`intake (ou brief --apply) → plan → assets → render → video`, avisa o custo aproximado
antes de gerar e abre a **revisão no navegador**.

**4. Você aprova**: aprovar / rejeitar / refazer por peça. "Refazer" volta ao agente com o
motivo. Aprovadas saem em `campaigns/<id>/out/<conceito>/` + contact sheet por conceito.

### Nunca perca o link da revisão

- O navegador **abre sozinho** no `review` e no `onboard` (`--no-open` para headless).
- Atalho clicável **`ABRIR-REVISAO.html`** dentro da pasta da campanha.
- O endereço fica **no topo da tela** e é impresso no fim de `render` / `video`.
- Porta ocupada → próxima livre: cada campanha tem o seu endereço, sem conflito.

### Campanha nova

- **Marca nova:** repita do passo 2 com outra pasta.
- **Mesma marca:** só um briefing novo (objetivo, oferta, CTA, canais, conceitos, copy);
  o agente reusa `brands/<id>` e cria `campaigns/<id>-<slug>`.

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