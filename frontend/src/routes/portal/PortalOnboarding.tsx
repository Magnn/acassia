import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Star, Moon, ArrowRight, Check } from 'lucide-react';

const SIGNS = [
  { id: 'aries', symbol: '♈', name: 'Áries', element: 'fire' },
  { id: 'touro', symbol: '♉', name: 'Touro', element: 'earth' },
  { id: 'gemeos', symbol: '♊', name: 'Gêmeos', element: 'air' },
  { id: 'cancer', symbol: '♋', name: 'Câncer', element: 'water' },
  { id: 'leao', symbol: '♌', name: 'Leão', element: 'fire' },
  { id: 'virgem', symbol: '♍', name: 'Virgem', element: 'earth' },
  { id: 'libra', symbol: '♎', name: 'Libra', element: 'air' },
  { id: 'escorpiao', symbol: '♏', name: 'Escorpião', element: 'water' },
  { id: 'sagitario', symbol: '♐', name: 'Sagitário', element: 'fire' },
  { id: 'capricornio', symbol: '♑', name: 'Capricórnio', element: 'earth' },
  { id: 'aquario', symbol: '♒', name: 'Aquário', element: 'air' },
  { id: 'peixes', symbol: '♓', name: 'Peixes', element: 'water' },
];

const INTERESTS = [
  { id: 'tarot', emoji: '🔮', label: 'Tarot' },
  { id: 'astrologia', emoji: '⭐', label: 'Astrologia' },
  { id: 'meditacao', emoji: '🧘', label: 'Meditação' },
  { id: 'cristais', emoji: '💎', label: 'Cristais' },
  { id: 'rituais', emoji: '🕯️', label: 'Rituais' },
  { id: 'sonhos', emoji: '🌙', label: 'Sonhos' },
  { id: 'numerologia', emoji: '🔢', label: 'Numerologia' },
  { id: 'sombra', emoji: '🌑', label: 'Shadow Work' },
];

const ELEMENT_COLORS: Record<string, string> = {
  fire: 'from-orange-500/20 to-red-500/20 border-orange-500/30',
  earth: 'from-emerald-500/20 to-green-500/20 border-emerald-500/30',
  air: 'from-sky-500/20 to-blue-500/20 border-sky-500/30',
  water: 'from-purple-500/20 to-indigo-500/20 border-purple-500/30',
};

export default function PortalOnboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [sign, setSign] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [interests, setInterests] = useState<string[]>([]);
  const [name, setName] = useState('');

  const toggleInterest = (id: string) => {
    setInterests(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const finish = () => {
    // Store in localStorage for now — will be sent to API on next auth
    localStorage.setItem('portal_profile', JSON.stringify({ sign, birthDate, interests, name }));
    navigate('/portal/rituals');
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
      <div className="max-w-lg w-full space-y-8">
        {/* Progress */}
        <div className="flex gap-2">
          {[0, 1, 2].map(i => (
            <div key={i} className={`flex-1 h-1 rounded-full transition-all duration-500 ${i <= step ? 'bg-gradient-to-r from-accent-amethyst to-pink-500' : 'bg-zinc-800'}`} />
          ))}
        </div>

        {step === 0 && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="text-center space-y-4">
              <div className="text-6xl">✨</div>
              <h1 className="text-4xl font-black leading-tight">
                As estrelas sabem<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst to-pink-400">quem você é.</span>
              </h1>
              <p className="text-zinc-400 text-lg">Qual é o seu signo solar?</p>
            </div>

            <div className="space-y-3">
              <input value={name} onChange={e => setName(e.target.value)} placeholder="Primeiro, seu nome..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-5 py-4 text-center font-bold focus:border-accent-amethyst/50 outline-none" />

              <div className="grid grid-cols-4 gap-2">
                {SIGNS.map(s => (
                  <button key={s.id} onClick={() => setSign(s.id)}
                    className={`flex flex-col items-center gap-1 p-3 rounded-xl border transition-all ${
                      sign === s.id
                        ? `bg-gradient-to-br ${ELEMENT_COLORS[s.element]} shadow-lg scale-105`
                        : 'border-zinc-800 hover:border-zinc-700'
                    }`}>
                    <span className="text-2xl">{s.symbol}</span>
                    <span className="text-[10px] font-bold">{s.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <button onClick={() => setStep(1)} disabled={!sign || !name}
              className="w-full py-4 bg-gradient-to-r from-accent-amethyst to-pink-500 disabled:opacity-20 text-white rounded-2xl font-black uppercase tracking-widest text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-all">
              Continuar <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="text-center space-y-4">
              <div className="text-6xl">🔮</div>
              <h1 className="text-3xl font-black leading-tight">
                O que te chama,<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst to-pink-400">{name}?</span>
              </h1>
              <p className="text-zinc-400">Escolha o que te interessa (pode marcar vários).</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {INTERESTS.map(i => (
                <button key={i.id} onClick={() => toggleInterest(i.id)}
                  className={`flex items-center gap-3 p-4 rounded-xl border transition-all text-left ${
                    interests.includes(i.id)
                      ? 'border-accent-amethyst bg-accent-amethyst/10 text-white'
                      : 'border-zinc-800 text-zinc-400 hover:border-zinc-700'
                  }`}>
                  <span className="text-2xl">{i.emoji}</span>
                  <span className="font-bold text-sm">{i.label}</span>
                  {interests.includes(i.id) && <Check className="w-4 h-4 text-accent-amethyst ml-auto" />}
                </button>
              ))}
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(0)} className="flex-1 py-4 bg-zinc-900 border border-zinc-800 rounded-2xl font-bold text-sm">Voltar</button>
              <button onClick={() => setStep(2)} disabled={interests.length === 0}
                className="flex-1 py-4 bg-gradient-to-r from-accent-amethyst to-pink-500 disabled:opacity-20 text-white rounded-2xl font-black text-sm flex items-center justify-center gap-2">
                Continuar <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="text-center space-y-4">
              <div className="text-6xl">🌟</div>
              <h1 className="text-3xl font-black leading-tight">
                Tudo pronto,<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-amethyst to-pink-400">{name}.</span>
              </h1>
              <p className="text-zinc-400 text-lg">Sua jornada espiritual começa agora.</p>
            </div>

            <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{SIGNS.find(s => s.id === sign)?.symbol}</span>
                <div>
                  <div className="font-black">{name}</div>
                  <div className="text-xs text-zinc-500">{SIGNS.find(s => s.id === sign)?.name} • {interests.length} interesses</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {interests.map(i => {
                  const it = INTERESTS.find(x => x.id === i);
                  return <span key={i} className="text-xs bg-accent-amethyst/10 text-accent-amethyst px-3 py-1 rounded-lg font-bold">{it?.emoji} {it?.label}</span>;
                })}
              </div>
            </div>

            <div className="space-y-3">
              <div className="bg-gradient-to-r from-accent-amethyst/10 to-pink-500/5 border border-accent-amethyst/20 rounded-2xl p-4 flex items-center gap-3">
                <Star className="w-5 h-5 text-accent-amethyst flex-shrink-0" />
                <div className="text-sm"><strong className="text-accent-amethyst">Bônus:</strong> Sua primeira leitura diária é grátis!</div>
              </div>
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 flex items-center gap-3">
                <Moon className="w-5 h-5 text-zinc-500 flex-shrink-0" />
                <div className="text-xs text-zinc-500">Vamos personalizar rituais, leituras e insights com base no seu perfil.</div>
              </div>
            </div>

            <button onClick={finish}
              className="w-full py-5 bg-gradient-to-r from-accent-amethyst to-pink-500 text-white rounded-2xl font-black uppercase tracking-widest text-sm hover:opacity-90 transition-all shadow-xl shadow-accent-amethyst/20 flex items-center justify-center gap-2">
              <Sparkles className="w-5 h-5" /> Começar Minha Jornada
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
