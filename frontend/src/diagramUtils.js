export const DIAGRAM_DECLARATIONS = {
  class_diagram: ['classDiagram'],
  er_diagram: ['erDiagram'],
  architecture_diagram: ['flowchart', 'graph', 'architecture-beta'],
  use_case_diagram: ['usecase-beta'],
  data_flow_diagram: ['flowchart', 'graph'],
  sequence_diagram: ['sequenceDiagram'],
};

export const DIAGRAM_LABELS = {
  class_diagram: 'Class diagram',
  er_diagram: 'ER diagram',
  architecture_diagram: 'Architecture diagram',
  use_case_diagram: 'Use-case diagram',
  data_flow_diagram: 'Data-flow diagram',
  sequence_diagram: 'Sequence diagram',
};

export function normalizeMermaidSource(source) {
  return String(source || '')
    .replace(/\\r\\n|\\n/g, '\n')
    .replace(/^\s*```(?:mermaid)?\s*/i, '')
    .replace(/\s*```\s*$/, '')
    .replace(/\\t/g, '  ')
    .trim();
}

export function selectDiagramSource(result, diagramType) {
  const diagramSources = result?.diagram_sources || result?.analysis?.diagram_sources;
  const source = diagramSources && typeof diagramSources === 'object' ? diagramSources[diagramType] : '';
  const sourceIsUrl = typeof source === 'string' && /^https?:\/\//i.test(normalizeMermaidSource(source));
  if (typeof source === 'string' && source.trim() && !sourceIsUrl) return source;

  const aliases = {
    class_diagram: [result?.uml_diagram, result?.analysis?.uml_diagram, result?.refactored_srs?.uml_diagram],
    architecture_diagram: [result?.architecture_diagram, result?.analysis?.architecture_diagram, result?.refactored_srs?.architecture_diagram],
  }[diagramType] || [];
  return aliases.find((candidate) => typeof candidate === 'string' && candidate.trim() && !/^https?:\/\//i.test(normalizeMermaidSource(candidate))) || (typeof source === 'string' ? source : '');
}

export function getDiagramUrlError(source, diagramType) {
  const cleanSource = normalizeMermaidSource(source);
  if (!/^https?:\/\//i.test(cleanSource)) return '';
  let host = 'URL';
  let embeddedState = false;
  try {
    const url = new URL(cleanSource);
    host = url.hostname || host;
    embeddedState = /^#(?:pako|base64):/i.test(url.hash);
  } catch { /* retain generic URL label */ }
  const label = DIAGRAM_LABELS[diagramType] || 'Diagram';
  const reason = /(^|\.)mermaid\.live$/i.test(host)
    ? embeddedState ? 'its embedded Mermaid data could not be decoded' : 'it does not contain embedded Mermaid source'
    : `it is a link (${host}), not Mermaid code`;
  return `${label} source cannot render because ${reason}. The original value is preserved below; rerun project generation to replace it with Mermaid source.`;
}

export async function decodeMermaidLiveSource(source) {
  const cleanSource = normalizeMermaidSource(source);
  if (!/^https?:\/\//i.test(cleanSource)) return null;
  let url;
  try { url = new URL(cleanSource); } catch { return null; }
  if (!/(^|\.)mermaid\.live$/i.test(url.hostname)) return null;
  const fragment = url.hash.slice(1);
  const pakoMatch = fragment.match(/^pako:([A-Za-z0-9_-]+)$/);
  const base64Match = fragment.match(/^base64:([A-Za-z0-9_-]+)$/);
  const match = pakoMatch || base64Match;
  if (!match || match[1].length > 100_000 || typeof atob !== 'function') return null;

  try {
    const base64 = match[1].replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - match[1].length % 4) % 4);
    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    let jsonText;
    if (pakoMatch) {
      if (typeof DecompressionStream !== 'function') return null;
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'));
      const reader = stream.getReader();
      const chunks = [];
      let total = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        total += value.byteLength;
        if (total > 262_144) {
          await reader.cancel();
          return null;
        }
        chunks.push(value);
      }
      const output = new Uint8Array(total);
      let offset = 0;
      for (const chunk of chunks) { output.set(chunk, offset); offset += chunk.byteLength; }
      jsonText = new TextDecoder('utf-8', { fatal: true }).decode(output);
    } else {
      if (bytes.byteLength > 262_144) return null;
      jsonText = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    }
    const state = JSON.parse(jsonText);
    const decoded = typeof state?.code === 'string' ? state.code : '';
    if (!decoded || decoded.length > 200_000 || /^https?:\/\//i.test(decoded.trim())) return null;
    return normalizeMermaidSource(decoded) || null;
  } catch {
    return null;
  }
}

export function buildUseCaseDiagram(items = []) {
  const cases = Array.isArray(items) ? items : [];
  const rows = cases.map((item, index) => {
    const label = String(item?.title || item?.id || `Use case ${index + 1}`).replace(/[\r\n]+/g, ' ').trim().slice(0, 52);
    return `  UC${index + 1}("${label.replace(/"/g, "'")}")`;
  });
  return [
    'usecase-beta',
    'actor Stakeholder',
    'systemBoundary System',
    ...(rows.length ? rows : ['  UC1("Select a requirement")']),
    '  end',
    ...cases.map((_, index) => `  Stakeholder --> UC${index + 1}`),
  ].join('\n');
}

export async function validateMermaidSource(mermaid, source, diagramType) {
  const cleanSource = await decodeMermaidLiveSource(source) || normalizeMermaidSource(source);
  const label = DIAGRAM_LABELS[diagramType] || 'Diagram';
  if (!cleanSource) throw new Error(`${label} source is empty.`);
  const urlError = getDiagramUrlError(cleanSource, diagramType);
  if (urlError) throw new Error(urlError);

  const declaration = cleanSource.match(/^\s*([\w-]+)/)?.[1];
  const supported = DIAGRAM_DECLARATIONS[diagramType];
  if (supported && !supported.includes(declaration)) {
    throw new Error(`${label} must start with ${supported.join(' or ')}; found ${declaration || 'no diagram declaration'}.`);
  }

  try {
    await mermaid.parse(cleanSource);
  } catch (error) {
    const detail = String(error?.message || 'Mermaid could not parse this source.').split('\n').slice(0, 4).join(' ');
    throw new Error(`${label} has invalid Mermaid syntax: ${detail}`);
  }
  return cleanSource;
}
