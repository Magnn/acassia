import React, { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { patchConfig, readNum, readStr, type InspectorProps } from '../helpers';

/* ── Constantes legado ──────────────────────────────────────────────── */
const BUILTIN_KEYS = [
  'lead.id', 'lead.telefone', 'lead.nome', 'lead.email',
  'tenant.slug', 'session.id',
];

const BUILTIN_FIELDS = [
  { value: '', label: 'Selecione um campo' },
  { value: 'resposta', label: 'resposta' },
  { value: 'resposta_pergunta', label: 'resposta_pergunta' },
  { value: 'lead.nome', label: 'lead.nome' },
  { value: 'lead.telefone', label: 'lead.telefone' },
  { value: 'lead.email', label: 'lead.email' },
];

const REPLY_MODES = [
  { v: 'texto_livre', label: 'Texto livre', icon: '💬', desc: 'O lead responde livremente' },
  { v: 'botoes', label: 'Botões rápidos', icon: '🔘', desc: 'Botões WhatsApp (máx. 3)' },
];

/* ── Helpers de expiração (idênticos ao dashboard.html) ── */
function splitExpiry(sec: number): { amt: number; unit: 'minute' | 'hour' | 'day' } {
  const s = Number.isFinite(sec) && sec > 0 ? sec : 3600;
  if (s < 3600 && s % 60 === 0) return { amt: Math.round(s / 60), unit: 'minute' };
  if (s < 86400 && s % 3600 === 0) return { amt: Math.round(s / 3600), unit: 'hour' };
  if (s % 86400 === 0) return { amt: Math.round(s / 86400), unit: 'day' };
  if (s < 3600) return { amt: Math.max(1, Math.round(s / 60)), unit: 'minute' };
  if (s < 86400) return { amt: Math.max(1, Math.round(s / 3600)), unit: 'hour' };
  return { amt: Math.max(1, Math.round(s / 86400)), unit: 'day' };
}

function expirySliderMax(unit: string) {
  if (unit === 'minute') return 120;
  if (unit === 'day') return 30;
  return 168; // horas
}

function expiryToSeconds(amt: number, unit: string) {
  const mult = unit === 'minute' ? 60 : unit === 'day' ? 86400 : 3600;
  return Math.max(60, Math.round(amt * mult));
}

function expiryLabel(sec: number) {
  if (sec < 60) return `Se não responder em ${Math.round(sec)}s`;
  if (sec < 3600) { const m = Math.round(sec / 60); return m <= 1 ? 'Se não responder em 1 min' : `Se não responder em ${m} min`; }
  if (sec < 86400) { const h = Math.round(sec / 3600); return h <= 1 ? 'Se não responder em 1h' : `Se não responder em ${h}h`; }
  const d = Math.round(sec / 86400);
  return d <= 1 ? 'Se não responder em 1 dia' : `Se não responder em ${d} dias`;
}

function isContactVar(k: string) {
  const s = k.toLowerCase();
  return s.startsWith('lead.') || /nome|sobrenome|telefone|email|phone|whatsapp|celular/.test(s);
}

/* ── Componente ─────────────────────────────────────────────────────── */
export default function PerguntaInspector({ node, onUpdate }: InspectorProps) {
  const cfg = node.data.config;

  /* Leitura com chaves legado */
  const question = readStr(cfg, 'question') || readStr(cfg, 'body') || readStr(cfg, 'question_text');
  const saveField = readStr(cfg, 'save_to_flow_field') || readStr(cfg, 'output_var');
  const rawSec = readNum(cfg, 'question_timeout_seconds');
  const timeoutSec = typeof rawSec === 'number' && rawSec > 0 ? rawSec : 3600;
  const replyMode = readStr(cfg, 'reply_mode') || 'texto_livre';
  const quickReplies = Array.isArray(cfg.quick_replies) ? (cfg.quick_replies as string[]) : [];

  /* ── State ── */
  const [varsOpen, setVarsOpen] = useState(false);
  const [tenantVars, setTenantVars] = useState<{ key: string }[]>([]);
  const [loadingVars, setLoadingVars] = useState(false);
  const [expiryOpen, setExpiryOpen] = useState(false);
  const [newFieldName, setNewFieldName] = useState('');
  const [showNewField, setShowNewField] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const ex0 = splitExpiry(timeoutSec);
  const [exUnit, setExUnit] = useState<'minute' | 'hour' | 'day'>(ex0.unit);
  const [exAmt, setExAmt] = useState(Math.max(1, Math.min(expirySliderMax(ex0.unit), ex0.amt)));

  /* ── Buscar variáveis do tenant ── */
  const fetchVars = useCallback(async () => {
    setLoadingVars(true);
    try {
      const res = await fetch('/api/flows/tenant/variables');
      const j = await res.json();
      if (res.ok && j?.ok && Array.isArray(j.variables)) {
        setTenantVars(j.variables.map((r: any) => ({ key: String(r.key || '').trim() })).filter((r: any) => r.key));
      }
    } catch { /* ignore */ }
    setLoadingVars(false);
  }, []);

  useEffect(() => { fetchVars(); }, [fetchVars]);

  const allVarKeys = useMemo(() => {
    const seen = new Set<string>();
    const keys: string[] = [];
    tenantVars.forEach((r) => { if (r.key && !seen.has(r.key)) { seen.add(r.key); keys.push(r.key); } });
    BUILTIN_KEYS.forEach((k) => { if (!seen.has(k)) { seen.add(k); keys.push(k); } });
    keys.sort((a, b) => a.localeCompare(b, 'pt'));
    return keys;
  }, [tenantVars]);

  const contactVars = useMemo(() => allVarKeys.filter(isContactVar), [allVarKeys]);
  const flowVars = useMemo(() => allVarKeys.filter((k) => !isContactVar(k)), [allVarKeys]);

  const allFieldOptions = useMemo(() => {
    const seen = new Set(BUILTIN_FIELDS.map((f) => f.value));
    const extra = tenantVars.filter((r) => r.key && !seen.has(r.key)).map((r) => ({ value: r.key, label: r.key }));
    if (saveField && !seen.has(saveField) && !extra.find((e) => e.value === saveField)) {
      extra.unshift({ value: saveField, label: saveField });
    }
    return [...BUILTIN_FIELDS, ...extra];
  }, [tenantVars, saveField]);

  /* ── Inserir variável no cursor ── */
  const insertVar = useCallback((key: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const before = ta.value.substring(0, ta.selectionStart);
    const after = ta.value.substring(ta.selectionEnd);
    const ins = `{{${key}}}`;
    const newVal = before + ins + after;
    onUpdate(patchConfig(node, { question: newVal, body: newVal }));
    setTimeout(() => { ta.focus(); ta.selectionStart = ta.selectionEnd = before.length + ins.length; }, 50);
  }, [node, onUpdate]);

  /* ── Expiry helpers ── */
  const updateExpiry = useCallback((amt: number, unit: string) => {
    onUpdate(patchConfig(node, { question_timeout_seconds: expiryToSeconds(amt, unit) }));
  }, [node, onUpdate]);

  const currentExpirySec = expiryToSeconds(exAmt, exUnit);

  return (
    <div className="space-y-4">

      {/* ── Intro (como o legado) ── */}
      <div className="rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-3 space-y-1.5">
        <p className="text-[11px] text-[#475569] leading-[1.5]">
          Este bloco envia uma <strong>pergunta</strong> ao contato e aguarda a resposta.
          O fluxo ficará <strong>pausado</strong> até que o contato responda ou até que o bloco expire.
        </p>
        <p className="text-[10px] text-[#94a3b8] leading-[1.45]">
          <strong>Dica:</strong> insira apenas um "espaço" no campo da pergunta para pausar sem enviar texto.
          Assim, você pode enviar perguntas por áudio: <em>Bloco com áudio → Bloco de pergunta configurado com "espaço"</em>.
        </p>
      </div>

      {/* ── 1. Faça uma pergunta ── */}
      <div className="rounded-xl border border-[#ff5722]/25 overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-[#ff5722]/8 to-[#ff5722]/3 border-b border-[#ff5722]/15">
          <div className="w-5 h-5 rounded-md bg-[#ff5722] flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">?</span>
          </div>
          <span className="text-[11px] font-bold text-[#ff5722] uppercase tracking-[0.06em]">
            Faça uma pergunta
          </span>
          <button
            type="button"
            onClick={() => { setVarsOpen((v) => !v); if (!varsOpen) fetchVars(); }}
            className={[
              'ml-auto flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold transition-colors border',
              varsOpen ? 'border-[#ff5722] bg-[#ff5722]/10 text-[#ff5722]' : 'border-[#e2e8f0] text-[#64748b] hover:border-[#ff5722]/50 hover:text-[#ff5722]',
            ].join(' ')}
          >
            {varsOpen ? '✕ Fechar' : '👁 Campos Personalizados'}
          </button>
        </div>
        <div className="p-3 space-y-2">
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => onUpdate(patchConfig(node, { question: e.target.value, body: e.target.value }))}
            rows={5}
            placeholder="Ex.: Qual o seu nome?"
            className="w-full rounded-[10px] border border-[#e2e8f0] bg-[#f1f5f9] px-2.5 py-2 text-[13px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-[#ff5722] focus:ring-[3px] focus:ring-[rgba(255,87,34,0.12)] focus:bg-white transition-colors resize-y min-h-[100px] max-h-[220px] leading-[1.45]"
            style={{ fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif" }}
          />
          <p className="text-[10px] text-[#94a3b8]">
            Use <code className="bg-[#f1f5f9] px-1 rounded text-[9px] font-mono">{'{{variavel}}'}</code> para personalizar.
          </p>

          {/* Painel de variáveis (Contact / Flow, como legado) */}
          {varsOpen && (
            <div className="rounded-lg border border-[#e2e8f0] bg-white p-2.5 space-y-2">
              {loadingVars ? (
                <p className="text-[10px] text-[#94a3b8] text-center py-2">Carregando variáveis...</p>
              ) : (
                <>
                  {/* Campos de contato */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <div className="h-px flex-1 bg-[#e2e8f0]" />
                      <span className="text-[9px] font-bold text-[#94a3b8] uppercase tracking-wider shrink-0">Campos de contato</span>
                      <div className="h-px flex-1 bg-[#e2e8f0]" />
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {contactVars.length === 0 ? (
                        <span className="text-[10px] text-[#cbd5e1]">Nenhuma variável nesta categoria.</span>
                      ) : contactVars.map((k) => (
                        <button key={k} type="button" onClick={() => insertVar(k)}
                          className="px-2 py-0.5 rounded-full bg-[#2563eb]/10 text-[#2563eb] text-[10px] font-mono font-medium hover:bg-[#2563eb]/20 transition-colors cursor-pointer">
                          {`{{${k}}}`}
                        </button>
                      ))}
                    </div>
                  </div>
                  {/* Campos do fluxo */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <div className="h-px flex-1 bg-[#e2e8f0]" />
                      <span className="text-[9px] font-bold text-[#94a3b8] uppercase tracking-wider shrink-0">Campos do fluxo</span>
                      <div className="h-px flex-1 bg-[#e2e8f0]" />
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {flowVars.length === 0 ? (
                        <span className="text-[10px] text-[#cbd5e1]">Nenhuma variável nesta categoria.</span>
                      ) : flowVars.map((k) => (
                        <button key={k} type="button" onClick={() => insertVar(k)}
                          className="px-2 py-0.5 rounded-full bg-[#10b981]/10 text-[#10b981] text-[10px] font-mono font-medium hover:bg-[#10b981]/20 transition-colors cursor-pointer">
                          {`{{${k}}}`}
                        </button>
                      ))}
                    </div>
                  </div>
                  <p className="text-[9px] text-[#94a3b8] text-center pt-1">Toque numa variável para inserir na posição do cursor.</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── 2. Salvar resposta em campo de fluxo (dropdown + criar novo) ── */}
      <div className="rounded-xl border border-[#2563eb]/25 overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-[#2563eb]/8 to-[#2563eb]/3 border-b border-[#2563eb]/15">
          <div className="w-5 h-5 rounded-md bg-[#2563eb] flex items-center justify-center">
            <span className="text-white text-[10px]">📦</span>
          </div>
          <span className="text-[11px] font-bold text-[#2563eb] uppercase tracking-[0.06em]">
            Salvar resposta em campo
          </span>
          <span className="text-[10px] text-[#94a3b8] ml-auto">(opcional)</span>
        </div>
        <div className="p-3 space-y-2">
          <div className="flex items-center gap-1.5">
            <select
              value={saveField}
              onChange={(e) => {
                const v = e.target.value;
                onUpdate(patchConfig(node, { save_to_flow_field: v || undefined }));
              }}
              className="flex-1 rounded-[10px] border border-[#e2e8f0] bg-[#f1f5f9] px-2.5 py-[7px] text-[13px] text-slate-800 focus:outline-none focus:border-[#2563eb] focus:ring-[3px] focus:ring-[rgba(37,99,235,0.12)] focus:bg-white transition-colors"
              style={{ fontFamily: "'Inter', ui-sans-serif, system-ui, sans-serif" }}
            >
              {allFieldOptions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setShowNewField((v) => !v)}
              className="w-8 h-8 rounded-lg border border-[#e2e8f0] bg-white flex items-center justify-center text-[#2563eb] hover:bg-[#2563eb]/10 hover:border-[#2563eb]/50 transition-colors text-[14px] font-bold shrink-0"
              title="Adicionar campo no catálogo do tenant"
            >+</button>
          </div>

          {/* Form inline para criar campo novo */}
          {showNewField && (
            <div className="flex items-center gap-1.5 p-2 rounded-lg border border-[#2563eb]/25 bg-[#2563eb]/5">
              <input
                type="text"
                value={newFieldName}
                onChange={(e) => setNewFieldName(e.target.value.replace(/[^a-zA-Z0-9_.]/g, '').toLowerCase())}
                placeholder="nome_do_campo"
                className="flex-1 rounded-lg border border-[#e2e8f0] bg-white px-2 py-1 text-[12px] text-slate-800 font-mono placeholder:text-slate-400 focus:outline-none focus:border-[#2563eb]"
              />
              <button
                type="button"
                onClick={async () => {
                  if (!newFieldName.trim()) return;
                  try {
                    await fetch('/api/flows/tenant/variables', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ key: newFieldName.trim(), value: '' }),
                    });
                    await fetchVars();
                    onUpdate(patchConfig(node, { save_to_flow_field: newFieldName.trim() }));
                    setNewFieldName('');
                    setShowNewField(false);
                  } catch { /* ignore */ }
                }}
                disabled={!newFieldName.trim()}
                className="px-3 py-1 rounded-lg bg-[#2563eb] text-white text-[11px] font-semibold hover:bg-[#1d4ed8] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >Criar</button>
            </div>
          )}

          {saveField && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#2563eb]/8 border border-[#2563eb]/20">
              <span className="text-[10px] text-[#2563eb] font-medium">
                A resposta será salva em <code className="bg-white px-1 rounded text-[9px] font-mono font-bold">{`{{${saveField}}}`}</code>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── 3. Modo de resposta ── */}
      <div className="rounded-xl border border-[#e2e8f0] overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 bg-[#f8fafc] border-b border-[#e2e8f0]">
          <span className="text-[11px] font-bold text-[#475569] uppercase tracking-[0.06em]">
            Modo de Resposta
          </span>
        </div>
        <div className="p-3 space-y-3">
          <div className="grid grid-cols-2 gap-1.5">
            {REPLY_MODES.map((m) => (
              <button
                key={m.v}
                type="button"
                onClick={() => onUpdate(patchConfig(node, { reply_mode: m.v }))}
                className={[
                  'flex flex-col items-center gap-1 py-2.5 px-2 rounded-lg border text-center transition-all',
                  replyMode === m.v
                    ? 'border-[#ff5722] bg-[#ff5722]/8 text-[#ff5722] shadow-sm'
                    : 'border-[#e2e8f0] bg-white text-[#64748b] hover:border-[#cbd5e1] hover:bg-[#f8fafc]',
                ].join(' ')}
              >
                <span className="text-[18px]">{m.icon}</span>
                <span className="text-[10px] font-semibold">{m.label}</span>
                <span className="text-[9px] opacity-70">{m.desc}</span>
              </button>
            ))}
          </div>

          {/* Botões rápidos — só quando reply_mode = botoes */}
          {replyMode === 'botoes' && (
            <div className="space-y-2 pt-1">
              {quickReplies.map((reply, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-[#10b981] text-white text-[9px] font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                  <input type="text" value={reply} maxLength={20}
                    onChange={(e) => { const next = [...quickReplies]; next[i] = e.target.value; onUpdate(patchConfig(node, { quick_replies: next })); }}
                    placeholder={`Opção ${i + 1}`}
                    className="flex-1 rounded-lg border border-[#e2e8f0] bg-[#f1f5f9] px-2.5 py-1.5 text-[12px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-[#10b981] focus:ring-[2px] focus:ring-[rgba(16,185,129,0.12)] focus:bg-white transition-colors" />
                  <button type="button" onClick={() => { const next = quickReplies.filter((_, j) => j !== i); onUpdate(patchConfig(node, { quick_replies: next })); }}
                    className="w-6 h-6 rounded-md flex items-center justify-center text-[#94a3b8] hover:text-red-500 hover:bg-red-50 transition-colors" title="Remover">×</button>
                </div>
              ))}
              {quickReplies.length < 3 && (
                <button type="button" onClick={() => onUpdate(patchConfig(node, { quick_replies: [...quickReplies, ''] }))}
                  className="w-full py-2 rounded-lg border-2 border-dashed border-[#e2e8f0] text-[11px] font-semibold text-[#94a3b8] hover:border-[#10b981] hover:text-[#10b981] hover:bg-[#10b981]/5 transition-all">
                  + Adicionar opção
                </button>
              )}
              <p className="text-[10px] text-[#94a3b8]">Botões do WhatsApp. Máx. 3 opções, 20 caracteres cada.</p>
            </div>
          )}
        </div>
      </div>

      {/* ── 4. Bloco expira em (minutos/horas/dias com slider, como legado) ── */}
      <div className="rounded-xl border border-[#ef4444]/25 overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-[#ef4444]/8 to-[#ef4444]/3 border-b border-[#ef4444]/15">
          <div className="w-5 h-5 rounded-md bg-[#ef4444] flex items-center justify-center">
            <span className="text-white text-[10px]">⏱️</span>
          </div>
          <span className="text-[11px] font-bold text-[#ef4444] uppercase tracking-[0.06em]">
            Bloco Expira em
          </span>
        </div>

        {/* Card clicável (como legado) */}
        <button
          type="button"
          onClick={() => setExpiryOpen((v) => !v)}
          className="w-full flex flex-col items-center py-3 px-3 text-center hover:bg-[#fef2f2]/50 transition-colors border-b border-[#ef4444]/10"
        >
          <span className="text-[13px] font-bold text-[#ef4444]">
            {expiryLabel(currentExpirySec)}
          </span>
          <span className="text-[10px] text-[#94a3b8]">
            {expiryOpen ? 'Fechar configuração' : 'Clique para configurar'}
          </span>
        </button>

        {/* Painel expansível com slider + unit selector (como legado) */}
        {expiryOpen && (
          <div className="p-3 space-y-2">
            <p className="text-[10px] text-[#475569] font-semibold">Tempo para expirar esse bloco</p>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={1}
                max={expirySliderMax(exUnit)}
                step={1}
                value={exAmt}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setExAmt(v);
                  updateExpiry(v, exUnit);
                }}
                className="flex-1"
                style={{ accentColor: '#ef4444' }}
              />
              <select
                value={exUnit}
                onChange={(e) => {
                  const newUnit = e.target.value as 'minute' | 'hour' | 'day';
                  const oldMult = exUnit === 'minute' ? 60 : exUnit === 'day' ? 86400 : 3600;
                  const sec = Math.max(60, Math.round(exAmt * oldMult));
                  const newMult = newUnit === 'minute' ? 60 : newUnit === 'day' ? 86400 : 3600;
                  const newMax = expirySliderMax(newUnit);
                  const newAmt = Math.max(1, Math.min(newMax, Math.round(sec / newMult)));
                  setExUnit(newUnit);
                  setExAmt(newAmt);
                  updateExpiry(newAmt, newUnit);
                }}
                className="rounded-lg border border-[#e2e8f0] bg-[#f1f5f9] px-2 py-1 text-[12px] text-[#475569] focus:outline-none focus:border-[#ef4444]"
              >
                <option value="minute">Minutos</option>
                <option value="hour">Horas</option>
                <option value="day">Dias</option>
              </select>
            </div>
            <div className="flex items-start gap-1.5 px-2.5 py-2 rounded-lg bg-[#fef2f2] border border-[#fecaca]">
              <span className="text-[10px] leading-tight text-[#991b1b]">
                ⚠️ {expiryLabel(currentExpirySec)} — o fluxo seguirá pela saída de timeout (vermelha).
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
