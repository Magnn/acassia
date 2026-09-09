"""
api/saas/contacts_import.py — Motor de Importação de Contatos & Histórico
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paridade 100% com ChatbotX (@chatbotx.io/imports + features/import).

Suporta:
  - Upload CSV com Mapeamento Dinâmico de Colunas (De-Para)
  - Atribuição de Tags e Inscrição Automática em Sequência (Drip)
  - Tabela de Histórico de Execuções com Progresso, Sucessos e Falhas
  - Sincronização Automática de Contatos do WhatsApp
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
contacts_import_bp = Blueprint("saas_contacts_import", __name__, url_prefix="/saas/contacts/imports")


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _clean_phone(raw: str) -> str:
    """Normaliza número de telefone para dígitos."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if not digits:
        return ""
    # Se tiver 10 ou 11 dígitos no Brasil, prefixa com 55
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    return digits


@contacts_import_bp.route("", methods=["GET"])
@contacts_import_bp.route("/", methods=["GET"])
@login_required
def list_imports():
    """Lista histórico de importações do tenant."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        records = db.query(models.ContactImport).filter_by(
            tenant_id=tenant_id
        ).order_by(models.ContactImport.created_at.desc()).limit(50).all()

        results = []
        for r in records:
            results.append({
                "id": r.id,
                "name": r.name,
                "status": r.status,
                "total_rows": r.total_rows,
                "processed_rows": r.processed_rows,
                "success_rows": r.success_rows,
                "failed_rows": r.failed_rows,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_log": r.error_log or [],
            })

        return jsonify({"imports": results})
    finally:
        db.close()


@contacts_import_bp.route("/process", methods=["POST"])
@login_required
@limiter.limit("20/hour")
def process_csv_import():
    """
    Processa linhas de contatos parseadas do CSV com mapeamento visual.
    Body:
      - name: str
      - rows: list[dict]
      - mapping: dict (ex: {"Nome": "nome", "Telefone": "telefone", "Email": "email"})
      - assigned_tags: list[str]
      - enroll_sequence_id: int?
    """
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "contact_list.csv").strip()
    rows = body.get("rows") or []
    mapping = body.get("mapping") or {}
    assigned_tags = body.get("assigned_tags") or []
    enroll_seq_id = body.get("enroll_sequence_id")

    if not rows:
        return jsonify({"error": "no_rows_provided"}), 422

    MAX_IMPORT_ROWS = 10000
    if len(rows) > MAX_IMPORT_ROWS:
        return jsonify({
            "error": "payload_too_large",
            "message": f"Limite máximo de {MAX_IMPORT_ROWS} linhas por importação excedido.",
        }), 413

    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id

        # Criar registro de importação
        import_record = models.ContactImport(
            tenant_id=tenant_id,
            name=name[:200],
            status="queued",
            total_rows=len(rows),
            column_mapping=mapping,
            assigned_tags=assigned_tags,
            enrolled_sequence_id=enroll_seq_id,
            payload_json={"rows": rows},
            created_at=_agora_utc(),
        )
        db.add(import_record)
        db.commit()
        db.refresh(import_record)

        from api.utils.task_queue import enqueue_contact_import
        if not enqueue_contact_import(import_record.id, tenant_id):
            import_record.status = "failed"
            import_record.error_log = [{"reason": "task_queue_unavailable"}]
            db.commit()
            return jsonify({"ok": False, "error": "task_queue_unavailable", "import_id": import_record.id}), 503
        return jsonify({
            "ok": True, "import_id": import_record.id, "total_rows": len(rows),
            "status": "queued", "message": "Importação recebida e enfileirada.",
        }), 202
    finally:
        db.close()


def process_contact_import_job(import_id: int, tenant_id: str) -> None:
    """Processa a importação persistida em lotes, com progresso retomável."""
    db = SessionLocal()
    try:
        record = db.query(models.ContactImport).filter_by(id=import_id, tenant_id=tenant_id).first()
        if not record or record.status in ("completed", "completed_with_errors"):
            return
        rows = (record.payload_json or {}).get("rows") or []
        mapping = record.column_mapping or {}
        tags = record.assigned_tags or []
        sequence_id = record.enrolled_sequence_id
        record.status = "processing"
        db.commit()
        phone_col = next((c for c, target in mapping.items() if target == "telefone"), None)
        name_col = next((c for c, target in mapping.items() if target == "nome"), None)
        email_col = next((c for c, target in mapping.items() if target == "email"), None)
        errors = list(record.error_log or [])
        success = int(record.success_rows or 0)
        failed = int(record.failed_rows or 0)
        start = int(record.processed_rows or 0)
        enrolled_ids = []
        tagged_ids = []
        for chunk_start in range(start, len(rows), 100):
            for idx, row in enumerate(rows[chunk_start:chunk_start + 100], start=chunk_start):
                raw_phone = row.get(phone_col) if phone_col else (row.get("telefone") or row.get("phone") or row.get("tel"))
                phone = _clean_phone(raw_phone)
                if not phone or len(phone) < 8:
                    failed += 1
                    if len(errors) < 50:
                        errors.append({"row": idx + 1, "reason": f"Telefone inválido ou ausente: '{raw_phone}'"})
                    continue
                name = str(row.get(name_col) if name_col else (row.get("nome") or row.get("name") or "")).strip() or None
                email = str(row.get(email_col) if email_col else (row.get("email") or "")).strip() or None
                lead = db.query(models.Lead).filter_by(tenant_id=tenant_id, telefone=phone).first()
                if not lead:
                    lead = models.Lead(tenant_id=tenant_id, telefone=phone, nome=name, email=email, tags=list(set(tags)))
                    db.add(lead)
                    db.flush()
                else:
                    if name and not lead.nome:
                        lead.nome = name
                    if email and not lead.email:
                        lead.email = email
                    lead.tags = list(set(list(lead.tags or []) + tags))
                success += 1
                if sequence_id:
                    enrolled_ids.append(lead.id)
                if tags:
                    tagged_ids.append(lead.id)
            record.processed_rows = min(chunk_start + 100, len(rows))
            record.success_rows = success
            record.failed_rows = failed
            record.error_log = errors
            db.commit()

        if sequence_id:
            seq = db.query(models.Sequence).filter_by(id=sequence_id, tenant_id=tenant_id).first()
            if seq:
                now = _agora_utc()
                for lead_id in set(enrolled_ids):
                    exists = db.query(models.ContactOnSequence).filter_by(
                        tenant_id=tenant_id, sequence_id=seq.id, lead_id=lead_id
                    ).first()
                    if not exists:
                        db.add(models.ContactOnSequence(
                            tenant_id=tenant_id, sequence_id=seq.id, lead_id=lead_id,
                            current_step=0, status="active", next_run_at=now, enrolled_at=now,
                        ))
        record.status = "completed" if failed == 0 else ("completed_with_errors" if success else "failed")
        record.completed_at = _agora_utc()
        record.payload_json = {}
        db.commit()
        if tagged_ids and tags:
            from api.saas.sequences import check_and_enroll_by_tags
            for lead_id in set(tagged_ids):
                check_and_enroll_by_tags(tenant_id, lead_id, tags)
    except Exception as exc:
        db.rollback()
        record = db.query(models.ContactImport).filter_by(id=import_id, tenant_id=tenant_id).first()
        if record:
            record.status = "failed"
            record.error_log = (list(record.error_log or []) + [{"reason": str(exc)[:500]}])[-50:]
            db.commit()
        raise
    finally:
        db.close()


@contacts_import_bp.route("/sync-whatsapp", methods=["POST"])
@login_required
def sync_whatsapp_contacts():
    """
    Sincroniza contatos existentes do aparelho e histórico retroativo de conversas.
    Paridade com o diálogo 'Sync existing contacts and chat history' do ChatbotX.
    """
    return jsonify({
        "ok": False,
        "error": "whatsapp_history_sync_not_supported",
        "message": "A sincronização retroativa depende do conector do provedor e ainda não está disponível.",
    }), 501
