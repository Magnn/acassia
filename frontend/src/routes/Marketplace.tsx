import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Store, Sparkles, Crown, Heart, Star, RefreshCw,
  ShoppingBag, Tag, Layers, ArrowRight, X, Check,
  Copy, QrCode, ChevronRight, BadgeCheck, AlertCircle, Plus,
} from 'lucide-react';
import {
  marketplaceApi,
  type MarketplaceListing,
  type MarketplaceListingDetail,
  type MyListing,
} from '../api/marketplace';
import { blueprintsApi } from '../api/blueprints';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

type Tab = 'catalogo' | 'listings' | 'vendas';

const CATEGORY_META: Record<string, { label: string; Icon: typeof Sparkles; color: string }> = {
  amor: { label: 'Amor', Icon: Heart, color: 'text-rose-400' },
  premium: { label: 'Premium', Icon: Crown, color: 'text-amber-400' },
  astrologia: { label: 'Astrologia', Icon: Star, color: 'text-purple-400' },
  recuperacao: { label: 'Recuperação', Icon: RefreshCw, color: 'text-blue-400' },
};

export default function Marketplace() {
  const [tab, setTab] = useState<Tab>('catalogo');

  return (
    <div className="p-10 max-w-6xl mx-auto space-y-8">
      <header>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
            <Store className="w-5 h-5 text-accent-amethyst" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Marketplace de Fluxos</h1>
        </div>
        <p className="text-secondary text-sm font-medium">
          Compre fluxos prontos de outros taroteiros — ou venda os seus e ganhe 70% do valor.
        </p>
      </header>

      <nav className="flex gap-2 border-b border-border">
        {([
          ['catalogo', 'Catálogo', ShoppingBag] as const,
          ['listings', 'Meus Listings', Tag] as const,
          ['vendas', 'Minhas Vendas', BadgeCheck] as const,
        ]).map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2.5 text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2 border-b-2 -mb-px ${
              tab === key
                ? 'border-accent-amethyst text-accent-amethyst'
                : 'border-transparent text-secondary hover:text-primary'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </nav>

      {tab === 'catalogo' && <Catalog />}
      {tab === 'listings' && <MyListings />}
      {tab === 'vendas' && <MySales />}
    </div>
  );
}

function Catalog() {
  const [category, setCategory] = useState<string | null>(null);
  const [sort, setSort] = useState('popular');
  const [previewing, setPreviewing] = useState<MarketplaceListing | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['marketplace', category, sort],
    queryFn: () => marketplaceApi.list({ category: category || undefined, sort }),
  });

  const items = data?.listings ?? [];
  const categories = useMemo(
    () => Array.from(new Set(items.map((l) => l.category).filter(Boolean))) as string[],
    [items],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => setCategory(null)}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
            !category ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary hover:text-primary'
          }`}
        >
          Todos
        </button>
        {categories.map((c) => {
          const meta = CATEGORY_META[c];
          const Icon = meta?.Icon || Sparkles;
          return (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                category === c ? 'bg-accent-amethyst text-white' : 'bg-bg-surface text-secondary hover:text-primary'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {meta?.label || c}
            </button>
          );
        })}

        <div className="ml-auto">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="bg-bg-surface border border-border rounded-lg px-3 py-1.5 text-xs font-bold text-primary"
          >
            <option value="popular">Mais vendidos</option>
            <option value="recent">Mais recentes</option>
            <option value="rating">Melhor avaliados</option>
            <option value="price_asc">Preço: menor</option>
            <option value="price_desc">Preço: maior</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-72 bg-bg-surface rounded-3xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-secondary">
          Nenhum fluxo no marketplace ainda. Seja o primeiro a publicar!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((l) => (
            <ListingCard key={l.id} listing={l} onClick={() => setPreviewing(l)} />
          ))}
        </div>
      )}

      {previewing && (
        <DetailModal listingId={previewing.id} onClose={() => setPreviewing(null)} />
      )}
    </div>
  );
}

function ListingCard({ listing, onClick }: { listing: MarketplaceListing; onClick: () => void }) {
  const meta = listing.category ? CATEGORY_META[listing.category] : null;
  const Icon = meta?.Icon || Sparkles;
  return (
    <button
      onClick={onClick}
      className="bg-bg-surface border border-border rounded-3xl p-6 flex flex-col text-left hover:border-accent-amethyst/30 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl bg-bg-primary flex items-center justify-center ${meta?.color || 'text-accent-amethyst'}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="text-right">
          <div className="text-2xl font-black tabular-nums">R$ {listing.price_brl.toFixed(0)}</div>
          {listing.rating_count > 0 && (
            <div className="text-[10px] text-secondary mt-0.5">
              ★ {listing.rating_avg?.toFixed(1)} ({listing.rating_count})
            </div>
          )}
        </div>
      </div>

      <h3 className="font-black text-lg tracking-tight">{listing.title}</h3>
      <p className="text-[11px] text-secondary mt-1 line-clamp-2 flex-1">
        {listing.description}
      </p>

      <div className="flex items-center gap-3 mt-4 text-[11px] text-secondary">
        <span className="flex items-center gap-1">
          <Layers className="w-3 h-3" />
          {listing.node_count} nós
        </span>
        {listing.total_sales > 0 && (
          <>
            <span>·</span>
            <span>{listing.total_sales} vendas</span>
          </>
        )}
      </div>

      <div className="mt-4 flex items-center text-xs font-black uppercase tracking-widest text-accent-amethyst">
        Ver detalhes
        <ChevronRight className="w-3.5 h-3.5 ml-1" />
      </div>
    </button>
  );
}

function DetailModal({ listingId, onClose }: { listingId: number; onClose: () => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [pixData, setPixData] = useState<{
    qr_image: string; qr_text: string; expires_at: string; purchase_id: number;
  } | null>(null);
  const [appliedBlueprintId, setAppliedBlueprintId] = useState<number | null>(null);

  const { data: detail, isLoading } = useQuery({
    queryKey: ['marketplace-detail', listingId],
    queryFn: () => marketplaceApi.get(listingId),
  });

  const buyMut = useMutation({
    mutationFn: () => marketplaceApi.buy(listingId, 'pix'),
    onSuccess: (res) => {
      if (res.already_purchased) {
        toast.success('Você já comprou. Aplicando ao seu workspace…');
        if (res.applied_blueprint_id) {
          setAppliedBlueprintId(res.applied_blueprint_id);
        } else {
          applyMut.mutate(res.purchase_id);
        }
        return;
      }
      if (res.qr_code_image_url && res.qr_code_text && res.expires_at) {
        setPixData({
          qr_image: res.qr_code_image_url,
          qr_text: res.qr_code_text,
          expires_at: res.expires_at,
          purchase_id: res.purchase_id,
        });
      }
    },
    onError: handleApiError('Erro ao iniciar compra'),
  });

  const applyMut = useMutation({
    mutationFn: (purchaseId: number) => marketplaceApi.apply(purchaseId),
    onSuccess: (res) => {
      if (res.blueprint_id) {
        setAppliedBlueprintId(res.blueprint_id);
        toast.success('Fluxo importado pro seu workspace!');
        qc.invalidateQueries({ queryKey: ['marketplace-detail', listingId] });
      }
    },
    onError: handleApiError('Erro ao aplicar fluxo'),
  });

  if (pixData) {
    return (
      <PixModal
        pix={pixData}
        listingTitle={detail?.title || ''}
        onClose={() => { setPixData(null); onClose(); }}
        onPaid={() => {
          applyMut.mutate(pixData.purchase_id);
          setPixData(null);
        }}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-border flex items-start justify-between gap-3">
          <div className="flex-1">
            {isLoading ? (
              <div className="h-7 w-48 bg-bg-primary rounded animate-pulse" />
            ) : (
              <>
                <h2 className="text-xl font-black tracking-tight">{detail?.title}</h2>
                <p className="text-xs text-secondary mt-1">{detail?.description}</p>
              </>
            )}
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {isLoading ? (
            <div className="text-center text-secondary text-sm py-8">Carregando…</div>
          ) : detail ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Preço" value={`R$ ${detail.price_brl.toFixed(2)}`} />
                <Stat label="Vendas" value={String(detail.total_sales)} />
                <Stat
                  label="Avaliação"
                  value={detail.rating_count > 0 ? `${detail.rating_avg?.toFixed(1)} ★` : '—'}
                />
              </div>

              {appliedBlueprintId ? (
                <div className="bg-accent-amethyst/10 border border-accent-amethyst/30 rounded-2xl p-5">
                  <p className="text-sm font-bold mb-3">
                    ✦ Fluxo importado! Editar agora pra personalizar.
                  </p>
                  <button
                    onClick={() => navigate(`/flows/${appliedBlueprintId}`)}
                    className="w-full px-4 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest"
                  >
                    Abrir no Builder →
                  </button>
                </div>
              ) : detail.already_bought ? (
                <button
                  onClick={() => buyMut.mutate()}
                  disabled={buyMut.isPending || applyMut.isPending}
                  className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
                >
                  {applyMut.isPending ? 'Aplicando…' : 'Reaplicar ao Workspace'}
                </button>
              ) : (
                <button
                  onClick={() => buyMut.mutate()}
                  disabled={buyMut.isPending}
                  className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
                >
                  <QrCode className="w-4 h-4" />
                  {buyMut.isPending ? 'Gerando Pix…' : `Comprar por R$ ${detail.price_brl.toFixed(2)}`}
                </button>
              )}

              {detail.reviews.length > 0 && (
                <div>
                  <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary mb-3">
                    Avaliações ({detail.reviews.length})
                  </h3>
                  <div className="space-y-2">
                    {detail.reviews.map((r) => (
                      <div key={r.id} className="bg-bg-primary border border-border rounded-xl p-3">
                        <div className="flex items-center gap-1 text-amber-400 text-xs">
                          {'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}
                        </div>
                        {r.comment && (
                          <p className="text-xs text-primary mt-1.5">{r.comment}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-bg-primary border border-border rounded-xl p-3 text-center">
      <div className="text-[9px] font-black uppercase tracking-widest text-secondary">{label}</div>
      <div className="text-sm font-black mt-1 tabular-nums">{value}</div>
    </div>
  );
}

function PixModal({
  pix, listingTitle, onClose, onPaid,
}: {
  pix: { qr_image: string; qr_text: string; expires_at: string; purchase_id: number };
  listingTitle: string;
  onClose: () => void;
  onPaid: () => void;
}) {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(pix.qr_text);
    toast.success('Pix copiado!');
  };
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-md w-full overflow-hidden">
        <div className="p-6 border-b border-border flex items-start justify-between">
          <div>
            <h2 className="text-xl font-black tracking-tight">Pague com Pix</h2>
            <p className="text-xs text-secondary mt-1">{listingTitle}</p>
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div className="bg-white rounded-2xl p-4 flex justify-center">
            <img src={pix.qr_image} alt="QR Code Pix" className="w-56 h-56" />
          </div>
          <div className="bg-bg-primary border border-border rounded-xl p-3">
            <div className="text-[9px] font-black uppercase tracking-widest text-secondary mb-1">
              Pix copia-e-cola
            </div>
            <div className="font-mono text-[10px] break-all text-primary leading-relaxed">
              {pix.qr_text}
            </div>
          </div>
          <button
            onClick={copyToClipboard}
            className="w-full px-4 py-2.5 bg-bg-primary border border-border hover:border-accent-amethyst/30 rounded-xl text-xs font-bold flex items-center justify-center gap-2"
          >
            <Copy className="w-3.5 h-3.5" />
            Copiar código
          </button>
          <p className="text-[11px] text-secondary text-center">
            Expira em {new Date(pix.expires_at).toLocaleTimeString('pt-BR')}
          </p>
          <button
            onClick={onPaid}
            className="w-full px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4" />
            Já paguei — Aplicar fluxo
          </button>
          <p className="text-[10px] text-secondary text-center">
            (Aplica direto. Em breve detecção automática via webhook Mercado Pago.)
          </p>
        </div>
      </div>
    </div>
  );
}

function MyListings() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['my-listings'],
    queryFn: () => marketplaceApi.myListings(),
  });

  const items = data?.listings ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-xs text-secondary">
          Publique seus fluxos prontos. Você recebe <strong className="text-primary">70%</strong>{' '}
          de cada venda; Acássia retém 30%.
        </p>
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2.5 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center gap-2"
        >
          <Plus className="w-3.5 h-3.5" />
          Publicar fluxo
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-secondary text-sm">Carregando…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-secondary">
          Você ainda não publicou nenhum fluxo no marketplace.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((l) => <MyListingRow key={l.id} listing={l} />)}
        </div>
      )}

      {creating && (
        <CreateListingModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            qc.invalidateQueries({ queryKey: ['my-listings'] });
            setCreating(false);
          }}
        />
      )}
    </div>
  );
}

function MyListingRow({ listing }: { listing: MyListing }) {
  const statusColor = {
    pending_review: 'text-amber-400 bg-amber-400/10',
    active: 'text-emerald-400 bg-emerald-400/10',
    paused: 'text-secondary bg-bg-primary',
    removed: 'text-rose-400 bg-rose-400/10',
  }[listing.status] || 'text-secondary bg-bg-primary';
  const statusLabel = {
    pending_review: 'Em análise',
    active: 'Ativo',
    paused: 'Pausado',
    removed: 'Removido',
  }[listing.status] || listing.status;

  return (
    <div className="bg-bg-surface border border-border rounded-2xl p-5 flex items-start justify-between gap-4">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1.5">
          <h3 className="font-black text-base">{listing.title}</h3>
          <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${statusColor}`}>
            {statusLabel}
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-secondary">
          <span>R$ {listing.price_brl.toFixed(2)}</span>
          <span>·</span>
          <span>{listing.total_sales} vendas</span>
          <span>·</span>
          <span>R$ {listing.total_revenue_brl.toFixed(2)} faturados</span>
          {listing.rating_count > 0 && (
            <>
              <span>·</span>
              <span>★ {listing.rating_avg?.toFixed(1)}</span>
            </>
          )}
        </div>
        {listing.rejection_reason && (
          <div className="mt-2 text-[11px] text-rose-400 flex items-start gap-1.5">
            <AlertCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
            <span>Recusado: {listing.rejection_reason}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function CreateListingModal({
  onClose, onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [price, setPrice] = useState<string>('29');
  const [blueprintId, setBlueprintId] = useState<number | null>(null);

  const { data: blueprints } = useQuery({
    queryKey: ['blueprints'],
    queryFn: blueprintsApi.list,
  });

  const detailQ = useQuery({
    queryKey: ['blueprint-detail', blueprintId],
    queryFn: () => blueprintsApi.get(blueprintId!),
    enabled: blueprintId !== null,
  });

  const createMut = useMutation({
    mutationFn: () => {
      if (!detailQ.data) throw new Error('blueprint não carregado');
      return marketplaceApi.createListing({
        title: title.trim(),
        description: description.trim(),
        category: category || null,
        price_brl: Number(price),
        blueprint_json: detailQ.data.body,
      });
    },
    onSuccess: () => {
      toast.success('Listing enviado! Aguardando review da equipe.');
      onCreated();
    },
    onError: handleApiError('Erro ao publicar listing'),
  });

  const valid =
    title.trim().length >= 5 &&
    description.trim().length >= 30 &&
    Number(price) >= 9 && Number(price) <= 5000 &&
    blueprintId !== null && detailQ.data !== undefined;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl max-w-xl w-full max-h-[85vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-border flex items-start justify-between">
          <div>
            <h2 className="text-xl font-black tracking-tight">Publicar fluxo no Marketplace</h2>
            <p className="text-xs text-secondary mt-1">
              Vai pra análise antes de aparecer no catálogo.
            </p>
          </div>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          <Field label="Título" hint="Mínimo 5 caracteres.">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
              placeholder="Ex.: Fluxo de Tarot Amoroso 7 etapas"
            />
          </Field>

          <Field label="Descrição" hint="Mínimo 30 caracteres. Descreva o que o fluxo entrega.">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm resize-none"
              placeholder="Descreva claramente o que o fluxo faz, pra que tipo de cliente é, e o ticket médio que entrega."
            />
            <div className="text-[10px] text-secondary mt-1">{description.length} caracteres</div>
          </Field>

          <Field label="Categoria">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              <option value="">Sem categoria</option>
              <option value="amor">Amor</option>
              <option value="premium">Premium</option>
              <option value="astrologia">Astrologia</option>
              <option value="recuperacao">Recuperação</option>
            </select>
          </Field>

          <Field label="Preço (R$)" hint="Entre R$ 9 e R$ 5.000.">
            <input
              type="number"
              min={9}
              max={5000}
              step={1}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm tabular-nums"
            />
            <div className="text-[10px] text-secondary mt-1">
              Você recebe R$ {(Number(price) * 0.7).toFixed(2)} por venda · Acássia retém R$ {(Number(price) * 0.3).toFixed(2)}
            </div>
          </Field>

          <Field label="Fluxo a publicar" hint="Apenas blueprints do seu workspace.">
            <select
              value={blueprintId ?? ''}
              onChange={(e) => setBlueprintId(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm"
            >
              <option value="">Selecione…</option>
              {(blueprints ?? []).map((b) => (
                <option key={b.id} value={b.id}>{b.title}</option>
              ))}
            </select>
          </Field>
        </div>

        <div className="p-4 border-t border-border flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => createMut.mutate()}
            disabled={!valid || createMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2"
          >
            <ArrowRight className="w-4 h-4" />
            {createMut.isPending ? 'Enviando…' : 'Enviar pra review'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label, hint, children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="text-[10px] font-black uppercase tracking-widest text-secondary block mb-1.5">
        {label}
      </label>
      {children}
      {hint && <div className="text-[10px] text-secondary mt-1">{hint}</div>}
    </div>
  );
}

function MySales() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-sales'],
    queryFn: () => marketplaceApi.mySales(),
  });

  if (isLoading) {
    return <div className="text-center py-12 text-secondary text-sm">Carregando…</div>;
  }

  const sales = data?.sales ?? [];
  const summary = data?.summary ?? {};

  if (sales.length === 0) {
    return (
      <div className="text-center py-16 text-secondary">
        Nenhuma venda ainda. Publique seus fluxos pra começar a faturar.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-bg-surface border border-border rounded-2xl p-5">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">
            Vendas totais
          </div>
          <div className="text-3xl font-black tabular-nums">{summary.total_sales ?? 0}</div>
        </div>
        <div className="bg-bg-surface border border-border rounded-2xl p-5">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary mb-1">
            Receita líquida
          </div>
          <div className="text-3xl font-black tabular-nums">
            R$ {(summary.total_revenue_brl ?? 0).toFixed(2)}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-[10px] font-black uppercase tracking-widest text-secondary">
          Histórico de vendas
        </h3>
        {sales.map((s) => (
          <div
            key={s.id}
            className="bg-bg-surface border border-border rounded-xl p-4 flex items-center justify-between"
          >
            <div>
              <div className="text-xs font-bold">Listing #{s.listing_id}</div>
              <div className="text-[10px] text-secondary mt-0.5">
                {new Date(s.purchased_at).toLocaleString('pt-BR')}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-black tabular-nums text-emerald-400">
                +R$ {s.payout_brl.toFixed(2)}
              </div>
              <div className="text-[10px] text-secondary">
                bruto R$ {s.amount_brl.toFixed(2)} · taxa R$ {s.fee_brl.toFixed(2)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
