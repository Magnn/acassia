import React, { useState, useEffect } from 'react';
import { Search, Sparkles, ChevronRight, Star, MapPin, Clock, Heart } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';

export default function PortalExplore() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['b2c-experts', category, search],
    queryFn: () => api.get<{ experts: any[] }>(`/api/b2c/experts?category=${category}&q=${search}`),
  });

  const experts = data?.experts ?? [];

  const CATEGORIES = [
    { id: '', label: '✨ Todos', color: 'from-accent-amethyst to-pink-500' },
    { id: 'tarot', label: '🔮 Tarot', color: 'from-purple-600 to-indigo-600' },
    { id: 'astrologia', label: '⭐ Astrologia', color: 'from-blue-600 to-cyan-600' },
    { id: 'terapia', label: '🧘 Terapia', color: 'from-emerald-600 to-teal-600' },
    { id: 'meditacao', label: '🕯️ Meditação', color: 'from-amber-600 to-orange-600' },
    { id: 'cristais', label: '💎 Cristais', color: 'from-rose-600 to-pink-600' },
    { id: 'numerologia', label: '🔢 Numerologia', color: 'from-violet-600 to-purple-600' },
  ];

  return (
    <div className="space-y-8 pb-20 md:pb-0">
      {/* Hero */}
      <section className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-accent-amethyst/20 via-black to-pink-900/10 border border-accent-amethyst/10 p-8 md:p-12">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-accent-amethyst/5 to-transparent" />
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 bg-accent-amethyst/10 border border-accent-amethyst/20 rounded-full px-4 py-1.5 mb-6">
            <Sparkles className="w-3.5 h-3.5 text-accent-amethyst" />
            <span className="text-[10px] font-black uppercase tracking-widest text-accent-amethyst">Sua jornada começa aqui</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-white mb-4 leading-[1.1]">
            O universo tem uma <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst to-pink-400">mensagem</span> pra você.
          </h1>
          <p className="text-zinc-400 text-lg mb-8 leading-relaxed">
            Encontre guias espirituais verificados. Consultas ao vivo, leituras personalizadas e rituais transformadores.
          </p>
          
          <div className="relative flex items-center">
            <Search className="absolute left-4 w-5 h-5 text-zinc-500" />
            <input 
              type="text" 
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por tarot, terapia, ansiedade..." 
              className="w-full bg-zinc-900/80 backdrop-blur-md border border-zinc-800 rounded-full py-4 pl-12 pr-36 text-white focus:outline-none focus:border-accent-amethyst transition-colors"
            />
            <button className="absolute right-2 px-6 py-2.5 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white font-black rounded-full hover:opacity-90 text-sm uppercase tracking-wider">
              Encontrar Meu Guia
            </button>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section>
        <div className="flex gap-2 overflow-x-auto pb-2 hide-scrollbar">
          {CATEGORIES.map(cat => (
            <button key={cat.id} onClick={() => setCategory(cat.id)}
              className={`whitespace-nowrap px-5 py-2.5 rounded-full font-bold text-sm transition-all ${
                category === cat.id
                  ? `bg-gradient-to-r ${cat.color} text-white shadow-lg` 
                  : 'bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700'
              }`}>
              {cat.label}
            </button>
          ))}
        </div>
      </section>

      {/* Experts Grid */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-black text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-accent-amethyst" />
            {category ? `Especialistas em ${CATEGORIES.find(c => c.id === category)?.label.split(' ')[1]}` : 'Recomendados para Você'}
          </h2>
          {experts.length > 0 && (
            <span className="text-xs text-zinc-500 font-bold">{experts.length} encontrados</span>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-72 bg-zinc-900 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : experts.length === 0 ? (
          <div className="text-center py-16 space-y-4">
            <div className="text-6xl">🔮</div>
            <h3 className="text-xl font-black text-white">Os astros estão alinhando...</h3>
            <p className="text-zinc-500 text-sm max-w-md mx-auto">
              Em breve, os melhores guias espirituais estarão aqui. Enquanto isso, 
              explore seus <strong className="text-accent-amethyst">rituais diários</strong> e o <strong className="text-accent-amethyst">diário espiritual</strong>.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {experts.map((expert: any) => (
              <div key={expert.id} className="group bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden hover:border-accent-amethyst/50 transition-all cursor-pointer hover:shadow-xl hover:shadow-accent-amethyst/5 hover:-translate-y-1 flex flex-col">
                <div className="h-32 bg-gradient-to-br from-zinc-800 to-zinc-950 relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-accent-amethyst/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute -bottom-6 left-6 w-16 h-16 rounded-xl bg-gradient-to-br from-accent-amethyst/20 to-zinc-800 border-4 border-zinc-900 flex items-center justify-center text-2xl shadow-lg">
                    {expert.avatar || '🔮'}
                  </div>
                  <button className="absolute top-3 right-3 w-8 h-8 rounded-full bg-zinc-900/60 backdrop-blur flex items-center justify-center text-zinc-400 hover:text-pink-400 transition-colors">
                    <Heart className="w-4 h-4" />
                  </button>
                </div>
                <div className="p-6 pt-10 flex flex-col flex-1">
                  <h3 className="text-lg font-black text-white mb-1 group-hover:text-accent-amethyst transition-colors">{expert.name}</h3>
                  <p className="text-zinc-500 text-xs font-medium mb-3 flex items-center gap-1">
                    {expert.specialty || expert.description}
                  </p>
                  <div className="mt-auto">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-emerald-300">
                        A partir de R$ {expert.price_starts || expert.min_price || '---'}
                      </span>
                      <span className="text-sm font-bold text-zinc-400 flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" /> {expert.rating || '5.0'}
                      </span>
                    </div>
                    <button className="w-full py-2.5 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white rounded-xl font-black text-xs uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">
                      Agendar Consulta
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Social Proof */}
      <section className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 text-center space-y-4">
        <h3 className="text-lg font-black text-white">Milhares de pessoas já transformaram suas vidas</h3>
        <div className="flex justify-center gap-8">
          <div><div className="text-2xl font-black text-accent-amethyst">2.5k+</div><div className="text-[10px] text-zinc-500 font-bold uppercase">Consultas</div></div>
          <div><div className="text-2xl font-black text-pink-400">98%</div><div className="text-[10px] text-zinc-500 font-bold uppercase">Satisfação</div></div>
          <div><div className="text-2xl font-black text-emerald-400">500+</div><div className="text-[10px] text-zinc-500 font-bold uppercase">Guias</div></div>
        </div>
      </section>
    </div>
  );
}
