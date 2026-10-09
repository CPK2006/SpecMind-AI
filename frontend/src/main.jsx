import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import './styles.css';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
});

function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('specmind_user') || 'null'));
  const [page, setPage] = useState('dashboard');
  const [activeProjectId, setActiveProjectId] = useState(null);

  if (!user) {
    return <AuthPage onAuthenticated={(authenticatedUser) => {
      setUser(authenticatedUser);
      setPage('create');
    }} />;
  }

  const logout = () => {
    localStorage.removeItem('specmind_user');
    setUser(null);
    setPage('dashboard');
  };

  if (page === 'create') {
    return <ProjectCreationPage user={user} onLogout={logout} onBack={() => setPage('dashboard')} />;
  }

  if (page === 'workspace' && activeProjectId) return <WorkspacePage projectId={activeProjectId} user={user} onLogout={logout} onBack={() => setPage('dashboard')} />;
  return <DashboardPage user={user} onLogout={logout} onNewProject={() => setPage('create')} onOpenProject={(id) => { setActiveProjectId(id); setPage('workspace'); }} />;
}

function AuthPage({ onAuthenticated }) {
  const [authMode, setAuthMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [state, setState] = useState({ status: 'idle', message: '' });

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const submit = (event) => {
    event.preventDefault();
    const users = JSON.parse(localStorage.getItem('specmind_users') || '[]');
    const email = form.email.trim().toLowerCase();

    if (authMode === 'register') {
      if (users.some((candidate) => candidate.email === email)) {
        setState({ status: 'error', message: 'An account with this email already exists.' });
        return;
      }
      const newUser = { name: form.name.trim(), email, password: form.password };
      localStorage.setItem('specmind_users', JSON.stringify([...users, newUser]));
      setAuthMode('login');
      setForm({ name: '', email, password: '' });
      setState({ status: 'success', message: 'Account created. Please sign in to continue.' });
      return;
    }

    const existingUser = users.find((candidate) => candidate.email === email && candidate.password === form.password);
    if (!existingUser) {
      setState({ status: 'error', message: 'Invalid email or password.' });
      return;
    }
    localStorage.setItem('specmind_user', JSON.stringify({ name: existingUser.name, email }));
    onAuthenticated({ name: existingUser.name, email });
  };

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="brand-mark">S</div>
        <p className="eyebrow">SPECMIND AI</p>
        <h1>{authMode === 'login' ? 'Welcome back.' : 'Build with clarity.'}</h1>
        <p className="lede">{authMode === 'login' ? 'Sign in to continue to your requirements workspace.' : 'Create your workspace and turn ideas into better software specifications.'}</p>
        <form onSubmit={submit}>
          {authMode === 'register' && <label>Full name<input name="name" value={form.name} onChange={update} required placeholder="Your name" /></label>}
          <label>Email address<input type="email" name="email" value={form.email} onChange={update} required placeholder="you@example.com" /></label>
          <label>Password<input type="password" name="password" value={form.password} onChange={update} required minLength="6" placeholder="At least 6 characters" /></label>
          <button className="primary auth-submit">{authMode === 'login' ? 'Sign in' : 'Create account'}</button>
          {state.message && <p className={`status ${state.status}`}>{state.message}</p>}
        </form>
        <p className="auth-switch">
          {authMode === 'login' ? 'New to SpecMind?' : 'Already have an account?'}{' '}
          <button type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setState({ status: 'idle', message: '' }); }}>
            {authMode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
        <p className="demo-note">MVP demo authentication is stored locally in this browser.</p>
      </section>
    </main>
  );
}

function DashboardPage({ user, onLogout, onNewProject, onOpenProject }) {
  const [projects, setProjects] = useState([]);
  const [state, setState] = useState({ status: 'loading', message: 'Loading your projects...' });

  const loadProjects = async () => {
    setState({ status: 'loading', message: 'Loading your projects...' });
    try {
      const response = await api.get('/projects');
      setProjects(response.data.data || []);
      setState({ status: 'idle', message: '' });
    } catch (error) {
      setState({ status: 'error', message: apiError(error, 'Unable to load projects. Check that the backend is running.') });
    }
  };

  React.useEffect(() => { loadProjects(); }, []);

  return (
    <main className="shell">
      <header className="topbar"><span className="topbar-brand">SpecMind <em>AI</em></span><div className="account"><span>{user.name || user.email}</span><button type="button" onClick={onLogout}>Log out</button></div></header>
      <section className="dashboard-heading">
        <div><p className="eyebrow">YOUR WORKSPACE</p><h1>Welcome back, {user.name?.split(' ')[0] || 'builder'}.</h1><p className="lede">Continue improving a project or start a new requirements workspace.</p></div>
        <button className="primary" type="button" onClick={onNewProject}>+ New project</button>
      </section>
      <section className="dashboard-section">
        <div className="section-heading"><div><p className="eyebrow">PROJECTS</p><h2>Previous projects</h2></div><button className="refresh-button" type="button" onClick={loadProjects}>Refresh</button></div>
        {state.status === 'loading' && <p className="empty-state">{state.message}</p>}
        {state.status === 'error' && <p className="status error">{state.message}</p>}
        {state.status !== 'loading' && !projects.length && <div className="empty-state"><strong>No projects yet.</strong><span>Create your first project to begin.</span><button className="secondary" type="button" onClick={onNewProject}>Create a project</button></div>}
        {!!projects.length && <div className="project-grid">{projects.map((project) => <article className="project-card project-card-button" role="button" tabIndex="0" key={project.id} onClick={() => onOpenProject(project.id)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpenProject(project.id); } }}><div className="project-card-top"><span className="project-mode">{project.creation_mode === 'pitch' ? '✦ Pitch' : '↥ SRS improvement'}</span><span className="project-status">{project.status}</span></div><h3>{project.name}</h3><p>{project.description || 'Open the saved project workspace.'}</p><small>Created {new Date(project.created_at).toLocaleDateString()} · Open workspace →</small></article>)}</div>}
      </section>
    </main>
  );
}

function ProjectCreationPage({ user, onLogout, onBack }) {
  const [mode, setMode] = useState('pitch');
  const [form, setForm] = useState({ name: '', description: '', idea_pitch: '', title: '' });
  const [file, setFile] = useState(null);
  const [state, setState] = useState({ status: 'idle', message: '' });
  const [result, setResult] = useState(null);
  const [projectId, setProjectId] = useState(null);

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const changeMode = (nextMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    setProjectId(null);
    setResult(null);
    setState({ status: 'idle', message: '' });
  };

  const submit = async (event) => {
    event.preventDefault();
    setResult(null);
    setState({ status: 'loading', message: 'Creating your project...' });
    let uploadSaved = false;
    let generatedDraft = false;

    try {
      if (mode === 'upload' && !file) throw new Error('Choose a PDF or DOCX SRS document first.');
      let currentProjectId = projectId;
      const projectPayload = {
        name: form.name,
        description: form.description || null,
        project_type: 'Software Project',
        creation_mode: mode,
        idea_pitch: mode === 'pitch' ? form.idea_pitch : null,
      };
      if (currentProjectId) {
        await api.put(`/projects/${currentProjectId}`, projectPayload);
      } else {
        const project = await api.post('/projects', projectPayload);
        currentProjectId = project.data.data.id;
        setProjectId(currentProjectId);
      }

      if (mode === 'upload') {
        const body = new FormData();
        body.append('project_id', currentProjectId);
        body.append('title', form.title || file.name);
        body.append('description', form.description || '');
        body.append('file', file);
        const requirement = await api.post('/requirements/upload', body);
        uploadSaved = true;
        setState({ status: 'loading', message: 'Analyzing requirements, test cases, and quality...' });
        const requirementId = requirement.data.data.id;
        const report = await api.post(`/requirements/${requirementId}/generate-report`);
        generatedDraft = report.data.data?.generation_status === 'draft';
        setResult({ type: 'upload', requirementId, data: report.data.data });
      } else {
        setState({ status: 'loading', message: 'Generating your structured SRS...' });
        const generated = await api.post(`/projects/${currentProjectId}/generate-srs`);
        generatedDraft = generated.data.data?.generation_status === 'draft';
        setResult({ type: 'pitch', data: generated.data.data });
      }

      setState({
        status: 'success',
          message: generatedDraft
            ? 'A source-based draft is ready; AI refinement can be retried when the service is available.'
            : mode === 'pitch'
            ? 'SRS generated successfully.'
            : 'Analysis completed successfully.',
      });
    } catch (error) {
      setState({
        status: 'error',
        message: uploadSaved
          ? `Your document is uploaded and saved, but analysis did not finish: ${apiError(error, 'Please retry from the project workspace.')}`
          : apiError(error, 'Something went wrong.'),
      });
    }
  };

  return (
    <main className="shell">
      <header className="topbar"><button className="back-button" type="button" onClick={onBack}>← Dashboard</button><span className="topbar-brand">SpecMind <em>AI</em></span><div className="account"><span>{user.name || user.email}</span><button type="button" onClick={onLogout}>Log out</button></div></header>
      <section className="hero">
        <p className="eyebrow">REQUIREMENTS INTELLIGENCE</p>
        <h1>Make the next version of your idea easier to build.</h1>
        <p className="lede">Choose whether SpecMind should turn an idea into an SRS or improve an SRS you already have.</p>
      </section>

      <section className="mode-grid" aria-label="Creation mode">
        <button className={mode === 'pitch' ? 'mode-card active' : 'mode-card'} onClick={() => changeMode('pitch')}>
          <span className="mode-icon">✦</span>
          <strong>Pitch an idea</strong>
          <span>Start with a rough concept and shape it into a complete, testable SRS.</span>
        </button>
        <button className={mode === 'upload' ? 'mode-card active' : 'mode-card'} onClick={() => changeMode('upload')}>
          <span className="mode-icon">↥</span>
          <strong>Improve an SRS</strong>
          <span>Upload an existing document to find gaps, clarify requirements, and refactor it.</span>
        </button>
      </section>

      <form className="panel" onSubmit={submit}>
        <div className="panel-heading">
          <div><p className="eyebrow">STEP 1</p><h2>{mode === 'pitch' ? 'Describe your idea' : 'Bring your existing SRS'}</h2></div>
          <span className="badge">{mode === 'pitch' ? 'GENERATION' : 'IMPROVEMENT'}</span>
        </div>
        <label>Project name<input name="name" value={form.name} onChange={update} required placeholder="e.g. Campus transport app" /></label>
        <label>Project context<textarea name="description" value={form.description} onChange={update} placeholder="Who is this for, and what outcome matters?" rows="3" /></label>
        {mode === 'pitch' ? (
          <label>Idea pitch<textarea name="idea_pitch" value={form.idea_pitch} onChange={update} required placeholder="Explain the problem, users, and the experience you imagine." rows="7" /></label>
        ) : (
          <>
            <label>Document title<input name="title" value={form.title} onChange={update} placeholder="Leave blank to use the filename" /></label>
            <label className="upload"><span>{file ? file.name : 'Choose a PDF or DOCX document'}</span><input type="file" accept=".pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label>
          </>
        )}
        <button className="primary" disabled={state.status === 'loading'}>{state.status === 'loading' ? 'Working…' : mode === 'pitch' ? 'Create project and generate SRS' : 'Upload and analyze SRS'}</button>
        {state.message && <p className={`status ${state.status}`}>{state.message}</p>}
      </form>
      {result && <ReportView result={result} projectId={projectId} onResultUpdate={(data) => setResult((current) => current ? { ...current, data } : current)} />}
    </main>
  );
}

function WorkspacePage({ projectId, user, onLogout, onBack }) {
  const [workspace, setWorkspace] = useState(null);
  const [state, setState] = useState({ status: 'loading', message: 'Opening saved project workspace...' });
  const [retryCount, setRetryCount] = useState(0);
  React.useEffect(() => {
    let active = true;
    api.get(`/projects/${projectId}/workspace`).then((response) => {
      if (!active) return;
      setWorkspace(response.data.data);
      setState({ status: 'idle', message: '' });
    }).catch(async (error) => {
      if (!active) return;
      let message = apiError(error, 'Unable to open this project workspace.');
      if (error.response?.status === 404) {
        try {
          await api.get(`/projects/${projectId}`);
          message = 'This project exists, but the backend does not have the workspace endpoint yet. Restart the backend server so it loads the latest API routes, then retry.';
        } catch (projectError) {
          message = projectError.response?.status === 404
            ? 'This project was not found by the backend. Refresh the dashboard and open a project that is still listed.'
            : apiError(projectError, 'Unable to verify this project with the backend.');
        }
      }
      if (active) setState({ status: 'error', message });
    });
    return () => { active = false; };
  }, [projectId, retryCount]);
  const retryGeneration = async () => {
    if (workspace?.project.creation_mode !== 'pitch') { setRetryCount((count) => count + 1); return; }
    setState({ status: 'loading', message: 'Retrying SRS generation...' });
    try {
      const response = await api.post(`/projects/${projectId}/generate-srs`);
      setWorkspace({ ...workspace, result: response.data.data });
      setState({ status: 'idle', message: '' });
    } catch (error) {
      setState({ status: 'error', message: apiError(error, 'SRS generation failed. Please try again.') });
    }
  };
  return <main className="shell">
    <header className="topbar"><button className="back-button" type="button" onClick={onBack}>← Dashboard</button><span className="topbar-brand">SpecMind <em>AI</em></span><div className="account"><span>{user.name || user.email}</span><button type="button" onClick={onLogout}>Log out</button></div></header>
    {state.status === 'loading' && <p className="empty-state">{state.message}</p>}
    {state.status === 'error' && <div className="empty-state"><p className="status error">{state.message}</p><button className="secondary" type="button" onClick={() => setRetryCount((count) => count + 1)}>Retry loading</button><button className="secondary" type="button" onClick={onBack}>Return to projects</button></div>}
    {workspace && <><section className="hero"><p className="eyebrow">SAVED PROJECT WORKSPACE</p><h1>{workspace.project.name}</h1><p className="lede">{workspace.project.description || 'Your generated requirements workspace.'}</p></section>{workspace.result ? <ReportView result={{ type: workspace.project.creation_mode, requirementId: workspace.requirement_id, data: workspace.result }} projectId={projectId} onResultUpdate={(result) => setWorkspace({ ...workspace, result })} /> : <div className="panel"><h2>Results are not ready</h2><p className="muted">Generation did not finish. Retry to continue this saved project.</p><button className="primary" type="button" onClick={retryGeneration}>Retry generation</button>{state.status === 'error' && <p className="status error">{state.message}</p>}</div>}</>}
  </main>;
}

function ReportView({ result, projectId, onResultUpdate }) {
  const data = result.data || {};
  if (result.type === 'pitch') return <PitchResults data={data} projectId={projectId} onResultUpdate={onResultUpdate} />;
  return <UploadResults requirementId={result.requirementId} data={data} projectId={projectId} onResultUpdate={onResultUpdate} />;
}

function UploadResults({ requirementId, data, projectId, onResultUpdate }) {
  const [tab, setTab] = useState('analyzer');
  const [diagramType, setDiagramType] = useState('architecture_diagram');
  const [answers, setAnswers] = useState(data.applied_answers || {});
  const [answerState, setAnswerState] = useState({ status: 'idle', message: '' });
  const [generationState, setGenerationState] = useState({ status: 'idle', message: '' });
  const analysis = data.analysis || {};
  const requirements = data.functional_requirements || analysis.functional_requirements || [];
  const nfrs = data.non_functional_requirements || analysis.non_functional_requirements || [];
  const [selectedUseCases, setSelectedUseCases] = useState(requirements.map((item) => item.id));
  React.useEffect(() => setSelectedUseCases(requirements.map((item) => item.id)), [data]);
  const questions = data.clarification_questions || [];
  const diagrams = data.diagram_sources || {};
  const testCases = data.test_cases || [];
  const suggestions = data.suggested_additions || [];
  const improvedSrs = data.refactored_srs || {};
  const download = (extension, content, mime) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `specmind-improved-srs.${extension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const submitAnswers = async (event) => {
    event.preventDefault();
    setAnswerState({ status: 'loading', message: 'Applying clarification answers…' });
    try {
      const response = await api.post(`/requirements/${requirementId}/clarification-answers`, { answers });
      const updated = response.data.data || {};
      setAnswerState({ status: 'success', message: 'Answers applied to the improved SRS.' });
      onResultUpdate?.(updated);
    } catch (error) {
      setAnswerState({ status: 'error', message: apiError(error, 'Unable to apply answers. Please try again.') });
    }
  };
  const retryFullAnalysis = async () => {
    setGenerationState({ status: 'loading', message: 'Retrying AI refinement and quality review...' });
    try {
      const response = await api.post(`/requirements/${requirementId}/generate-report?refresh=true`);
      setGenerationState({ status: 'success', message: 'AI refinement and quality review completed.' });
      onResultUpdate?.(response.data.data || {});
    } catch (error) {
      setGenerationState({ status: 'error', message: apiError(error, 'AI refinement is unavailable. Your saved draft remains available.') });
    }
  };
  const markdown = buildSrsMarkdown(data, true);
  return (
    <section className="results panel" aria-label="Mode 2 improved SRS results">
      <div className="panel-heading"><div><p className="eyebrow">MODE 2 RESULTS · SOURCE PRESERVED</p><h2>{improvedSrs.title || 'SRS improvement workspace'}</h2><p className="result-summary">Complete extracted-source analysis with traceable improvements, answers, diagrams, tests, and exports.</p></div><span className="badge">{data.generation_status === 'draft' ? 'DRAFT' : 'COMPLETE'}</span></div>
      {data.generation_status === 'draft' && <div className="status error document-warning"><strong>Saved analysis draft</strong><p>{data.generation_note}</p><button className="secondary" type="button" onClick={retryFullAnalysis} disabled={generationState.status === 'loading'}>{generationState.status === 'loading' ? 'Retrying…' : 'Retry AI refinement'}</button>{generationState.message && <p className={`status ${generationState.status}`}>{generationState.message}</p>}</div>}
      {data.is_software_document === false && <div className="status error document-warning"><strong>This does not appear to be a software SRS.</strong><p>{data.message || 'The uploaded content could not be analyzed as software requirements.'}</p></div>}
      <nav className="result-tabs" aria-label="SRS improvement sections">
        {[['analyzer', 'Specification Analyzer'], ['qa', 'Interactive Q&A'], ['diagrams', 'Diagrams'], ['tests', 'Test Cases Analyzer'], ['srs', 'Refactored SRS'], ['report', 'Report']].map(([id, label]) => <button key={id} type="button" className={tab === id ? 'result-tab active' : 'result-tab'} onClick={() => setTab(id)}>{label}</button>)}
      </nav>
      {tab === 'analyzer' && <div className="tab-content"><div className="summary-grid"><InfoCard label="Suitable domain" value={data.suitable_domain} /><InfoCard label="Recommended tech stack" value={Object.entries(data.recommended_tech_stack || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' · ')} /></div><ResultSection title="Extracted source analysis"><p className="source-meta">{data.source_text_length || data.source_text?.length || 0} characters preserved from {data.document_name || 'uploaded document'}.</p><pre className="source-text">{data.source_text || 'No extracted source returned.'}</pre></ResultSection><div className="report-columns"><ResultSection title="Extracted functional requirements"><RequirementList items={requirements} /></ResultSection><ResultSection title="Extracted non-functional requirements"><RequirementList items={nfrs} /></ResultSection></div><div className="report-columns"><ResultSection title="User stories"><List items={data.user_stories} /></ResultSection><ResultSection title="Acceptance criteria"><List items={data.acceptance_criteria} /></ResultSection></div><div className="report-columns"><ResultSection title="Risks and assumptions"><List items={[...(data.risks || []), ...(data.assumptions || [])]} /></ResultSection><ResultSection title="Missing requirements and suggested additions"><List items={[...(data.missing_requirements || []), ...suggestions]} /></ResultSection></div></div>}
      {tab === 'qa' && <div className="tab-content"><ResultSection title="Clarification questions"><form onSubmit={submitAnswers} className="qa-form">{questions.length ? questions.map((question) => <label key={question.id}><span><b>{question.id}</b> {question.question}<small>{question.priority || 'medium'} priority · {question.reason}</small></span><textarea rows="2" value={answers[question.id] || ''} onChange={(event) => setAnswers({ ...answers, [question.id]: event.target.value })} placeholder="Add an answer for the improved SRS" /></label>) : <p className="muted">No clarification questions were returned.</p>}<button className="primary" type="submit" disabled={answerState.status === 'loading'}>Apply answers to SRS</button>{answerState.message && <p className={`status ${answerState.status}`}>{answerState.message}</p>}</form></ResultSection></div>}
      {tab === 'diagrams' && <div className="tab-content"><div className="diagram-picker">{Object.entries(DIAGRAM_LABELS).map(([id, label]) => <button type="button" key={id} className={diagramType === id ? 'diagram-button active' : 'diagram-button'} onClick={() => setDiagramType(id)}>{label}</button>)}</div>{diagramType === 'use_case_diagram' && <ResultSection title="Select use cases"><div className="use-case-picker">{requirements.map((item) => <label key={item.id}><input type="checkbox" checked={selectedUseCases.includes(item.id)} onChange={(event) => setSelectedUseCases(event.target.checked ? [...selectedUseCases, item.id] : selectedUseCases.filter((id) => id !== item.id))} />{item.id}: {item.title || item.description}</label>)}</div></ResultSection>}<ResultSection title={`${DIAGRAM_LABELS[diagramType]} preview`}><DiagramPreview source={diagramType === 'use_case_diagram' ? createUseCaseDiagram(requirements.filter((item) => selectedUseCases.includes(item.id))) : diagrams[diagramType]} /><details><summary>Mermaid source</summary><pre className="diagram-source">{diagramType === 'use_case_diagram' ? createUseCaseDiagram(requirements.filter((item) => selectedUseCases.includes(item.id))) : diagrams[diagramType] || 'No source returned.'}</pre></details></ResultSection></div>}
      {tab === 'tests' && <div className="tab-content"><ResultSection title="Generated test cases mapped to requirements"><TestCaseList items={testCases} /></ResultSection><ResultSection title="Suggested functionality covered"><List items={suggestions} /></ResultSection></div>}
      {tab === 'srs' && <div className="tab-content"><div className="document-actions"><button className="secondary" type="button" onClick={() => download('json', JSON.stringify({ ...data, original_source: data.source_text }, null, 2), 'application/json')}>Download JSON</button><button className="secondary" type="button" onClick={() => download('md', markdown, 'text/markdown')}>Download Markdown</button><button className="secondary" type="button" onClick={() => projectId && downloadDocx(projectId)}>Download DOCX</button><button className="secondary" type="button" onClick={() => window.print()}>Save as PDF</button></div><article className="srs-document"><h1>{improvedSrs.title || 'Improved SRS'}</h1><p>{improvedSrs.summary || analysis.summary}</p><p><b>Domain:</b> {data.suitable_domain || 'Not specified'}</p><p><b>Recommended technology:</b> {formatStack(data.recommended_tech_stack)}</p><h3>Functional requirements</h3><RequirementList items={requirements} /><h3>Non-functional requirements</h3><RequirementList items={nfrs} /><h3>User stories</h3><List items={data.user_stories} /><h3>Actors</h3><List items={data.actors} /><h3>Risks and assumptions</h3><List items={[...(data.risks || []), ...(data.assumptions || [])]} /><h3>Test cases</h3><TestCaseList items={testCases} /><h3>Diagrams</h3>{Object.entries(diagrams).map(([name, source]) => <section key={name}><h4>{DIAGRAM_LABELS[name] || name}</h4><DiagramPreview source={source} /><pre>{source}</pre></section>)}<h3>Suggestions and additions</h3><List items={suggestions} /><h3>Original source preserved</h3><pre className="source-text">{data.source_text}</pre></article></div>}
      {tab === 'report' && <div className="tab-content"><div className="score-grid"><InfoCard label="Quality score" value={`${data.quality_score ?? '—'} / 100`} /><InfoCard label="Confidence score" value={`${data.confidence_score ?? '—'} / 100`} /><InfoCard label="Requirements" value={`${requirements.length} functional · ${nfrs.length} non-functional`} /><InfoCard label="Test coverage" value={`${testCases.length} generated`} /></div><div className="report-columns"><ResultSection title="Confidence reasons"><List items={data.confidence_reasons} /></ResultSection><ResultSection title="Original vs improved changes"><List items={[...(data.change_summary?.improved || []), ...(data.change_summary?.added || []), ...(data.change_summary?.removed || []).map((item) => `Removed: ${item}`)]} /></ResultSection></div><ResultSection title="Issues and suggestions"><List items={[...(data.quality?.issues || []), ...suggestions]} /></ResultSection></div>}
    </section>
  );
}

function LegacyReportView({ result }) {
  const data = result.data || {};
  if (result.type === 'pitch') return <PitchResults data={data} />;

  const quality = data.quality || data;
  const analysis = data.analysis || data;
  const testCases = data.test_cases?.test_cases || data.test_cases || [];
  const requirements = data.functional_requirements || analysis.functional_requirements || [];
  const improved = quality.improved_requirements || [];

  return (
    <section className="report panel">
      <div className="panel-heading"><div><p className="eyebrow">RESULTS</p><h2>{result.type === 'pitch' ? 'Generated software requirements specification' : 'SRS improvement report'}</h2></div><span className="badge">COMPLETE</span></div>
      <div className="score-grid">
        <div className="score-card"><span>Quality score</span><strong>{quality.quality_score ?? data.quality_score ?? '—'}</strong><small>/ 100</small></div>
        <div className="score-card"><span>Confidence score</span><strong>{data.confidence_score ?? '—'}</strong><small>/ 100</small></div>
        <div className="score-card"><span>Requirements</span><strong>{requirements.length}</strong><small>identified</small></div>
        <div className="score-card"><span>Test cases</span><strong>{testCases.length}</strong><small>generated</small></div>
      </div>
      {analysis.summary && <div className="report-block"><h3>Summary</h3><p>{analysis.summary}</p></div>}
      <div className="report-columns">
        <div className="report-block"><h3>{result.type === 'pitch' ? 'Functional requirements' : 'Detected requirements'}</h3><List items={requirements} /></div>
        <div className="report-block"><h3>{result.type === 'pitch' ? 'Actors' : 'Quality issues'}</h3><List items={result.type === 'pitch' ? (analysis.actors || []) : (quality.issues || []).map((issue) => `${issue.severity}: ${issue.reason}`)} /></div>
      </div>
      {improved.length > 0 && <div className="report-block"><h3>Improved requirements</h3><List items={improved} /></div>}
      {data.clarification_questions?.length > 0 && <div className="report-block"><h3>Clarification questions</h3><List items={data.clarification_questions.map((item) => `${item.question} — ${item.reason}`)} /></div>}
      {data.refactored_srs && <div className="report-block"><h3>Refactored SRS preview</h3><p>{data.refactored_srs.summary || 'A refactored SRS was generated successfully.'}</p><List items={data.refactored_srs.functional_requirements || []} /></div>}
      {testCases.length > 0 && <div className="report-block"><h3>Test cases</h3><div className="test-case-list">{testCases.map((testCase) => <article className="test-case" key={testCase.id}><strong>{testCase.id}</strong><span>{testCase.requirement}</span><small>{testCase.expected_result}</small></article>)}</div></div>}
      {(data.uml_diagram || data.architecture_diagram) && <div className="report-block"><h3>Diagram source</h3><pre>{data.uml_diagram || data.architecture_diagram}</pre></div>}
    </section>
  );
}

const DIAGRAM_LABELS = {
  class_diagram: 'Class diagram',
  er_diagram: 'ER diagram',
  architecture_diagram: 'Architecture diagram',
  use_case_diagram: 'Use-case diagram',
  data_flow_diagram: 'Data-flow diagram',
  sequence_diagram: 'Sequence diagram',
};

function PitchResults({ data, projectId, onResultUpdate }) {
  const [tab, setTab] = useState('specification');
  const [diagramType, setDiagramType] = useState('architecture_diagram');
  const [generationState, setGenerationState] = useState({ status: 'idle', message: '' });
  const requirements = data.functional_requirements || [];
  const nfrs = data.non_functional_requirements || [];
  const [selectedUseCases, setSelectedUseCases] = useState(requirements.map((item) => item.id));
  React.useEffect(() => setSelectedUseCases(requirements.map((item) => item.id)), [data]);
  const diagrams = data.diagram_sources || {};
  const testCases = data.test_cases || [];
  const srs = { ...data, diagram_sources: diagrams };
  const completeMarkdown = buildSrsMarkdown(srs);
  const savedGenerationNote = data.generation_note || '';
  const isLegacyStoppedFailover = savedGenerationNote.includes('automatic fallback stopped');

  const download = (extension, content, mime) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${(data.title || 'specmind-srs').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.${extension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const retryAiGeneration = async () => {
    setGenerationState({ status: 'loading', message: 'Retrying AI SRS generation...' });
    try {
      const response = await api.post(`/projects/${projectId}/generate-srs`);
      setGenerationState({ status: 'success', message: 'AI SRS generation completed.' });
      onResultUpdate?.(response.data.data || {});
    } catch (error) {
      setGenerationState({ status: 'error', message: apiError(error, 'AI generation is unavailable. Your saved draft remains available.') });
    }
  };

  const markdown = `# ${data.title || 'Software Requirements Specification'}\n\n## Summary\n${data.summary || ''}\n\n## Domain\n${data.suitable_domain || ''}\n\n## Recommended stack\n${Object.entries(data.recommended_tech_stack || {}).map(([key, value]) => `- **${key}:** ${Array.isArray(value) ? value.join(', ') : value}`).join('\n')}\n\n## Functional requirements\n${requirements.map((item) => `- **${item.id || ''} ${item.title || ''}:** ${item.description || ''}`).join('\n')}\n\n## Non-functional requirements\n${nfrs.map((item) => `- **${item.id || ''} ${item.category || ''}:** ${item.description || ''}`).join('\n')}\n\n## User stories\n${(data.user_stories || []).map((item) => `- ${item.story || item}`).join('\n')}\n\n## Acceptance criteria\n${requirements.flatMap((item) => item.acceptance_criteria || []).map((item) => `- ${item}`).join('\n')}\n\n## Risks and assumptions\n${[...(data.risks || []), ...(data.assumptions || [])].map((item) => `- ${typeof item === 'string' ? item : JSON.stringify(item)}`).join('\n')}`;

  return (
    <section className="results panel" aria-label="Mode 1 generated results">
      <div className="panel-heading"><div><p className="eyebrow">MODE 1 RESULTS</p><h2>{data.title || 'Professional software specification'}</h2><p className="result-summary">{data.summary}</p></div><span className="badge">{data.generation_status === 'draft' ? 'DRAFT' : 'COMPLETE'}</span></div>
      {data.generation_status === 'draft' && <div className="status error document-warning"><strong>Pitch-based draft</strong><p>{isLegacyStoppedFailover ? 'This draft contains a saved result from the previous provider routing attempt. Retry to run it through the current NVIDIA → OpenRouter → Gemini failover chain.' : savedGenerationNote}</p><button className="secondary" type="button" onClick={retryAiGeneration} disabled={generationState.status === 'loading'}>{generationState.status === 'loading' ? 'Retrying…' : 'Retry AI generation'}</button>{generationState.message && <p className={`status ${generationState.status}`}>{generationState.message}</p>}</div>}
      <nav className="result-tabs" aria-label="Generated result sections">
        {[['specification', 'Specification Generator'], ['diagrams', 'Diagrams'], ['test-cases', 'Test Cases'], ['srs', 'SRS Document'], ['report', 'Report']].map(([id, label]) => <button key={id} type="button" className={tab === id ? 'result-tab active' : 'result-tab'} onClick={() => setTab(id)}>{label}</button>)}
      </nav>

      {tab === 'specification' && <div className="tab-content">
        <div className="summary-grid"><InfoCard label="Suitable domain" value={data.suitable_domain} /><InfoCard label="Recommended stack" value={Object.entries(data.recommended_tech_stack || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' · ')} /></div>
        <ResultSection title="Functional requirements"><RequirementList items={requirements} /></ResultSection>
        <ResultSection title="Non-functional requirements"><RequirementList items={nfrs} /></ResultSection>
        <div className="report-columns"><ResultSection title="User stories"><List items={data.user_stories} /></ResultSection><ResultSection title="Acceptance criteria"><List items={requirements.flatMap((item) => item.acceptance_criteria || [])} /></ResultSection></div>
        <div className="report-columns"><ResultSection title="Predicted risks"><List items={data.risks} /></ResultSection><ResultSection title="Assumptions"><List items={data.assumptions} /></ResultSection></div>
      </div>}

      {tab === 'diagrams' && <div className="tab-content"><div className="diagram-picker">{Object.entries(DIAGRAM_LABELS).map(([id, label]) => <button type="button" key={id} className={diagramType === id ? 'diagram-button active' : 'diagram-button'} onClick={() => setDiagramType(id)}>{label}</button>)}</div>{diagramType === 'use_case_diagram' && <ResultSection title="Select use cases"><div className="use-case-picker">{requirements.map((item) => <label key={item.id}><input type="checkbox" checked={selectedUseCases.includes(item.id)} onChange={(event) => setSelectedUseCases(event.target.checked ? [...selectedUseCases, item.id] : selectedUseCases.filter((id) => id !== item.id))} />{item.id}: {item.title || item.description}</label>)}</div></ResultSection>}<ResultSection title={`${DIAGRAM_LABELS[diagramType]} preview`}><DiagramPreview source={diagramType === 'use_case_diagram' ? createUseCaseDiagram(requirements.filter((item) => selectedUseCases.includes(item.id))) : diagrams[diagramType]} /><details><summary>Mermaid source</summary><pre className="diagram-source">{diagramType === 'use_case_diagram' ? createUseCaseDiagram(requirements.filter((item) => selectedUseCases.includes(item.id))) : diagrams[diagramType] || 'No source was returned for this diagram.'}</pre></details></ResultSection></div>}

      {tab === 'test-cases' && <div className="tab-content"><ResultSection title="Test cases by functionality"><TestCaseList items={testCases} /></ResultSection></div>}

      {tab === 'srs' && <div className="tab-content"><div className="document-actions"><button className="secondary" type="button" onClick={() => download('json', JSON.stringify(srs, null, 2), 'application/json')}>Download JSON</button><button className="secondary" type="button" onClick={() => download('md', completeMarkdown, 'text/markdown')}>Download Markdown</button><button className="secondary" type="button" onClick={() => projectId && downloadDocx(projectId)}>Download DOCX</button><button className="secondary" type="button" onClick={() => window.print()}>Save as PDF</button></div><article className="srs-document"><h1>{data.title}</h1><p>{data.summary}</p><h3>Domain and technology</h3><p><b>{data.suitable_domain}</b></p><p>{formatStack(data.recommended_tech_stack)}</p><h3>Functional requirements</h3><RequirementList items={requirements} /><h3>Non-functional requirements</h3><RequirementList items={nfrs} /><h3>User stories</h3><List items={data.user_stories} /><h3>Actors</h3><List items={data.actors} /><h3>Risks and assumptions</h3><List items={[...(data.risks || []), ...(data.assumptions || [])]} /><h3>Test cases</h3><TestCaseList items={testCases} /><h3>Diagrams</h3>{Object.entries(diagrams).map(([name, source]) => <section key={name}><h4>{DIAGRAM_LABELS[name] || name}</h4><DiagramPreview source={source} /><pre>{source}</pre></section>)}</article></div>}

      {tab === 'report' && <div className="tab-content"><div className="score-grid"><InfoCard label="Quality score" value={`${data.quality_score ?? '—'} / 100`} /><InfoCard label="Confidence score" value={`${data.confidence_score ?? '—'} / 100`} /><InfoCard label="Requirements" value={`${requirements.length} functional · ${nfrs.length} non-functional`} /><InfoCard label="Test coverage" value={`${testCases.length} linked tests`} /></div><div className="report-columns"><ResultSection title="Confidence reasons"><List items={data.confidence_reasons} /></ResultSection><ResultSection title="Quality issues"><List items={data.confidence_issues} /></ResultSection></div><ResultSection title="Recommendations"><List items={data.suggestions} /></ResultSection></div>}
    </section>
  );
}

function InfoCard({ label, value }) { return <div className="info-card"><span>{label}</span><strong>{value || 'Not specified'}</strong></div>; }
function apiError(error, fallback) {
  if (error.response?.data?.detail || error.response?.data?.message) return error.response.data.detail || error.response.data.message;
  if (!error.response && error.message === 'Network Error') return `Cannot reach the SpecMind API at ${api.defaults.baseURL}. Check that the backend is running on port 8000 and reload this page.`;
  return error.message || fallback;
}
function ResultSection({ title, children }) { return <section className="result-section"><h3>{title}</h3>{children}</section>; }
function RequirementList({ items }) { return <div className="requirement-list">{items?.length ? items.map((item, index) => { const origin = item.origin || 'generated'; return <article key={item.id || index}><strong>{item.id} {item.title || item.category}</strong><span className={`origin-tag origin-${origin}`}>{origin}</span><p>{item.description || item}</p>{item.source_trace && <small className="source-trace">Source: {item.source_trace}</small>}{item.acceptance_criteria?.length > 0 && <><b>Acceptance criteria</b><List items={item.acceptance_criteria} /></>}</article>; }) : <p className="muted">No items returned.</p>}</div>; }

function TestCaseList({ items }) {
  return <div className="test-case-list">{items?.length ? items.map((item, index) => <article className="test-case" key={item.id || index}><strong>{item.id || `TC-${index + 1}`} · {item.requirement_id || item.requirement || 'Requirement'}</strong>{item.coverage_gap_filled && <small className="coverage-generated">Generated to fill a missing test coverage gap.</small>}<span>{item.precondition || 'No precondition specified.'}</span><ol>{(item.steps || []).map((step, stepIndex) => <li key={stepIndex}>{step}</li>)}</ol><small><b>Expected:</b> {item.expected_result || 'No expected result specified.'}</small></article>) : <p className="muted">No test cases returned.</p>}</div>;
}

function DiagramPreview({ source }) {
  const id = React.useId().replace(/:/g, '');
  const [rendered, setRendered] = useState('');
  const [error, setError] = useState('');
  React.useEffect(() => {
    let active = true;
    const cleanSource = (source || '').replace(/^```(?:mermaid)?\s*/i, '').replace(/\s*```$/, '').trim();
    if (!cleanSource) { setRendered(''); setError('No diagram source returned.'); return () => { active = false; }; }
    import('mermaid').then(({ default: mermaid }) => {
      if (!active) return;
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'dark' });
      return mermaid.render(`diagram-${id}`, cleanSource).then(({ svg }) => { if (active) { setRendered(svg); setError(''); } });
    }).catch(() => { if (active) { setRendered(''); setError('Preview unavailable. The Mermaid source is available below to inspect or edit.'); } });
    return () => { active = false; };
  }, [source, id]);
  return <div className="diagram-preview">{rendered ? <div className="diagram-svg" dangerouslySetInnerHTML={{ __html: rendered }} /> : <p className="muted">{error}</p>}</div>;
}

function createUseCaseDiagram(items) {
  const cases = items || [];
  const rows = cases.map((item, index) => {
    const label = String(item.title || item.description || item.id || `Use case ${index + 1}`).replace(/["\n\r]/g, ' ').slice(0, 100);
    return `  Stakeholder --> UC${index}((${JSON.stringify(label)}))`;
  });
  return ['flowchart LR', '  Stakeholder[Stakeholder]', ...rows].join('\n');
}

function formatStack(stack = {}) {
  return Object.entries(stack || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' · ');
}

function buildSrsMarkdown(data, includeSource = false) {
  const lines = [`# ${data.title || 'Software Requirements Specification'}`, '', data.summary || '', '', `## Domain`, data.suitable_domain || 'Not specified', '', '## Recommended technology stack', formatStack(data.recommended_tech_stack) || 'Not specified'];
  const addList = (title, items, render) => { lines.push('', `## ${title}`); if (!items?.length) lines.push('None specified.'); else items.forEach((item) => lines.push(`- ${render(item)}`)); };
  const defaultOrigin = data.source_text ? 'extracted' : 'generated';
  const renderRequirement = (item) => `**${item.id || ''} ${item.title || item.category || ''}** (${item.origin || defaultOrigin}): ${item.description || item}${item.source_trace ? ` — Source: ${item.source_trace}` : ''}${item.acceptance_criteria?.length ? ` — Acceptance criteria: ${item.acceptance_criteria.join('; ')}` : ''}`;
  addList('Functional requirements', data.functional_requirements, renderRequirement);
  addList('Non-functional requirements', data.non_functional_requirements, renderRequirement);
  addList('User stories', data.user_stories, (item) => `${item.story || item}${item.acceptance_criteria?.length ? ` — Acceptance criteria: ${item.acceptance_criteria.join('; ')}` : ''}`);
  addList('Actors', data.actors, (item) => typeof item === 'string' ? item : item.name || item.title || JSON.stringify(item));
  addList('Risks', data.risks, (item) => typeof item === 'string' ? item : `${item.risk || item.description || JSON.stringify(item)}${item.mitigation ? ` — Mitigation: ${item.mitigation}` : ''}`);
  addList('Assumptions', data.assumptions, (item) => typeof item === 'string' ? item : item.description || JSON.stringify(item));
  addList('Test cases', data.test_cases, (item) => `**${item.id || ''} ${item.requirement_id || item.requirement || ''}**: ${item.precondition || ''}; steps: ${(item.steps || []).join('; ')}; expected: ${item.expected_result || ''}`);
  lines.push('', '## Diagrams');
  Object.entries(data.diagram_sources || {}).forEach(([name, source]) => lines.push('', `### ${DIAGRAM_LABELS[name] || name}`, '```mermaid', source, '```'));
  if (includeSource && data.source_text) lines.push('', '## Original source text', data.source_text);
  return lines.join('\n');
}

async function downloadDocx(projectId) {
  try {
    const response = await api.get(`/projects/${projectId}/export/docx`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'specmind-srs.docx';
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    const message = error.response?.data?.detail || 'Unable to export DOCX. Please try again.';
    window.alert(message);
  }
}

function List({ items }) {
  if (!items?.length) return <p className="muted">No items returned.</p>;
  return <ul className="report-list">{items.map((item, index) => <li key={item.id || index}>{typeof item === 'string' ? item : item.story || item.risk || item.description || item.title || item.requirement || item.question || item.reason || JSON.stringify(item)}{typeof item === 'object' && item.acceptance_criteria?.length ? <ul>{item.acceptance_criteria.map((criterion, criterionIndex) => <li key={criterionIndex}>{criterion}</li>)}</ul> : null}{typeof item === 'object' && item.mitigation ? ` · Mitigation: ${item.mitigation}` : ''}{typeof item === 'object' && item.suggestion ? ` · Suggestion: ${item.suggestion}` : ''}</li>)}</ul>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);
