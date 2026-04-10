"""
Coloca um lead no funil estático Meu Mistério (node `static_meumisterio_b1`).

Evita mexer no SQL à mão. Usa a mesma base que o motor (`cigana.db` por defeito).

Uso (na pasta do projeto):
  python scripts/colocar_lead_no_funil_estatico.py 5511999998888
  python scripts/colocar_lead_no_funil_estatico.py 5511999998888 --reset-meta-estatico

Recomendado — mesmo número WABA, estático + IA do motor off (reiniciar o servidor após mudar):
  no .env: FUNIL_ESTATICO_ATIVO=1

Para voltar ao funil com IA (Cigana nos nodes):
  FUNIL_ESTATICO_ATIVO=0
  (Leads que já estavam no estático continuam no nó atual até mudares na base ou script.)
"""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.chdir(_ROOT)

from sqlalchemy.orm import Session  # noqa: E402

from db.database import SessionLocal  # noqa: E402
from db.models import Lead  # noqa: E402
from tenant_context import get_engine_tenant_id, normalize_tenant_id  # noqa: E402

NODE_ESTATICO = "static_meumisterio_b1"

_PREFIXOS_META = ("static_mm_", "static_meumisterio_")


def _so_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _candidatos_telefone(arg: str) -> list[str]:
    a = (arg or "").strip()
    out = [a]
    d = _so_digitos(a)
    if d:
        out.append(d)
    if a.startswith("+"):
        out.append(a[1:])
    # dedup preserve order
    seen = set()
    uniq = []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _encontrar_lead(db: Session, tenant_id: str, telefone_arg: str) -> Lead | None:
    cands = _candidatos_telefone(telefone_arg)
    q = db.query(Lead).filter(Lead.tenant_id == tenant_id)
    for c in cands:
        lead = q.filter(Lead.telefone == c).first()
        if lead:
            return lead
    # último recurso: sufixo (9 dígitos locais BR)
    dig = _so_digitos(telefone_arg)
    if len(dig) >= 9:
        suf = dig[-9:]
        for row in db.query(Lead).filter(Lead.tenant_id == tenant_id).all():
            if _so_digitos(row.telefone or "").endswith(suf):
                return row
    return None


def _limpar_meta_estatico(meta: dict) -> dict:
    if not isinstance(meta, dict):
        return {}
    out = dict(meta)
    for k in list(out.keys()):
        ks = str(k)
        if ks.startswith(_PREFIXOS_META) or ks in (
            "nome_pessoa_amada_b2",
            "static_mm_b1_concluido_em",
            "static_mm_b3_placeholder_enviado",
        ):
            out.pop(k, None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Define node_atual do lead para o funil estático Meu Mistério.")
    ap.add_argument(
        "telefone",
        help="Telefone como na base (ex.: 5511999998888) ou com +55",
    )
    ap.add_argument(
        "--tenant",
        default=get_engine_tenant_id(),
        help="tenant_id (default: ACASSIA_TENANT_ID ou 'default')",
    )
    ap.add_argument(
        "--node",
        default=NODE_ESTATICO,
        help=f"nó destino (default: {NODE_ESTATICO})",
    )
    ap.add_argument(
        "--reset-meta-estatico",
        action="store_true",
        help="remove chaves static_mm_* / nome amado do metadata_json para teste limpo",
    )
    ap.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="não pede confirmação",
    )
    args = ap.parse_args()

    tid = normalize_tenant_id(args.tenant)
    db = SessionLocal()
    try:
        lead = _encontrar_lead(db, tid, args.telefone)
        if not lead:
            print(f"Nenhum lead encontrado para tenant={tid!r} e telefone parecido com {args.telefone!r}.")
            print("Dica: confere o número em `leads.telefone` (SQLite: cigana.db).")
            return 1

        antes_node = lead.node_atual
        antes_meta_keys = list((lead.metadata_json or {}).keys()) if isinstance(lead.metadata_json, dict) else []

        print("Lead encontrado:")
        print(f"  id={lead.id}  telefone={lead.telefone!r}  tenant={lead.tenant_id!r}")
        print(f"  node_atual (antes) = {antes_node!r}")

        if not args.yes:
            s = input(f"Alterar para node_atual={args.node!r}? [s/N] ").strip().lower()
            if s not in ("s", "sim", "y", "yes"):
                print("Cancelado.")
                return 0

        lead.node_atual = (args.node or NODE_ESTATICO).strip()
        if args.reset_meta_estatico:
            m = lead.metadata_json if isinstance(lead.metadata_json, dict) else {}
            lead.metadata_json = _limpar_meta_estatico(m)
            print("metadata_json: removidas chaves do funil estático (teste limpo).")

        db.commit()
        db.refresh(lead)

        print()
        print("OK — atualizado:")
        print(f"  node_atual (depois) = {lead.node_atual!r}")
        if args.reset_meta_estatico:
            print(f"  metadata (chaves antes): {antes_meta_keys[:12]}{'...' if len(antes_meta_keys) > 12 else ''}")
        print()
        print("Próximo passo: manda mensagem no WhatsApp (ex.: «quero minha consulta»).")
        print("Se o servidor já estava a correr, não precisa reiniciar só por esta alteração.")
        return 0
    except Exception as e:
        db.rollback()
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
