import { blueprintsApi } from '../api/blueprints';
import { toast } from './toast';

/** Baixa o blueprint atual como arquivo JSON. */
export async function exportBlueprint(blueprintId: number, slug: string) {
  try {
    const doc = await blueprintsApi.exportOne(blueprintId);
    const blob = new Blob([JSON.stringify(doc, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flow_${slug}_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast.success('Fluxo exportado.');
  } catch (e) {
    toast.error(`Falha ao exportar: ${(e as Error).message}`);
  }
}

/** Lê arquivo JSON, extrai title/slug/body e cria blueprint via /import. */
export async function importBlueprintFromFile(file: File): Promise<number | null> {
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);

    // Suporta formatos:
    //   { exportVersion, blueprint: { title, slug, body } } — produzido pelo /export
    //   { title, slug, body } — manual
    //   meumisterio-flow doc direto: usa .title como title, sem slug
    let title = '';
    let slug: string | undefined;
    let body: Record<string, unknown> = {};

    if (parsed && typeof parsed === 'object') {
      const inner = (parsed.blueprint && typeof parsed.blueprint === 'object')
        ? parsed.blueprint
        : parsed;
      title = String(inner.title || '').trim();
      slug = inner.slug ? String(inner.slug).trim() : undefined;
      body = (inner.body && typeof inner.body === 'object') ? inner.body : (inner.graph ? parsed : {});
    }

    if (!title) {
      // Pede ao usuário se não veio
      const t = window.prompt('Título do fluxo:', file.name.replace(/\.json$/i, ''));
      if (!t) return null;
      title = t.trim();
    }

    const res = await blueprintsApi.importOne({ title, slug, body });
    toast.success(`Fluxo "${res.blueprint.title}" importado.`);
    return res.blueprint.id;
  } catch (e) {
    toast.error(`Falha ao importar: ${(e as Error).message}`);
    return null;
  }
}
