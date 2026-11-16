# Copy Kit — skill independente de copy (design)

**Data:** 2026-11-15
**Status:** aprovado em conversa (Dann), aguardando review desta spec
**Repo:** creative-kit-generator · branch `main`

## Problema / contexto

A feature de conteúdo (planilha do time + painel Revisar copy) foi **removida** da main
(commit `3195e3d`) a pedido do Dann: copy/conteúdo deve ser um **sistema independente**,
não um passo dentro do kit visual. Ele quer esse sistema como uma **segunda skill no
mesmo repositório**, com comando de start próprio, pra poupar esforço (instalador e
infra compartilhados). O hub online ficou parked (branch `online-collaboration`); este
design NÃO depende dele.

## O que é

Um fluxo guiado, local, agent-driven — espelho do kit visual, mas **só para copy**:

1. **Onboarding enxuto** no navegador: **briefing** + um **campo de texto** onde o usuário
   cola **textos de exemplo**. **Sem logo, sem brandbook, sem refs de arquivo, sem
   fotos/vídeos.** Mesmo estilo passo a passo do visual, slots diferentes.
2. **Geração (agente):** o agente lê briefing + exemplos e **cria o copy** — tanto para
   **PPC (só texto)** quanto para **overlay** (hook/kicker/program/CTA). Volume alto
   (conceitos × eixos × destinos × versões). O kit **valida a forma**, não inventa copy
   (padrão normalize: agente gera, Python valida).
3. **Revisão em tabela** no navegador: cada linha aprovar / rejeitar / refazer+nota.
   Disciplina mark-then-batch; **nada não-aprovado segue adiante**. Tabela porque o
   volume pode ser grande.
4. **Entrega:** tudo aprovado → o agente gera **arquivo pra download** (planilha) e/ou
   solta na **pasta de entrega no Desktop** (`~/Desktop/Copy Kit/<campanha>/`), mesmo
   padrão do visual (botão Abrir pasta).
5. **Independente:** o kit visual fica intacto. O copy entrega o arquivo dele; não há
   acoplamento nem import automático pelo visual (handoff = passo futuro, se ele quiser).

## Contrato de comando / skill

- Plugin `campaign-kit` ganha um segundo comando: **`/campaign-kit:copy`** (`commands/copy.md`)
  e uma segunda skill **`skills/copy-kit/SKILL.md`**. O `/campaign-kit:start` atual segue
  só para o visual.
- **Um fluxo por vez na UI do navegador:** cada comando sobe seu próprio servidor em
  loopback; rodar um ou outro, nunca os dois na mesma sessão. (Wizard visual 8766 /
  review 8765; copy usa portas próprias a partir de 8767/8768 — sem colidir.)
- CLI: novo subcomando **`copy`** com ações (`python3 -m kit.cli copy <ação> <caminho>`):
  - `copy onboard <inbox>` — scaffold enxuto (briefing.md + examples.txt) + wizard leve.
  - `copy plan <campaign>` — imprime briefing + exemplos + vocabulário de destinos/kinds
    pro agente autorar o copy.
  - `copy validate <campaign>` — valida `copy.json` (forma canônica; gaps/erros).
  - `copy review <campaign>` — servidor da tabela de revisão (abre navegador; atalho
    `ABRIR-COPY.html`).
  - `copy deliver <campaign>` — exporta aprovadas → planilha(s) + pasta Desktop.

## Modelo de dados (`campaigns/<slug>/copy.json`)

Lista de linhas; cada linha:

```json
{
  "id": "k01",
  "destination": "ppc",            // "ppc" | "overlay"
  "concept": "clean",
  "axis": "default",               // opcional
  "kind": "headline",              // ppc: headline|description|primary_text
                                    // overlay: hook|kicker|program|cta
  "text": "...",
  "lang": "pt",                    // pt|en
  "use": "both",                   // opcional p/ overlay: image|ppc|both (roteamento futuro)
  "status": "pending",             // pending|approved|rejected|redo
  "note": "",
  "origin": "agent",               // sempre agent aqui (gerado); sheet se vier de planilha
  "updated_at": "ISO-UTC",
  "updated_by": "nome"
}
```

- `copy validate`: destinos/kinds/status/lang válidos; `text` não-vazio; ids únicos.
  Erro → nada gravado (atômico). Gaps (ex.: conceito sem hook) viram pergunta.
- `decide(id, status, note)`: marca a linha (intenção). `redo` exige nota. Recarimba
  `updated_at`/`updated_by`. **Agente nunca marca `approved`** — é do usuário.
- Re-ingest/geração nova preserva decisões por id quando o texto não mudou; texto novo
  volta a `pending`.

## Entrega (arquivo)

`copy deliver` exporta **só as aprovadas**:
- **PPC** → planilha(s) no formato de import (Meta primary text/headline; Google RSA
  headlines ≤30 / descriptions ≤90), CSV + XLSX. URL/orçamento/IDs em branco (time PPC).
- **Overlay** → planilha conceito × eixo × kind (hook/kicker/program/CTA), CSV + XLSX.
- Vai pra `~/Desktop/Copy Kit/<campanha>/` + botão **Abrir pasta** e **download** na UI.
- Limites de caractere do RSA validados no export (aviso, não porteiro).

## O que reaproveita do kit (DRY)

- `kit/i18n.py` (PT/EN), padrão de servidor HTTP de `kit/ui.py` (`_serve`,
  `ThreadingHTTPServer`, toggle de idioma, abrir navegador, atalho HTML).
- Padrão de pasta de entrega no Desktop + `_open_folder`.
- `openpyxl`/csv já usados pelo `ppc.py` pro XLSX.
- Instalador (`install.sh`/`Instalar.bat`) e venv gerenciado — iguais.

## O que é NEW (independente do visual)

- `kit/copy.py` — modelo + validate + decide + export (sem tocar campaign/render/ppc visual).
- `kit/copy_ui.py` — wizard leve (briefing + exemplos) + página de tabela + rotas
  (`/state`, `/decide`, `/deliver`, `/download`, `/open-folder`). Servidor próprio.
- `commands/copy.md`, `skills/copy-kit/SKILL.md`.
- Subcomando `copy` no `kit/cli.py` (só adiciona; não muda os existentes).
- README.md (English-only): "Copy Kit" section + `/campaign-kit:copy` command.
- Testes do módulo copy (TDD).

## Regras invioláveis (herdadas)

- **Nunca invente copy** — agente gera do briefing + exemplos; kit valida a forma.
- **Nada não-aprovado sai** — deliver/export só com `approved`.
- **Agente nunca marca approved** — decisão é do usuário na tabela.
- **Arquivos e controle locais** — sem URL pública/deploy sem pedir.
- **Um fluxo por vez na UI.**

## Limites honestos

- A criatividade (escrever o copy) é do agente; o Python valida forma e exporta.
- Sem logo/brandbook: a voz vem do briefing + exemplos colados.
- Independente do visual: não renderiza imagem, não fala com provider, não toca PPC visual.