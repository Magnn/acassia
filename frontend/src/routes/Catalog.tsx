import React, { useState, useEffect } from 'react';
import { Package, Plus, DollarSign, Clock, Calendar, CheckCircle2, XCircle } from 'lucide-react';
import { api } from '../api/client';

interface Service {
  id: number;
  title: string;
  type: string;
  price_brl: number;
  is_active: boolean;
}

export default function Catalog() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    service_type: 'live_reading',
    price_cents: 0,
    duration_minutes: 60
  });

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    try {
      const response = await api.get<{services: Service[]}>('/api/b2c/expert/services');
      setServices(response.services);
    } catch (error) {
      console.error("Erro ao buscar serviços", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/api/b2c/expert/services', formData);
      setShowModal(false);
      fetchServices();
    } catch (error) {
      console.error("Erro ao criar serviço", error);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-white">Meus Produtos & Serviços</h1>
          <p className="text-zinc-400 mt-1">Crie os serviços que ficarão disponíveis no Marketplace B2C.</p>
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent-amethyst text-white font-bold rounded-xl hover:bg-accent-amethyst/90 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Novo Produto
        </button>
      </div>

      {loading ? (
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-4 bg-zinc-800 rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-zinc-800 rounded"></div>
              <div className="h-4 bg-zinc-800 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {services.map((service) => (
            <div key={service.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 flex flex-col hover:border-accent-amethyst/50 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 bg-accent-amethyst/10 rounded-xl text-accent-amethyst">
                  <Package className="w-6 h-6" />
                </div>
                {service.is_active ? (
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full">
                    <CheckCircle2 className="w-3 h-3" /> Ativo
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-bold text-red-400 bg-red-400/10 px-2 py-1 rounded-full">
                    <XCircle className="w-3 h-3" /> Inativo
                  </span>
                )}
              </div>
              <h3 className="text-xl font-bold text-white mb-1">{service.title}</h3>
              <p className="text-zinc-500 text-sm uppercase font-bold tracking-widest mb-6">{service.type}</p>
              
              <div className="mt-auto flex items-center justify-between pt-4 border-t border-zinc-800">
                <div className="flex items-center gap-1 text-emerald-400 font-bold">
                  <DollarSign className="w-4 h-4" />
                  {service.price_brl.toFixed(2)}
                </div>
              </div>
            </div>
          ))}
          
          {services.length === 0 && (
            <div className="col-span-full text-center py-12 bg-zinc-900/50 rounded-2xl border border-dashed border-zinc-800">
              <Package className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-zinc-300">Nenhum produto cadastrado</h3>
              <p className="text-zinc-500">Crie seu primeiro serviço para vender na plataforma.</p>
            </div>
          )}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-md">
            <h2 className="text-2xl font-black text-white mb-6">Novo Produto</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-zinc-400 mb-1">Nome do Serviço</label>
                <input 
                  type="text" 
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-accent-amethyst"
                  required
                  value={formData.title}
                  onChange={e => setFormData({...formData, title: e.target.value})}
                  placeholder="Ex: Tarot do Amor ao Vivo"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-zinc-400 mb-1">Tipo de Entrega</label>
                <select 
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-accent-amethyst"
                  value={formData.service_type}
                  onChange={e => setFormData({...formData, service_type: e.target.value})}
                >
                  <option value="live_reading">Leitura ao Vivo (Agendada)</option>
                  <option value="digital_product">Produto Digital Gravado</option>
                  <option value="therapy">Sessão de Terapia</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-1">Preço (R$)</label>
                  <input 
                    type="number" 
                    min="0"
                    step="0.01"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-accent-amethyst"
                    required
                    onChange={e => setFormData({...formData, price_cents: Math.round(parseFloat(e.target.value) * 100)})}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-zinc-400 mb-1">Duração (Minutos)</label>
                  <input 
                    type="number" 
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-accent-amethyst"
                    value={formData.duration_minutes}
                    onChange={e => setFormData({...formData, duration_minutes: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-3 bg-zinc-800 text-white font-bold rounded-xl hover:bg-zinc-700 transition-colors"
                >
                  Cancelar
                </button>
                <button 
                  type="submit"
                  className="flex-1 px-4 py-3 bg-accent-amethyst text-white font-bold rounded-xl hover:bg-accent-amethyst/90 transition-colors"
                >
                  Salvar Produto
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
