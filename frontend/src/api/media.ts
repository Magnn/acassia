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

// Formatos aceitos pela API Meta / WhatsApp Business
export const ACCEPT_BY_KIND: Record<string, string> = {
  image: 'image/jpeg,image/png',
  video: 'video/mp4,video/3gpp',
  audio: 'audio/aac,audio/mp3,audio/mpeg,audio/amr,audio/ogg,audio/opus',
  document: '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt',
};
