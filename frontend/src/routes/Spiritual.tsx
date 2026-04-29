import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles, Sun, Moon, Compass, Hash, Heart, Briefcase, Home,
  Search, Send, RefreshCw, Wand2, Calculator, Star, Zap, ImageIcon,
} from 'lucide-react';
import { spiritualApi, type SpiritualProfile } from '../api/spiritual';
import { auraApi } from '../api/aura';
import { inboxApi, type LeadPreview } from '../api/inbox';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

type Focus = 'geral' | 'amor' | 'carreira' | 'familia';

export default function Spiritual() {
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <header>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Perfil Espiritual</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Mapa astral lite + numerologia + interpretação IA por lead.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <LeadPicker selectedId={selectedLeadId} onSelect={setSelectedLeadId} />
        <div>
          {selectedLeadId ? (
            <ProfilePanel leadId={selectedLeadId} />
          ) : (
            <div className="bg-bg-surface border border-border rounded-3xl p-12 text-center text-secondary">
              Selecione um lead à esquerda para ver/gerar o perfil espiritual.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function LeadPicker({
  selectedId, onSelect,
}: {
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const [search, setSearch] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['leads-picker', search],
    queryFn: () => inboxApi.getLeads({ search: search || undefined, limit: 50 }),
  });
  const items = (data?.items ?? []) as LeadPreview[];

  return (
    <div className="bg-bg-surface border border-border rounded-3xl p-4 space-y-3 sticky top-6 self-start">
      <div className="flex items-center gap-2 bg-bg-primary border border-border rounded-xl px-3 py-2">
        <Search className="w-3.5 h-3.5 text-secondary" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar lead…"
          className="flex-1 bg-transparent text-sm outline-none"
        />
      </div>

      <div className="space-y-1 max-h-[60vh] overflow-y-auto">
        {isLoading ? (
          <div className="text-center text-secondary text-xs py-4">Carregando…</div>
        ) : items.length === 0 ? (
          <div className="text-center text-secondary text-xs py-4">Nenhum lead.</div>
        ) : (
          items.map((l) => (
            <button
              key={l.id}
              onClick={() => onSelect(l.id)}
              className={`w-full text-left px-3 py-2 rounded-xl transition-all ${
                selectedId === l.id
                  ? 'bg-accent-amethyst/10 border border-accent-amethyst/30'
                  : 'hover:bg-bg-primary border border-transparent'
              }`}
            >
              <div className="text-sm font-bold truncate">{l.nome || l.telefone}</div>
              <div className="text-[11px] text-secondary truncate">{l.telefone}</div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

function ProfilePanel({ leadId }: { leadId: number }) {
  const qc = useQueryClient();
  const { data: profile, isLoading } = useQuery({
    queryKey: ['spiritual-profile', leadId],
    queryFn: () => spiritualApi.getProfile(leadId),
  });

  const computeNatalMut = useMutation({
    mutationFn: (payload: { birth_time?: string; birth_place?: string; lat?: number; lon?: number }) =>
      spiritualApi.computeNatal(leadId, payload),
    onSuccess: () => {
      toast.success('Mapa recalculado');
      qc.invalidateQueries({ queryKey: ['spiritual-profile', leadId] });
    },
    onError: handleApiError('Erro ao calcular mapa'),
  });

  const interpretNatalMut = useMutation({
    mutationFn: (focus: Focus) => spiritualApi.interpretNatal(leadId, focus),
    onSuccess: () => {
      toast.success('Interpretação gerada');
      qc.invalidateQueries({ queryKey: ['spiritual-profile', leadId] });
    },
    onError: handleApiError('Erro na interpretação'),
  });

  const computeNumMut = useMutation({
    mutationFn: () => spiritualApi.computeNumerology(leadId),
    onSuccess: () => {
      toast.success('Numerologia calculada');
      qc.invalidateQueries({ queryKey: ['spiritual-profile', leadId] });
    },
    onError: handleApiError('Erro ao calcular'),
  });

  const interpretNumMut = useMutation({
    mutationFn: () => spiritualApi.interpretNumerology(leadId),
    onSuccess: () => {
      toast.success('Análise numerológica gerada');
      qc.invalidateQueries({ queryKey: ['spiritual-profile', leadId] });
    },
    onError: handleApiError('Erro na análise'),
  });

  const sendMut = useMutation({
    mutationFn: () => spiritualApi.sendSummary(leadId),
    onSuccess: () => toast.success('Resumo enviado pro lead'),
    onError: handleApiError('Erro ao enviar'),
  });

  if (isLoading || !profile) {
    return <div className="bg-bg-surface border border-border rounded-3xl p-12 text-center text-secondary">Carregando…</div>;
  }

  return (
    <div className="space-y-6">
      <LeadSummary profile={profile} />
      <NatalSection
        profile={profile}
        onCompute={(p) => computeNatalMut.mutate(p)}
        computing={computeNatalMut.isPending}
        onInterpret={(f) => interpretNatalMut.mutate(f)}
        interpreting={interpretNatalMut.isPending}
      />
      <NumerologySection
        profile={profile}
        onCompute={() => computeNumMut.mutate()}
        computing={computeNumMut.isPending}
        onInterpret={() => interpretNumMut.mutate()}
        interpreting={interpretNumMut.isPending}
      />
      <AuraSection leadId={leadId} signo={profile.lead.signo} />
      <div className="bg-bg-surface border border-border rounded-3xl p-5">
        <button
          onClick={() => sendMut.mutate()}
          disabled={sendMut.isPending}
          className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" />
          {sendMut.isPending ? 'Enviando…' : 'Enviar resumo via WhatsApp'}
        </button>
      </div>
    </div>
  );
}

function LeadSummary({ profile }: { profile: SpiritualProfile }) {
  const lead = profile.lead;
  return (
    <div className="bg-bg-surface border border-border rounded-3xl p-5 flex items-center justify-between">
      <div>
        <h2 className="text-xl font-black">{lead.nome || lead.telefone}</h2>
        <div className="text-[11px] text-secondary mt-1">
          {lead.telefone}
          {lead.birth_date && ` · nascimento ${new Date(lead.birth_date).toLocaleDateString('pt-BR')}`}
          {lead.signo && ` · ${lead.signo}`}
        </div>
      </div>
    </div>
  );
}

function NatalSection({
  profile, onCompute, computing, onInterpret, interpreting,
}: {
  profile: SpiritualProfile;
  onCompute: (p: { birth_time?: string; birth_place?: string; lat?: number; lon?: number }) => void;
  computing: boolean;
  onInterpret: (focus: Focus) => void;
  interpreting: boolean;
}) {
  const natal = profile.natal;
  const [time, setTime] = useState(natal?.birth_time || '');
  const [place, setPlace] = useState(natal?.birth_place || '');
  const [lat, setLat] = useState(natal?.lat?.toString() || '');
  const [lon, setLon] = useState(natal?.lon?.toString() || '');
  const [focus, setFocus] = useState<Focus>('geral');

  const noBirthDate = !profile.lead.birth_date;

  return (
    <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <h2 className="text-lg font-black tracking-tight flex items-center gap-2">
        <Compass className="w-4 h-4 text-accent-amethyst" />
        Mapa Astral
      </h2>

      {noBirthDate ? (
        <div className="text-xs text-amber-400">
          Lead sem data de nascimento. Capture via fluxo ou edite o cadastro do lead.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <SmallField label="Hora (HH:MM)" value={time} onChange={setTime} placeholder="07:30" />
            <SmallField label="Cidade" value={place} onChange={setPlace} placeholder="Rio de Janeiro" />
            <SmallField label="Lat" value={lat} onChange={setLat} placeholder="-22.9" type="number" />
            <SmallField label="Lon" value={lon} onChange={setLon} placeholder="-43.2" type="number" />
          </div>
          <button
            onClick={() => onCompute({
              birth_time: time || undefined,
              birth_place: place || undefined,
              lat: lat ? Number(lat) : undefined,
              lon: lon ? Number(lon) : undefined,
            })}
            disabled={computing}
            className="px-4 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center gap-2"
          >
            <Calculator className={`w-3.5 h-3.5 ${computing ? 'animate-spin' : ''}`} />
            {natal?.chart ? 'Recalcular mapa' : 'Calcular mapa'}
          </button>

          {natal?.chart && (
            <div className="grid grid-cols-3 gap-3">
              <PlanetCard Icon={Sun} label="Sol" sign={natal.chart.sun?.sign} />
              <PlanetCard Icon={Moon} label="Lua" sign={natal.chart.moon?.sign} approx={natal.chart.moon?.approx} />
              <PlanetCard Icon={Compass} label="Asc" sign={natal.chart.asc?.sign || '—'} />
            </div>
          )}

          {natal?.chart && (
            <div className="grid grid-cols-4 gap-2 text-center text-[11px] text-secondary">
              <div>🔥 Fogo · {natal.chart.elements.fogo}</div>
              <div>🌍 Terra · {natal.chart.elements.terra}</div>
              <div>💨 Ar · {natal.chart.elements.ar}</div>
              <div>💧 Água · {natal.chart.elements.agua}</div>
            </div>
          )}

          {natal?.chart && (
            <div className="space-y-3 border-t border-border pt-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-black uppercase tracking-widest text-secondary">Foco:</span>
                {(['geral', 'amor', 'carreira', 'familia'] as const).map((f) => {
                  const Icon = f === 'amor' ? Heart : f === 'carreira' ? Briefcase : f === 'familia' ? Home : Star;
                  return (
                    <button
                      key={f}
                      onClick={() => setFocus(f)}
                      className={`text-[11px] px-2.5 py-1 rounded-lg flex items-center gap-1 ${
                        focus === f ? 'bg-accent-amethyst text-white' : 'bg-bg-primary text-secondary'
                      }`}
                    >
                      <Icon className="w-3 h-3" />
                      {f}
                    </button>
                  );
                })}
                <button
                  onClick={() => onInterpret(focus)}
                  disabled={interpreting}
                  className="ml-auto px-3 py-1.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-lg text-[11px] font-bold flex items-center gap-1.5"
                >
                  <Wand2 className={`w-3 h-3 ${interpreting ? 'animate-spin' : ''}`} />
                  {natal.interpretation ? 'Regenerar' : 'Interpretar'}
                </button>
              </div>

              {natal.interpretation && (
                <div className="bg-bg-primary border border-border rounded-2xl p-4 text-xs leading-relaxed whitespace-pre-wrap">
                  {natal.interpretation}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function NumerologySection({
  profile, onCompute, computing, onInterpret, interpreting,
}: {
  profile: SpiritualProfile;
  onCompute: () => void;
  computing: boolean;
  onInterpret: () => void;
  interpreting: boolean;
}) {
  const num = profile.numerology;

  return (
    <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-black tracking-tight flex items-center gap-2">
          <Hash className="w-4 h-4 text-accent-amethyst" />
          Numerologia
        </h2>
        <button
          onClick={onCompute}
          disabled={computing}
          className="text-[11px] px-3 py-1.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-lg flex items-center gap-1.5 font-bold"
        >
          <RefreshCw className={`w-3 h-3 ${computing ? 'animate-spin' : ''}`} />
          {num ? 'Recalcular' : 'Calcular'}
        </button>
      </div>

      {!num ? (
        <p className="text-xs text-secondary">
          Ainda não calculado. Precisa de nome completo + data de nascimento.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <NumberCard label="Vida" n={num.life_path} meaning={num.components?.life_path_meaning} />
            <NumberCard label="Expressão" n={num.expression} meaning={num.components?.expression_meaning} />
            <NumberCard label="Alma" n={num.soul} meaning={num.components?.soul_meaning} />
          </div>

          <div className="border-t border-border pt-4">
            <button
              onClick={onInterpret}
              disabled={interpreting}
              className="px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-lg text-xs font-black uppercase tracking-widest flex items-center gap-1.5"
            >
              <Wand2 className={`w-3 h-3 ${interpreting ? 'animate-spin' : ''}`} />
              {num.interpretation ? 'Regenerar análise' : 'Gerar análise IA'}
            </button>
            {num.interpretation && (
              <div className="bg-bg-primary border border-border rounded-2xl p-4 text-xs leading-relaxed whitespace-pre-wrap mt-3">
                {num.interpretation}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function AuraSection({ leadId, signo }: { leadId: number; signo: string | null }) {
  const qc = useQueryClient();
  const [mood, setMood] = useState('');

  const statusQ = useQuery({
    queryKey: ['aura-status'],
    queryFn: () => auraApi.status(),
    staleTime: 5 * 60 * 1000,
  });

  const auraQ = useQuery({
    queryKey: ['aura-latest', leadId],
    queryFn: () => auraApi.getLatest(leadId),
  });

  const generateMut = useMutation({
    mutationFn: (force: boolean) => auraApi.generate(leadId, { force, mood: mood || undefined }),
    onSuccess: (res) => {
      toast.success(res.cached ? 'Aura desta semana já existia' : 'Aura gerada');
      qc.invalidateQueries({ queryKey: ['aura-latest', leadId] });
    },
    onError: handleApiError('Erro ao gerar aura'),
  });

  const sendMut = useMutation({
    mutationFn: () => auraApi.send(leadId, auraQ.data?.aura?.id),
    onSuccess: () => {
      toast.success('Aura enviada via WhatsApp');
      qc.invalidateQueries({ queryKey: ['aura-latest', leadId] });
    },
    onError: handleApiError('Erro ao enviar aura'),
  });

  const status = statusQ.data;
  const aura = auraQ.data?.aura;
  const isCurrentWeek = aura && auraQ.data?.current_week === aura.week_id;

  return (
    <section className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <h2 className="text-lg font-black tracking-tight flex items-center gap-2">
        <Zap className="w-4 h-4 text-accent-amethyst" />
        Aura desta semana
      </h2>

      {!status?.available ? (
        <div className="bg-bg-primary border border-border rounded-2xl p-4 text-xs text-secondary">
          Provider de imagem não configurado. {status?.hint}
        </div>
      ) : !signo ? (
        <p className="text-xs text-amber-400">
          Calcule o signo do lead primeiro (seção Mapa Astral acima).
        </p>
      ) : (
        <>
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              placeholder="Mood opcional (ex.: esperança, transformação)"
              className="flex-1 bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
              maxLength={40}
            />
            <button
              onClick={() => generateMut.mutate(false)}
              disabled={generateMut.isPending}
              className="px-4 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center gap-2"
            >
              <Wand2 className={`w-3.5 h-3.5 ${generateMut.isPending ? 'animate-spin' : ''}`} />
              {aura && isCurrentWeek ? 'Existente' : 'Gerar'}
            </button>
            {aura && isCurrentWeek && (
              <button
                onClick={() => generateMut.mutate(true)}
                disabled={generateMut.isPending}
                className="px-3 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${generateMut.isPending ? 'animate-spin' : ''}`} />
                Regen
              </button>
            )}
          </div>

          {generateMut.isPending && (
            <div className="text-[11px] text-secondary text-center py-4">
              Gerando aura — pode demorar até 30s…
            </div>
          )}

          {aura && (
            <div className="space-y-3">
              <div className="aspect-square max-w-md mx-auto bg-bg-primary rounded-2xl overflow-hidden border border-border">
                <img
                  src={aura.image_url}
                  alt={`Aura de ${aura.signo}`}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="text-center text-[11px] text-secondary">
                {aura.signo} · semana {aura.week_id} · {aura.provider}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => sendMut.mutate()}
                  disabled={sendMut.isPending || aura.sent_to_lead}
                  className="flex-1 px-4 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2"
                >
                  <Send className="w-3.5 h-3.5" />
                  {aura.sent_to_lead ? 'Enviada' : 'Enviar via WhatsApp'}
                </button>
                <a
                  href={aura.image_url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center gap-2"
                >
                  <ImageIcon className="w-3.5 h-3.5" />
                  Abrir
                </a>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function PlanetCard({
  Icon, label, sign, approx,
}: {
  Icon: typeof Sun;
  label: string;
  sign: string | undefined;
  approx?: boolean;
}) {
  return (
    <div className="bg-bg-primary border border-border rounded-2xl p-4 text-center">
      <Icon className="w-4 h-4 mx-auto text-accent-amethyst mb-1.5" />
      <div className="text-[10px] font-black uppercase tracking-widest text-secondary">{label}</div>
      <div className="text-base font-black mt-1">{sign || '—'}</div>
      {approx && <div className="text-[9px] text-secondary mt-0.5">aprox</div>}
    </div>
  );
}

function NumberCard({
  label, n, meaning,
}: {
  label: string;
  n: number | null | undefined;
  meaning: string | null | undefined;
}) {
  return (
    <div className="bg-bg-primary border border-border rounded-2xl p-4">
      <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">{label}</div>
      <div className="text-3xl font-black tabular-nums text-accent-amethyst">{n ?? '—'}</div>
      {meaning && <p className="text-[10px] text-secondary mt-2 leading-relaxed">{meaning}</p>}
    </div>
  );
}

function SmallField({
  label, value, onChange, placeholder, type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="text-[9px] font-black uppercase tracking-widest text-secondary block mb-1">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-bg-primary border border-border rounded-lg px-3 py-2 text-xs"
      />
    </div>
  );
}
