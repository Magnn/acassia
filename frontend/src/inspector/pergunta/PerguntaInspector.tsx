import React, { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { patchConfig, readNum, readStr, type InspectorProps } from '../helpers';
import { api } from '../../api/client';

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
  if (sec < 60) return `Resposta após ${Math.round(sec)}s usa a saída expirada`;
  if (sec < 3600) { const m = Math.round(sec / 60); return `Resposta após ${m} min usa a saída expirada`; }
  if (sec < 86400) { const h = Math.round(sec / 3600); return `Resposta após ${h}h usa a saída expirada`; }
  const d = Math.round(sec / 86400);
  return `Resposta após ${d} dia${d === 1 ? '' : 's'} usa a saída expirada`;
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
      const j = await api.get<{ ok: boolean; variables: Array<{ key: string }> }>('/api/flows/tenant/variables');
      if (j?.ok && Array.isArray(j.variables)) {
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
    <div className="space-y-5">
      {/* ── Intro ── */}
      <div className="space-y-3">
        <p className="text-[10px] text-slate-500 leading-relaxed">
          Esse bloco possibilita uma conversa humanizada com perguntas e respostas. A pergunta será enviada e o fluxo ficará pausado até o contato responder. Respostas recebidas após o prazo seguem pela saída expirada.
        </p>
        <p className="text-[10px] text-slate-500 leading-relaxed">
          <strong>Dica importante:</strong> você pode inserir apenas um "espaço" no campo "Faça uma pergunta", a pausa será ativada e nenhum texto será enviado ao contato. Assim, você poderá enviar perguntas por áudio na seguinte estrutura: Bloco com áudio → Bloco de pergunta configurado com "espaço".
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Configurar</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      {/* ── 1. Faça uma pergunta ── */}
      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center">
          <label className="text-[13px] font-semibold text-slate-800">Faça uma pergunta:</label>
          <button
            type="button"
            onClick={() => { setVarsOpen((v) => !v); if (!varsOpen) fetchVars(); }}
            className="text-[11px] font-bold text-blue-500 flex items-center gap-1 hover:text-blue-600 transition-colors"
          >
            {varsOpen ? '✕ Fechar' : '👁️ Campos Personalizados'}
          </button>
        </div>
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => onUpdate(patchConfig(node, { question: e.target.value, body: e.target.value }))}
          rows={4}
          className="w-full rounded border border-slate-200 p-2.5 text-[13px] text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors resize-y shadow-sm"
        />

        {/* Painel de variáveis */}
        {varsOpen && (
          <div className="bg-white mt-2 space-y-4">
            {loadingVars ? (
              <p className="text-[10px] text-slate-400 text-center py-2">Carregando...</p>
            ) : (
              <>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="h-px flex-1 bg-slate-200" />
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Campos de contato</span>
                    <div className="h-px flex-1 bg-slate-200" />
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {contactVars.map((k) => (
                      <button key={k} type="button" onClick={() => insertVar(k)} className="px-2 py-1.5 rounded bg-slate-50 border border-slate-200 text-slate-500 text-[10px] font-bold hover:bg-[#9333ea] hover:text-white hover:border-[#9333ea] transition-all truncate text-center shadow-sm">
                        {`{{${k}}}`}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="h-px flex-1 bg-slate-200" />
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Campos do fluxo</span>
                    <div className="h-px flex-1 bg-slate-200" />
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {flowVars.map((k) => (
                      <button key={k} type="button" onClick={() => insertVar(k)} className="px-2 py-1.5 rounded bg-[#16a34a] border border-[#16a34a] text-white text-[10px] font-bold hover:bg-[#15803d] transition-all truncate text-center shadow-sm">
                        {`{{${k}}}`}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* ── 2. Salvar resposta em campo de fluxo (opcional) ── */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[13px] font-semibold text-slate-800">Salvar resposta em um campo de fluxo (opcional)</label>
        <div className="flex items-center gap-2">
          <select
             className="flex-1 rounded border border-slate-200 bg-white px-3 py-2 text-[12px] text-slate-700 outline-none shadow-sm"
             value={saveField || ''}
             onChange={(e) => onUpdate(patchConfig(node, { save_to_flow_field: e.target.value, output_var: e.target.value }))}
          >
             {allFieldOptions.map((opt) => (
               <option key={opt.value} value={opt.value}>{opt.label}</option>
             ))}
          </select>
          <button 
             className="ml-1 flex items-center justify-center w-[30px] h-[30px] shrink-0 rounded border border-slate-200 bg-white text-slate-500 hover:bg-slate-50 transition-colors shadow-sm"
             onClick={() => setShowNewField(true)}
          >
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
        </div>

        {/* Modal de Campos Personalizados */}
        {showNewField && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="bg-white rounded-lg shadow-2xl w-full max-w-[500px] overflow-hidden flex flex-col">
              {/* Header Roxo */}
              <div className="bg-[#a855f7] px-5 py-4 flex items-center justify-between shrink-0">
                 <h2 className="text-white font-bold text-[18px]">Campos Personalizados</h2>
                 <button onClick={() => setShowNewField(false)} className="bg-white text-[#a855f7] hover:bg-slate-100 p-1 rounded-full transition-colors flex items-center justify-center">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                 </button>
              </div>

              {/* Body */}
              <div className="p-6 flex flex-col flex-1">
                 <div className="mb-5">
                    <span className="inline-block border border-[#a855f7] text-[#a855f7] px-3 py-1 rounded-full text-[11px] font-bold shadow-sm">
                       Campos de fluxo
                    </span>
                 </div>
                 
                 <div className="flex flex-col gap-4">
                    {/* Nome */}
                    <div className="flex flex-col gap-1.5">
                       <label className="text-[13px] font-bold text-slate-800 flex items-center gap-1">
                          Nome <span className="text-[10px] font-medium text-slate-500">(Máximo de 15 caracteres e apenas letras e _)</span>
                       </label>
                       <input 
                          type="text" 
                          maxLength={15}
                          value={newFieldName}
                          onChange={(e) => setNewFieldName(e.target.value.replace(/[^a-zA-Z_]/g, ''))}
                          placeholder="Nome do campo de fluxo"
                          className="w-full px-3 py-2.5 border border-slate-200 rounded-md text-[13px] outline-none focus:border-purple-500 text-slate-700"
                       />
                    </div>

                    {/* Tipo do campo */}
                    <div className="flex flex-col gap-1.5">
                       <label className="text-[13px] font-bold text-slate-800">Tipo do campo</label>
                       <select className="w-full px-3 py-2.5 border border-slate-200 rounded-md text-[13px] outline-none focus:border-purple-500 text-slate-700 bg-white">
                          <option value="Texto">Texto</option>
                          <option value="Número">Número</option>
                          <option value="Data/Hora">Data/Hora</option>
                       </select>
                    </div>

                    {/* Descrição */}
                    <div className="flex flex-col gap-1.5">
                       <label className="text-[13px] font-bold text-slate-800">Descrição</label>
                       <input 
                          type="text" 
                          placeholder="Descrição do campo de fluxo"
                          className="w-full px-3 py-2.5 border border-slate-200 rounded-md text-[13px] outline-none focus:border-purple-500 text-slate-700"
                       />
                    </div>
                 </div>

                 {/* Botões Ação */}
                 <div className="flex items-center gap-3 mt-8">
                    <button 
                       onClick={() => setShowNewField(false)}
                       className="flex-1 bg-[#ef4444] hover:bg-[#dc2626] text-white py-3 rounded text-[14px] font-bold transition-colors"
                    >
                       Cancelar
                    </button>
                    <button 
                       onClick={async () => {
                         if (!newFieldName.trim()) return;
                         try {
                           await api.post('/api/flows/tenant/variables', { key: newFieldName.trim(), value: '' });
                           await fetchVars();
                           onUpdate(patchConfig(node, { save_to_flow_field: newFieldName.trim(), output_var: newFieldName.trim() }));
                           setNewFieldName('');
                           setShowNewField(false);
                         } catch { /* ignore */ }
                       }}
                       disabled={!newFieldName.trim()}
                       className={`flex-1 py-3 rounded text-[14px] font-bold transition-colors ${newFieldName.trim() ? 'bg-[#10b981] hover:bg-[#059669] text-white' : 'bg-slate-200 text-slate-400 cursor-not-allowed'}`}
                    >
                       Salvar Campos
                    </button>
                 </div>

                 <p className="text-[10px] text-slate-400 mt-5 text-center leading-relaxed px-4">
                    Você pode utilizar palavras ou frases como palavra-chave. O fluxo será acionado quando o cliente enviar uma mensagem exatamente igual à palavra-chave. Uma dica é copiar o texto pronto que está configurado na sua campanha de mensagem.
                 </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Prazo da resposta</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      {/* ── 3. Bloco expira em ── */}
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setExpiryOpen((v) => !v)}
          className="w-full flex flex-col items-center justify-center py-4 rounded-lg border border-dashed border-red-400 hover:bg-red-50 transition-colors bg-white"
        >
          <span className="text-[13px] font-bold text-red-500">
            {expiryLabel(currentExpirySec)}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">
            Clique para configurar
          </span>
        </button>

        {expiryOpen && (
          <div className="p-3.5 bg-white border border-slate-200 rounded-lg space-y-3 mt-1 shadow-sm">
            <label className="text-[11px] font-bold text-slate-800">Tempo para expirar esse bloco</label>
            <div className="flex items-center gap-3 mt-2">
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
                className="flex-1 accent-[#9333ea] h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
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
                className="rounded border border-slate-200 bg-white px-2 py-1.5 text-[12px] font-medium text-slate-700 focus:outline-none focus:border-[#9333ea] w-24 shadow-sm"
              >
                <option value="minute">Minutos</option>
                <option value="hour">Horas</option>
                <option value="day">Dias</option>
              </select>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
