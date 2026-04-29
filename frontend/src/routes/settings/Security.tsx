import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck, ShieldOff, Copy, AlertTriangle, CheckCircle2,
  KeyRound, AlertCircle,
} from 'lucide-react';
import { adminApi } from '../../api/admin';
import { ApiError } from '../../api/client';
import { toast } from '../../lib/toast';

type SetupStep = 'idle' | 'qr' | 'confirm' | 'codes' | 'disable';

export default function SecuritySettings() {
  const qc = useQueryClient();
  const [step, setStep] = useState<SetupStep>('idle');
  const [qrData, setQrData] = useState<{ qr_data_url: string; secret: string; setup_token: string } | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['user-2fa-status'],
    queryFn: adminApi.twoFAStatus,
    retry: false,
  });

  const setupMut = useMutation({
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

  const confirmMut = useMutation({
    mutationFn: ({ totp, token }: { totp: string; token: string }) =>
      adminApi.twoFASetupConfirm(totp, token),
    onSuccess: (data) => {
      setRecoveryCodes(data.recovery_codes);
      setStep('codes');
      qc.invalidateQueries({ queryKey: ['user-2fa-status'] });
    },
    onError: () => toast.error('Código TOTP inválido'),
  });

  const disableMut = useMutation({
    mutationFn: adminApi.twoFADisable,
    onSuccess: () => {
      toast.success('2FA desativado');
      setStep('idle');
      setDisableCode('');
      qc.invalidateQueries({ queryKey: ['user-2fa-status'] });
    },
    onError: () => toast.error('Código TOTP inválido'),
  });

  if (statusLoading) {
    return (
      <div className="p-10 max-w-3xl mx-auto animate-pulse space-y-4">
        <div className="h-8 w-1/3 bg-bg-surface rounded" />
        <div className="h-32 bg-bg-surface rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="p-10 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-black tracking-tight">Segurança</h1>
        <p className="text-secondary text-sm font-medium mt-1">
          Proteja sua conta com camadas adicionais de segurança
        </p>
      </div>

      {/* 2FA Card */}
      <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
              status?.enabled ? 'bg-emerald-500/10' : 'bg-secondary/10'
            }`}>
              {status?.enabled ? (
                <ShieldCheck className="w-6 h-6 text-emerald-500" />
              ) : (
                <ShieldOff className="w-6 h-6 text-secondary" />
              )}
            </div>
            <div>
              <h2 className="text-base font-black">Autenticação em 2 Etapas (2FA)</h2>
              <p className="text-xs text-secondary mt-0.5">
                {status?.enabled
                  ? 'Ativa — código TOTP exigido a cada login'
                  : 'Desativa — recomendado ativar pra maior segurança'}
              </p>
            </div>
          </div>
          {status?.enabled ? (
            <button
              onClick={() => setStep('disable')}
              className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-xl text-xs font-black uppercase tracking-widest text-red-400 transition-all"
            >
              Desativar
            </button>
          ) : (
            <button
              onClick={() => setupMut.mutate()}
              disabled={setupMut.isPending}
              className="px-4 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all"
            >
              {setupMut.isPending ? 'Iniciando...' : 'Ativar 2FA'}
            </button>
          )}
        </div>

        {status?.enabled && (
          <div className="bg-bg-primary border border-border rounded-2xl p-4 flex items-start gap-3">
            <KeyRound className="w-4 h-4 text-secondary flex-shrink-0 mt-0.5" />
            <div className="text-xs">
              <p className="font-bold">Códigos de recuperação</p>
              <p className="text-secondary mt-0.5">
                {status.has_recovery_codes
                  ? 'Você tem códigos de recuperação salvos. Mantenha-os em local seguro.'
                  : 'Você usou todos os códigos de recuperação. Desative e reative o 2FA pra gerar novos.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Recommendations card */}
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-3xl p-6">
        <h3 className="text-xs font-black uppercase tracking-widest text-blue-400 mb-3">
          Recomendações de Segurança
        </h3>
        <ul className="space-y-2 text-sm">
          <RecItem ok={status?.enabled || false} text="Autenticação 2FA ativada" />
          <RecItem ok={true} text="Senha com mais de 8 caracteres" />
          <RecItem ok={true} text="Cookies seguros (httpOnly, SameSite)" />
        </ul>
      </div>

      {/* Setup QR step */}
      {step === 'qr' && qrData && (
        <Modal title="Escaneie o QR code">
          <div className="text-center space-y-4">
            <p className="text-sm text-secondary">
              Use Google Authenticator, Authy, 1Password ou similar:
            </p>
            <div className="inline-block bg-white p-3 rounded-2xl">
              <img src={qrData.qr_data_url} alt="QR code TOTP" className="w-48 h-48" />
            </div>
            <div>
              <p className="text-[10px] text-secondary uppercase tracking-widest mb-1">Ou cadastre manualmente:</p>
              <div className="inline-flex items-center gap-2 bg-bg-primary border border-border px-3 py-2 rounded-xl font-mono text-xs">
                {qrData.secret}
                <button
                  onClick={() => { navigator.clipboard.writeText(qrData.secret); toast.success('Copiado'); }}
                  className="text-secondary hover:text-primary"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => setStep('idle')}
              className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
            >
              Cancelar
            </button>
            <button
              onClick={() => setStep('confirm')}
              className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
            >
              Próximo
            </button>
          </div>
        </Modal>
      )}

      {step === 'confirm' && qrData && (
        <Modal title="Digite o código de 6 dígitos">
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
            autoFocus
            placeholder="123456"
            className="w-full text-center text-3xl font-mono tracking-[0.4em] bg-bg-primary border border-border rounded-2xl py-5 text-primary placeholder:text-secondary/40 focus:border-accent-amethyst/50 focus:outline-none"
          />
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => setStep('qr')}
              className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
            >
              Voltar
            </button>
            <button
              onClick={() => confirmMut.mutate({ totp: totpCode, token: qrData.setup_token })}
              disabled={totpCode.length !== 6 || confirmMut.isPending}
              className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
            >
              {confirmMut.isPending ? 'Validando...' : 'Confirmar'}
            </button>
          </div>
        </Modal>
      )}

      {step === 'codes' && (
        <Modal title="Salve seus códigos de recuperação">
          <div className="space-y-4">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-300">
                <strong>Salve esses 10 códigos AGORA.</strong> Cada um funciona uma única vez.
                São o único modo de recuperar acesso se você perder o autenticador.
                Você não verá eles de novo.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 bg-bg-primary border border-border rounded-2xl p-4">
              {recoveryCodes.map((code) => (
                <div key={code} className="font-mono text-sm text-primary text-center py-2 px-3 bg-bg-surface rounded-lg">
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
                className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold flex items-center justify-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Copiar todos
              </button>
              <button
                onClick={() => { setStep('idle'); setRecoveryCodes([]); }}
                className="flex-1 px-5 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                Salvei — fechar
              </button>
            </div>
          </div>
        </Modal>
      )}

      {step === 'disable' && (
        <Modal title="Desativar 2FA">
          <div className="space-y-4">
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">
                Sua conta ficará menos segura. Recomendamos manter 2FA ativo.
                Digite o código atual do autenticador pra confirmar.
              </p>
            </div>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              className="w-full text-center text-2xl font-mono tracking-[0.4em] bg-bg-primary border border-border rounded-2xl py-4 text-primary"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setStep('idle'); setDisableCode(''); }}
                className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
              >
                Cancelar
              </button>
              <button
                onClick={() => disableMut.mutate(disableCode)}
                disabled={disableCode.length !== 6 || disableMut.isPending}
                className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-500 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
              >
                {disableMut.isPending ? 'Desativando...' : 'Desativar 2FA'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function RecItem({ ok, text }: { ok: boolean; text: string }) {
  return (
    <li className="flex items-center gap-2">
      {ok ? (
        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
      ) : (
        <div className="w-4 h-4 rounded-full border border-secondary" />
      )}
      <span className={`text-sm ${ok ? 'text-primary' : 'text-secondary'}`}>{text}</span>
    </li>
  );
}

function Modal({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-6 max-w-lg w-full">
        <h3 className="text-base font-black mb-4">{title}</h3>
        {children}
      </div>
    </div>
  );
}
