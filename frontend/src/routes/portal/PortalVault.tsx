import React from 'react';
import { Play, FileText, Lock, Headphones } from 'lucide-react';

export default function PortalVault() {
  const assets = [
    { id: 1, type: 'audio', title: 'Leitura de Tarot Anual 2026', author: 'Taróloga Mãe Serena', date: 'Há 2 dias', locked: false },
    { id: 2, type: 'video', title: 'Sessão: Limpeza de Crenças', author: 'Dr. Marcos Alinhamento', date: 'Há 1 semana', locked: false },
    { id: 3, type: 'pdf', title: 'Mapa Astral Natal', author: 'Sistema Inteligente', date: 'Há 2 meses', locked: false },
    { id: 4, type: 'audio', title: 'Meditação: Foco Total', author: 'Espaço Luz Interior', date: 'Bloqueado', locked: true },
  ];

  return (
    <div className="space-y-8 pb-20 md:pb-0">
      <div>
        <h1 className="text-3xl font-black text-white">Meu Cofre</h1>
        <p className="text-zinc-400 mt-2">
          Todo o seu conteúdo adquirido fica salvo aqui de forma vitalícia.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {assets.map(asset => (
          <div key={asset.id} className={`bg-zinc-900 border ${asset.locked ? 'border-zinc-800/50 opacity-60' : 'border-zinc-800 hover:border-accent-amethyst/50 cursor-pointer'} rounded-2xl p-6 transition-colors flex flex-col`}>
            <div className="flex justify-between items-start mb-6">
              <div className={`p-3 rounded-xl ${asset.locked ? 'bg-zinc-800 text-zinc-500' : 'bg-accent-amethyst/10 text-accent-amethyst'}`}>
                {asset.type === 'audio' && <Headphones className="w-6 h-6" />}
                {asset.type === 'video' && <Play className="w-6 h-6" />}
                {asset.type === 'pdf' && <FileText className="w-6 h-6" />}
              </div>
              {asset.locked && (
                <Lock className="w-5 h-5 text-zinc-500" />
              )}
            </div>
            
            <h3 className="text-lg font-bold text-white mb-2">{asset.title}</h3>
            <p className="text-zinc-400 text-sm font-medium mb-1">{asset.author}</p>
            
            <div className="mt-auto pt-4 flex items-center justify-between border-t border-zinc-800/50">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                {asset.date}
              </span>
              {!asset.locked && (
                <button className="text-accent-amethyst text-sm font-bold hover:text-white transition-colors">
                  Acessar
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
