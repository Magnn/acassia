import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Play, FileText, Headphones, LogOut, PackageOpen, ExternalLink } from 'lucide-react';
import { api } from '../../api/client';
import { useConsumerAuth } from '../../hooks/useConsumerAuth';
import ConsumerAuthCard from '../../components/ConsumerAuthCard';

interface VaultAsset {
  id: number;
  expert_tenant_id: string;
  type: string;
  title: string;
  content_url: string;
  unlocked_at: string;
}

export default function PortalVault() {
  const { consumer, isAuthenticated, isLoading: authLoading, logout } = useConsumerAuth();
  const [filterType, setFilterType] = useState<string>('all');

  const { data, isLoading: vaultLoading } = useQuery({
    queryKey: ['b2c-vault', consumer?.id],
    queryFn: () => api.get<{ vault: VaultAsset[] }>(`/api/b2c/me/${consumer?.id}/vault`),
    enabled: Boolean(consumer?.id),
  });

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-zinc-500 text-sm font-bold animate-pulse">Carregando seus conteúdos...</div>
      </div>
    );
  }

  if (!isAuthenticated || !consumer) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4">
        <ConsumerAuthCard
          title="Acesse seu Cofre"
          subtitle="Faça login com seu WhatsApp para ver todos os seus áudios, vídeos e leituras gravadas."
        />
      </div>
    );
  }

  const assets = data?.vault ?? [];
  const filteredAssets = filterType === 'all' ? assets : assets.filter(a => a.type === filterType);

  return (
    <div className="space-y-8 pb-20 md:pb-0">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Meu Cofre</h1>
          <p className="text-zinc-400 mt-1">
            Olá, <span className="text-white font-bold">{consumer.name || consumer.phone}</span>. Todo o seu conteúdo adquirido fica salvo aqui de forma vitalícia.
          </p>
        </div>
        <button
          onClick={logout}
          className="self-start sm:self-auto flex items-center gap-2 px-3 py-1.5 rounded-xl border border-zinc-800 text-xs font-bold text-zinc-400 hover:text-white hover:border-zinc-700 transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" /> Sair da Conta
        </button>
      </div>

      {/* Type filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {[
          { id: 'all', label: 'Todos' },
          { id: 'audio', label: '🎧 Áudios' },
          { id: 'video', label: '🎬 Vídeos' },
          { id: 'pdf', label: '📄 Leituras / PDFs' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setFilterType(tab.id)}
            className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all shrink-0 ${
              filterType === tab.id
                ? 'bg-accent-amethyst text-white shadow-lg shadow-accent-amethyst/20'
                : 'bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {vaultLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 h-48 animate-pulse" />
          ))}
        </div>
      ) : filteredAssets.length === 0 ? (
        <div className="mt-8 p-12 bg-zinc-900/40 border border-dashed border-zinc-800 rounded-3xl text-center max-w-lg mx-auto">
          <div className="w-12 h-12 rounded-2xl bg-zinc-800/80 text-zinc-400 flex items-center justify-center mx-auto mb-4">
            <PackageOpen className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Cofre Vazio</h3>
          <p className="text-zinc-400 text-sm mb-6">
            Você ainda não possui conteúdos salvos {filterType !== 'all' ? 'nesta categoria' : ''}. Quando você adquirir leituras ou sessões com nossos especialistas, elas aparecerão aqui automaticamente.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAssets.map(asset => (
            <div
              key={asset.id}
              className="bg-zinc-900 border border-zinc-800 hover:border-accent-amethyst/50 rounded-2xl p-6 transition-all flex flex-col group shadow-lg"
            >
              <div className="flex justify-between items-start mb-6">
                <div className="p-3 rounded-xl bg-accent-amethyst/10 text-accent-amethyst">
                  {asset.type === 'audio' && <Headphones className="w-6 h-6" />}
                  {asset.type === 'video' && <Play className="w-6 h-6" />}
                  {asset.type !== 'audio' && asset.type !== 'video' && <FileText className="w-6 h-6" />}
                </div>
                <span className="text-[10px] font-black uppercase tracking-wider px-2 py-1 bg-zinc-800 text-zinc-400 rounded-lg">
                  {asset.type}
                </span>
              </div>

              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-accent-amethyst transition-colors">
                {asset.title}
              </h3>
              <p className="text-zinc-400 text-xs font-medium mb-4">
                Liberado em {new Date(asset.unlocked_at).toLocaleDateString('pt-BR')}
              </p>

              <div className="mt-auto pt-4 flex items-center justify-between border-t border-zinc-800/50">
                <a
                  href={asset.content_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-accent-amethyst hover:text-white text-xs font-bold transition-colors"
                >
                  <span>Acessar Conteúdo</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
