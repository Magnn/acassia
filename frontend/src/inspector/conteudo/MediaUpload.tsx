import { useRef, useState } from 'react';
import { Upload, Image as ImageIcon, Video, Mic, FileText, RotateCw } from 'lucide-react';
import { ACCEPT_BY_KIND, uploadMedia } from '../../api/media';
import type { CardKind } from './types';

interface Props {
  kind: Extract<CardKind, 'image' | 'audio' | 'video' | 'document'>;
  url: string;
  onChange: (url: string) => void;
}

/* LAILLA FLOW_CONTEUDO_MEDIA_UPLOAD_COPY tokens */
const UPLOAD_COPY: Record<string, { icon: typeof ImageIcon; title: string; formats: string }> = {
  image:    { icon: ImageIcon, title: 'Clique para enviar uma imagem', formats: 'JPEG, PNG (máx. 5 MB)' },
  video:    { icon: Video,     title: 'Clique para enviar um vídeo',  formats: 'MP4, 3GP (máx. 16 MB)' },
  audio:    { icon: Mic,       title: 'Clique para enviar um áudio',  formats: 'MP3, AAC, OGG, OPUS (máx. 16 MB)' },
  document: { icon: FileText,  title: 'Clique para enviar um documento', formats: 'PDF, DOC, DOCX, XLS, PPT, TXT (máx. 100 MB)' },
};

/* Limites oficiais da Meta / WhatsApp Business API */
const MAX_SIZE_BY_KIND: Record<string, number> = {
  image: 5,
  video: 16,
  audio: 16,
  document: 100,
};

export default function MediaUpload({ kind, url, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [dropping, setDropping] = useState(false);
  const copy = UPLOAD_COPY[kind] || UPLOAD_COPY.image;
  const Icon = copy.icon;

  const maxMb = MAX_SIZE_BY_KIND[kind] || 16;

  const onPick = async (file: File) => {
    if (file.size > maxMb * 1024 * 1024) {
      setErr(`Arquivo muito grande (${(file.size / 1024 / 1024).toFixed(1)} MB). Limite Meta para ${kind}: ${maxMb} MB.`);
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const u = await uploadMedia(file);
      onChange(u);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropping(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) onPick(f);
  };

  // ── No file uploaded — show the LAILLA upload zone ──
  if (!url) {
    return (
      <div className="space-y-1.5">
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDropping(true); }}
          onDragLeave={() => setDropping(false)}
          onDrop={handleDrop}
          className={[
            "flex flex-col items-center justify-center gap-2 w-full py-5 px-3.5",
            "border-2 border-dashed rounded-xl bg-[#f8fafc] text-[#64748b] cursor-pointer text-center",
            "transition-all hover:border-[#94a3b8] hover:bg-[#f1f5f9] hover:text-[#475569]",
            dropping ? "border-[#94a3b8] bg-[#f1f5f9] text-[#475569]" : "border-[#cbd5e1]",
            busy ? "opacity-50 pointer-events-none" : "",
          ].join(' ')}
        >
          <Icon className="w-7 h-7 opacity-90" strokeWidth={1.5} />
          <span className="text-[13px] font-semibold text-[#334155] leading-tight">
            {busy ? 'Enviando…' : copy.title}
          </span>
          <span className="text-[11px] font-medium text-[#94a3b8] tracking-wide">
            {copy.formats}
          </span>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_BY_KIND[kind]}
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onPick(f);
            e.target.value = '';
          }}
        />
        {err && <div className="text-[11px] text-red-500 font-medium">{err}</div>}
      </div>
    );
  }

  // ── File uploaded — show preview + replace button (LAILLA style) ──
  return (
    <div className="space-y-2">
      <div
        className={[
          "flex flex-col gap-2.5 p-3 border-2 border-dashed rounded-xl bg-[#fafafa]",
          dropping ? "border-[#94a3b8] bg-[#f1f5f9]" : "border-[#e2e8f0]",
        ].join(' ')}
        onDragOver={(e) => { e.preventDefault(); setDropping(true); }}
        onDragLeave={() => setDropping(false)}
        onDrop={handleDrop}
      >
        <div className="w-full rounded-lg overflow-hidden bg-white">
          <Preview kind={kind} url={url} />
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="self-center px-3 py-1.5 text-[11px] font-semibold text-[#475569] bg-white border border-[#e2e8f0] rounded-lg hover:border-[#c7d2fe] hover:text-[#4338ca] hover:bg-[#f8fafc] transition-colors disabled:opacity-50"
        >
          <RotateCw className="w-3 h-3 inline mr-1" />
          {busy ? 'Enviando…' : 'Substituir arquivo'}
        </button>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_BY_KIND[kind]}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onPick(f);
          e.target.value = '';
        }}
      />
      {err && <div className="text-[11px] text-red-500 font-medium">{err}</div>}
    </div>
  );
}

function Preview({
  kind,
  url,
}: {
  kind: 'image' | 'audio' | 'video' | 'document';
  url: string;
}) {
  if (kind === 'image') {
    return (
      <img
        src={url}
        alt=""
        className="block w-full max-h-[220px] object-contain"
        loading="lazy"
      />
    );
  }
  if (kind === 'video') {
    return <video src={url} controls preload="metadata" playsInline className="block w-full" />;
  }
  if (kind === 'audio') {
    return <audio src={url} controls preload="metadata" className="block w-full min-h-[40px]" />;
  }
  /* document */
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-5 px-3 text-center">
      <FileText className="w-8 h-8 text-[#94a3b8]" strokeWidth={1.5} />
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[12px] font-semibold text-[#4338ca] hover:underline"
      >
        Abrir documento
      </a>
    </div>
  );
}
