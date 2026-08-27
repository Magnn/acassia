import { Plus, X, Trash2, ChevronDown, CheckCircle2 } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

export interface Rule {
  var: string;
  op: string;
  value: string;
  custom_field?: string;
}

export type Logic = 'AND' | 'OR';

interface Props {
  rules: Rule[];
  logic: Logic;
  onRulesChange: (next: Rule[]) => void;
  onLogicChange: (next: Logic) => void;
}

export default function RuleBuilder({
  rules,
  logic,
  onRulesChange,
  onLogicChange,
}: Props) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const update = (i: number, patch: Partial<Rule>) => {
    const next = rules.slice();
    next[i] = { ...next[i], ...patch };
    onRulesChange(next);
  };
  const remove = (i: number) => {
    const next = rules.slice();
    next.splice(i, 1);
    onRulesChange(next);
  };
  const addSpecific = (varType: string) => {
    let op = 'equals';
    if (varType === 'etiqueta') op = 'contains';
    if (varType === 'horario') op = 'after';
    onRulesChange([...rules, { var: varType, op, value: '' }]);
    setIsMenuOpen(false);
  };

  const renderRuleContent = (r: Rule, i: number) => {
    const OPS_STANDARD = [
      { value: 'equals', label: 'Igual' },
      { value: 'not_equals', label: 'Diferente' },
      { value: 'contains', label: 'Contém' },
      { value: 'not_contains', label: 'Não Contém' },
    ];

    const getOpText = (op: string) => {
      if (op === 'equals') return 'igual a';
      if (op === 'not_equals') return 'diferente de';
      if (op === 'contains') return 'contém';
      if (op === 'not_contains') return 'não contém';
      return '';
    };

    if (r.var === 'etiqueta') {
      const ops = [
        { value: 'contains', label: 'Contém' },
        { value: 'not_contains', label: 'Não Contém' }
      ];
      return (
        <>
          <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit">
            {ops.map((op) => (
              <button
                key={op.value}
                onClick={() => update(i, { op: op.value })}
                className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
              >
                {op.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">Etiqueta {r.op === 'contains' ? 'Contém' : 'Não Contém'}</label>
            <div className="relative">
              <select
                value={r.value}
                onChange={(e) => update(i, { value: e.target.value })}
                className="w-full appearance-none rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm bg-white"
              >
                <option value="">Selecione uma etiqueta</option>
                <option value="Respondeu a primeira pergunta">🟢 Respondeu a primeira pergunta</option>
                <option value="Novo Lead">🟢 Novo Lead</option>
              </select>
              <div className="absolute inset-y-0 right-2 flex items-center gap-2 pointer-events-none">
                <X className="w-3.5 h-3.5 text-slate-400" />
                <ChevronDown className="w-4 h-4 text-slate-500" />
              </div>
            </div>
          </div>
        </>
      );
    }

    if (r.var === 'dia_semana') {
      const ops = [
        { value: 'equals', label: 'Igual' },
        { value: 'not_equals', label: 'Diferente' }
      ];
      return (
        <>
          <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit">
            {ops.map((op) => (
              <button
                key={op.value}
                onClick={() => update(i, { op: op.value })}
                className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
              >
                {op.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">Dia da semana {getOpText(r.op)}</label>
            <div className="relative">
              <select
                value={r.value}
                onChange={(e) => update(i, { value: e.target.value })}
                className="w-full appearance-none rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm bg-white"
              >
                <option value="">Selecione o dia</option>
                <option value="Domingo">Domingo</option>
                <option value="Segunda-Feira">Segunda-Feira</option>
                <option value="Terça-Feira">Terça-Feira</option>
                <option value="Quarta-Feira">Quarta-Feira</option>
                <option value="Quinta-Feira">Quinta-Feira</option>
                <option value="Sexta-Feira">Sexta-Feira</option>
                <option value="Sábado">Sábado</option>
              </select>
              <div className="absolute inset-y-0 right-2 flex items-center gap-2 pointer-events-none">
                <X className="w-3.5 h-3.5 text-slate-400" />
                <ChevronDown className="w-4 h-4 text-slate-500" />
              </div>
            </div>
          </div>
        </>
      );
    }

    if (r.var === 'horario') {
      const ops = [
        { value: 'before', label: 'Antes de' },
        { value: 'after', label: 'Depois de' }
      ];
      return (
        <>
          <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit">
            {ops.map((op) => (
              <button
                key={op.value}
                onClick={() => update(i, { op: op.value })}
                className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
              >
                {op.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">Horário {r.op === 'before' ? 'Antes de' : 'Depois de'}</label>
            <div className="relative">
              <input
                type="time"
                value={r.value}
                onChange={(e) => update(i, { value: e.target.value })}
                className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm"
              />
            </div>
          </div>
        </>
      );
    }

    if (['contact.ddd', 'contact.name', 'contact.first_name', 'chat.message'].includes(r.var)) {
      const titles: Record<string, string> = { 
        'contact.ddd': 'DDD', 
        'contact.name': 'Nome Completo', 
        'contact.first_name': 'Primeiro Nome',
        'chat.message': 'Mensagem do chat'
      };
      const title = titles[r.var];
      return (
        <>
          <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit">
            {OPS_STANDARD.map((op) => (
              <button
                key={op.value}
                onClick={() => update(i, { op: op.value })}
                className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
              >
                {op.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">{title} {getOpText(r.op)}</label>
            <input
              type="text"
              value={r.value}
              onChange={(e) => update(i, { value: e.target.value })}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm"
              placeholder={title}
            />
            {r.var === 'chat.message' && (
              <span className="text-[10.5px] text-blue-500 font-medium">Você pode usar o símbolo "|" para separar sinônimos das palavras.</span>
            )}
          </div>
        </>
      );
    }

    if (r.var === 'contact.custom' || r.var === 'flow.field') {
      const selectLabel = r.var === 'contact.custom' ? 'Selecione um campo de contato' : 'Selecione um campo de fluxo';
      return (
        <>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">{selectLabel}</label>
            <div className="relative">
              <select
                value={r.custom_field || ''}
                onChange={(e) => update(i, { custom_field: e.target.value })}
                className="w-full appearance-none rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm bg-white"
              >
                <option value="">Selecione um parametro</option>
                <option value="score">Score</option>
                <option value="origin">Origem</option>
              </select>
              <div className="absolute inset-y-0 right-2 flex items-center gap-2 pointer-events-none">
                <ChevronDown className="w-4 h-4 text-slate-500" />
              </div>
            </div>
          </div>
          
          <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit mt-1">
            {OPS_STANDARD.map((op) => (
              <button
                key={op.value}
                onClick={() => update(i, { op: op.value })}
                className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
              >
                {op.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">Campo de contato {getOpText(r.op)}</label>
            <input
              type="text"
              value={r.value}
              onChange={(e) => update(i, { value: e.target.value })}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm"
              placeholder="Valor a ser validado"
            />
            <span className="text-[10.5px] text-blue-500 font-medium">Você pode usar o símbolo "|" para separar sinônimos das palavras.</span>
          </div>
        </>
      );
    }

    if (r.var === 'webhook.data') {
      return (
        <>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">Caminho do dado(path)</label>
            <input
              type="text"
              value={r.custom_field || ''}
              onChange={(e) => update(i, { custom_field: e.target.value })}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm"
              placeholder="Ex: data.product.name"
            />
          </div>
          <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit mt-1">
            {OPS_STANDARD.map((op) => (
              <button
                key={op.value}
                onClick={() => update(i, { op: op.value })}
                className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
              >
                {op.label}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-semibold text-slate-800">Valor a ser comparado</label>
            <input
              type="text"
              value={r.value}
              onChange={(e) => update(i, { value: e.target.value })}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm"
              placeholder="Ex: Produto X"
            />
          </div>
        </>
      );
    }

    // Default Generic View
    return (
      <>
        <div className="flex flex-col gap-1.5">
          <label className="text-[12px] font-semibold text-slate-800">Selecione um campo de fluxo</label>
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded p-1">
            <input
              className="flex-1 bg-white text-[12px] p-1.5 rounded outline-none shadow-sm text-slate-700 font-mono"
              value={r.var}
              onChange={(e) => update(i, { var: e.target.value })}
              placeholder="Ex: GPT_IMC"
            />
          </div>
        </div>
        <div className="flex bg-slate-50 p-1 rounded-lg border border-slate-200 w-fit">
          {OPS_STANDARD.map((op) => (
            <button
              key={op.value}
              onClick={() => update(i, { op: op.value })}
              className={`px-4 py-1.5 text-[11px] font-semibold rounded-md transition-all ${r.op === op.value ? 'bg-white border-green-500 text-green-600 shadow-sm ring-1 ring-green-500' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'}`}
            >
              {op.label}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-[12px] font-semibold text-slate-800">Valor {getOpText(r.op)}</label>
          <input
            type="text"
            value={r.value}
            onChange={(e) => update(i, { value: e.target.value })}
            className="w-full rounded border border-slate-200 px-3 py-2 text-[13px] text-slate-800 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 shadow-sm"
          />
        </div>
      </>
    );
  };

  const getFooterLabel = (varName: string) => {
    if (varName === 'etiqueta') return 'Etiqueta';
    if (varName === 'dia_semana') return 'Dia da semana';
    if (varName === 'horario') return 'Horário';
    if (varName === 'contact.ddd') return 'DDD';
    if (varName === 'contact.name') return 'Nome Completo';
    if (varName === 'contact.first_name') return 'Primeiro Nome';
    if (varName === 'contact.custom') return 'Campos personalizados';
    if (varName === 'chat.message') return 'Mensagem do chat';
    if (varName === 'flow.field') return 'Validar campo de fluxo';
    if (varName === 'webhook.data') return 'Dados do webhook';
    return 'Validar variável';
  };

  return (
    <div className="space-y-4">
      {/* ── Regras Lógicas (Cards) ── */}
      <div className="space-y-2">
        <div 
          onClick={() => onLogicChange('AND')}
          className={`p-3 rounded-lg border-2 cursor-pointer transition-colors ${logic === 'AND' ? 'border-blue-500 bg-blue-50/50' : 'border-slate-200 bg-white hover:border-slate-300'}`}
        >
          <div className={`text-[12px] font-bold ${logic === 'AND' ? 'text-slate-800' : 'text-slate-700'}`}>Corresponde a TODAS condições</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Regra lógica</div>
        </div>

        <div 
          onClick={() => onLogicChange('OR')}
          className={`p-3 rounded-lg border-2 cursor-pointer transition-colors ${logic === 'OR' ? 'border-blue-500 bg-blue-50/50' : 'border-slate-200 bg-white hover:border-slate-300'}`}
        >
          <div className={`text-[12px] font-bold ${logic === 'OR' ? 'text-slate-800' : 'text-slate-700'}`}>Corresponde a QUALQUER uma das condições</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Regra lógica</div>
        </div>
      </div>

      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="w-full text-[12px] font-semibold py-2.5 rounded border border-slate-200 bg-white text-blue-500 hover:bg-slate-50 flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4 text-blue-500" />
          Adicionar condição
        </button>

        {isMenuOpen && (
          <div className="absolute top-full mt-2 w-full bg-white border border-slate-200 rounded-lg shadow-xl z-20 max-h-[300px] overflow-y-auto py-2">
            <div className="px-4 py-2">
              <span className="text-[11px] font-bold text-slate-400">Mais Usados</span>
            </div>
            <button onClick={() => addSpecific('etiqueta')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium">Etiqueta</button>
            <button onClick={() => addSpecific('dia_semana')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Dia da semana</button>
            <button onClick={() => addSpecific('horario')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Horário</button>
            
            <div className="px-4 py-2 mt-1">
              <span className="text-[11px] font-bold text-slate-400">Campos do contato</span>
            </div>
            <button onClick={() => addSpecific('contact.ddd')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium">DDD</button>
            <button onClick={() => addSpecific('contact.name')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Nome Completo</button>
            <button onClick={() => addSpecific('contact.first_name')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Primeiro Nome</button>
            <button onClick={() => addSpecific('contact.custom')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Campos personalizados</button>
            
            <div className="px-4 py-2 mt-1">
              <span className="text-[11px] font-bold text-slate-400">Utilitário</span>
            </div>
            <button onClick={() => addSpecific('chat.message')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium">Mensagem do chat</button>
            <button onClick={() => addSpecific('flow.field')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Validar campo de fluxo</button>
            <button onClick={() => addSpecific('webhook.data')} className="w-full text-left px-4 py-2 text-[13px] text-slate-700 hover:bg-slate-50 font-medium border-t border-slate-50">Dados do webhook</button>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {rules.map((r, i) => (
          <div key={i} className="rounded-lg border border-slate-200 bg-white overflow-hidden shadow-sm">
            <div className="p-3 space-y-3">
              {renderRuleContent(r, i)}
            </div>
            <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-t border-slate-200">
              <span className="text-[11px] font-semibold text-slate-700">{getFooterLabel(r.var)}</span>
              <button 
                onClick={() => remove(i)}
                className="text-red-500 hover:bg-red-100 p-1.5 rounded transition-colors"
                title="Remover Condição"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
