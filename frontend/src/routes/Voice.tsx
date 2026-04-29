import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Mic, MicOff, Play, Trash2, Sparkles, AlertCircle, CheckCircle2,
  Volume2, Wand2, RefreshCw,
} from 'lucide-react';
import { voiceApi, type VoiceClone } from '../api/voice';
import { handleApiError } from '../lib/handleApiError';
import { toast } from '../lib/toast';

export default function Voice() {
  const qc = useQueryClient();
  const [showEnroll, setShowEnroll] = useState(false);
  const [synthesizingClone, setSynthesizingClone] = useState<VoiceClone | null>(null);

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
    onSuccess: () => {
      toast.success('Voz removida');
      qc.invalidateQueries({ queryKey: ['voice-clones'] });
    },
  });

  const testMut = useMutation({
    mutationFn: (id: number) => voiceApi.testSample(id),
    onSuccess: (res) => {
      toast.success('Amostra gerada');
      const audio = new Audio(res.sample_audio_url);
      audio.play();
      qc.invalidateQueries({ queryKey: ['voice-clones'] });
    },
    onError: handleApiError('Erro ao gerar amostra'),
  });

  const clones = data?.clones ?? [];
  const configured = configResp?.configured ?? false;

  return (
    <div className="p-10 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-2xl bg-accent-amethyst/10 flex items-center justify-center">
              <Volume2 className="w-5 h-5 text-accent-amethyst" />
            </div>
            <h1 className="text-3xl font-black tracking-tight">Voice Cloning</h1>
          </div>
          <p className="text-secondary text-sm font-medium">
            Clone sua voz em IA. Bot manda áudios na sua voz pros leads. ✨
          </p>
        </div>
        {configured && clones.length === 0 && (
          <button
            onClick={() => setShowEnroll(true)}
            className="flex items-center gap-2 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl font-black uppercase tracking-widest text-xs"
          >
            <Mic className="w-4 h-4" />
            Clonar minha voz
          </button>
        )}
      </div>

      {!configured && (
        <div className="bg-amber-500/5 border border-amber-500/30 rounded-3xl p-6 flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-amber-500 flex-shrink-0 mt-1" />
          <div>
            <h3 className="font-black text-sm mb-1">ElevenLabs não configurado</h3>
            <p className="text-xs text-secondary">
              Pedir admin pra configurar <code className="font-mono bg-bg-primary px-1 rounded">elevenlabs.api_key</code> em segredos do tenant.
              Voice cloning é feature Pro+.
            </p>
          </div>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="text-center text-secondary text-sm py-8">Carregando...</div>
      ) : clones.length === 0 ? (
        configured && <EmptyState onStart={() => setShowEnroll(true)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {clones.map((c) => (
            <CloneCard
              key={c.id}
              clone={c}
              onSynth={() => setSynthesizingClone(c)}
              onTest={() => testMut.mutate(c.id)}
              onDelete={() => {
                if (confirm(`Remover voz "${c.name}"? Não pode desfazer.`)) {
                  deleteMut.mutate(c.id);
                }
              }}
              testing={testMut.isPending}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {showEnroll && (
        <EnrollModal
          onClose={() => setShowEnroll(false)}
          onCreated={() => {
            setShowEnroll(false);
            qc.invalidateQueries({ queryKey: ['voice-clones'] });
          }}
        />
      )}
      {synthesizingClone && (
        <SynthesizeModal
          clone={synthesizingClone}
          onClose={() => setSynthesizingClone(null)}
        />
      )}
    </div>
  );
}

function EmptyState({ onStart }: { onStart: () => void }) {
  return (
    <div className="bg-bg-surface border border-dashed border-border rounded-3xl p-12 text-center">
      <Mic className="w-16 h-16 mx-auto text-accent-amethyst/40 mb-4" />
      <h3 className="font-black text-lg mb-2">Sua voz, na voz da IA</h3>
      <p className="text-secondary text-sm mb-4 max-w-md mx-auto">
        Grave 1min da sua voz e a IA cria um clone que pode falar qualquer texto
        com sua entonação. Bot manda áudios em PT-BR pros leads como se fosse você.
      </p>
      <button
        onClick={onStart}
        className="px-6 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-2xl text-xs font-black uppercase tracking-widest"
      >
        Começar agora
      </button>
    </div>
  );
}

function CloneCard({
  clone, onSynth, onTest, onDelete, testing,
}: {
  clone: VoiceClone;
  onSynth: () => void;
  onTest: () => void;
  onDelete: () => void;
  testing: boolean;
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-3xl p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-black text-lg">{clone.name}</h3>
          <div className="text-[10px] text-secondary mt-1">
            {clone.provider} · {clone.status}
            {clone.consented_at && (
              <> · consentido {new Date(clone.consented_at).toLocaleDateString('pt-BR')}</>
            )}
          </div>
        </div>
        {clone.status === 'active' && (
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
        )}
      </div>

      {clone.sample_audio_url && (
        <audio src={clone.sample_audio_url} controls className="w-full h-10" />
      )}

      <div className="flex gap-2">
        <button
          onClick={onSynth}
          className="flex-1 px-3 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-1.5"
        >
          <Wand2 className="w-3.5 h-3.5" />
          Gerar áudio
        </button>
        <button
          onClick={onTest}
          disabled={testing}
          className="px-3 py-2 bg-bg-primary border border-border hover:border-accent-amethyst/30 disabled:opacity-30 rounded-xl text-xs font-bold flex items-center gap-1"
          title="Gerar amostra de teste"
        >
          {testing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          Testar
        </button>
        <button
          onClick={onDelete}
          className="px-3 py-2 bg-bg-primary border border-border hover:border-red-500/30 rounded-xl text-xs hover:text-red-400"
          title="Remover"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function EnrollModal({
  onClose, onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('Minha voz');
  const [consent, setConsent] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [recordedSec, setRecordedSec] = useState(0);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<number | null>(null);

  const enrollMut = useMutation({
    mutationFn: async () => {
      if (!audioBlob) throw new Error('Sem áudio gravado');
      const fd = new FormData();
      fd.append('audio', audioBlob, 'voice-enroll.webm');
      fd.append('name', name);
      fd.append('consent', 'true');
      return voiceApi.enroll(fd);
    },
    onSuccess: () => {
      toast.success('Voz clonada! Pode demorar alguns minutos pra ficar 100%.');
      onCreated();
    },
    onError: (e: unknown) => {
      const body = (e as { body?: { error?: string; message?: string } }).body;
      toast.error(body?.message || body?.error || 'Erro ao enviar áudio');
    },
  });

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start();
      mediaRecRef.current = mr;
      setRecording(true);
      setRecordedSec(0);
      intervalRef.current = window.setInterval(() => {
        setRecordedSec(s => s + 1);
      }, 1000);
    } catch {
      toast.error('Não foi possível acessar microfone');
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

  const reset = () => {
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordedSec(0);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full max-h-[90vh] overflow-y-auto space-y-5">
        <h2 className="text-xl font-black tracking-tight">Clonar sua voz</h2>

        <div className="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-4 text-xs space-y-2">
          <h3 className="font-black flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            Como gravar
          </h3>
          <p className="text-secondary">
            Leia este texto naturalmente em sua voz mais clara. Mínimo 30s, ideal 60-90s.
            Ambiente silencioso, sem outras vozes.
          </p>
          <div className="bg-bg-primary border border-border rounded-xl p-3 italic text-primary leading-relaxed">
            "Olá, sou {name}, sua tarot reader. Estou aqui pra te guiar na sua jornada
            espiritual. Cada carta tem um propósito, cada leitura é única. Quando você
            chega até mim, é porque o universo já preparou uma resposta. Vou abrir as
            cartas com cuidado, escutando o que sua alma está pedindo. Confie no processo
            — a sabedoria do tarot revela o que você precisa ouvir agora, não o que você
            quer ouvir. Vamos começar essa jornada juntas."
          </div>
        </div>

        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            Nome da voz
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-accent-amethyst/30"
          />
        </div>

        {/* Recording controls */}
        <div className="bg-bg-primary border border-border rounded-2xl p-6 text-center space-y-3">
          {audioUrl ? (
            <>
              <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-500" />
              <div className="text-sm font-black">Gravado: {recordedSec}s</div>
              <audio src={audioUrl} controls className="w-full" />
              <button
                onClick={reset}
                className="text-[11px] text-secondary hover:text-primary underline-offset-2 hover:underline"
              >
                Gravar novamente
              </button>
            </>
          ) : recording ? (
            <>
              <div className="w-16 h-16 mx-auto rounded-full bg-red-500/10 flex items-center justify-center animate-pulse">
                <Mic className="w-8 h-8 text-red-500" />
              </div>
              <div className="text-3xl font-black tracking-tight font-mono">
                {Math.floor(recordedSec / 60)}:{String(recordedSec % 60).padStart(2, '0')}
              </div>
              <button
                onClick={stopRecording}
                className="px-5 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center gap-2 mx-auto"
              >
                <MicOff className="w-3.5 h-3.5" />
                Parar gravação
              </button>
            </>
          ) : (
            <>
              <div className="w-16 h-16 mx-auto rounded-full bg-accent-amethyst/10 flex items-center justify-center">
                <Mic className="w-8 h-8 text-accent-amethyst" />
              </div>
              <p className="text-xs text-secondary">Clique pra começar a gravar</p>
              <button
                onClick={startRecording}
                className="px-5 py-2 bg-accent-amethyst hover:bg-accent-amethyst/90 text-white rounded-xl text-xs font-black uppercase tracking-widest"
              >
                Começar
              </button>
            </>
          )}
        </div>

        <label className="flex items-start gap-2 text-xs text-secondary cursor-pointer">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            Autorizo a Acássia a processar minha voz pra clonagem via IA
            (LGPD: dados de voz são considerados pessoais sensíveis).
            Posso revogar a qualquer momento.
          </span>
        </label>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
          >
            Cancelar
          </button>
          <button
            onClick={() => enrollMut.mutate()}
            disabled={!audioBlob || !consent || enrollMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
          >
            {enrollMut.isPending ? 'Enviando...' : 'Clonar voz'}
          </button>
        </div>
      </div>
    </div>
  );
}

function SynthesizeModal({
  clone, onClose,
}: {
  clone: VoiceClone;
  onClose: () => void;
}) {
  const [text, setText] = useState('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const synthMut = useMutation({
    mutationFn: () => voiceApi.synthesize(clone.id, text),
    onSuccess: (res) => {
      setAudioUrl(res.audio_url);
      toast.success(`Áudio gerado (${res.size_bytes} bytes)`);
    },
    onError: handleApiError('Erro ao gerar áudio'),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6">
      <div className="bg-bg-surface border border-border rounded-3xl p-8 max-w-lg w-full space-y-5">
        <div>
          <h2 className="text-xl font-black tracking-tight">Gerar áudio</h2>
          <p className="text-secondary text-xs mt-1">Voz: {clone.name}</p>
        </div>

        <div>
          <label className="text-[10px] uppercase font-black tracking-widest text-secondary mb-1.5 block">
            Texto pra falar (max 5000 chars)
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            placeholder="Olá querida! Recebi sua mensagem. Vamos fazer sua leitura agora..."
            className="w-full bg-bg-primary border border-border rounded-xl px-4 py-3 text-sm placeholder:text-secondary/40 focus:outline-none focus:border-accent-amethyst/30 resize-none"
          />
          <div className="text-[10px] text-secondary mt-1 text-right">{text.length}/5000</div>
        </div>

        {audioUrl && (
          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-2xl p-4 space-y-2">
            <div className="text-xs font-black flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Áudio gerado
            </div>
            <audio src={audioUrl} controls autoPlay className="w-full" />
            <a
              href={audioUrl}
              download="acassia-voice.mp3"
              className="block text-center text-[11px] text-accent-amethyst hover:underline"
            >
              Baixar MP3
            </a>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-5 py-3 bg-bg-primary border border-border rounded-2xl text-sm font-bold"
          >
            Fechar
          </button>
          <button
            onClick={() => synthMut.mutate()}
            disabled={!text.trim() || synthMut.isPending}
            className="flex-1 px-5 py-3 bg-accent-amethyst hover:bg-accent-amethyst/90 disabled:opacity-30 text-white rounded-2xl text-sm font-black uppercase tracking-widest"
          >
            {synthMut.isPending ? 'Gerando...' : 'Gerar áudio'}
          </button>
        </div>
      </div>
    </div>
  );
}
