import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  QrCode, Copy, CheckCircle2, Clock, XCircle, RefreshCw, Plus,
} from 'lucide-react';
import { pixApi, type PixPayment } from '../api/pix';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Pix() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [activePix, setActivePix] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['pix-list'],
    queryFn: () => pixApi.list({ limit: 50 }),
    refetchInterval: 15000,
  });

  const items = data?.items ?? [];

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <QrCode className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Pix QR</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Gere QR codes Pix dinâmicos — tem prazo de pagamento, lead recebe na hora.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs"
        >
          <Plus className="w-4 h-4" />
          Novo Pix
        </button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-bg-surface rounded-2xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
          <QrCode className="w-12 h-12 mx-auto text-secondary/40 mb-4" />
          <h3 className="font-black text-lg mb-2">Nenhum Pix gerado ainda</h3>
          <p className="text-secondary text-sm mb-4">
            Crie um QR code dinâmico pra mandar pro lead via WhatsApp.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-xs font-black uppercase tracking-widest"
          >
            Criar primeiro Pix
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePix(p.id)}
              className="text-left bg-bg-surface border border-border hover:border-accent-amethyst/30 rounded-2xl p-5 transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-2xl font-black tracking-tight font-mono">
                    R${p.amount_brl.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-secondary mt-0.5 truncate max-w-[200px]">
                    {p.description || 'sem descrição'}
                  </div>
                </div>
                <StatusBadge status={p.status} />
              </div>
              <div className="text-[10px] text-secondary flex items-center justify-between">
                <span>
                  {p.lead_id ? `Lead #${p.lead_id}` : 'Manual'}
                </span>
                <span>
                  {p.expires_at && fmtRelative(p.expires_at)}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreatePixModal
          onClose={() => setShowCreate(false)}
          onCreated={(id) => {
            setShowCreate(false);
            setActivePix(id);
            qc.invalidateQueries({ queryKey: ['pix-list'] });
          }}
        />
      )}

      {/* Detail modal */}
      {activePix !== null && (
        <PixDetailModal
          pixId={activePix}
          onClose={() => setActivePix(null)}
        />
      )}
    </div>
  );
}

function CreatePixModal({
  onClose, onCreated,
}: {
  onClose: () => void;
  onCreated: (id: number) => void;
}) {
  const [amount, setAmount] = useState('67');
  const [description, setDescription] = useState('Tarô do Amor');
  const [expiresMin, setExpiresMin] = useState(30);

  const createMut = useMutation({
    mutationFn: () =>
      pixApi.create({
        amount_brl: parseFloat(amount),
        description: description || undefined,
        expires_min: expiresMin,
      }),
    onSuccess: (res) => {
      toast.success('Pix gerado!');
      onCreated(res.id);
    },
    onError: handleApiError('Erro ao gerar Pix'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5">
        <h2 className="text-xl font-black tracking-tight">Novo Pix</h2>

        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            Valor (R$)
          </label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            min={1}
            max={50000}
            step={0.01}
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-2xl font-mono tracking-tight focus:outline-none focus:border-accent-amethyst/30"
          />
        </div>

        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            Descrição
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ex: Tarô do Amor Express"
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30"
          />
        </div>

        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            Vence em
          </label>
          <div className="flex gap-2">
            {[15, 30, 60, 1440].map((m) => (
              <button
                key={m}
                onClick={() => setExpiresMin(m)}
                className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                  expiresMin === m
                    ? 'bg-accent-amethyst text-white'
                    : 'bg-bg-primary text-secondary hover:text-primary'
                }`}
              >
                {m === 1440 ? '24h' : m === 60 ? '1h' : `${m}min`}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => createMut.mutate()}
            disabled={!amount || parseFloat(amount) < 1 || createMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
          >
            {createMut.isPending ? 'Gerando...' : 'Gerar QR Code'}
          </button>
        </div>
      </div>
    </div>
  );
}

function PixDetailModal({
  pixId, onClose,
}: {
  pixId: number;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['pix-detail', pixId],
    queryFn: () => pixApi.get(pixId),
    refetchInterval: 5000,
  });

  const cancelMut = useMutation({
    mutationFn: () => pixApi.cancel(pixId),
    onSuccess: () => {
      toast.success('Pix cancelado');
      qc.invalidateQueries({ queryKey: ['pix-detail', pixId] });
      qc.invalidateQueries({ queryKey: ['pix-list'] });
    },
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-md w-full space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between">
          <h2 className="text-xl font-black tracking-tight">Pix #{pixId}</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        {isLoading || !data ? (
          <div className="text-center py-8 text-secondary">Carregando...</div>
        ) : (
          <>
            <div className="text-center space-y-2">
              <div className="text-4xl font-black tracking-tight font-mono">
                R${data.amount_brl.toFixed(2)}
              </div>
              <StatusBadge status={data.status} large />
            </div>

            {data.status === 'pending' && data.qr_code_image_url && (
              <div className="space-y-3">
                <div className="bg-white p-3 rounded-2xl">
                  <img src={data.qr_code_image_url} alt="QR Code Pix" className="w-full" />
                </div>

                {data.qr_code_text && (
                  <div className="space-y-2">
                    <div className="text-[10px] font-black uppercase tracking-widest text-secondary">
                      Código copia-e-cola:
                    </div>
                    <div className="flex gap-2">
                      <code className="flex-1 bg-bg-primary border border-border rounded-xl p-3 text-[10px] font-mono break-all max-h-20 overflow-y-auto">
                        {data.qr_code_text}
                      </code>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(data.qr_code_text!);
                          toast.success('Copiado');
                        }}
                        className="px-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl flex items-center"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}

                <div className="text-[11px] text-secondary text-center">
                  Vence em {data.expires_at && fmtRelative(data.expires_at)}
                </div>
              </div>
            )}

            {data.status === 'approved' && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-4 text-center">
                <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-500 mb-2" />
                <div className="text-sm font-black text-emerald-400">Pago!</div>
                {data.paid_at && (
                  <div className="text-[10px] text-secondary mt-1">
                    {new Date(data.paid_at).toLocaleString('pt-BR')}
                  </div>
                )}
              </div>
            )}

            {(data.status === 'expired' || data.status === 'cancelled') && (
              <div className="bg-zinc-800/50 border border-zinc-700 rounded-2xl p-4 text-center">
                <XCircle className="w-12 h-12 mx-auto text-secondary mb-2" />
                <div className="text-sm font-black text-secondary capitalize">{data.status}</div>
              </div>
            )}

            {data.description && (
              <div className="text-[11px] text-center text-secondary">
                {data.description}
              </div>
            )}

            {data.status === 'pending' && (
              <button
                onClick={() => cancelMut.mutate()}
                disabled={cancelMut.isPending}
                className="w-full px-5 py-3 bg-bg-primary border border-border hover:border-red-500/30 rounded-2xl text-xs font-bold uppercase tracking-widest text-secondary hover:text-red-400"
              >
                Cancelar Pix
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status, large = false }: { status: PixPayment['status']; large?: boolean }) {
  const config = {
    pending: { label: 'Aguardando', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30', Icon: Clock },
    approved: { label: 'Pago', color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30', Icon: CheckCircle2 },
    expired: { label: 'Expirado', color: 'text-zinc-500 bg-zinc-500/10 border-zinc-500/30', Icon: XCircle },
    cancelled: { label: 'Cancelado', color: 'text-red-400 bg-red-500/10 border-red-500/30', Icon: XCircle },
  }[status] || { label: status, color: 'text-secondary bg-zinc-500/10 border-zinc-500/30', Icon: RefreshCw };

  const Icon = config.Icon;
  const sizeClasses = large
    ? 'px-4 py-2 text-sm gap-2'
    : 'px-2 py-0.5 text-[10px] gap-1';

  return (
    <span className={`inline-flex items-center rounded-md border font-black uppercase tracking-widest ${config.color} ${sizeClasses}`}>
      <Icon className={large ? 'w-4 h-4' : 'w-3 h-3'} />
      {config.label}
    </span>
  );
}

function fmtRelative(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const min = Math.round(diff / 60000);
  if (min < 0) return `expirado há ${-min}min`;
  if (min < 60) return `${min}min`;
  return `${Math.round(min / 60)}h`;
}
