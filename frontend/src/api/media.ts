// POST /api/media/upload — multipart com 'file'; backend devolve { ok, url: '/media/xxx' }.
// Limite do backend: 40 MB.

interface UploadResponse {
  ok: boolean;
  url?: string;
  error?: string;
}

export async function uploadMedia(file: File): Promise<string> {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/media/upload', {
    method: 'POST',
    credentials: 'include',
    body: fd,
  });
  const data = (await res.json()) as UploadResponse;
  if (!res.ok || !data.ok || !data.url) {
    throw new Error(data.error || `upload falhou (${res.status})`);
  }
  return data.url;
}

export const ACCEPT_BY_KIND: Record<string, string> = {
  image: 'image/*',
  video: 'video/*',
  audio: 'audio/*',
  document: '.pdf,.doc,.docx,.txt',
};
