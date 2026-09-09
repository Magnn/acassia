import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Calendar as CalendarIcon, Clock, Video, LogOut, Sparkles, ExternalLink } from 'lucide-react';
import { api } from '../../api/client';
import { useConsumerAuth } from '../../hooks/useConsumerAuth';
import ConsumerAuthCard from '../../components/ConsumerAuthCard';

interface AppointmentItem {
  id: number | null;
  slot_id: number | null;
  expert_tenant_id: string;
  expert_name: string;
  title: string;
  datetime: string | null;
  duration_minutes: number;
  status: 'scheduled' | 'completed';
  meeting_url?: string | null;
}

export default function PortalSchedule() {
  const { consumer, isAuthenticated, isLoading: authLoading, logout } = useConsumerAuth();

  const { data, isLoading: apptsLoading } = useQuery({
    queryKey: ['b2c-appointments', consumer?.id],
    queryFn: () => api.get<{ appointments: AppointmentItem[] }>(`/api/b2c/me/${consumer?.id}/appointments`),
    enabled: Boolean(consumer?.id),
  });

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-zinc-500 text-sm font-bold animate-pulse">Carregando seus agendamentos...</div>
      </div>
    );
  }

  if (!isAuthenticated || !consumer) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4">
        <ConsumerAuthCard
          title="Acesse sua Agenda"
          subtitle="Faça login para ver suas sessões ao vivo com especialistas e links de videochamada."
        />
      </div>
    );
  }

  const appointments = data?.appointments ?? [];
  const upcoming = appointments.filter(a => a.status === 'scheduled');
  const past = appointments.filter(a => a.status === 'completed');

  const formatDateTime = (isoStr: string | null) => {
    if (!isoStr) return 'Horário a definir';
    const d = new Date(isoStr);
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-8 pb-20 md:pb-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Minha Agenda</h1>
          <p className="text-zinc-400 mt-1">
            Olá, <span className="text-white font-bold">{consumer.name || consumer.phone}</span>. Seus próximos encontros ao vivo com especialistas.
          </p>
        </div>
        <button
          onClick={logout}
          className="self-start sm:self-auto flex items-center gap-2 px-3 py-1.5 rounded-xl border border-zinc-800 text-xs font-bold text-zinc-400 hover:text-white hover:border-zinc-700 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" /> Sair da Conta
        </button>
      </div>

      {apptsLoading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 h-28 animate-pulse" />
          ))}
        </div>
      ) : upcoming.length === 0 ? (
        <div className="p-12 bg-zinc-900/40 border border-dashed border-zinc-800 rounded-3xl text-center max-w-lg mx-auto">
          <div className="w-12 h-12 rounded-2xl bg-accent-amethyst/10 text-accent-amethyst flex items-center justify-center mx-auto mb-4">
            <CalendarIcon className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Nenhum Agendamento Futuro</h3>
          <p className="text-zinc-400 text-sm mb-6">
            Você não possui sessões agendadas para os próximos dias. Explore nossos especialistas disponíveis para marcar uma sessão.
          </p>
          <a
            href="/portal/explore"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-accent-amethyst hover:bg-accent-amethyst/90 text-white font-bold text-xs uppercase tracking-wider transition-all"
          >
            <Sparkles className="w-4 h-4" /> Ver Especialistas
          </a>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-accent-amethyst">
            Próximas Sessões ({upcoming.length})
          </h2>
          {upcoming.map((apt, idx) => (
            <div
              key={apt.id ?? apt.slot_id ?? idx}
              className="bg-zinc-900 border border-zinc-800 hover:border-accent-amethyst/40 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all shadow-lg"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-accent-amethyst/10 rounded-2xl flex items-center justify-center text-accent-amethyst shrink-0">
                  <CalendarIcon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white mb-1">{apt.title}</h3>
                  <p className="text-zinc-400 font-medium text-sm">{apt.expert_name}</p>
                  <div className="flex flex-wrap items-center gap-4 mt-3">
                    <span className="flex items-center gap-1.5 text-xs text-zinc-300 font-bold bg-zinc-800/80 px-2.5 py-1 rounded-lg">
                      <Clock className="w-3.5 h-3.5 text-accent-amethyst" /> {formatDateTime(apt.datetime)}
                    </span>
                    <span className="text-xs text-zinc-400 font-medium">
                      ⏱️ {apt.duration_minutes} minutos
                    </span>
                  </div>
                </div>
              </div>

              {apt.meeting_url ? (
                <a
                  href={apt.meeting_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full md:w-auto px-6 py-3 bg-white text-black font-black rounded-xl hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2 text-sm shadow"
                >
                  <Video className="w-4 h-4 text-purple-600" />
                  <span>Entrar na Sala</span>
                  <ExternalLink className="w-3.5 h-3.5 text-zinc-500" />
                </a>
              ) : (
                <div className="text-xs text-zinc-500 italic bg-zinc-950 px-4 py-2.5 rounded-xl border border-zinc-800 text-center">
                  Link de videochamada será enviado no WhatsApp
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Histórico anterior */}
      {past.length > 0 && (
        <div className="mt-12 space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">
            Sessões Concluídas ({past.length})
          </h2>
          <div className="space-y-3 opacity-70">
            {past.map((apt, idx) => (
              <div
                key={apt.id ?? apt.slot_id ?? idx}
                className="bg-zinc-950 border border-zinc-900 rounded-xl p-4 flex items-center justify-between"
              >
                <div>
                  <h4 className="text-sm font-bold text-white">{apt.title}</h4>
                  <p className="text-xs text-zinc-500">{apt.expert_name} • {formatDateTime(apt.datetime)}</p>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-1 bg-zinc-900 text-zinc-400 rounded-md">
                  Concluída
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
