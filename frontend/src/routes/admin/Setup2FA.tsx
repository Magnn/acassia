import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Copy, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { adminApi } from '../../api/admin';
import { ApiError } from '../../api/client';
import { toast } from '../../lib/toast';

type Step = 'init' | 'qr' | 'confirm' | 'codes';

export default function Setup2FA() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('init');
  const [qrData, setQrData] = useState<{ qr_data_url: string; secret: string; setup_token: string } | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  const { data: status } = useQuery({
    queryKey: ['admin-2fa-status'],
    queryFn: adminApi.twoFAStatus,
  });

  const setupMutation = useMutation({
    mutationFn: adminApi.twoFASetupInit,
    onSuccess: (data) => {
      setQrData(data);
      setStep('qr');
    },
    onError: (e: unknown) => {
      const msg = e instanceof ApiError ? (e.body as { error?: string })?.error : 'Erro';
      toast.error(msg || 'Falha ao iniciar setup');
    },
  });

  const confirmMutation = useMutation({
    mutationFn: ({ totp, token }: { totp: string; token: string }) =>
      adminApi.twoFASetupConfirm(totp, token),
    onSuccess: (data) => {
      setRecoveryCodes(data.recovery_codes);
      setStep('codes');
    },
    onError: (e: unknown) => {
      const msg = e instanceof ApiError ? (e.body as { error?: string })?.error : 'Código inválido';
      toast.error(msg || 'Código inválido');
    },
  });

  if (status?.enabled) {
    return (
      <div className="p-12 max-w-xl mx-auto">
        <div className="bg-zinc-900/50 border border-emerald-900/40 rounded-3xl p-10 text-center space-y-6">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-emerald-500/10 flex items-center justify-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-500" />
          </div>
          <div>
            <h2 className="text-xl font-black">2FA já está ativo</h2>
            <p className="text-zinc-500 text-sm mt-2">Sua conta admin está protegida por TOTP</p>
          </div>
          <button
            onClick={() => navigate('/admin/tenants')}
            className="px-6 py-3 bg-red-600 hover:bg-red-500 rounded-2xl text-sm font-black"
          >
            Ir pro admin →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-12 max-w-2xl mx-auto">
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-10 space-y-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <ShieldCheck className="w-7 h-7 text-red-500" />
          </div>
          <div>
            <h1 className="text-xl font-black">Configurar 2FA</h1>
            <p className="text-zinc-500 text-sm font-medium">Autenticação obrigatória pra acessar /admin</p>
          </div>
        </div>

        {step === 'init' && (
          <div className="space-y-6">
            <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-6 space-y-3">
              <h3 className="text-sm font-black">Você vai precisar de um app autenticador:</h3>
              <ul className="text-xs text-zinc-400 space-y-1.5 font-medium">
                <li>• Google Authenticator</li>
                <li>• Authy</li>
                <li>• 1Password</li>
                <li>• Microsoft Authenticator</li>
              </ul>
            </div>
            <button
              onClick={() => setupMutation.mutate()}
              disabled={setupMutation.isPending}
              className="w-full px-6 py-4 bg-red-600 hover:bg-red-500 disabled:opacity-30 rounded-2xl text-sm font-black uppercase tracking-widest transition-all"
            >
              {setupMutation.isPending ? 'Gerando...' : 'Começar configuração'}
            </button>
          </div>
        )}

        {step === 'qr' && qrData && (
          <div className="space-y-6">
            <div className="text-center space-y-3">
              <p className="text-sm text-zinc-400">Escaneie o QR code com seu autenticador:</p>
              <div className="inline-block bg-white p-4 rounded-2xl">
                <img src={qrData.qr_data_url} alt="QR code TOTP" className="w-56 h-56" />
              </div>
              <div className="space-y-2">
                <p className="text-[10px] text-zinc-500 uppercase tracking-widest">Ou cadastre manualmente:</p>
                <div className="inline-flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-3 py-2 rounded-xl font-mono text-xs">
                  {qrData.secret}
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(qrData.secret);
                      toast.success('Copiado');
                    }}
                    className="text-zinc-500 hover:text-white"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
            <button
              onClick={() => setStep('confirm')}
              className="w-full px-6 py-4 bg-red-600 hover:bg-red-500 rounded-2xl text-sm font-black uppercase tracking-widest"
            >
              Configurei — próximo
            </button>
          </div>
        )}

        {step === 'confirm' && qrData && (
          <div className="space-y-6">
            <div className="text-center space-y-2">
              <p className="text-sm text-zinc-400">Digite o código de 6 dígitos do seu autenticador:</p>
            </div>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
              autoFocus
              placeholder="123456"
              className="w-full text-center text-3xl font-mono tracking-[0.4em] bg-zinc-950 border border-zinc-800 rounded-2xl py-6 text-white placeholder:text-zinc-700 focus:border-red-500/50 focus:outline-none"
            />
            <div className="flex gap-3">
              <button
                onClick={() => setStep('qr')}
                className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
              >
                Voltar
              </button>
              <button
                onClick={() => confirmMutation.mutate({ totp: totpCode, token: qrData.setup_token })}
                disabled={totpCode.length !== 6 || confirmMutation.isPending}
                className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 disabled:opacity-30 rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                {confirmMutation.isPending ? 'Validando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        )}

        {step === 'codes' && (
          <div className="space-y-6">
            <div className="bg-amber-950/30 border border-amber-900/40 rounded-2xl p-4 flex gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-black text-amber-300">⚠️ Salve esses códigos AGORA</p>
                <p className="text-xs text-amber-200/70 mt-1">
                  São os únicos meios de recuperar acesso se você perder seu autenticador.
                  Cada código funciona apenas uma vez. Você não verá eles de novo.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 bg-zinc-950 border border-zinc-800 rounded-2xl p-4">
              {recoveryCodes.map((code) => (
                <div key={code} className="font-mono text-sm text-white text-center py-2 px-3 bg-zinc-900 rounded-lg">
                  {code}
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(recoveryCodes.join('\n'));
                  toast.success('Códigos copiados');
                }}
                className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold flex items-center justify-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Copiar todos
              </button>
              <button
                onClick={() => navigate('/admin/tenants')}
                className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                Salvei — Continuar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
