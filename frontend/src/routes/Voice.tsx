import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Mic, Play, Trash2, Sparkles, AlertCircle, CheckCircle2,
  Volume2, Wand2, RefreshCw, Star, Headphones, UploadCloud
} from 'lucide-react';
import { voiceApi, type VoiceClone } from '../api/voice';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

// ElevenLabs preset voices (real voice IDs from their API)
const PRESET_VOICES = [
  { id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel', type: 'Pré-Configurada', avatar: '🔮' },
  { id: '29vD33N1CtxCmqQRPOHJ', name: 'Drew', type: 'Pré-Configurada', avatar: '🎴' },
  { id: '2EiwWnXFnvU5JabPnv8n', name: 'Clyde', type: 'Pré-Configurada', avatar: '🌙' },
  { id: '5Q0t7uMcjvnagumLfvZi', name: 'Paul', type: 'Pré-Configurada', avatar: '⚔️' },
  { id: 'AZnzlk1XvdvUeBnXmlld', name: 'Domi', type: 'Pré-Configurada', avatar: '🛡️' },
  { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Bella', type: 'Pré-Configurada', avatar: '🌸' },
  { id: 'ErXwobaYiN019PkySvjV', name: 'Antoni', type: 'Pré-Configurada', avatar: '✨' },
  { id: 'MF3mGyEYCl7XYWbV9V6O', name: 'Elli', type: 'Pré-Configurada', avatar: '🧭' }
];

export default function Voice() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'gerar' | 'adicionar'>('gerar');
  
  // Studio State
  const [selectedVoice, setSelectedVoice] = useState<VoiceClone | { id: string, name: string, isPreset: boolean } | null>(null);
  const [text, setText] = useState('');
  const [stability, setStability] = useState(0.5);
  const [similarity, setSimilarity] = useState(0.7);
  const [style, setStyle] = useState(0.5);
  const [speed, setSpeed] = useState(1.0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const { data: configResp } = useQuery({
    queryKey: ['voice-configured'],
    queryFn: voiceApi.configured,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['voice-clones'],
    queryFn: voiceApi.list,
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => voiceApi.delete(id),
    onSuccess: (_res, id) => {
      toast.success('Voz removida');
      qc.invalidateQueries({ queryKey: ['voice-clones'] });
      if (selectedVoice && !('isPreset' in selectedVoice) && selectedVoice.id === id) {
        setSelectedVoice(null);
      }
    },
  });

  const synthMut = useMutation({
    mutationFn: () => {
      if (!selectedVoice) {
        throw new Error('Selecione uma voz para gerar.');
      }
      if ('isPreset' in selectedVoice) {
        return voiceApi.synthesizePreset(selectedVoice.id as string, text, undefined, stability, similarity);
      }
      return voiceApi.synthesize(selectedVoice.id as number, text, undefined, stability, similarity);
    },
    onSuccess: (res) => {
      setAudioUrl(res.audio_url);
      toast.success(`Áudio gerado com sucesso!`);
    },
    onError: handleApiError('Erro ao gerar áudio'),
  });

  const setDefaultMut = useMutation({
    mutationFn: (id: number) => voiceApi.setDefault(id),
    onSuccess: () => {
      toast.success('Voz definida como padrão para o Oráculo.');
      qc.invalidateQueries({ queryKey: ['voice-clones'] });
    },
    onError: handleApiError('Erro ao definir padrão'),
  });

  const clones = data?.clones ?? [];
  const configured = configResp?.configured ?? false;

  // Set default selection
  useEffect(() => {
    if (!selectedVoice && clones.length > 0) {
      setSelectedVoice(clones[0]);
    }
  }, [clones, selectedVoice]);

  return (
    <div className="px-8 py-8 max-w-7xl mx-auto min-h-screen">
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sibila-amethyst to-sibila-ember flex items-center justify-center shadow-glow-amethyst">
              <Volume2 className="w-6 h-6 text-white" />
            </div>
            <h1 className="font-display text-4xl text-primary tracking-tight">Voice Studio</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Gerenciar as vozes disponíveis, assim como personalizar vozes de acordo com suas preferências.
          </p>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-primary">Vozes clonadas: <span className="text-sibila-amethyst">{clones.length}</span></div>
          <div className="text-xs text-secondary">{configured ? '✅ API conectada' : '⚠️ API não configurada'}</div>
        </div>
      </div>

      {!configured && (
        <div className="bg-sibila-gold/10 border border-sibila-gold/30 rounded-2xl p-4 mb-8 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-sibila-gold flex-shrink-0" />
          <div>
            <h3 className="font-bold text-sm text-sibila-gold">API de Voz não configurada</h3>
            <p className="text-xs text-sibila-gold/80">Adicione a sua API Key do ElevenLabs nos segredos para liberar a clonagem.</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LADO ESQUERDO: ESTÚDIO / ADICIONAR VOZ */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* TABS */}
          <div className="flex items-center gap-4 border-b border-border">
            <button
              onClick={() => setActiveTab('gerar')}
              className={`flex items-center gap-2 pb-3 px-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'gerar' ? 'border-sibila-amethyst text-sibila-amethyst' : 'border-transparent text-secondary hover:text-primary'}`}
            >
              <Headphones className="w-4 h-4" /> Gerar áudio
            </button>
            <button
              onClick={() => setActiveTab('adicionar')}
              className={`flex items-center gap-2 pb-3 px-2 text-sm font-bold border-b-2 transition-colors ${activeTab === 'adicionar' ? 'border-sibila-amethyst text-sibila-amethyst' : 'border-transparent text-secondary hover:text-primary'}`}
            >
              <Mic className="w-4 h-4" /> Adicionar uma nova voz
            </button>
          </div>

          <div className="bg-bg-surface border border-border rounded-3xl p-6 shadow-premium min-h-[500px]">
            
            {activeTab === 'gerar' ? (
              // TAB: GERAR ÁUDIO
              <div className="animate-in fade-in duration-500">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="font-display text-xl text-primary flex items-center gap-2">
                    <Wand2 className="w-5 h-5 text-sibila-amethyst" />
                    Sintetizador
                  </h2>
                  <div className="text-xs text-secondary bg-bg-sidebar px-3 py-1 rounded-full">
                    {selectedVoice ? selectedVoice.name : 'Nenhuma voz selecionada'}
                  </div>
                </div>

                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={5}
                  placeholder="Digite aqui o texto desejado para virar um áudio."
                  className="w-full bg-bg-sidebar border border-border rounded-2xl px-5 py-4 text-sm text-primary placeholder:text-secondary/50 focus:outline-none focus:border-sibila-amethyst focus:ring-1 focus:ring-sibila-amethyst/50 resize-none transition-all mb-6"
                />

                <div className="space-y-6 mb-8">
                  <SliderControl label="Estabilidade" value={stability} setValue={setStability} />
                  <SliderControl label="Similaridade" value={similarity} setValue={setSimilarity} />
                  <SliderControl label="Sotaque" value={style} setValue={setStyle} />
                  <SliderControl label="Velocidade" value={speed} setValue={setSpeed} />
                </div>

                <div className="flex items-center justify-between mt-6">
                  <div>
                    <div className="text-xs text-secondary font-medium">Custo estimado:</div>
                    <div className="text-lg font-bold text-sibila-amethyst">{text.length || 0} <span className="text-sm">tokens</span></div>
                  </div>
                  
                  <button
                    onClick={() => synthMut.mutate()}
                    disabled={!text.trim() || synthMut.isPending || !selectedVoice}
                    className="px-8 py-3 bg-sibila-amethyst text-white hover:opacity-90 disabled:opacity-50 rounded-xl text-sm font-bold transition-all flex items-center gap-2 shadow-glow-amethyst"
                  >
                    {synthMut.isPending ? (
                      <><RefreshCw className="w-4 h-4 animate-spin" /> Materializando...</>
                    ) : (
                      <><Wand2 className="w-4 h-4" /> Gerar Áudio da Entidade</>
                    )}
                  </button>
                </div>

                <div className="mt-6 p-4 bg-bg-sidebar rounded-2xl border border-border flex items-center justify-center">
                  {audioUrl ? (
                    <audio src={audioUrl} controls autoPlay className="w-full h-10" />
                  ) : (
                    <div className="text-xs text-secondary italic flex items-center gap-2">
                      <Volume2 className="w-4 h-4" />
                      O áudio materializado aparecerá aqui (0:00)
                    </div>
                  )}
                </div>
              </div>
            ) : (
              // TAB: ADICIONAR UMA NOVA VOZ
              <EnrollForm 
                clonesCount={clones.length}
                onCreated={() => {
                  qc.invalidateQueries({ queryKey: ['voice-clones'] });
                  setActiveTab('gerar');
                }}
              />
            )}
            
          </div>
        </div>

        {/* LADO DIREITO: BIBLIOTECA DE VOZES */}
        <div className="lg:col-span-5 space-y-8">
          
          {/* Vozes Clonadas */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-primary">Vozes personalizadas</h3>
            </div>
            
            {isLoading ? (
              <div className="text-center text-secondary text-sm py-4">Carregando vozes...</div>
            ) : clones.length === 0 ? (
              <div className="text-center py-6 text-xs text-secondary italic px-10">
                Você ainda não possui nenhuma voz personalizada.
              </div>
            ) : (
              <div className="space-y-3">
                {clones.map(c => {
                  const isSelected = selectedVoice?.id === c.id;
                  const isDefault = !!c.is_default;
                  return (
                    <div 
                      key={c.id}
                      onClick={() => {
                        setSelectedVoice(c);
                        setActiveTab('gerar');
                      }}
                      className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center justify-between shadow-sm ${
                        isSelected ? 'bg-bg-surface border-sibila-amethyst shadow-glow-amethyst' : 'bg-bg-surface border-border hover:border-sibila-amethyst/50'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full flex items-center justify-center bg-cyan-500 text-white">
                          <Mic className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="font-bold text-sm text-primary flex items-center gap-2">
                            {c.name}
                            {isDefault && (
                              <span title="Voz Padrão do Oráculo">
                                <Star className="w-3 h-3 text-sibila-gold fill-current" />
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-secondary mt-0.5">Clonada</div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm('Deletar voz permanentemente?')) deleteMut.mutate(c.id);
                          }}
                          className="text-sibila-crimson hover:opacity-80 transition-opacity"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <div className="text-[10px] font-bold text-primary">
                          {new Date(c.consented_at || Date.now()).toLocaleDateString('pt-BR', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Vozes Pré-aprovadas */}
          <div>
            <h3 className="text-lg font-bold text-primary mb-4">Modelos pré aprovados</h3>
            <div className="grid grid-cols-2 gap-3">
              {PRESET_VOICES.map(v => {
                 const isSelected = selectedVoice?.id === v.id;
                 return (
                  <div 
                    key={v.id}
                    onClick={() => {
                      setSelectedVoice({ ...v, isPreset: true });
                      setActiveTab('gerar');
                    }}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between shadow-sm ${
                      isSelected ? 'bg-bg-surface border-sibila-amethyst' : 'bg-bg-surface border-border hover:border-sibila-amethyst/30'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-2xl w-8 h-8 flex items-center justify-center bg-bg-sidebar rounded-full">{v.avatar}</div>
                      <div>
                        <div className="font-bold text-xs text-primary">{v.name}</div>
                        <div className="text-[9px] text-secondary">{v.type}</div>
                      </div>
                    </div>
                    <button className="w-6 h-6 rounded-full bg-bg-surface border border-border flex items-center justify-center text-primary hover:text-sibila-amethyst transition-colors">
                      <Play className="w-3 h-3 ml-0.5" />
                    </button>
                  </div>
                 );
              })}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// ── COMPONENTES AUXILIARES ─────────────────────────────────────────

function SliderControl({ label, value, setValue }: { label: string, value: number, setValue: (v: number) => void }) {
  return (
    <div className="flex items-center gap-4">
      <label className="text-xs font-bold text-primary w-24">
        {label}
      </label>
      <input
        type="range"
        min="0" max="1" step="0.1"
        value={value}
        onChange={(e) => setValue(parseFloat(e.target.value))}
        className="flex-1 h-1.5 bg-border rounded-lg appearance-none cursor-pointer accent-sibila-amethyst"
      />
      <span className="text-xs text-sibila-amethyst font-bold bg-sibila-amethyst/10 px-2 py-0.5 rounded w-8 text-center">{value.toFixed(1)}</span>
    </div>
  );
}

function EnrollForm({
  clonesCount, onCreated,
}: {
  clonesCount: number;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [consent, setConsent] = useState(false);
  const [audioFile, setAudioFile] = useState<File | Blob | null>(null);
  
  // Recording states
  const [recording, setRecording] = useState(false);
  const [recordedSec, setRecordedSec] = useState(0);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const enrollMut = useMutation({
    mutationFn: async () => {
      if (!audioFile) throw new Error('Sem áudio anexado ou gravado');
      const fd = new FormData();
      const fileName = audioFile instanceof File ? audioFile.name : 'voice-enroll.webm';
      fd.append('audio', audioFile, fileName);
      fd.append('name', name);
      fd.append('consent', 'true');
      return voiceApi.enroll(fd);
    },
    onSuccess: () => {
      toast.success('Voz criada com sucesso!');
      onCreated();
    },
    onError: (e: unknown) => {
      const body = (e as { body?: { error?: string; message?: string } }).body;
      toast.error(body?.message || body?.error || 'Erro ao enviar áudio');
    },
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setAudioFile(e.target.files[0]);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioFile(blob);
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start();
      mediaRecRef.current = mr;
      setRecording(true);
      setRecordedSec(0);
      setAudioFile(null);
      intervalRef.current = window.setInterval(() => {
        setRecordedSec(s => s + 1);
      }, 1000);
    } catch {
      toast.error('Não foi possível acessar o microfone.');
    }
  };

  const stopRecording = () => {
    mediaRecRef.current?.stop();
    setRecording(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
      
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sibila-amethyst font-bold">
          <Sparkles className="w-5 h-5" /> 
        </div>
        <div className="text-lg font-bold text-secondary">
          <span className="text-primary">{clonesCount}</span> de 1 <span className="text-sm">clonagens</span>
        </div>
      </div>

      <div>
        <label className="text-xs font-bold text-primary mb-1.5 block">
          Nome da voz
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nome da voz"
          className="w-full bg-bg-surface border border-border rounded-xl px-4 py-3 text-sm text-primary placeholder:text-secondary focus:outline-none focus:border-sibila-amethyst transition-colors"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 items-center relative">
        {/* Upload Box */}
        <button 
          onClick={() => fileInputRef.current?.click()}
          className={`h-32 rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-2 transition-all ${
            audioFile && audioFile instanceof File ? 'border-sibila-amethyst bg-sibila-amethyst/5' : 'border-sibila-amethyst/40 hover:border-sibila-amethyst hover:bg-sibila-amethyst/5'
          }`}
        >
          <UploadCloud className={`w-6 h-6 ${audioFile && audioFile instanceof File ? 'text-sibila-amethyst' : 'text-secondary'}`} />
          <div className="text-sm text-primary">
            {audioFile && audioFile instanceof File ? audioFile.name : 'Clique para enviar um áudio'}
          </div>
          <div className="text-[10px] text-secondary font-bold uppercase tracking-widest">WAV, MP3</div>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            accept="audio/wav,audio/mp3,audio/mpeg" 
            className="hidden" 
          />
        </button>

        {/* Separator OU */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-bg-surface text-secondary text-xs font-bold px-2 py-1 z-10">
          OU
        </div>

        {/* Record Box */}
        <div className={`h-32 rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-2 transition-all relative ${
          (audioFile && !(audioFile instanceof File)) || recording ? 'border-sibila-amethyst bg-sibila-amethyst/5' : 'border-sibila-amethyst/40 hover:border-sibila-amethyst hover:bg-sibila-amethyst/5'
        }`}>
          {recording ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="w-10 h-10 rounded-full bg-sibila-crimson/20 flex items-center justify-center animate-pulse mb-1">
                <div className="w-6 h-6 rounded-full bg-sibila-crimson flex items-center justify-center">
                  <Mic className="w-3 h-3 text-white" />
                </div>
              </div>
              <div className="font-mono font-bold text-primary text-sm mb-1">
                {Math.floor(recordedSec / 60)}:{String(recordedSec % 60).padStart(2, '0')}
              </div>
              <button onClick={stopRecording} className="text-[10px] uppercase font-bold tracking-widest text-sibila-crimson hover:underline z-20">
                Parar Gravação
              </button>
            </div>
          ) : audioFile && !(audioFile instanceof File) ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-emerald-500 mb-1" />
              <div className="text-sm font-bold text-primary mb-1">Áudio Gravado ({recordedSec}s)</div>
              <button onClick={() => { setAudioFile(null); setRecordedSec(0); }} className="text-[10px] uppercase font-bold tracking-widest text-secondary hover:text-primary underline z-20">
                Gravar de novo
              </button>
            </div>
          ) : (
            <button onClick={startRecording} className="absolute inset-0 flex flex-col items-center justify-center w-full h-full z-10">
              <Mic className="w-6 h-6 text-secondary mb-2" />
              <div className="text-sm text-primary">Clique para gravar áudio</div>
              <div className="text-[10px] text-secondary font-bold uppercase tracking-widest">Pressione para iniciar</div>
            </button>
          )}
        </div>
      </div>

      <label className="flex items-start gap-3 text-[11px] text-primary cursor-pointer p-4 rounded-xl border border-transparent hover:bg-bg-sidebar transition-colors">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5 accent-sibila-amethyst w-4 h-4 flex-shrink-0"
        />
        <span className="leading-relaxed font-medium">
          Eu confirmo possuir todos os direitos ou consentimentos necessários para carregar e clonar amostras de voz, garantindo que não utilizarei o conteúdo gerado pela plataforma para fins ilegais, fraudulentos ou prejudiciais. Reafirmo meu compromisso em cumprir os <a href="#" className="text-sibila-amethyst font-bold hover:underline">Termos de Serviço</a> e a <a href="#" className="text-sibila-amethyst font-bold hover:underline">Política de Privacidade</a> do Meu Mistério.
        </span>
      </label>

      <button
        onClick={() => enrollMut.mutate()}
        disabled={!name.trim() || !audioFile || !consent || enrollMut.isPending}
        className="w-full py-4 bg-sibila-rose/70 hover:bg-sibila-rose disabled:opacity-50 text-white rounded-xl text-sm font-bold transition-all"
      >
        {enrollMut.isPending ? 'CRIANDO VOZ...' : 'CRIAR UMA VOZ CUSTOMIZADA'}
      </button>
    </div>
  );
}
