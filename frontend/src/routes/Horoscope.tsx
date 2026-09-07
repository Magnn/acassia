import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles, Sun, Clock, Users, Zap, RefreshCw,
  Send, AlertCircle, Check, BarChart3, Wand2,
} from 'lucide-react';
import { horoscopeApi, type HoroscopeConfig, type FanoutStats } from '../api/horoscope';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

const SEGMENT_LABELS = {
  all: 'Todos os leads',
  hot_warm: 'Apenas Hot + Warm',
  hot: 'Apenas Hot',
  warm: 'Apenas Warm',
};

const COMMON_TIMEZONES = [
  'America/Sao_Paulo',
  'America/Manaus',
  'America/Belem',
  'America/Fortaleza',
  'America/Recife',
];

export default function Horoscope() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['horoscope-config'],
    queryFn: horoscopeApi.getConfig,
  });

  const patchMut = useMutation({
    mutationFn: (patch: Partial<HoroscopeConfig>) => horoscopeApi.patchConfig(patch),
    onSuccess: (res) => {
      qc.setQueryData(['horoscope-config'], (prev: { config: HoroscopeConfig; stats: any } | undefined) =>
        prev ? { ...prev, config: res.config } : prev,
      );
      toast.success('Configuração salva');
    },
    onError: handleApiError('Erro ao salvar'),
  });

  const runMut = useMutation({
    mutationFn: (dry: boolean) => horoscopeApi.runNow(dry),
    onSuccess: (res) => {
      const s = res.stats;
      if (res.dry_run) {
        toast.success(`Simulação: ${s.sent} envios estimados.`);
      } else {
        toast.success(`Disparo: ${s.sent} enviados, ${s.failed} falhas, ${s.opted_out} sem opt-in.`);
      }
      qc.invalidateQueries({ queryKey: ['horoscope-deliveries'] });
    },
    onError: handleApiError('Erro ao disparar'),
  });

  const backfillMut = useMutation({
    mutationFn: () => horoscopeApi.backfillSigns(),
    onSuccess: (res) => {
      toast.success(`${res.updated} leads atualizados com signo.`);
      qc.invalidateQueries({ queryKey: ['horoscope-config'] });
    },
    onError: handleApiError('Erro ao recalcular'),
  });

  if (isLoading || !data) {
    return <div className="p-10 text-center text-secondary">Carregando…</div>;
  }

  const cfg = data.config;
  const stats = data.stats;

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <header>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Horóscopo Diário</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Cada lead recebe automaticamente o horóscopo do seu signo no horário definido. Engajamento sem esforço.
        </p>
      </header>

      <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap className={`w-5 h-5 ${cfg.enabled ? 'text-emerald-400' : 'text-secondary'}`} />
            <div>
              <h2 className="text-lg font-black tracking-tight">
                Automação {cfg.enabled ? 'ativa' : 'pausada'}
              </h2>
              <p className="text-[11px] text-secondary">
                {cfg.last_run_date
                  ? `Último disparo: ${new Date(cfg.last_run_date).toLocaleDateString('pt-BR')}`
                  : 'Nunca disparado'}
                {' · '}
                {cfg.total_sent} envios totais
              </p>
            </div>
          </div>
          <Toggle
            on={cfg.enabled}
            onChange={(on) => patchMut.mutate({ enabled: on })}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Hora de envio (local)" Icon={Clock}>
            <input
              type="number"
              min={0}
              max={23}
              value={cfg.send_hour_local}
              onChange={(e) => patchMut.mutate({ send_hour_local: Number(e.target.value) })}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm tabular-nums"
            />
          </Field>

          <Field label="Fuso horário" Icon={Sun}>
            <select
              value={cfg.timezone}
              onChange={(e) => patchMut.mutate({ timezone: e.target.value })}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </Field>

          <Field label="Origem do texto" Icon={Wand2}>
            <select
              value={cfg.source}
              onChange={(e) => patchMut.mutate({ source: e.target.value as 'gemini' | 'manual' })}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              <option value="gemini">IA (Gemini, automático)</option>
              <option value="manual">Manual (eu escrevo)</option>
            </select>
          </Field>

          <Field label="Segmento" Icon={Users}>
            <select
              value={cfg.segment_filter}
              onChange={(e) => patchMut.mutate({ segment_filter: e.target.value as any })}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              {Object.entries(SEGMENT_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Mensagem antes do horóscopo (opcional)">
          <textarea
            defaultValue={cfg.custom_prefix || ''}
            onBlur={(e) => {
              const v = e.target.value.trim();
              if (v !== (cfg.custom_prefix || '')) patchMut.mutate({ custom_prefix: v });
            }}
            rows={2}
            placeholder="Ex.: Bom dia, querida! Sua mensagem do universo:"
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm resize-none"
          />
        </Field>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <StatBox label="Leads c/ signo" value={stats.candidates_with_sign} />
          <StatBox label="Opt-in horóscopo" value={stats.opted_in} highlight />
        </div>

        <div className="flex gap-3 pt-2 border-t border-border pt-5">
          <button
            onClick={() => backfillMut.mutate()}
            disabled={backfillMut.isPending}
            className="flex-1 px-4 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center justify-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${backfillMut.isPending ? 'animate-spin' : ''}`} />
            Calcular signos das datas de nascimento
          </button>
          <button
            onClick={() => runMut.mutate(true)}
            disabled={runMut.isPending}
            className="px-4 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center gap-2"
          >
            Simular
          </button>
          <button
            onClick={() => runMut.mutate(false)}
            disabled={runMut.isPending || !cfg.enabled}
            className="px-4 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center gap-2"
          >
            <Send className="w-3.5 h-3.5" />
            Disparar agora
          </button>
        </div>
        {!cfg.enabled && (
          <div className="text-[11px] text-amber-400 flex items-center gap-1.5">
            <AlertCircle className="w-3 h-3" />
            Ative a automação para disparar.
          </div>
        )}
      </section>

      <TodaySection />
      <DeliveriesSection />
    </div>
  );
}

function Toggle({ on, onChange }: { on: boolean; onChange: (on: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={`relative w-12 h-7 rounded-full transition-colors ${
        on ? 'bg-accent-amethyst' : 'bg-bg-primary border border-border'
      }`}
    >
      <span
        className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
          on ? 'translate-x-6' : 'translate-x-0.5'
        }`}
      />
    </button>
  );
}

function Field({
  label, Icon, children,
}: {
  label: string;
  Icon?: typeof Sparkles;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5 flex items-center gap-1.5">
        {Icon && <Icon className="w-3 h-3" />}
        {label}
      </label>
      {children}
    </div>
  );
}

function StatBox({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-2xl p-4 border ${
      highlight ? 'bg-accent-amethyst/10 border-accent-amethyst/30' : 'bg-bg-primary border-border'
    }`}>
      <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">{label}</div>
      <div className="text-2xl font-black tabular-nums">{value.toLocaleString('pt-BR')}</div>
    </div>
  );
}

function TodaySection() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['horoscope-today'],
    queryFn: () => horoscopeApi.today(),
  });

  const previewMut = useMutation({
    mutationFn: (signo: string) => horoscopeApi.preview(signo, true),
    onSuccess: () => {
      toast.success('Texto regenerado');
      qc.invalidateQueries({ queryKey: ['horoscope-today'] });
    },
    onError: handleApiError('Erro ao regenerar'),
  });

  return (
    <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-black tracking-tight flex items-center gap-2">
          <Sun className="w-4 h-4 text-amber-400" />
          Horóscopo de hoje · todos os signos
        </h2>
        <span className="text-[10px] text-secondary">{data?.date}</span>
      </div>

      {isLoading ? (
        <div className="text-center text-secondary text-sm py-6">Carregando…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(data?.signs ?? []).map((s) => (
            <div
              key={s.signo}
              className="bg-bg-primary border border-border rounded-2xl p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-black text-sm tracking-tight">{s.signo}</h3>
                <button
                  onClick={() => previewMut.mutate(s.signo)}
                  disabled={previewMut.isPending}
                  className="text-[10px] text-accent-amethyst hover:underline flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${
                    previewMut.isPending && previewMut.variables === s.signo ? 'animate-spin' : ''
                  }`} />
                  Regenerar
                </button>
              </div>
              <p className="text-xs text-primary leading-relaxed">{s.text}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function DeliveriesSection() {
  const { data } = useQuery({
    queryKey: ['horoscope-deliveries'],
    queryFn: () => horoscopeApi.deliveries(7),
  });
  if (!data) return null;
  const sent = data.summary.sent || 0;
  const failed = data.summary.failed || 0;

  return (
    <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <h2 className="text-lg font-black tracking-tight flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-accent-amethyst" />
        Últimos 7 dias
      </h2>
      <div className="grid grid-cols-3 gap-3">
        <StatBox label="Enviados" value={sent} highlight />
        <StatBox label="Falhas" value={failed} />
        <StatBox label="Pulados" value={data.summary.opted_out || 0} />
      </div>
      {data.deliveries.length > 0 && (
        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {data.deliveries.slice(0, 50).map((d) => (
            <div
              key={d.id}
              className="bg-bg-primary border border-border rounded-lg p-2.5 flex items-center justify-between text-[11px]"
            >
              <div className="flex items-center gap-2">
                {d.status === 'sent' ? (
                  <Check className="w-3 h-3 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-3 h-3 text-rose-400" />
                )}
                <span className="font-mono text-secondary">#{d.lead_id}</span>
                <span className="font-bold">{d.signo}</span>
              </div>
              <span className="text-secondary">
                {new Date(d.sent_at).toLocaleString('pt-BR')}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
