import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ShieldOff, AlertTriangle } from 'lucide-react';
import { adminApi } from '../../api/admin';
import { ApiError } from '../../api/client';
import { toast } from '../../lib/toast';

export default function Recover() {
  const navigate = useNavigate();
  const [code, setCode] = useState('');

  const recoverMutation = useMutation({
    mutationFn: adminApi.twoFARecover,
    onSuccess: (data) => {
      toast.success(`Recuperado! ${data.remaining_recovery_codes} códigos restantes`);
      window.location.href = '/admin/tenants';
    },
    onError: (e: unknown) => {
      const msg = e instanceof ApiError ? (e.body as { error?: string })?.error : 'Erro';
      toast.error(msg || 'Código inválido ou já usado');
    },
  });

  return (
    <div className="min-h-screen bg-[#0d0d0d] flex items-center justify-center p-8">
      <div className="max-w-md w-full bg-zinc-900 border border-amber-900/40 rounded-3xl p-10 space-y-6">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-amber-500/10 flex items-center justify-center">
          <ShieldOff className="w-8 h-8 text-amber-500" />
        </div>

        <div className="text-center">
          <h1 className="text-xl font-black">Recuperação de acesso</h1>
          <p className="text-zinc-500 text-sm font-medium mt-2">
            Use um dos seus códigos de recuperação salvos
          </p>
        </div>

        <div className="bg-amber-950/30 border border-amber-900/40 rounded-2xl p-4 flex gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-200/80">
            Cada código funciona apenas uma vez. Após usar, você terá menos códigos disponíveis.
          </p>
        </div>

        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="XXXX-XXXX"
          autoFocus
          className="w-full text-center text-xl font-mono tracking-[0.2em] bg-zinc-950 border border-zinc-800 rounded-2xl py-5 text-white placeholder:text-zinc-700 uppercase focus:border-amber-500/50 focus:outline-none"
        />

        <div className="flex gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex-1 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-2xl text-sm font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => recoverMutation.mutate(code)}
            disabled={code.length < 8 || recoverMutation.isPending}
            className="flex-1 px-5 py-3 bg-amber-600 hover:bg-amber-500 disabled:opacity-30 rounded-2xl text-sm font-black uppercase tracking-widest"
          >
            {recoverMutation.isPending ? 'Validando...' : 'Recuperar'}
          </button>
        </div>
      </div>
    </div>
  );
}
