import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Lock, Smartphone, User, Sparkles, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

interface Props {
  onSuccess?: () => void;
  title?: string;
  subtitle?: string;
}

export default function ConsumerAuthCard({
  onSuccess,
  title = 'Acesse sua Conta',
  subtitle = 'Conecte-se para acessar seus conteúdos e atendimentos salvos.',
}: Props) {
  const qc = useQueryClient();
  const [isSignup, setIsSignup] = useState(false);
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanPhone = phone.trim();
    if (!cleanPhone || !password) {
      setError('Preencha todos os campos obrigatórios.');
      return;
    }
    if (password.length < 8) {
      setError('A senha deve ter pelo menos 8 caracteres.');
      return;
    }

    setLoading(true);
    try {
      if (isSignup) {
        const res = await api.post<{ access_token: string; consumer: { id: number; name: string } }>(
          '/api/b2c/auth/signup',
          { phone: cleanPhone, password, name: name.trim() || undefined }
        );
        localStorage.setItem('b2c_access_token', res.access_token);
      } else {
        const res = await api.post<{ access_token: string; consumer: { id: number; name: string } }>(
          '/api/b2c/auth/login',
          { phone: cleanPhone, password }
        );
        localStorage.setItem('b2c_access_token', res.access_token);
      }

      await qc.invalidateQueries({ queryKey: ['b2c-auth-me'] });
      await qc.invalidateQueries({ queryKey: ['b2c-vault'] });
      await qc.invalidateQueries({ queryKey: ['b2c-appointments'] });
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err?.message || 'Falha ao autenticar. Verifique suas credenciais.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md w-full mx-auto bg-zinc-900/90 border border-zinc-800 rounded-3xl p-8 shadow-2xl backdrop-blur-xl">
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-2xl bg-accent-amethyst/10 text-accent-amethyst flex items-center justify-center mx-auto mb-3 font-bold">
          <Sparkles className="w-6 h-6" />
        </div>
        <h2 className="text-2xl font-black text-white">{title}</h2>
        <p className="text-xs text-zinc-400 mt-1">{subtitle}</p>
      </div>

      <div className="flex bg-zinc-950 p-1 rounded-xl mb-6 border border-zinc-800">
        <button
          type="button"
          onClick={() => { setIsSignup(false); setError(null); }}
          className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${!isSignup ? 'bg-zinc-800 text-white shadow' : 'text-zinc-400 hover:text-white'}`}
        >
          Entrar
        </button>
        <button
          type="button"
          onClick={() => { setIsSignup(true); setError(null); }}
          className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${isSignup ? 'bg-zinc-800 text-white shadow' : 'text-zinc-400 hover:text-white'}`}
        >
          Criar Conta
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-950/40 border border-red-800/40 rounded-xl flex items-center gap-2 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {isSignup && (
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-1.5">
              Seu Nome
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-3 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Ex: Maria Silva"
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-accent-amethyst"
              />
            </div>
          </div>
        )}

        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-1.5">
            WhatsApp / Telefone
          </label>
          <div className="relative">
            <Smartphone className="absolute left-3.5 top-3 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              placeholder="Ex: 5511999999999"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-accent-amethyst"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-1.5">
            Senha (mínimo 8 caracteres)
          </label>
          <div className="relative">
            <Lock className="absolute left-3.5 top-3 w-4 h-4 text-zinc-500" />
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-accent-amethyst"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-6 py-3 px-4 rounded-xl bg-accent-amethyst hover:bg-accent-amethyst/90 text-white font-bold text-sm tracking-wide transition-all shadow-lg shadow-accent-amethyst/20 disabled:opacity-50"
        >
          {loading ? 'Processando...' : isSignup ? 'Criar Minha Conta' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
