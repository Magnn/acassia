import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Plus, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { Wordmark } from '../components/Logo';

interface Workspace {
  id: string;
  name: string;
  role: string;
  is_current: boolean;
}

export default function Workspaces() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const fetchWorkspaces = async () => {
    try {
      const res = await api.get<{workspaces: Workspace[]}>('/saas/workspaces');
      setWorkspaces(res.workspaces);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitch = async (id: string) => {
    setSwitching(id);
    try {
      await api.post('/saas/workspaces/switch', { workspace_id: id });
      // Force reload to refresh all context/stores globally
      window.location.href = '/builder/dashboard';
    } catch (err) {
      console.error(err);
      setSwitching(null);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post<{message: string, id: string}>('/saas/workspaces', { name: newName });
      await handleSwitch(res.id);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4 selection:bg-accent-amethyst/30">
      <div className="mb-12">
        <Wordmark className="text-3xl" />
      </div>

      <div className="w-full max-w-md animate-fade-in">
        <h1 className="text-2xl font-black text-white mb-2 text-center">Selecione seu Workspace</h1>
        <p className="text-zinc-400 text-center mb-8">Escolha a clínica ou espaço que deseja acessar.</p>

        {loading && !switching ? (
          <div className="flex justify-center p-8">
            <Loader2 className="w-8 h-8 text-accent-amethyst animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            {workspaces.map(w => (
              <button
                key={w.id}
                onClick={() => handleSwitch(w.id)}
                disabled={switching !== null}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl p-4 flex items-center justify-between hover:border-accent-amethyst/50 transition-colors group text-left"
              >
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl ${w.is_current ? 'bg-accent-amethyst/20 text-accent-amethyst' : 'bg-zinc-800 text-zinc-400'}`}>
                    <Building2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-white font-bold text-lg">{w.name}</h3>
                    <p className="text-zinc-500 text-sm">Função: {w.role}</p>
                  </div>
                </div>
                {switching === w.id ? (
                  <Loader2 className="w-5 h-5 text-accent-amethyst animate-spin" />
                ) : (
                  <ArrowRight className="w-5 h-5 text-zinc-600 group-hover:text-accent-amethyst transition-colors" />
                )}
              </button>
            ))}

            {showNew ? (
              <form onSubmit={handleCreate} className="bg-zinc-900 border border-accent-amethyst/50 rounded-2xl p-4 mt-8 animate-fade-in">
                <label className="block text-sm font-bold text-zinc-400 mb-2">Nome do novo Workspace</label>
                <input 
                  type="text" 
                  autoFocus
                  required
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  placeholder="Ex: Terapia Holística SP"
                  className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-accent-amethyst mb-4"
                />
                <div className="flex gap-2">
                  <button type="button" onClick={() => setShowNew(false)} className="flex-1 py-2 text-zinc-400 font-bold hover:text-white transition-colors">Cancelar</button>
                  <button type="submit" className="flex-1 py-2 bg-accent-amethyst text-white font-bold rounded-xl hover:bg-accent-amethyst/90 transition-colors">Criar</button>
                </div>
              </form>
            ) : (
              <button 
                onClick={() => setShowNew(true)}
                className="w-full mt-6 py-4 border-2 border-dashed border-zinc-800 rounded-2xl text-zinc-400 font-bold flex items-center justify-center gap-2 hover:border-zinc-600 hover:text-white transition-colors"
              >
                <Plus className="w-5 h-5" />
                Criar Novo Workspace
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
