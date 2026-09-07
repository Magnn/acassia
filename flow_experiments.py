"""
A/B testing em nó de fluxo (Frente 3.28-3.29).

Funcoes:
    pick_variant_for_lead(experiment_id, lead_id) -> 'A'|'B'
        Determinístico via hash(experiment_id+lead_id) % 100 < split_pct.
    record_conversion(experiment_id, lead_id, when?)
    pick_winner(experiment) -> dict { winner, p_value, lift_pct, decision }
        Chi-squared test; declara winner se p<0.05 + diff>5% e
        ambas variantes >= min_sample_size.
    hourly_pick_winners() -> int
        Cron: avalia todos status=running e marca winner.
"""

from __future__ import annotations

import hashlib
import logging
import math
from datetime import datetime, timezone

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


def pick_variant_for_lead(experiment_id: int, lead_id: int, split_pct: int = 50) -> str:
    """
    Atribuicao deterministica. Mesmo lead sempre vai pra mesma variante
    (estabilidade das amostras).
    """
    seed = f"{experiment_id}:{lead_id}"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "A" if bucket < split_pct else "B"


def assign_lead_if_needed(
    experiment_id: int,
    lead_id: int,
    *,
    db_session=None,
) -> tuple[str, models.FlowNodeExperimentAssignment]:
    """
    Garante que o lead tem assignment pra esse experimento.
    Retorna (variant, assignment_row).
    Idempotente.
    """
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        existing = db.query(models.FlowNodeExperimentAssignment).filter_by(
            experiment_id=experiment_id, lead_id=lead_id,
        ).first()
        if existing:
            return existing.variant, existing

        exp = db.query(models.FlowNodeExperiment).filter_by(id=experiment_id).first()
        if not exp:
            raise ValueError(f"experiment_not_found: {experiment_id}")
        if exp.status != "running":
            # Promover variante "vencedora" pra todos novos leads
            variant = exp.winner or "A"
        else:
            variant = pick_variant_for_lead(exp.id, lead_id, exp.split_pct)

        assignment = models.FlowNodeExperimentAssignment(
            experiment_id=experiment_id,
            lead_id=lead_id,
            variant=variant,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return variant, assignment
    finally:
        if own:
            db.close()


def record_conversion(
    experiment_id: int,
    lead_id: int,
    *,
    when: datetime | None = None,
    db_session=None,
) -> bool:
    """Marca assignment como convertido (idempotente — primeira conversion ganha)."""
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        a = db.query(models.FlowNodeExperimentAssignment).filter_by(
            experiment_id=experiment_id, lead_id=lead_id,
        ).first()
        if not a:
            return False
        if a.converted:
            return False
        a.converted = True
        a.converted_at = when or datetime.now(timezone.utc)
        db.commit()
        return True
    finally:
        if own:
            db.close()


# ─── Winner picker ────────────────────────────────────────────────────


def _z_two_proportions(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """
    Z-test two-proportion (mais simples que chi-squared, equivalente).
    Retorna (z_score, p_value bilateral aproximado).
    """
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    p1 = x1 / n1
    p2 = x2 / n2
    pp = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    # p-value aproximado bilateral via erfc(|z|/sqrt(2))
    p = math.erfc(abs(z) / math.sqrt(2))
    return z, p


def evaluate_experiment(experiment: models.FlowNodeExperiment, db) -> dict:
    """
    Avalia um experimento. Retorna dict com:
        n_a, conv_a, rate_a, n_b, conv_b, rate_b, p_value, lift_pct, decision

    decision:
        'continue'           — sample size insuficiente
        'winner_a'           — A venceu p<threshold + lift>=5%
        'winner_b'           — B venceu p<threshold + lift>=5%
        'no_significant'    — N>=500 cada lado mas sem diff
    """
    rows = db.query(models.FlowNodeExperimentAssignment).filter_by(
        experiment_id=experiment.id,
    ).all()
    n_a = sum(1 for r in rows if r.variant == "A")
    n_b = sum(1 for r in rows if r.variant == "B")
    conv_a = sum(1 for r in rows if r.variant == "A" and r.converted)
    conv_b = sum(1 for r in rows if r.variant == "B" and r.converted)

    rate_a = conv_a / n_a if n_a else 0
    rate_b = conv_b / n_b if n_b else 0

    decision = "continue"
    p_value = 1.0
    lift_pct = 0.0

    if n_a >= experiment.min_sample_size and n_b >= experiment.min_sample_size:
        _z, p_value = _z_two_proportions(conv_a, n_a, conv_b, n_b)
        if rate_a > 0:
            lift_pct = round((rate_b - rate_a) / rate_a * 100, 2)
        threshold = 1 - experiment.confidence_threshold
        diff_pct = abs(rate_a - rate_b) * 100
        if p_value < threshold and diff_pct >= 5.0:
            decision = "winner_a" if rate_a > rate_b else "winner_b"
        elif n_a >= 500 and n_b >= 500:
            decision = "no_significant"

    return {
        "n_a": n_a, "conv_a": conv_a, "rate_a": round(rate_a, 4),
        "n_b": n_b, "conv_b": conv_b, "rate_b": round(rate_b, 4),
        "p_value": round(p_value, 4),
        "lift_pct": lift_pct,
        "decision": decision,
    }


def pick_winner(experiment_id: int, *, db_session=None) -> dict:
    """Aplica decisao em um experimento."""
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        exp = db.query(models.FlowNodeExperiment).filter_by(id=experiment_id).first()
        if not exp:
            return {"error": "not_found"}
        if exp.status != "running":
            return {"status": exp.status, "noop": True}

        result = evaluate_experiment(exp, db)
        decision = result["decision"]

        if decision in ("winner_a", "winner_b", "no_significant"):
            exp.winner_picked_at = datetime.now(timezone.utc)
            exp.p_value = result["p_value"]
            exp.lift_pct = result["lift_pct"]
            if decision == "winner_a":
                exp.winner = "A"
                exp.status = "completed_winner_a"
            elif decision == "winner_b":
                exp.winner = "B"
                exp.status = "completed_winner_b"
            else:
                exp.status = "completed_no_diff"
            db.commit()
            try:
                db.add(models.AuditEvent(
                    tenant_id=exp.tenant_id,
                    actor_user_id=None,
                    event_type=f"ab_test.{exp.status}",
                    target_type="flow_node_experiment",
                    target_id=str(exp.id),
                    payload=result,
                ))
                db.commit()
            except Exception:
                db.rollback()

        return {"status": exp.status, "winner": exp.winner, **result}
    finally:
        if own:
            db.close()


def hourly_pick_winners() -> int:
    """Cron: avalia todos os experimentos running e potencialmente promove."""
    db = SessionLocal()
    n = 0
    try:
        running = db.query(models.FlowNodeExperiment).filter_by(status="running").all()
        for exp in running:
            try:
                pick_winner(exp.id, db_session=db)
                n += 1
            except Exception as exc:
                logger.warning("[ab_test.pick] exp=%s falha: %s", exp.id, exc)
        return n
    finally:
        db.close()


def get_text_for_lead(experiment_id: int, lead_id: int, *, db_session=None) -> tuple[str, str]:
    """
    Helper pra engine: retorna (variant, text) que esse lead deve receber.
    Idempotente — assigment ja criado e reusado.
    """
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        variant, _ = assign_lead_if_needed(experiment_id, lead_id, db_session=db)
        exp = db.query(models.FlowNodeExperiment).filter_by(id=experiment_id).first()
        if not exp:
            return variant, ""
        text = exp.variant_a_text if variant == "A" else exp.variant_b_text
        return variant, text or ""
    finally:
        if own:
            db.close()
