"""
tests/test_public_booking.py — Testes para agendamento público e prevenção de conflitos
"""

from datetime import datetime, date, timedelta, timezone
from flask import Flask
from api.public.public_booking import booking_public_bp
from db import models
from db.database import Base, SessionLocal, engine


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_public_booking_flow(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    app = Flask("public-booking-test")
    app.config.update(TESTING=True, SECRET_KEY="test")
    app.register_blueprint(booking_public_bp)
    client = app.test_client()

    db = SessionLocal()
    tenant_id = "tenant-booking-test"
    try:
        # Limpar registros anteriores do teste
        db.query(models.Appointment).filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        db.query(models.ExpertScheduleSlot).filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        db.query(models.Lead).filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        db.query(models.User).filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        db.commit()

        # Criar usuário/expert ativo
        user = models.User(
            email="expert@test.com",
            password_hash="test-password-hash",
            tenant_id=tenant_id,
            is_active=True,
            name="Terapeuta Teste",
        )
        db.add(user)
        db.commit()

        # 1. Tenant inexistente retorna 404
        resp = client.get("/api/public/booking/invalid-tenant-xyz/slots")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "tenant_not_found"

        # 2. Busca slots para amanhã (fallback slots)
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_str = tomorrow.isoformat()
        resp = client.get(f"/api/public/booking/{tenant_id}/slots?date={tomorrow_str}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["slots"]) > 0
        first_time = data["slots"][0]["time"]

        # 3. Confirmar agendamento com sucesso
        booking_payload = {
            "tenant_id": tenant_id,
            "name": "Cliente Teste",
            "phone": "5511988887777",
            "date": tomorrow_str,
            "time": first_time,
        }
        resp = client.post("/api/public/booking/confirm", json=booking_payload)
        assert resp.status_code == 200
        booking_res = resp.get_json()
        assert booking_res["ok"] is True
        appt_id = booking_res["appointment_id"]
        slot_id = booking_res["slot_id"]

        # Verificar integridade no banco
        slot_db = db.query(models.ExpertScheduleSlot).filter_by(id=slot_id).first()
        assert slot_db is not None
        assert slot_db.is_booked is True
        assert slot_db.appointment_id == appt_id

        # 4. Tentar agendar exatamente o mesmo horário deve retornar 409 Conflict
        resp_conflict = client.post("/api/public/booking/confirm", json=booking_payload)
        assert resp_conflict.status_code == 409
        assert resp_conflict.get_json()["error"] == "slot_already_booked"

        # 5. Tentativa com slot_id explícito já reservado também retorna 409
        resp_conflict_slot = client.post("/api/public/booking/confirm", json={
            "tenant_id": tenant_id,
            "name": "Outro Cliente",
            "phone": "5511999990000",
            "date": tomorrow_str,
            "time": first_time,
            "slot_id": slot_id,
        })
        assert resp_conflict_slot.status_code == 409
        assert resp_conflict_slot.get_json()["error"] == "slot_already_booked"

        # 6. Um slot válido não pode ser reaproveitado com data/hora adulterada.
        second_time = data["slots"][1]["time"]
        explicit_slot = models.ExpertScheduleSlot(
            tenant_id=tenant_id,
            slot_date=tomorrow,
            slot_time=datetime.combine(
                tomorrow,
                datetime.strptime(second_time, "%H:%M").time(),
                tzinfo=timezone.utc,
            ),
        )
        db.add(explicit_slot)
        db.commit()
        resp_mismatch = client.post("/api/public/booking/confirm", json={
            **booking_payload,
            "time": "23:59",
            "slot_id": explicit_slot.id,
        })
        assert resp_mismatch.status_code == 409
        assert resp_mismatch.get_json()["error"] == "slot_payload_mismatch"

        # 7. Agendamento com data no passado deve falhar com 400
        past_date = (date.today() - timedelta(days=2)).isoformat()
        resp_past = client.post("/api/public/booking/confirm", json={
            "tenant_id": tenant_id,
            "name": "Cliente Passado",
            "phone": "5511988887777",
            "date": past_date,
            "time": "10:00",
        })
        assert resp_past.status_code == 400
        assert resp_past.get_json()["error"] == "cannot_book_past_time"

    finally:
        db.close()
