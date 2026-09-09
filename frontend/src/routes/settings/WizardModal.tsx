import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Check, AlertTriangle, Save } from 'lucide-react';
import { api } from '../../api/client';
import { toast } from '../../lib/toast';

const WaLogo = ({ className = 'w-8 h-8' }: { className?: string }) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
  </svg>
);

const MetaLogo = ({ className = 'w-5 h-5' }: { className?: string }) => (
  <svg viewBox="0 0 512 512" className={className} fill="currentColor">
    <path d="M412.7 163.2c-28.3 0-51.7 25.9-82.7 75.2l-13.6 21.5-12.2-20.4c-36.1-60.3-60-76.3-91.8-76.3-35.3 0-65.7 28.4-89.4 82C98.7 300 83.6 377.1 83.6 420c0 31.5 11.1 51.7 33.6 51.7 14.9 0 26.6-8.2 44.9-37.7l41-66.3 8.9-14.6 4.8-8 8.6-14.4c17.4-29.4 27.2-42.2 42.3-42.2 12.2 0 20.6 9.9 33 33.9l6 11.8 4.1 8.3 4.1 8.4 8.4 17.3c18.3 37.3 30.3 52 51.2 52 22.5 0 33.6-20.2 33.6-51.7 0-43-14.7-120-53.4-175.1-23.7-33.8-51.6-57.9-77.7-57.9"/>
  </svg>
);

declare global {
  interface Window {
    fbAsyncInit: () => void;
    FB: any;
  }
}

type Step = 'type' | 'meta_req' | 'meta_costs' | 'meta_coex' | 'meta_nickname' | 'evolution_form' | 'openwa_form';

export function WizardModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>('type');
  
  const emptyForm = {
    nickname: '', provider: 'meta_cloud', phone_display: '',
    meta_phone_number_id: '', meta_waba_id: '', meta_access_token: '',
    evolution_server_url: '', evolution_instance: '', evolution_api_key: '',
    openwa_server_url: '', openwa_session_id: '', openwa_api_key: ''
  };
  const [form, setForm] = useState(emptyForm);

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/saas/devices/', d),
    onSuccess: () => { 
      toast.success('Dispositivo criado!'); 
      qc.invalidateQueries({ queryKey: ['devices'] }); 
      onClose(); 
    },
    onError: (e: any) => toast.error(e?.message || 'Erro ao criar'),
  });

  // Carrega o SDK do Facebook (Embedded Signup)
  useEffect(() => {
    window.fbAsyncInit = function() {
      window.FB.init({
        appId            : '1114684347304934', // App ID da Meta fornecido
        autoLogAppEvents : true,
        xfbml            : true,
        version          : 'v20.0'
      });
    };

    if (document.getElementById('facebook-jssdk')) return;
    const script = document.createElement('script');
    script.id = 'facebook-jssdk';
    script.src = 'https://connect.facebook.net/pt_BR/sdk.js';
    document.body.appendChild(script);
  }, []);

  const launchWhatsAppSignup = () => {
    if (!window.FB) {
      toast.error('SDK do Facebook ainda não carregou.');
      return;
    }
    
    // ATENÇÃO: Substitua 'SEU_CONFIG_ID' pelo ID da configuração do Login do WhatsApp Business
    window.FB.login((response: any) => {
      if (response.authResponse) {
        const accessToken = response.authResponse.accessToken;
        const code = response.authResponse.code;
        toast.success('Autenticado com a Meta! Defina um apelido para salvar.');
        
        // Salva os dados retornados e vai para a tela de definir o apelido
        setForm(f => ({ ...f, meta_access_token: accessToken || code }));
        setStep('meta_nickname');
      } else {
        toast.error('Login cancelado ou não autorizado.');
      }
    }, {
      config_id: 'SEU_CONFIG_ID', // Requerido para Embedded Signup
      response_type: 'code',    
      override_default_response_type: true,
      extras: {
        setup: { /* Opções extras de setup */ }
      }
    });
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 font-sans" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="bg-[#f0f2f5] rounded-xl shadow-2xl max-w-[600px] w-full overflow-hidden relative">
        
        {/* Header - Purple */}
        <div className="bg-[#9300ea] text-white px-5 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">Escolha o tipo de conexão</h2>
          <button onClick={onClose} className="w-7 h-7 bg-white text-black rounded-full flex items-center justify-center hover:bg-gray-100 transition shadow-sm">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-8 relative">
          
          {step === 'type' && (
            <div className="space-y-4">
              <button onClick={() => { setForm(f => ({...f, provider: 'evolution'})); setStep('evolution_form'); }} className="w-full flex items-center gap-4 p-5 rounded-xl border border-gray-200 hover:border-[#25D366] shadow-sm hover:shadow-md transition bg-white text-left">
                <WaLogo className="w-10 h-10 text-[#25D366]" />
                <div>
                  <span className="text-lg font-bold text-gray-800 block">WhatsApp Business</span>
                  <span className="text-xs text-gray-500">Conexão via QR Code com Evolution API</span>
                </div>
              </button>
              <button onClick={() => { setForm(f => ({...f, provider: 'openwa'})); setStep('openwa_form'); }} className="w-full flex items-center gap-4 p-5 rounded-xl border border-gray-200 hover:border-emerald-500 shadow-sm hover:shadow-md transition bg-white text-left">
                <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-black text-sm flex-shrink-0 shadow-sm">WA</div>
                <div>
                  <span className="text-lg font-bold text-gray-800 block">OpenWA / Self-Hosted</span>
                  <span className="text-xs text-gray-500">Gateway wa-automate: áudio PTT nativo e proteção contra conflito</span>
                </div>
              </button>
              <button onClick={() => { setForm(f => ({...f, provider: 'meta_cloud'})); setStep('meta_req'); }} className="w-full flex items-center gap-4 p-5 rounded-xl border border-gray-200 hover:border-[#0082FB] shadow-sm hover:shadow-md transition bg-white text-left">
                <MetaLogo className="w-10 h-10 text-[#0082FB]" />
                <div>
                  <span className="text-lg font-bold text-gray-800 block">API Oficial</span>
                  <span className="text-xs text-gray-500">Meta Cloud API (Graph API) oficial</span>
                </div>
              </button>
            </div>
          )}

          {step === 'meta_req' && (
            <div className="mt-4 bg-[#f4f7fe] rounded-2xl p-6 border border-gray-200 shadow-sm relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[#0082FB] text-white px-5 py-1.5 rounded-full flex items-center gap-2 text-sm font-bold shadow-md">
                <MetaLogo className="w-4 h-4" /> Requisitos obrigatórios
              </div>
              <div className="space-y-6 pt-6">
                <div className="flex gap-3">
                  <div className="w-5 h-5 rounded bg-[#25D366] text-white flex items-center justify-center flex-shrink-0 mt-0.5"><Check className="w-3.5 h-3.5" strokeWidth={3} /></div>
                  <div>
                    <h4 className="font-bold text-gray-900 text-[15px]">Business Manager verificado</h4>
                    <p className="text-[13px] text-gray-600 mt-1">Sua Business Manager (BM) deve estar verificada pela Meta.</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-5 h-5 rounded bg-[#25D366] text-white flex items-center justify-center flex-shrink-0 mt-0.5"><Check className="w-3.5 h-3.5" strokeWidth={3} /></div>
                  <div>
                    <h4 className="font-bold text-gray-900 text-[15px]">CNPJ compatível com a categoria do WhatsApp</h4>
                    <p className="text-[13px] text-gray-600 mt-1">A atividade econômica (CNAE) do CNPJ vinculado à BM deve ser coerente com a categoria escolhida para o WhatsApp.</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-5 h-5 rounded bg-[#25D366] text-white flex items-center justify-center flex-shrink-0 mt-0.5"><Check className="w-3.5 h-3.5" strokeWidth={3} /></div>
                  <div>
                    <h4 className="font-bold text-gray-900 text-[15px]">Número apto para API</h4>
                    <p className="text-[13px] text-gray-600 mt-1">O número não pode estar ativo em outra API ou vinculado a outro provedor (BSP). Se estiver migrando de plataforma, a desconexão deve ser feita corretamente. Acesse dicas de migração.</p>
                  </div>
                </div>
              </div>
              <div className="mt-8 flex justify-end">
                <button onClick={() => setStep('meta_costs')} className="bg-[#0082FB] hover:bg-blue-600 text-white font-bold py-2 px-8 rounded-full shadow-md transition">Próximo</button>
              </div>
            </div>
          )}

          {step === 'meta_costs' && (
            <div className="mt-4 bg-[#f4f7fe] rounded-2xl p-6 border border-gray-200 shadow-sm relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[#0082FB] text-white px-5 py-1.5 rounded-full flex items-center gap-2 text-sm font-bold shadow-md">
                <MetaLogo className="w-4 h-4" /> Custos e cobranças
              </div>
              
              <div className="pt-6">
                <h4 className="font-bold text-gray-900 text-[15px] flex items-center gap-2 mb-2">
                  <span className="text-amber-500">⚠️</span> A Lailla não cobra pelas mensagens enviadas via API Oficial.
                </h4>
                <p className="text-[13px] text-gray-600 mb-6">As cobranças de conversas (marketing, utilidade, autenticação e serviço) são feitas diretamente pela Meta.</p>

                <h4 className="font-bold text-gray-900 text-[15px] mb-3">Você deve:</h4>
                <div className="space-y-4">
                  <div className="flex gap-3 items-center">
                    <div className="w-5 h-5 rounded bg-[#25D366] text-white flex items-center justify-center flex-shrink-0"><Check className="w-3.5 h-3.5" strokeWidth={3} /></div>
                    <span className="text-[13px] text-gray-600 font-medium">Configurar uma forma de pagamento na sua Business Manager</span>
                  </div>
                  <div className="flex gap-3 items-center">
                    <div className="w-5 h-5 rounded bg-[#25D366] text-white flex items-center justify-center flex-shrink-0"><Check className="w-3.5 h-3.5" strokeWidth={3} /></div>
                    <span className="text-[13px] text-gray-600 font-medium">Acompanhar seus custos pelo Gerenciador de Negócios da Meta</span>
                  </div>
                </div>
              </div>

              <div className="mt-8 flex justify-end">
                <button onClick={() => setStep('meta_coex')} className="bg-[#0082FB] hover:bg-blue-600 text-white font-bold py-2 px-8 rounded-full shadow-md transition">Próximo</button>
              </div>
            </div>
          )}

          {step === 'meta_coex' && (
            <div className="mt-4">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 bg-[#0082FB] text-white px-5 py-1.5 rounded-full flex items-center gap-2 text-sm font-bold shadow-md z-10">
                <MetaLogo className="w-4 h-4" /> Escolha o tipo de conexão
              </div>
              
              <div className="grid grid-cols-2 gap-4 mt-8">
                <div onClick={launchWhatsAppSignup} className="cursor-pointer bg-white border-2 border-blue-100 hover:border-[#0082FB] shadow-sm rounded-2xl p-6 text-center transition">
                  <h3 className="text-[#0082FB] font-black text-[15px] mb-3 uppercase tracking-wide">APENAS API</h3>
                  <p className="text-[13px] text-gray-600 leading-relaxed mb-4">O número passa a funcionar exclusivamente na API. O WhatsApp Business do celular deixa de funcionar.</p>
                  <p className="text-[11px] text-gray-500">Indicado para operações 100% profissionais e centralizadas.</p>
                </div>
                <div onClick={launchWhatsAppSignup} className="cursor-pointer bg-white border-2 border-blue-100 hover:border-[#0082FB] shadow-sm rounded-2xl p-6 text-center transition">
                  <h3 className="text-[#0082FB] font-black text-[15px] mb-3 uppercase tracking-wide">API COM COEXISTÊNCIA</h3>
                  <p className="text-[13px] text-gray-600 leading-relaxed mb-4">Permite usar o mesmo número no WhatsApp Business (celular) e na API ao mesmo tempo. Mensagens ficam sincronizadas.</p>
                  <p className="text-[11px] text-gray-500">Ideal para quem ainda precisa usar o app no celular.</p>
                </div>
              </div>

              <div className="mt-5 bg-[#fffdf0] border border-amber-200 shadow-sm rounded-xl p-5 text-center">
                <h4 className="text-amber-900 font-bold text-[13px] mb-3">Configurações obrigatórias na coexistência:</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-red-500"><AlertTriangle className="w-4 h-4" /></span>
                    <span className="text-amber-900 text-[12px] font-bold">Não utilize dispositivos complementares (WhatsApp Web ou aparelhos adicionais).</span>
                  </div>
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-red-500"><AlertTriangle className="w-4 h-4" /></span>
                    <span className="text-amber-900 text-[12px] font-bold">Desative mensagens automáticas do app (saudação e ausência).</span>
                  </div>
                </div>
                <p className="text-red-600 font-bold text-[12px] mt-4">Essas configurações causam conflitos com a API.</p>
              </div>
            </div>
          )}

          {step === 'meta_nickname' && (
            <div className="space-y-4">
              <div className="mb-6 text-center">
                <div className="w-16 h-16 rounded-full bg-[#25D366]/10 flex items-center justify-center mx-auto mb-4">
                  <Check className="w-8 h-8 text-[#25D366]" strokeWidth={3} />
                </div>
                <h3 className="text-xl font-black text-gray-900 mb-1">WhatsApp Conectado!</h3>
                <p className="text-[13px] text-gray-500">Dê um nome para identificar este número no sistema.</p>
              </div>

              <div className="max-w-sm mx-auto space-y-4">
                <div>
                  <label className="text-[13px] font-bold text-gray-700 block mb-1.5">Apelido Interno *</label>
                  <input autoFocus value={form.nickname} onChange={e => setForm(f => ({ ...f, nickname: e.target.value }))} placeholder="Ex: Vendas Oficial" className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-gray-900 focus:border-[#0082FB] focus:ring-1 focus:ring-[#0082FB] outline-none shadow-sm" />
                </div>
                
                <div className="pt-4 flex justify-end">
                  <button onClick={() => createMut.mutate(form)} disabled={!form.nickname || createMut.isPending} className="w-full flex items-center justify-center gap-2 px-8 py-3 bg-[#0082FB] hover:bg-blue-600 text-white rounded-xl font-bold shadow-md disabled:opacity-50 transition">
                    <Save className="w-4 h-4" /> {createMut.isPending ? 'Salvando...' : 'Salvar Dispositivo'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 'evolution_form' && (
            <div className="space-y-4">
              <div className="mb-6 text-center">
                <h3 className="text-xl font-black text-gray-900 mb-1">WhatsApp Business</h3>
                <p className="text-[13px] text-gray-500">Conexão via QR Code.</p>
              </div>

              <div>
                <label className="text-[13px] font-bold text-gray-700 block mb-1.5">Apelido Interno *</label>
                <input value={form.nickname} onChange={e => setForm(f => ({ ...f, nickname: e.target.value }))} placeholder="Ex: Suporte" className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-gray-900 focus:border-[#25D366] focus:ring-1 focus:ring-[#25D366] outline-none shadow-sm" />
              </div>

              <div className="p-5 bg-white border border-gray-200 rounded-xl space-y-3 shadow-sm">
                <p className="text-[13px] font-bold text-gray-700 mb-3">Credenciais Evolution API</p>
                <input value={form.evolution_server_url} onChange={e => setForm(f => ({ ...f, evolution_server_url: e.target.value }))} placeholder="Server URL (ex: https://evo.site.com)" className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:bg-white focus:border-[#25D366] outline-none" />
                <input value={form.evolution_instance} onChange={e => setForm(f => ({ ...f, evolution_instance: e.target.value }))} placeholder="Instance Name" className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:bg-white focus:border-[#25D366] outline-none" />
                <input value={form.evolution_api_key} onChange={e => setForm(f => ({ ...f, evolution_api_key: e.target.value }))} placeholder="Global API Key" type="password" className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:bg-white focus:border-[#25D366] outline-none" />
              </div>

              <div className="pt-4 flex justify-end">
                <button onClick={() => createMut.mutate(form)} disabled={!form.nickname || createMut.isPending} className="flex items-center gap-2 px-8 py-3 bg-[#25D366] hover:bg-green-600 text-white rounded-xl font-bold shadow-md disabled:opacity-50 transition">
                  <Save className="w-4 h-4" /> {createMut.isPending ? 'Criando...' : 'Criar Instância'}
                </button>
              </div>
            </div>
          )}

          {step === 'openwa_form' && (
            <div className="space-y-4">
              <div className="mb-6 text-center">
                <div className="w-14 h-14 rounded-2xl bg-emerald-600 text-white flex items-center justify-center font-black text-xl mx-auto mb-3 shadow-md">
                  WA
                </div>
                <h3 className="text-xl font-black text-gray-900 mb-1">OpenWA / Self-Hosted</h3>
                <p className="text-[13px] text-gray-500">Gateway wa-automate com suporte nativo a PTT e anti-conflito.</p>
              </div>

              <div>
                <label className="text-[13px] font-bold text-gray-700 block mb-1.5">Apelido Interno *</label>
                <input
                  value={form.nickname}
                  onChange={e => setForm(f => ({ ...f, nickname: e.target.value }))}
                  placeholder="Ex: WhatsApp Cigana"
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-gray-900 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 outline-none shadow-sm"
                />
              </div>

              <div className="p-5 bg-white border border-gray-200 rounded-xl space-y-3 shadow-sm">
                <p className="text-[13px] font-bold text-gray-700 mb-3">Configurações do Gateway OpenWA</p>
                <div>
                  <label className="text-xs text-gray-500 font-medium block mb-1">Server URL *</label>
                  <input
                    value={form.openwa_server_url}
                    onChange={e => setForm(f => ({ ...f, openwa_server_url: e.target.value }))}
                    placeholder="Ex: http://localhost:3000 ou https://openwa.meudominio.com"
                    className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:bg-white focus:border-emerald-600 outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 font-medium block mb-1">Session ID (Nome da Sessão) *</label>
                  <input
                    value={form.openwa_session_id}
                    onChange={e => setForm(f => ({ ...f, openwa_session_id: e.target.value }))}
                    placeholder="Ex: default ou cigana_session"
                    className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:bg-white focus:border-emerald-600 outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 font-medium block mb-1">API Key / Token Secreto</label>
                  <input
                    value={form.openwa_api_key}
                    onChange={e => setForm(f => ({ ...f, openwa_api_key: e.target.value }))}
                    placeholder="Chave AUTHENTICATION_API_KEY do OpenWA"
                    type="password"
                    className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:bg-white focus:border-emerald-600 outline-none"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  onClick={() => createMut.mutate(form)}
                  disabled={!form.nickname || !form.openwa_server_url || createMut.isPending}
                  className="flex items-center gap-2 px-8 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold shadow-md disabled:opacity-50 transition"
                >
                  <Save className="w-4 h-4" /> {createMut.isPending ? 'Salvando...' : 'Conectar OpenWA'}
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
