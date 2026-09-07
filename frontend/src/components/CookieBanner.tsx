import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Cookie, ShieldCheck } from 'lucide-react';
import { api } from '../api/client';

interface ConsentResp {
  consents: Record<string, boolean> | null;
  policy_version: string;
  needs_consent: boolean;
  recorded_at?: string;
}

interface ConsentSet {
  ok: boolean;
  consents: Record<string, boolean>;
  policy_version: string;
}

const CONSENT_QUERY_KEY = ['consent'];

export default function CookieBanner() {
  const qc = useQueryClient();
  const [showSettings, setShowSettings] = useState(false);
  const [analytics, setAnalytics] = useState(true);
  const [marketing, setMarketing] = useState(false);
  const [aiPersonalization, setAiPersonalization] = useState(true);

  const { data, isLoading } = useQuery({
    queryKey: CONSENT_QUERY_KEY,
    queryFn: () => api.get<ConsentResp>('/saas/consent'),
    retry: false,
    staleTime: Infinity,
  });

  const setMut = useMutation({
    mutationFn: (consents: Record<string, boolean>) =>
      api.post<ConsentSet>('/saas/consent', { consents }),
    onSuccess: () => qc.invalidateQueries({ queryKey: CONSENT_QUERY_KEY }),
  });

  // Sincronizar UI com salvos
  useEffect(() => {
    if (data?.consents) {
      setAnalytics(!!data.consents.analytics);
      setMarketing(!!data.consents.marketing);
      setAiPersonalization(!!data.consents.ai_personalization);
    }
  }, [data]);

  if (isLoading) return null;
  // Se já consentiu na versão atual, esconde
  if (data && !data.needs_consent && data.consents) return null;

  const acceptAll = () => {
    setMut.mutate({ analytics: true, marketing: true, ai_personalization: true });
  };
  const rejectNonEssential = () => {
    setMut.mutate({ analytics: false, marketing: false, ai_personalization: false });
  };
  const saveCustom = () => {
    setMut.mutate({ analytics, marketing, ai_personalization: aiPersonalization });
  };

  if (showSettings) {
    return (
      <div className="fixed inset-0 z-[55] bg-black/70 flex items-end md:items-center justify-center p-4">
        <div className="bg-bg-surface border border-border rounded-3xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-accent-amethyst" />
            </div>
            <div>
              <h2 className="text-base font-black">Suas preferências de privacidade</h2>
              <p className="text-[11px] text-secondary">LGPD: você decide o que compartilhamos</p>
            </div>
          </div>

          <div className="space-y-3">
            <ConsentToggle
              label="Essenciais"
              description="Funcionalidades obrigatórias da plataforma. Sempre ativas."
              checked
              disabled
            />
            <ConsentToggle
              label="Análise de uso"
              description="Métricas anônimas de como você usa o produto pra melhorá-lo."
              checked={analytics}
              onChange={setAnalytics}
            />
            <ConsentToggle
              label="Personalização IA"
              description="Permite que a IA use seus dados pra personalizar experiência."
              checked={aiPersonalization}
              onChange={setAiPersonalization}
            />
            <ConsentToggle
              label="Marketing"
              description="Email transacional sempre será enviado. Marketing apenas com seu OK."
              checked={marketing}
              onChange={setMarketing}
            />
          </div>

          <div className="flex flex-col-reverse md:flex-row gap-2 pt-2">
            <button
              onClick={() => setShowSettings(false)}
              className="flex-1 px-4 py-2.5 bg-bg-primary border border-border hover:border-secondary/30 rounded-xl text-xs font-black uppercase tracking-widest"
            >
              Voltar
            </button>
            <button
              onClick={() => {
                saveCustom();
                setShowSettings(false);
              }}
              disabled={setMut.isPending}
              className="flex-1 px-4 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest"
            >
              {setMut.isPending ? 'Salvando...' : 'Salvar preferências'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-6">
      <div className="max-w-3xl mx-auto bg-bg-surface border border-border rounded-3xl p-5 shadow-2xl flex flex-col md:flex-row items-start md:items-center gap-4">
        <div className="flex items-start gap-3 flex-1">
          <div className="w-10 h-10 rounded-xl bg-accent-amethyst/10 flex items-center justify-center flex-shrink-0">
            <Cookie className="w-5 h-5 text-accent-amethyst" />
          </div>
          <div className="text-sm text-primary">
            <p>
              Usamos cookies pra melhorar sua experiência. Você pode escolher
              o que aceitar.
            </p>
            <button
              onClick={() => setShowSettings(true)}
              className="text-xs text-accent-amethyst font-bold hover:underline mt-1"
            >
              Configurar preferências
            </button>
          </div>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <button
            onClick={rejectNonEssential}
            disabled={setMut.isPending}
            className="flex-1 md:flex-none px-4 py-2 bg-bg-primary border border-border rounded-xl text-[10px] font-black uppercase tracking-widest"
          >
            Rejeitar
          </button>
          <button
            onClick={acceptAll}
            disabled={setMut.isPending}
            className="flex-1 md:flex-none px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-[10px] font-black uppercase tracking-widest"
          >
            Aceitar todos
          </button>
        </div>
      </div>
    </div>
  );
}

function ConsentToggle({
  label, description, checked, onChange, disabled,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange?: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 p-3 bg-bg-primary rounded-xl border border-border">
      <div className="flex-1">
        <div className="text-sm font-bold">{label}</div>
        <div className="text-[11px] text-secondary mt-0.5">{description}</div>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange?.(!checked)}
        className={`relative w-11 h-6 rounded-full transition-all flex-shrink-0 ${
          checked ? 'bg-accent-amethyst' : 'bg-zinc-700'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <div
          className={`absolute top-0.5 w-5 h-5 bg-white rounded-full transition-all ${
            checked ? 'left-5' : 'left-0.5'
          }`}
        />
      </button>
    </div>
  );
}
