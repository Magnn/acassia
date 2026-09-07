"""
Upload em batch das 79 imagens do baralho de Marselha pro Supabase Storage.

Sobe 78 cartas + 1 baralho fechado pro bucket `templates-public/marselha/`.
Ver ADR_004 (Supabase Storage) e MARSELHA_ASSETS.md (sourcing das imagens).

Uso:
    SUPABASE_URL=https://abc.supabase.co \\
    SUPABASE_SERVICE_ROLE_KEY=eyJhbG... \\
    python scripts/upload_marselha_storage.py /caminho/para/imagens

Pra apenas validar que todos os 79 arquivos estão na pasta local (sem subir):
    python scripts/upload_marselha_storage.py /caminho/para/imagens --dry-run
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import requests

# Permite rodar o script direto: adiciona raiz do projeto ao sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flows.tarot.cartas import BARALHO_MARSELHA  # noqa: E402

logger = logging.getLogger(__name__)
BUCKET = "templates-public"
PASTA = "marselha"
TIMEOUT = (5, 30)  # connect, read


def slugs_esperados() -> list[str]:
    """Lista de nomes de arquivo esperados na pasta local (79 itens)."""
    return ["baralho_fechado"] + [c.slug for c in BARALHO_MARSELHA]


def validar_pasta_local(pasta: Path) -> tuple[list[str], list[str]]:
    """Retorna (encontrados, ausentes) comparando com slugs esperados."""
    encontrados, ausentes = [], []
    for slug in slugs_esperados():
        if (pasta / f"{slug}.jpg").exists():
            encontrados.append(slug)
        else:
            ausentes.append(slug)
    return encontrados, ausentes


def upload_imagem(
    supabase_url: str, service_key: str, slug: str, arquivo: Path
) -> bool:
    """Sobe uma imagem pro bucket. Usa upsert pra ser idempotente."""
    url = f"{supabase_url}/storage/v1/object/{BUCKET}/{PASTA}/{slug}.jpg"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "image/jpeg",
        "x-upsert": "true",
    }
    with arquivo.open("rb") as f:
        r = requests.post(url, data=f.read(), headers=headers, timeout=TIMEOUT)
    if r.status_code in (200, 201):
        return True
    logger.error("upload %s falhou: HTTP %s — %s", slug, r.status_code, r.text[:200])
    return False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pasta", type=Path, nargs="?", help="pasta local com os 79 .jpg")
    parser.add_argument("--dry-run", action="store_true", help="só valida, não envia")
    parser.add_argument("--list", action="store_true", help="lista os 79 slugs esperados e sai")
    args = parser.parse_args()

    if args.list:
        for slug in slugs_esperados():
            print(f"{slug}.jpg")
        return 0

    if args.pasta is None:
        parser.error("argumento 'pasta' é obrigatório (ou use --list)")
    if not args.pasta.is_dir():
        parser.error(f"pasta não existe: {args.pasta}")

    encontrados, ausentes = validar_pasta_local(args.pasta)
    logger.info("encontrados: %d/79", len(encontrados))
    if ausentes:
        logger.warning("AUSENTES (%d):\n  - %s", len(ausentes), "\n  - ".join(ausentes))

    if args.dry_run:
        logger.info("[dry-run] saindo sem enviar.")
        return 0 if not ausentes else 1

    if ausentes:
        logger.error("complete os arquivos ausentes antes de subir; abortando.")
        return 1

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        parser.error("defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no ambiente")

    sucessos, falhas = 0, 0
    for slug in encontrados:
        if upload_imagem(supabase_url, service_key, slug, args.pasta / f"{slug}.jpg"):
            sucessos += 1
            logger.info("ok %s", slug)
        else:
            falhas += 1

    logger.info("--- RESUMO --- sucessos=%d falhas=%d", sucessos, falhas)
    return 0 if falhas == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
