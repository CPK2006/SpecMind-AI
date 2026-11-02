import test from 'node:test';
import assert from 'node:assert/strict';
import { deflateSync } from 'node:zlib';
import { buildUseCaseDiagram, decodeMermaidLiveSource, normalizeMermaidSource, selectDiagramSource, validateMermaidSource } from '../src/diagramUtils.js';

// Mermaid's parser requires browser DOMPurify hooks in Node; production parsing
// uses the installed Mermaid parser in the browser. This adapter verifies the
// source-validation contract and deterministic parser failures without DOM.
const parser = {
  async parse(source) {
    if (source.includes('SYNTAX_ERROR')) throw new Error('Parse error on line 2: unexpected token');
    return true;
  },
};

const diagramFixtures = {
  class_diagram: 'classDiagram\n  class Book',
  er_diagram: 'erDiagram\n  BOOK ||--o{ LOAN : has',
  architecture_diagram: 'flowchart LR\n  Client --> API --> Database',
  use_case_diagram: 'usecase-beta\nactor Stakeholder\nsystemBoundary System\n  UC1("Borrow book")\nend\nStakeholder --> UC1',
  data_flow_diagram: 'flowchart LR\n  Input --> Process --> Output',
  sequence_diagram: 'sequenceDiagram\n  actor Librarian\n  Librarian->>System: Borrow book',
};

test('all supported diagram types enforce their expected declaration and invoke parsing', async () => {
  for (const [type, source] of Object.entries(diagramFixtures)) {
    assert.equal(await validateMermaidSource(parser, source, type), source);
  }
});

test('the generated use-case view keeps labels concise inside a system boundary', async () => {
  const source = buildUseCaseDiagram([
    { id: 'FR-001', title: 'Record book intake', description: 'Long detail should not be put inside the diagram node.' },
    { id: 'FR-002', title: 'Track loan due dates' },
  ]);
  assert.match(source, /^usecase-beta/);
  assert.match(source, /systemBoundary System/);
  assert.match(source, /Stakeholder --> UC1/);
  assert.doesNotMatch(source, /Long detail/);
  await validateMermaidSource(parser, source, 'use_case_diagram');
});

test('normalizes escaped newlines and fenced Mermaid source', () => {
  assert.equal(normalizeMermaidSource('```mermaid\\nflowchart LR\\n  A --> B\\n```'), 'flowchart LR\n  A --> B');
});

test('empty, mismatched, and malformed sources return specific errors', async () => {
  await assert.rejects(validateMermaidSource(parser, '  ', 'sequence_diagram'), /Sequence diagram source is empty/);
  await assert.rejects(validateMermaidSource(parser, diagramFixtures.class_diagram, 'sequence_diagram'), /must start with sequenceDiagram/);
  await assert.rejects(validateMermaidSource(parser, 'flowchart LR\n  SYNTAX_ERROR', 'data_flow_diagram'), /invalid Mermaid syntax: Parse error on line 2/);
});

test('a Mermaid Live link is diagnosed as a link and never passed to the parser', async () => {
  let parseCalls = 0;
  const trackingParser = { async parse() { parseCalls += 1; } };
  const source = 'https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f';
  await assert.rejects(
    validateMermaidSource(trackingParser, source, 'class_diagram'),
    /Class diagram source cannot render because it does not contain embedded Mermaid source/
  );
  assert.equal(parseCalls, 0);
  assert.equal(normalizeMermaidSource(source), source);
  assert.equal(selectDiagramSource({ diagram_sources: { class_diagram: source } }, 'class_diagram'), source);
});

test('bounded Mermaid Live pako links decode real source while UUID links remain unrecoverable', async () => {
  const source = 'classDiagram\n  class Book\n  class Loan\n  Book --> Loan : has';
  const state = JSON.stringify({ code: source, mermaid: { theme: 'default' } });
  const encoded = deflateSync(Buffer.from(state)).toString('base64url');
  const url = `https://mermaid.live/edit#pako:${encoded}`;
  assert.equal(await decodeMermaidLiveSource(url), source);
  assert.equal(await validateMermaidSource(parser, url, 'class_diagram'), source);
  assert.equal(await decodeMermaidLiveSource('https://mermaid.live/edit#2864ddc6-2578-40f4-83a4-b11711a95e5f'), null);
  assert.equal(await decodeMermaidLiveSource(`https://mermaid.live/edit#pako:${'A'.repeat(100_001)}`), null);
});

test('diagram selection returns the matching source and safely handles missing data', () => {
  const sources = { class_diagram: 'classDiagram\n  class Book', sequence_diagram: 'sequenceDiagram\n  actor Librarian' };
  const result = { diagram_sources: sources };
  assert.equal(selectDiagramSource(result, 'sequence_diagram'), sources.sequence_diagram);
  assert.equal(selectDiagramSource(result, 'er_diagram'), '');
  assert.equal(selectDiagramSource(null, 'class_diagram'), '');
  assert.equal(selectDiagramSource({ diagram_sources: { class_diagram: 'https://mermaid.live/edit#old' }, uml_diagram: sources.class_diagram }, 'class_diagram'), sources.class_diagram);
  assert.equal(selectDiagramSource({ uml_diagram: sources.class_diagram }, 'class_diagram'), sources.class_diagram);
});
