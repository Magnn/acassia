import React from 'react';
import { Calendar as CalendarIcon, Clock, Video } from 'lucide-react';

export default function PortalSchedule() {
  const appointments = [
    { id: 1, title: 'Terapia de Casal', expert: 'Dr. Marcos Alinhamento', date: 'Amanhã, 15:00', duration: '60 min', status: 'upcoming' },
    { id: 2, title: 'Leitura de Tarot', expert: 'Taróloga Mãe Serena', date: '12 Maio 2026, 19:30', duration: '30 min', status: 'upcoming' },
  ];

  return (
    <div className="space-y-8 pb-20 md:pb-0">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-white">Minha Agenda</h1>
          <p className="text-zinc-400 mt-2">
            Seus próximos encontros ao vivo com especialistas.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {appointments.map(apt => (
          <div key={apt.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:border-accent-amethyst/30 transition-colors">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-accent-amethyst/10 rounded-full flex items-center justify-center text-accent-amethyst shrink-0">
                <CalendarIcon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white mb-1">{apt.title}</h3>
                <p className="text-zinc-400 font-medium">{apt.expert}</p>
                <div className="flex items-center gap-4 mt-3">
                  <span className="flex items-center gap-1 text-sm text-zinc-500 font-bold">
                    <Clock className="w-4 h-4" /> {apt.date}
                  </span>
                  <span className="flex items-center gap-1 text-sm text-zinc-500 font-bold">
                    ⏱️ {apt.duration}
                  </span>
                </div>
              </div>
            </div>
            
            <button className="w-full md:w-auto px-6 py-3 bg-white text-black font-black rounded-xl hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2">
              <Video className="w-5 h-5" />
              Entrar na Sala
            </button>
          </div>
        ))}
      </div>
      
      <div className="mt-12 p-8 bg-zinc-900/50 border border-dashed border-zinc-800 rounded-2xl text-center">
        <h3 className="text-lg font-bold text-zinc-300 mb-2">Histórico Vazio</h3>
        <p className="text-zinc-500">Você ainda não realizou consultas anteriores.</p>
      </div>
    </div>
  );
}
