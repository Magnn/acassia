"""
api/public/public_booking.py — Webview Pública de Agendamento de Consultas
Permite que o cliente abra um link direto do WhatsApp (Webview tipo Calendly/Cal.com)
e selecione data e horário disponíveis com confirmação automática instantânea.
"""

from datetime import datetime, date, timedelta, timezone
from flask import Blueprint, jsonify, request, render_template_string
from db.database import SessionLocal
from db import models

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
          <div id="slots-container" class="grid grid-cols-3 gap-2">
            <button type="button" onclick="selectSlot('09:00')" class="slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all">09:00</button>
            <button type="button" onclick="selectSlot('11:00')" class="slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all">11:00</button>
            <button type="button" onclick="selectSlot('14:30')" class="slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all">14:30</button>
            <button type="button" onclick="selectSlot('16:00')" class="slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all">16:00</button>
            <button type="button" onclick="selectSlot('17:30')" class="slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all">17:30</button>
            <button type="button" onclick="selectSlot('19:00')" class="slot-btn p-2 rounded-xl border border-gray-800 bg-[#0b0c10] text-xs font-bold hover:border-purple-500 hover:text-purple-400 transition-all">19:00</button>
          </div>
        </div>

        <button id="confirm-btn" onclick="confirmBooking()" class="w-full mt-6 py-3 px-4 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-sm tracking-wide transition-all shadow-lg shadow-purple-600/20">
          Confirmar Agendamento
        </button>
      </div>

      <div id="success-box" class="hidden text-center py-6">
        <div class="text-4xl mb-3">🎉</div>
        <h2 class="text-xl font-bold text-white mb-1">Agendamento Confirmado!</h2>
        <p class="text-xs text-gray-400 mb-4">Você receberá os detalhes e lembretes diretamente no seu WhatsApp.</p>
        <button onclick="window.close()" class="px-5 py-2 bg-gray-800 rounded-xl text-xs font-bold text-gray-300">Fechar Janela</button>
      </div>
    </div>
  </div>

  <script>
    let selectedTime = '14:30';
    document.getElementById('date-picker').valueAsDate = new Date();

    function selectSlot(time) {
      selectedTime = time;
      document.querySelectorAll('.slot-btn').forEach(btn => {
        if (btn.innerText === time) {
          btn.classList.add('border-purple-500', 'bg-purple-600/20', 'text-purple-300');
        } else {
          btn.classList.remove('border-purple-500', 'bg-purple-600/20', 'text-purple-300');
        }
      });
    }

    async function confirmBooking() {
      const name = document.getElementById('name').value;
      const phone = document.getElementById('phone').value;
      const dateVal = document.getElementById('date-picker').value;
      const btn = document.getElementById('confirm-btn');

      if (!name || !phone || !dateVal) {
        alert('Por favor, preencha todos os campos.');
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
            time: selectedTime
          })
        });
        const data = await res.json();
        if (data.ok) {
          document.querySelector('.space-y-4').classList.add('hidden');
          document.getElementById('success-box').classList.remove('hidden');
        } else {
          alert('Erro ao agendar: ' + (data.error || 'Tente novamente'));
          btn.disabled = false;
          btn.innerText = 'Confirmar Agendamento';
        }
      } catch (err) {
        alert('Falha na comunicação com o servidor.');
        btn.disabled = false;
        btn.innerText = 'Confirmar Agendamento';
      }
    }
  </script>
</body>
</html>
"""

@booking_public_bp.route("/book/<string:tenant_id>", methods=["GET"])
def render_booking_page(tenant_id):
    """Renderiza a página de agendamento online (webview móvel)."""
    name = request.args.get("name", "")
    phone = request.args.get("phone", "")
    return render_template_string(
        BOOKING_HTML_TEMPLATE,
        tenant_id=tenant_id,
        client_name=name,
        client_phone=phone,
    )

@booking_public_bp.route("/api/public/booking/confirm", methods=["POST"])
def confirm_public_booking():
    """Recebe e confirma o agendamento enviado pela Webview."""
    data = request.get_json(silent=True) or {}
    tenant_id = data.get("tenant_id")
    name = data.get("name")
    phone = data.get("phone")
    slot_date = data.get("date")
    slot_time = data.get("time")

    if not name or not phone or not slot_date or not slot_time:
        return jsonify({"ok": False, "error": "Campos obrigatorios faltando"}), 400

    db = SessionLocal()
    try:
        # Encontra ou cria o lead
        lead = db.query(models.Lead).filter_by(tenant_id=tenant_id, phone=phone).first()
        if not lead:
            lead = models.Lead(
                tenant_id=tenant_id,
                phone=phone,
                name=name,
                status="agendado",
            )
            db.add(lead)
            db.flush()

        # Cria Appointment
        scheduled_dt = datetime.fromisoformat(f"{slot_date}T{slot_time}:00")
        appt = models.Appointment(
            tenant_id=tenant_id,
            lead_id=lead.id,
            client_name=name,
            client_phone=phone,
            scheduled_at=scheduled_dt,
            status="confirmed",
            appointment_type="consultation",
            modality="online",
        )
        db.add(appt)
        db.commit()

        return jsonify({
            "ok": True,
            "appointment_id": appt.id,
            "scheduled_at": scheduled_dt.isoformat(),
        })
    except Exception as exc:
        db.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        db.close()
