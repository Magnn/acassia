import { useRef, useState } from 'react';
import { ACCEPT_BY_KIND, uploadMedia } from '../../api/media';
import type { CardKind } from './types';

interface Props {
  kind: Extract<CardKind, 'image' | 'audio' | 'video' | 'document'>;
  url: string;
  onChange: (url: string) => void;
}

export default function MediaUpload({ kind, url, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onPick = async (file: File) => {
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

  return (
    <div className="space-y-2">
      {url && <Preview kind={kind} url={url} />}
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="text-xs px-2 py-1 rounded border border-sibila-mist bg-sibila-onyx hover:border-sibila-amethyst disabled:opacity-50"
        >
          {busy ? 'Enviando…' : url ? 'Trocar arquivo' : 'Escolher arquivo'}
        </button>
        {url && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="text-xs text-sibila-fog hover:text-red-400"
          >
            limpar
          </button>
        )}
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
      </div>
      {url && (
        <div className="text-[10px] text-sibila-smoke font-mono break-all">{url}</div>
      )}
      {err && <div className="text-xs text-red-400">{err}</div>}
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
        className="max-h-32 rounded border border-sibila-mist object-contain bg-sibila-onyx"
      />
    );
  }
  if (kind === 'audio') {
    return <audio src={url} controls className="w-full" />;
  }
  if (kind === 'video') {
    return <video src={url} controls className="max-h-32 w-full rounded border border-sibila-mist" />;
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="text-xs text-sky-400 underline break-all"
    >
      {url}
    </a>
  );
}
