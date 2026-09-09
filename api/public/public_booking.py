"""
api/public/public_booking.py — Webview Pública de Agendamento de Consultas
Permite que o cliente abra um link direto do WhatsApp (Webview tipo Calendly/Cal.com)
e selecione data e horário disponíveis com confirmação automática instantânea.
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, jsonify, request, render_template_string

from db.database import SessionLocal
from db import models
from extensions import limiter

logger = logging.getLogger(__name__)

booking_public_bp = Blueprint("booking_public", __name__)

BOOKING_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agendamento Online | Acássia</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; }
  </style>
</head>
<body class="bg-[#0b0c10] text-gray-100 min-h-screen flex items-center justify-center p-4">
  <div class="max-w-md w-full bg-[#161822] border border-gray-800 rounded-3xl p-6 shadow-2xl">
    <div class="text-center mb-6">
      <div class="w-12 h-12 rounded-2xl bg-purple-600/20 text-purple-400 flex items-center justify-center mx-auto mb-3 font-black text-xl">
        📅
      </div>
      <h1 class="text-2xl font-extrabold text-white">Agendar Horário</h1>
      <p class="text-xs text-gray-400 mt-1">Escolha a data e o horário ideal para sua sessão.</p>
    </div>

    <div id="booking-app">
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1.5">Seu Nome</label>
          <input id="name" type="text" placeholder="Ex: Maria Silva" class="w-full bg-[#0b0c10] border border-gray-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500" value="{{ client_name }}">
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1.5">WhatsApp / Telefone</label>
          <input id="phone" type="text" placeholder="Ex: 5511999999999" class="w-full bg-[#0b0c10] border border-gray-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500" value="{{ client_phone }}">
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1.5">Data Desejada</label>
          <input id="date-picker" type="date" class="w-full bg-[#0b0c10] border border-gray-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500">
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-1.5">Horários Disponíveis</label>
          <div id="slots-loading" class="text-center py-4 text-xs text-gray-400">Carregando horários...</div>
          <div id="slots-empty" class="hidden text-center py-4 text-xs text-amber-400/80 bg-amber-950/20 border border-amber-800/30 rounded-xl">
            Nenhum horário disponível para esta data.
          </div>
          <div id="slots-container" class="grid grid-cols-3 gap-2"></div>
        </div>

        <button id="confirm-btn" onclick="confirmBooking()" class="w-full mt-6 py-3 px-4 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm tracking-wide transition-all shadow-lg shadow-purple-600/20 disabled:opacity-50">
          Confirmar Agendamento
        </button>
      </div>

      <div id="success-box" class="hidden text-center py-6">
        <div class="text-4xl mb-3">🎉</div>
        <h2 class="text-xl font-bold text-white mb-1">Agendamento Confirmado!</h2>
        <p class="text-xs text-gray-400 mb-4">Você receberá os detalhes e confirmação no seu WhatsApp.</p>
        <button onclick="window.close()" class="px-5 py-2 bg-gray-800 rounded-xl text-xs font-bold text-gray-300">Fechar Janela</button>
      </div>
    </div>
  </div>

  <script>
    let selectedTime = null;
    let selectedSlotId = null;
    const datePicker = document.getElementById('date-picker');
    const today = new Date().toISOString().split('T')[0];
    datePicker.min = today;
    datePicker.value = today;

    datePicker.addEventListener('change', () => {
      loadSlots(datePicker.value);
    });

    async function loadSlots(dateVal) {
      const container = document.getElementById('slots-container');
      const loading = document.getElementById('slots-loading');
      const empty = document.getElementById('slots-empty');
      const confirmBtn = document.getElementById('confirm-btn');

      container.innerHTML = '';
      loading.classList.remove('hidden');
      empty.classList.add('hidden');
      selectedTime = null;
      selectedSlotId = null;

      try {
        const res = await fetch(`/api/public/booking/{{ tenant_id }}/slots?date=${dateVal}`);
        const data = await res.json();
        loading.classList.add('hidden');

        if (data.ok && data.slots && data.slots.length > 0) {
          data.slots.forEach((s, idx) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all';
            btn.innerText = s.time;
            btn.onclick = () => selectSlot(s.time, s.id, btn);
            container.appendChild(btn);

            if (idx === 0) {
              selectSlot(s.time, s.id, btn);
            }
          });
        } else {
          empty.classList.remove('hidden');
        }
      } catch (err) {
        loading.classList.add('hidden');
        empty.innerText = 'Erro ao buscar horários. Tente novamente.';
        empty.classList.remove('hidden');
      }
    }

    function selectSlot(time, slotId, buttonEl) {
      selectedTime = time;
      selectedSlotId = slotId;
      document.querySelectorAll('.slot-btn').forEach(btn => {
        btn.classList.remove('border-purple-500', 'bg-purple-600/20', 'text-purple-300');
      });
      if (buttonEl) {
        buttonEl.classList.add('border-purple-500', 'bg-purple-600/20', 'text-purple-300');
      }
    }

    async function confirmBooking() {
      const name = document.getElementById('name').value.trim();
      const phone = document.getElementById('phone').value.trim();
      const dateVal = datePicker.value;
      const btn = document.getElementById('confirm-btn');

      if (!name || !phone || !dateVal) {
        alert('Por favor, preencha todos os campos.');
        return;
      }
      if (!selectedTime) {
        alert('Por favor, selecione um horário disponível.');
        return;
      }

      btn.disabled = true;
      btn.innerText = 'Processando...';

      try {
        const res = await fetch('/api/public/booking/confirm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tenant_id: '{{ tenant_id }}',
            name: name,
            phone: phone,
            date: dateVal,
            time: selectedTime,
            slot_id: selectedSlotId
          })
        });
        const data = await res.json();
        if (data.ok) {
          document.querySelector('.space-y-4').classList.add('hidden');
          document.getElementById('success-box').classList.remove('hidden');
        } else {
          alert(data.message || data.error || 'Erro ao realizar agendamento.');
          btn.disabled = false;
          btn.innerText = 'Confirmar Agendamento';
          loadSlots(dateVal);
        }
      } catch (err) {
        alert('Falha na comunicação com o servidor.');
        btn.disabled = false;
        btn.innerText = 'Confirmar Agendamento';
      }
    }

    // Inicializa carregando os slots da data selecionada
    loadSlots(today);
  </script>
</body>
</html>
"""

@booking_public_bp.route("/book/<string:tenant_id>", methods=["GET"])
def render_booking_page(tenant_id: str):
    """Renderiza a página de agendamento online (webview móvel)."""
    name = request.args.get("name", "")
    phone = request.args.get("phone", "")
    return render_template_string(
        BOOKING_HTML_TEMPLATE,
        tenant_id=tenant_id,
        client_name=name,
        client_phone=phone,
    )


@booking_public_bp.route("/api/public/booking/<string:tenant_id>/slots", methods=["GET"])
@limiter.limit("60/minute")
def get_public_slots(tenant_id: str):
    """Retorna os horários disponíveis para agendamento em uma data específica."""
    date_str = request.args.get("date")
    if not date_str:
        target_date = date.today()
    else:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({
                "ok": False,
                "error": "invalid_date_format",
                "message": "Formato de data inválido. Use YYYY-MM-DD.",
            }), 400

    db = SessionLocal()
    try:
        if not db.query(models.User.id).filter_by(tenant_id=tenant_id, is_active=True).first():
            return jsonify({"ok": False, "error": "tenant_not_found"}), 404

        now_utc = datetime.now(timezone.utc)

        # 1. Busca slots explicitamente configurados pelo terapeuta
        db_slots = (
            db.query(models.ExpertScheduleSlot)
            .filter_by(tenant_id=tenant_id, slot_date=target_date, is_booked=False, is_blocked=False)
            .filter(models.ExpertScheduleSlot.slot_time > now_utc)
            .order_by(models.ExpertScheduleSlot.slot_time.asc())
            .all()
        )

        if db_slots:
            return jsonify({
                "ok": True,
                "date": target_date.isoformat(),
                "slots": [
                    {
                        "id": s.id,
                        "time": s.slot_time.strftime("%H:%M"),
                        "duration_minutes": s.duration_minutes,
                    }
                    for s in db_slots
                ]
            })

        # 2. Se o terapeuta não tem slots nesta data mas tem slots em outros dias, não cria horários livres
        has_any_slots = db.query(models.ExpertScheduleSlot.id).filter_by(tenant_id=tenant_id).first() is not None
        if has_any_slots:
            return jsonify({
                "ok": True,
                "date": target_date.isoformat(),
                "slots": []
            })

        # 3. Fallback inteligente com horários de atendimento padrão se o tenant ainda não configurou slots manuais
        default_hours = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        available = []
        for h_str in default_hours:
            try:
                hour, minute = map(int, h_str.split(":"))
                slot_dt = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=timezone.utc)
            except Exception:
                continue

            if slot_dt <= now_utc:
                continue

            existing = (
                db.query(models.Appointment.id)
                .filter_by(tenant_id=tenant_id, scheduled_at=slot_dt)
                .filter(models.Appointment.status.notin_(["cancelled"]))
                .first()
            )
            if not existing:
                available.append({
                    "id": None,
                    "time": h_str,
                    "duration_minutes": 60,
                })

        return jsonify({
            "ok": True,
            "date": target_date.isoformat(),
            "slots": available
        })
    finally:
        db.close()


@booking_public_bp.route("/api/public/booking/confirm", methods=["POST"])
@limiter.limit("30/minute")
def confirm_public_booking():
    """Recebe e confirma o agendamento de forma atômica contra conflitos e reservas simultâneas."""
    data = request.get_json(silent=True) or {}
    tenant_id = (data.get("tenant_id") or "").strip()
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    slot_date_str = (data.get("date") or "").strip()
    slot_time_str = (data.get("time") or "").strip()
    slot_id = data.get("slot_id")

    if not tenant_id or not name or not phone or not slot_date_str or not slot_time_str:
        return jsonify({"ok": False, "error": "Campos obrigatorios faltando"}), 400

    try:
        target_date = date.fromisoformat(slot_date_str)
        hour, minute = map(int, slot_time_str.split(":"))
        scheduled_dt = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=timezone.utc)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_date_or_time_format"}), 400

    now_utc = datetime.now(timezone.utc)
    if scheduled_dt <= now_utc:
        return jsonify({
            "ok": False,
            "error": "cannot_book_past_time",
            "message": "Não é possível agendar um horário no passado.",
        }), 400

    db = SessionLocal()
    try:
        if not db.query(models.User.id).filter_by(tenant_id=tenant_id, is_active=True).first():
            return jsonify({"ok": False, "error": "tenant_not_found"}), 404

        slot = None
        # 1. Se slot_id foi fornecido, consulta com bloqueio
        if slot_id:
            slot_q = db.query(models.ExpertScheduleSlot).filter_by(id=slot_id, tenant_id=tenant_id)
            if db.bind and db.bind.dialect.name != "sqlite":
                slot_q = slot_q.with_for_update()
            slot = slot_q.first()

            if not slot:
                return jsonify({"ok": False, "error": "slot_not_found"}), 404
            if slot.is_booked or slot.is_blocked:
                return jsonify({
                    "ok": False,
                    "error": "slot_already_booked",
                    "message": "Este horário já foi reservado por outro cliente.",
                }), 409
        else:
            # Verifica se já existe slot criado para este dia/horário
            slot_q = db.query(models.ExpertScheduleSlot).filter_by(
                tenant_id=tenant_id,
                slot_date=target_date,
                slot_time=scheduled_dt,
            )
            if db.bind and db.bind.dialect.name != "sqlite":
                slot_q = slot_q.with_for_update()
            slot = slot_q.first()

            if slot and (slot.is_booked or slot.is_blocked):
                return jsonify({
                    "ok": False,
                    "error": "slot_already_booked",
                    "message": "Este horário já foi reservado por outro cliente.",
                }), 409

        # 2. Previne conflito na tabela de agendamentos
        conflict_appt = (
            db.query(models.Appointment.id)
            .filter_by(tenant_id=tenant_id, scheduled_at=scheduled_dt)
            .filter(models.Appointment.status.notin_(["cancelled"]))
            .first()
        )
        if conflict_appt:
            return jsonify({
                "ok": False,
                "error": "slot_already_booked",
                "message": "Este horário já foi reservado por outro cliente.",
            }), 409

        # 3. Encontra ou cria o lead
        lead = db.query(models.Lead).filter_by(tenant_id=tenant_id, telefone=phone).first()
        if not lead:
            lead = models.Lead(
                tenant_id=tenant_id,
                telefone=phone,
                nome=name,
                node_atual="agendado",
            )
            db.add(lead)
            db.flush()
        else:
            if name and lead.nome in ("Novo Contato", "Lead Sem Nome", "", None):
                lead.nome = name
            lead.node_atual = "agendado"

        # 4. Cria Appointment
        appt = models.Appointment(
            tenant_id=tenant_id,
            slot_id=slot.id if slot else None,
            lead_id=lead.id,
            client_name=name,
            client_phone=phone,
            scheduled_at=scheduled_dt,
            status="confirmed",
            appointment_type="consultation",
            modality="online",
            duration_minutes=slot.duration_minutes if slot else 60,
        )
        db.add(appt)
        db.flush()

        # 5. Vincula o slot e marca como reservado
        if slot:
            slot.is_booked = True
            slot.lead_id = lead.id
            slot.appointment_id = appt.id
        else:
            new_slot = models.ExpertScheduleSlot(
                tenant_id=tenant_id,
                slot_date=target_date,
                slot_time=scheduled_dt,
                duration_minutes=60,
                is_booked=True,
                lead_id=lead.id,
                appointment_id=appt.id,
            )
            db.add(new_slot)
            db.flush()
            appt.slot_id = new_slot.id

        db.commit()

        return jsonify({
            "ok": True,
            "appointment_id": appt.id,
            "slot_id": appt.slot_id,
            "scheduled_at": scheduled_dt.isoformat(),
        })
    except Exception as exc:
        db.rollback()
        logger.exception("[PUBLIC_BOOKING] Erro ao confirmar agendamento: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        db.close()
