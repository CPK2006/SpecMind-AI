import React, { useEffect, useState } from 'react';
import { decodeMermaidLiveSource, normalizeMermaidSource, validateMermaidSource } from '../diagramUtils.js';

let mermaidInitialized = false;
let diagramRenderSequence = 0;

export default function DiagramPreview({ source, diagramType, editable = false }) {
  const id = React.useId().replace(/:/g, '');
  const [editableSource, setEditableSource] = useState(() => normalizeMermaidSource(source));
  const [rendered, setRendered] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    const normalized = normalizeMermaidSource(source);
    setEditableSource(normalized);
    decodeMermaidLiveSource(normalized).then((decoded) => {
      if (active && decoded) setEditableSource(decoded);
    });
    return () => { active = false; };
  }, [source]);
  useEffect(() => {
    let active = true;
    setRendered('');
    setError('Validating diagram source…');
    import('mermaid').then(async ({ default: mermaid }) => {
      if (!active) return;
      if (!mermaidInitialized) {
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'dark' });
        mermaidInitialized = true;
      }
      const cleanSource = await validateMermaidSource(mermaid, editableSource, diagramType);
      if (!active) return;
      const renderId = `diagram-${id}-${++diagramRenderSequence}`;
      const { svg } = await mermaid.render(renderId, cleanSource);
      if (active) { setRendered(svg); setError(''); }
    }).catch((renderError) => {
      if (active) {
        setRendered('');
        setError(renderError?.message || 'Mermaid could not render this diagram. The original source is preserved below.');
      }
    });
    return () => { active = false; };
  }, [editableSource, diagramType, id]);
  return <div className="diagram-workbench">
    <div className="diagram-preview" aria-live="polite">{rendered ? <div className="diagram-svg" data-testid="diagram-svg" dangerouslySetInnerHTML={{ __html: rendered }} /> : <p className="diagram-error" role="alert">{error}</p>}</div>
    {editable && <label className="diagram-source-editor">Mermaid source for local preview (not saved)
      <textarea rows="8" value={editableSource} onChange={(event) => setEditableSource(event.target.value)} spellCheck="false" aria-label="Mermaid source for local preview" />
    </label>}
  </div>;
}
