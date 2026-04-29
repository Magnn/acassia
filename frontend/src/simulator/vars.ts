// Substituição mínima de variáveis estilo {{lead.nome}} usando um objeto plano.

export type Persona = Record<string, string>;

const RE = /\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g;

export function substitute(text: string, persona: Persona): string {
  if (!text) return text;
  return text.replace(RE, (_, key: string) => {
    const v = persona[key];
    return typeof v === 'string' ? v : `{{${key}}}`;
  });
}
