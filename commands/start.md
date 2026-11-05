---
description: Instala o campaign-kit (Python gerenciado, sem admin) e conduz a campanha da pasta do usuário até a revisão no navegador.
---

Conduza o processo completo do campaign-kit nesta ordem:

1. Localize a raiz do kit (a pasta deste plugin/repo, com `AGENTS.md` e `install.sh`).
2. Se `.venv/` não existir, rode `./install.sh <inbox> --no-open` em background
   (baixa uv + Python 3.12 gerenciado + dependências; sem admin).
   `<inbox>` = pasta da campanha do usuário; se não souber, pergunte uma vez
   (default `~/Desktop/minha-campanha`).
3. Leia `AGENTS.md` na raiz do kit e siga o pipeline:
   `intake (ou brief --apply) → plan → assets → render → video`.
4. Avise o custo aproximado antes de jobs de provider (é aviso, não porteiro).
5. Suba `review` para o usuário (abre o navegador sozinho) e conduza
   aprovar / rejeitar / refazer; pedidos de refazer chegam em `requests.json`.

Não pule o compliance (nunca cobrir rostos) e não hardcode visual de marca.