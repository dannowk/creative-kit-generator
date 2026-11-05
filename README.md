# campaign-kit

Gere uma campanha completa a partir de uma pasta com **logo + referências + briefing**.
Roda na **sua máquina**, com o **seu agente de IA** (Claude, Codex, Qoder…). Não é um
serviço hospedado: nada de nuvem, login ou URL pública — os arquivos e o controle são
seus.

## Como usar

1. Clone o repositório.
2. Abra a pasta no seu agente e diga: **"leia o AGENTS.md e execute"**.
3. O agente instala as dependências e conduz o pipeline:

   `onboard → intake (ou brief --apply) → plan → assets → render → video → review`

Você prepara a pasta numa UI guiada, o agente faz a direção de arte a partir do briefing
e das referências, gera os assets de IA (imagem e vídeo, via seu MCP — ex.: Magnific),
renderiza a matriz de peças em vários formatos e abre a revisão local para
**aprovar / rejeitar / refazer** cada peça.

## Início rápido (manual)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 -m kit.cli onboard ~/inbox/acme        # prepara a pasta (UI em :8766)
python3 -m kit.cli intake  ~/inbox/acme acme   # deriva a marca
#  ou, pelo modelo canônico de briefing:
python3 -m kit.cli brief --template           # modelo markdown gerado do schema
python3 -m kit.cli brief ~/inbox/briefing.yaml --apply   # valida e escreve marca + campanha
python3 -m kit.cli plan    campaigns/acme-launch
python3 -m kit.cli assets  campaigns/acme-launch
python3 -m kit.cli render  campaigns/acme-launch
python3 -m kit.cli video   campaigns/acme-launch   # trim/reframe/overlay/concat/legenda
python3 -m kit.cli review  campaigns/acme-launch   # UI em :8765
```

## O que vem no repo

- `kit/` — motor de render declarativo + compliance + providers + UI local.
- `templates/` — biblioteca de specs de conceito (sobrescrevível por campanha).
- `brands/acme` + `campaigns/acme-launch` — exemplo genérico para você seguir.

O design **segue o briefing e as referências** — não herda o visual de outro cliente.
Regras completas e contrato de providers em **[AGENTS.md](AGENTS.md)**.