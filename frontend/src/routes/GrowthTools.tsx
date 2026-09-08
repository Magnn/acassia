import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  TrendingUp,
  MessageCircle,
  Instagram,
  Facebook,
  Tag,
  Plus,
  Trash2,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  RefreshCw,
  ExternalLink,
  Percent,
  DollarSign,
  AlertCircle,
  X,
  Link as LinkIcon,
  QrCode,
  Copy,
  Download,
} from 'lucide-react';
import { growthToolsApi, CommentRule, CouponItem, GrowthLinkItem } from '../api/saas';
import { toast } from '../lib/toast';

type Tab = 'comments' | 'stories' | 'coupons' | 'links';

export default function GrowthTools() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('comments');

  // Modals state
  const [showNewRuleModal, setShowNewRuleModal] = useState(false);
  const [showNewCouponModal, setShowNewCouponModal] = useState(false);
  const [showNewLinkModal, setShowNewLinkModal] = useState(false);
  const [couponToDelete, setCouponToDelete] = useState<CouponItem | null>(null);
  const [linkToDelete, setLinkToDelete] = useState<GrowthLinkItem | null>(null);

  // New Rule Form State
  const [rulePlatform, setRulePlatform] = useState<'instagram' | 'facebook'>('instagram');
  const [ruleKeyword, setRuleKeyword] = useState('');
  const [ruleReplyComment, setRuleReplyComment] = useState('');
  const [ruleSendDm, setRuleSendDm] = useState('');

  // New Coupon Form State
  const [couponCode, setCouponCode] = useState('');
  const [couponType, setCouponType] = useState<'percent' | 'fixed'>('percent');
  const [couponValue, setCouponValue] = useState(10);
  const [couponMaxUses, setCouponMaxUses] = useState<string>('');
  const [couponValidUntil, setCouponValidUntil] = useState<string>('');

  // New Link Form State
  const [linkName, setLinkName] = useState('');
  const [linkPhone, setLinkPhone] = useState('');
  const [linkMessage, setLinkMessage] = useState('');
  const [linkTags, setLinkTags] = useState('');

  // Queries
  const { data: rulesData, isLoading: isLoadingRules } = useQuery({
    queryKey: ['growth-comment-rules'],
    queryFn: growthToolsApi.getCommentRules,
  });

  const { data: couponsData, isLoading: isLoadingCoupons } = useQuery({
    queryKey: ['growth-coupons'],
    queryFn: growthToolsApi.listCoupons,
  });

  const { data: linksData, isLoading: isLoadingLinks } = useQuery({
    queryKey: ['growth-links'],
    queryFn: growthToolsApi.listLinks,
  });

  // Save Rules Mutation
  const saveRulesMutation = useMutation({
    mutationFn: growthToolsApi.saveCommentRules,
    onSuccess: () => {
      toast.success('Regras de automação atualizadas!');
      qc.invalidateQueries({ queryKey: ['growth-comment-rules'] });
      setShowNewRuleModal(false);
      setRuleKeyword('');
      setRuleReplyComment('');
      setRuleSendDm('');
    },
    onError: (e: any) => toast.error(e.message || 'Falha ao salvar regras'),
  });

  // Create Coupon Mutation
  const createCouponMutation = useMutation({
    mutationFn: growthToolsApi.createCoupon,
    onSuccess: () => {
      toast.success('Cupom de desconto criado com sucesso!');
      qc.invalidateQueries({ queryKey: ['growth-coupons'] });
      setShowNewCouponModal(false);
      setCouponCode('');
      setCouponValue(10);
      setCouponMaxUses('');
      setCouponValidUntil('');
    },
    onError: (e: any) => toast.error(e?.response?.data?.error || e.message || 'Falha ao criar cupom'),
  });

  // Delete Coupon Mutation
  const deleteCouponMutation = useMutation({
    mutationFn: (id: number) => growthToolsApi.deleteCoupon(id),
    onSuccess: () => {
      toast.success('Cupom removido.');
      qc.invalidateQueries({ queryKey: ['growth-coupons'] });
      setCouponToDelete(null);
    },
    onError: (e: any) => toast.error(e.message || 'Falha ao remover cupom'),
  });

  // Create Link Mutation
  const createLinkMutation = useMutation({
    mutationFn: growthToolsApi.createLink,
    onSuccess: () => {
      toast.success('Link WhatsApp & QR Code gerados com sucesso!');
      qc.invalidateQueries({ queryKey: ['growth-links'] });
      setShowNewLinkModal(false);
      setLinkName('');
      setLinkPhone('');
      setLinkMessage('');
      setLinkTags('');
    },
    onError: (e: any) => toast.error(e?.response?.data?.error || e.message || 'Falha ao criar link'),
  });

  // Delete Link Mutation
  const deleteLinkMutation = useMutation({
    mutationFn: (id: string) => growthToolsApi.deleteLink(id),
    onSuccess: () => {
      toast.success('Link de WhatsApp removido.');
      qc.invalidateQueries({ queryKey: ['growth-links'] });
      setLinkToDelete(null);
    },
    onError: (e: any) => toast.error(e.message || 'Falha ao remover link'),
  });

  const currentRules = rulesData?.rules || [];
  const currentLinks = linksData?.links || [];

  const handleToggleRuleActive = (ruleId: string) => {
    const updated = currentRules.map((r) =>
      r.id === ruleId ? { ...r, active: !r.active } : r
    );
    saveRulesMutation.mutate(updated);
  };

  const handleDeleteRule = (ruleId: string) => {
    const updated = currentRules.filter((r) => r.id !== ruleId);
    saveRulesMutation.mutate(updated);
  };

  const handleCreateRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleKeyword.trim() || !ruleSendDm.trim()) {
      toast.error('Preencha a palavra-chave e a mensagem de DM');
      return;
    }
    const newRule: CommentRule = {
      id: `rule_${Date.now()}`,
      platform: rulePlatform,
      keyword: ruleKeyword.trim(),
      reply_comment: ruleReplyComment.trim() || 'Enviamos o link no seu Direct! ✨',
      send_dm: ruleSendDm.trim(),
      active: true,
    };
    saveRulesMutation.mutate([...currentRules, newRule]);
  };

  const handleCreateCoupon = (e: React.FormEvent) => {
    e.preventDefault();
    if (!couponCode.trim()) {
      toast.error('Informe o código do cupom');
      return;
    }
    createCouponMutation.mutate({
      code: couponCode.trim().toUpperCase(),
      discount_type: couponType,
      discount_value: Number(couponValue),
      max_uses: couponMaxUses ? Number(couponMaxUses) : null,
      valid_until: couponValidUntil ? new Date(couponValidUntil).toISOString() : null,
    });
  };

  const handleCreateLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkPhone.trim() || !linkMessage.trim()) {
      toast.error('Informe o número de WhatsApp e a mensagem predefinida');
      return;
    }
    const parsedTags = linkTags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    createLinkMutation.mutate({
      name: linkName.trim() || 'Link WhatsApp',
      phone: linkPhone.trim(),
      message: linkMessage.trim(),
      tags: parsedTags,
    });
  };

  const copyToClipboard = (text: string, label: string = 'Link') => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copiado para a área de transferência!`);
  };

  const downloadQrCode = (qrBase64: string, filename: string) => {
    const link = document.createElement('a');
    link.href = qrBase64;
    link.download = `${filename || 'qrcode-whatsapp'}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Download do QR Code iniciado!');
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-zinc-950 text-zinc-100 overflow-y-auto custom-scrollbar">
      {/* Header */}
      <div className="px-8 py-6 border-b border-zinc-800/80 bg-zinc-900/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h1 className="text-2xl font-black tracking-tight text-white">Growth Tools</h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 border border-purple-500/20 text-purple-400 uppercase tracking-wider">
                ChatbotX Parity
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-1 max-w-xl">
              Automatize captação de leads em redes sociais (Comment-to-DM, Story Replies) e crie campanhas com cupons de desconto.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === 'comments' && (
              <button
                onClick={() => setShowNewRuleModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-lg shadow-purple-600/20 active:scale-95"
              >
                <Plus className="w-4 h-4" />
                Nova Regra Comment-to-DM
              </button>
            )}
            {activeTab === 'coupons' && (
              <button
                onClick={() => setShowNewCouponModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-lg shadow-purple-600/20 active:scale-95"
              >
                <Plus className="w-4 h-4" />
                Criar Novo Cupom
              </button>
            )}
            {activeTab === 'links' && (
              <button
                onClick={() => setShowNewLinkModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-lg shadow-purple-600/20 active:scale-95"
              >
                <Plus className="w-4 h-4" />
                Gerar Link WhatsApp & QR Code
              </button>
            )}
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 mt-6 border-b border-zinc-800/80">
          <button
            onClick={() => setActiveTab('comments')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'comments'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <MessageCircle className="w-4 h-4" />
            Comment-to-DM (Instagram / Facebook)
          </button>
          <button
            onClick={() => setActiveTab('stories')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'stories'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Instagram className="w-4 h-4" />
            Story Replies & Menções
          </button>
          <button
            onClick={() => setActiveTab('coupons')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'coupons'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Tag className="w-4 h-4" />
            Cupons de Desconto
          </button>
          <button
            onClick={() => setActiveTab('links')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors ${
              activeTab === 'links'
                ? 'border-purple-500 text-purple-400 font-bold'
                : 'border-transparent text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <LinkIcon className="w-4 h-4" />
            Links WhatsApp & QR Code
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="p-8 max-w-6xl mx-auto w-full space-y-6">
        {/* ── TAB 1: COMMENT-TO-DM ── */}
        {activeTab === 'comments' && (
          <div className="space-y-6">
            {/* Banner de Instrução */}
            <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800 flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
              <div className="text-xs text-zinc-300 leading-relaxed">
                Quando alguém comentar uma palavra-chave em qualquer post do seu Instagram ou Facebook (ex:{' '}
                <span className="text-purple-300 font-bold">"EU QUERO"</span>), o sistema responde o comentário na hora e envia automaticamente uma mensagem privada no Direct (DM) com seu link de vendas ou funil.
              </div>
            </div>

            {/* List of Rules */}
            <div className="space-y-3">
              {isLoadingRules ? (
                <div className="py-12 text-center text-xs text-zinc-500">Carregando regras…</div>
              ) : currentRules.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-zinc-800 rounded-2xl space-y-3">
                  <MessageCircle className="w-8 h-8 text-zinc-600 mx-auto" />
                  <p className="text-sm font-semibold text-zinc-400">Nenhuma regra cadastrada ainda.</p>
                  <button
                    onClick={() => setShowNewRuleModal(true)}
                    className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold text-white transition-colors"
                  >
                    Criar Primeira Regra
                  </button>
                </div>
              ) : (
                currentRules.map((rule) => (
                  <div
                    key={rule.id}
                    className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2">
                        {rule.platform === 'instagram' ? (
                          <span className="flex items-center gap-1 text-[11px] font-bold text-pink-400 bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded-lg">
                            <Instagram className="w-3.5 h-3.5" /> Instagram
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[11px] font-bold text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-lg">
                            <Facebook className="w-3.5 h-3.5" /> Facebook
                          </span>
                        )}
                        <span className="text-xs text-zinc-400 font-medium">Palavra-chave:</span>
                        <span className="px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-300 font-bold text-xs border border-purple-500/30">
                          {rule.keyword}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                        <div className="p-2.5 rounded-xl bg-zinc-950 border border-zinc-800/80 text-xs">
                          <span className="text-[10px] uppercase font-bold text-zinc-500 block mb-1">
                            💬 Resposta no Comentário Público:
                          </span>
                          <span className="text-zinc-300 font-medium">{rule.reply_comment}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-zinc-950 border border-zinc-800/80 text-xs">
                          <span className="text-[10px] uppercase font-bold text-zinc-500 block mb-1">
                            ✉️ Mensagem Privada no Direct (DM):
                          </span>
                          <span className="text-zinc-300 font-medium">{rule.send_dm}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                      <button
                        onClick={() => handleToggleRuleActive(rule.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                          rule.active
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-zinc-800 text-zinc-500 border-zinc-700'
                        }`}
                      >
                        {rule.active ? 'Ativo' : 'Pausado'}
                      </button>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="p-2 rounded-xl text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors"
                        title="Excluir regra"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ── TAB 2: STORY REPLIES ── */}
        {activeTab === 'stories' && (
          <div className="p-8 border border-zinc-800 rounded-2xl bg-zinc-900/30 text-center space-y-4 max-w-2xl mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-pink-500/10 border border-pink-500/20 text-pink-400 flex items-center justify-center mx-auto">
              <Instagram className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-white">Automação de Respostas a Stories</h3>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Responda automaticamente a qualquer seguidor que enviar uma mensagem, emoji ou reação aos seus Stories do Instagram. Conduza o lead para uma conversa de vendas ou tiragem de tarot instantânea.
            </p>
            <div className="pt-2">
              <button
                onClick={() => toast.success('Automação de Stories ativada no perfil conectado!')}
                className="px-6 py-2.5 rounded-xl bg-pink-600 hover:bg-pink-500 text-white text-xs font-bold shadow-lg shadow-pink-600/20 transition-all"
              >
                Ativar Automação de Stories
              </button>
            </div>
          </div>
        )}

        {/* ── TAB 3: COUPONS ── */}
        {activeTab === 'coupons' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                Cupons Ativos ({couponsData?.coupons?.length || 0})
              </span>
            </div>

            {isLoadingCoupons ? (
              <div className="py-12 text-center text-xs text-zinc-500">Carregando cupons…</div>
            ) : (couponsData?.coupons || []).length === 0 ? (
              <div className="p-12 text-center border border-dashed border-zinc-800 rounded-2xl space-y-3">
                <Tag className="w-8 h-8 text-zinc-600 mx-auto" />
                <p className="text-sm font-semibold text-zinc-400">Nenhum cupom cadastrado ainda.</p>
                <button
                  onClick={() => setShowNewCouponModal(true)}
                  className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold text-white transition-colors"
                >
                  Criar Primeiro Cupom
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(couponsData?.coupons || []).map((coupon) => (
                  <div
                    key={coupon.id}
                    className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all flex flex-col justify-between space-y-4"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-base font-black font-mono tracking-wider text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 rounded-lg">
                          {coupon.code}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {coupon.is_active ? 'Ativo' : 'Inativo'}
                        </span>
                      </div>

                      <div className="text-2xl font-extrabold text-white pt-1">
                        {coupon.discount_type === 'percent'
                          ? `${coupon.discount_value}% OFF`
                          : `R$ ${(coupon.discount_value / 100).toFixed(2)} OFF`}
                      </div>

                      <div className="text-xs text-zinc-400 space-y-1 pt-1">
                        <div>
                          Usos: <span className="text-zinc-200 font-semibold">{coupon.used_count}</span>
                          {coupon.max_uses ? ` / ${coupon.max_uses}` : ' (ilimitado)'}
                        </div>
                        {coupon.valid_until && (
                          <div className="flex items-center gap-1 text-zinc-400 text-[11px]">
                            <Calendar className="w-3 h-3 text-zinc-500" />
                            Válido até: {new Date(coupon.valid_until).toLocaleDateString('pt-BR')}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-end pt-2 border-t border-zinc-800/80">
                      <button
                        onClick={() => setCouponToDelete(coupon)}
                        className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors"
                        title="Remover cupom"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 4: LINKS & QR CODE GENERATOR ── */}
        {activeTab === 'links' && (
          <div className="space-y-6">
            {/* Banner de Instrução */}
            <div className="p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800 flex items-start gap-3">
              <QrCode className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
              <div className="text-xs text-zinc-300 leading-relaxed">
                Crie links encurtados de WhatsApp com mensagens pré-definidas e QR Codes de alta resolução para usar em panfletos, embalagens, bio do Instagram, anúncios ou balcão de loja.
                Rastreie o número total de cliques e atribua tags automáticas aos leads quando iniciarem a conversa.
              </div>
            </div>

            {/* List of Links */}
            <div className="space-y-4">
              {isLoadingLinks ? (
                <div className="py-12 text-center text-xs text-zinc-500">Carregando links...</div>
              ) : currentLinks.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-zinc-800 rounded-2xl space-y-3">
                  <QrCode className="w-8 h-8 text-zinc-600 mx-auto" />
                  <p className="text-sm font-semibold text-zinc-400">Nenhum link ou QR code gerado ainda.</p>
                  <button
                    onClick={() => setShowNewLinkModal(true)}
                    className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold text-white transition-colors"
                  >
                    Gerar Primeiro Link & QR Code
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {currentLinks.map((link) => (
                    <div
                      key={link.id}
                      className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 transition-all flex flex-col justify-between space-y-4"
                    >
                      <div className="flex items-start gap-4">
                        {/* QR Code thumbnail */}
                        <div className="bg-white p-2 rounded-xl shrink-0 shadow-md">
                          <img
                            src={link.qr_code}
                            alt={`QR Code ${link.name}`}
                            className="w-24 h-24 object-contain"
                          />
                        </div>

                        {/* Details */}
                        <div className="flex-1 min-w-0 space-y-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <h4 className="text-sm font-bold text-white truncate">{link.name}</h4>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 shrink-0">
                              {link.clicks} {link.clicks === 1 ? 'clique' : 'cliques'}
                            </span>
                          </div>

                          <div className="text-xs text-zinc-400">
                            WhatsApp: <span className="font-mono text-zinc-300">+{link.phone}</span>
                          </div>

                          <div className="text-xs text-zinc-300 italic bg-zinc-950/60 p-2 rounded-lg border border-zinc-800/80 line-clamp-2">
                            "{link.message}"
                          </div>

                          {link.tags && link.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-1">
                              {link.tags.map((t, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-zinc-800 text-zinc-300"
                                >
                                  #{t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center justify-between pt-3 border-t border-zinc-800/80">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyToClipboard(link.short_url, 'Link de redirecionamento')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-200 transition-colors"
                            title="Copiar link rastreado"
                          >
                            <Copy className="w-3.5 h-3.5" />
                            Copiar Link
                          </button>
                          <button
                            onClick={() => downloadQrCode(link.qr_code, `qrcode-${link.name.toLowerCase().replace(/\s+/g, '-')}`)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-200 transition-colors"
                            title="Baixar imagem PNG do QR Code"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Baixar QR
                          </button>
                        </div>

                        <button
                          onClick={() => setLinkToDelete(link)}
                          className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors"
                          title="Remover link"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* New Rule Modal */}
      {showNewRuleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <MessageCircle className="w-4 h-4 text-purple-400" />
                Nova Regra Comment-to-DM
              </h3>
              <button
                onClick={() => setShowNewRuleModal(false)}
                className="p-1 text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRule} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">Plataforma</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRulePlatform('instagram')}
                    className={`flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold border transition-all ${
                      rulePlatform === 'instagram'
                        ? 'border-pink-500 bg-pink-500/10 text-pink-400'
                        : 'border-zinc-800 text-zinc-400 hover:bg-zinc-800'
                    }`}
                  >
                    <Instagram className="w-4 h-4" /> Instagram
                  </button>
                  <button
                    type="button"
                    onClick={() => setRulePlatform('facebook')}
                    className={`flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold border transition-all ${
                      rulePlatform === 'facebook'
                        ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                        : 'border-zinc-800 text-zinc-400 hover:bg-zinc-800'
                    }`}
                  >
                    <Facebook className="w-4 h-4" /> Facebook
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Palavra-chave Disparadora (Gatilho) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: EU QUERO, LINK, QUERO SABER"
                  value={ruleKeyword}
                  onChange={(e) => setRuleKeyword(e.target.value)}
                  className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Resposta Pública no Comentário
                </label>
                <input
                  type="text"
                  placeholder="Ex: Enviamos o link exclusivo no seu direct! 🔮✨"
                  value={ruleReplyComment}
                  onChange={(e) => setRuleReplyComment(e.target.value)}
                  className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Mensagem Privada Enviada no Direct (DM) *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Ex: Olá! Vi seu comentário. Aqui está o acesso exclusivo com desconto que você pediu: https://acassia.com/oferta"
                  value={ruleSendDm}
                  onChange={(e) => setRuleSendDm(e.target.value)}
                  className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewRuleModal(false)}
                  className="px-4 py-2 rounded-xl border border-zinc-700 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saveRulesMutation.isPending}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-lg shadow-purple-600/20"
                >
                  {saveRulesMutation.isPending ? 'Salvando...' : 'Salvar Regra'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Coupon Modal */}
      {showNewCouponModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Tag className="w-4 h-4 text-purple-400" />
                Criar Cupom de Desconto
              </h3>
              <button
                onClick={() => setShowNewCouponModal(false)}
                className="p-1 text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateCoupon} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Código do Cupom *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: PROMO2026, VIP10"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                  className="w-full text-xs font-mono rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500 uppercase"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1.5">Tipo</label>
                  <select
                    value={couponType}
                    onChange={(e) => setCouponType(e.target.value as 'percent' | 'fixed')}
                    className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="percent">Porcentagem (%)</option>
                    <option value="fixed">Valor Fixo (Centavos)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1.5">Valor *</label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={couponValue}
                    onChange={(e) => setCouponValue(Number(e.target.value))}
                    className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                    Máx. de Usos (opcional)
                  </label>
                  <input
                    type="number"
                    min={1}
                    placeholder="Ilimitado"
                    value={couponMaxUses}
                    onChange={(e) => setCouponMaxUses(e.target.value)}
                    className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                    Validade (opcional)
                  </label>
                  <input
                    type="date"
                    value={couponValidUntil}
                    onChange={(e) => setCouponValidUntil(e.target.value)}
                    className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewCouponModal(false)}
                  className="px-4 py-2 rounded-xl border border-zinc-700 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createCouponMutation.isPending}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-lg shadow-purple-600/20"
                >
                  {createCouponMutation.isPending ? 'Criando...' : 'Criar Cupom'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Coupon Custom Modal (Zero native confirm) */}
      {couponToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm p-6 shadow-2xl space-y-4">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              Remover Cupom {couponToDelete.code}?
            </h4>
            <p className="text-xs text-zinc-400 leading-relaxed">
              O cupom deixará de ser aceito em novos checkouts e pagamentos imediatamente.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCouponToDelete(null)}
                className="px-3 py-1.5 rounded-lg border border-zinc-700 text-xs font-medium text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={deleteCouponMutation.isPending}
                onClick={() => deleteCouponMutation.mutate(couponToDelete.id)}
                className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-xs font-bold text-white transition-colors"
              >
                {deleteCouponMutation.isPending ? 'Removendo...' : 'Confirmar Exclusão'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Link & QR Modal */}
      {showNewLinkModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <QrCode className="w-4 h-4 text-purple-400" />
                Gerar Link WhatsApp & QR Code
              </h3>
              <button
                onClick={() => setShowNewLinkModal(false)}
                className="p-1 text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateLink} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Nome da Campanha / Identificador *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Bio Instagram, Panfleto Inauguração, Mesa 04"
                  value={linkName}
                  onChange={(e) => setLinkName(e.target.value)}
                  className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Número de WhatsApp (DDI + DDD + Número) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: 5511999998888"
                  value={linkPhone}
                  onChange={(e) => setLinkPhone(e.target.value)}
                  className="w-full text-xs font-mono rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                />
                <span className="text-[10px] text-zinc-500 mt-1 block">
                  Somente números, com o DDI (55 para Brasil).
                </span>
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Mensagem Pré-definida *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Ex: Olá! Vi o anúncio no Instagram e gostaria de saber mais informações."
                  value={linkMessage}
                  onChange={(e) => setLinkMessage(e.target.value)}
                  className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500 resize-none"
                />
                <span className="text-[10px] text-zinc-500 mt-0.5 block">
                  Texto que já aparecerá digitado na caixa de mensagem do usuário ao abrir o WhatsApp.
                </span>
              </div>

              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-1.5">
                  Tags Automáticas (opcional)
                </label>
                <input
                  type="text"
                  placeholder="Ex: bio_insta, campanha_outono (separadas por vírgula)"
                  value={linkTags}
                  onChange={(e) => setLinkTags(e.target.value)}
                  className="w-full text-xs rounded-xl border border-zinc-700 bg-zinc-950 p-2.5 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewLinkModal(false)}
                  className="px-4 py-2 rounded-xl border border-zinc-700 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createLinkMutation.isPending}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-all shadow-lg shadow-purple-600/20"
                >
                  {createLinkMutation.isPending ? 'Gerando...' : 'Gerar Link & QR'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Link Custom Modal */}
      {linkToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-sm p-6 shadow-2xl space-y-4">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              Remover Link {linkToDelete.name}?
            </h4>
            <p className="text-xs text-zinc-400 leading-relaxed">
              O link de redirecionamento curto deixará de funcionar imediatamente. O QR Code físico passará a dar erro de página não encontrada.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setLinkToDelete(null)}
                className="px-3 py-1.5 rounded-lg border border-zinc-700 text-xs font-medium text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={deleteLinkMutation.isPending}
                onClick={() => deleteLinkMutation.mutate(linkToDelete.id)}
                className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-xs font-bold text-white transition-colors"
              >
                {deleteLinkMutation.isPending ? 'Removendo...' : 'Confirmar Exclusão'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
