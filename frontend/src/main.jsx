import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import './styles.css';
import DiagramPreview from './components/DiagramPreview.jsx';
import { buildUseCaseDiagram, DIAGRAM_LABELS, selectDiagramSource } from './diagramUtils.js';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('specmind_access_token');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    const isAuthRequest = /\/auth\/(login|register)(?:\?|$)/.test(url);
    if (error.response?.status === 401 && !isAuthRequest) {
      sessionStorage.removeItem('specmind_access_token');
      sessionStorage.removeItem('specmind_user');
      window.dispatchEvent(new Event('specmind:unauthorized'));
    }
    return Promise.reject(error);
  },
);

function readSessionUser() {
  try {
    return JSON.parse(sessionStorage.getItem('specmind_user') || 'null');
  } catch {
    return null;
  }
}

function App() {
  const [user, setUser] = useState(readSessionUser);
  const [page, setPage] = useState('dashboard');
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [creationMode, setCreationMode] = useState('pitch');

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setPage('dashboard');
    };
    window.addEventListener('specmind:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('specmind:unauthorized', handleUnauthorized);
  }, []);

  if (!user) {
    return <AuthPage onAuthenticated={(authenticatedUser) => {
      setUser(authenticatedUser);
      setPage('create');
    }} />;
  }

  const logout = () => {
    sessionStorage.removeItem('specmind_access_token');
    sessionStorage.removeItem('specmind_user');
    setUser(null);
    setPage('dashboard');
  };

  if (page === 'create') {
    return <ProjectCreationPage key={creationMode} user={user} initialMode={creationMode} onLogout={logout} onBack={() => setPage('dashboard')} onNewProject={(mode) => { setCreationMode(mode); setPage('create'); }} />;
  }

  if (page === 'workspace' && activeProjectId) return <WorkspacePage projectId={activeProjectId} user={user} onLogout={logout} onBack={() => setPage('dashboard')} onNewProject={(mode) => { setCreationMode(mode); setPage('create'); }} />;
  return <DashboardPage user={user} onLogout={logout} onNewProject={(mode = 'pitch') => { setCreationMode(mode); setPage('create'); }} onOpenProject={(id) => { setActiveProjectId(id); setPage('workspace'); }} />;
}

function AppHeader({ user, onLogout, onNavigateProjects, onNewProject, currentPage }) {
  return (
    <header className="topbar">
      <button className="topbar-brand" type="button" onClick={onNavigateProjects} aria-label="SpecMind AI home">SpecMind <em>AI</em></button>
      <nav className="app-navigation" aria-label="Main navigation">
        <button className="app-nav-link" type="button" aria-current={currentPage === 'dashboard' || currentPage === 'workspace' ? 'page' : undefined} onClick={onNavigateProjects}>Projects</button>
        <button className="app-nav-link app-nav-primary" type="button" aria-current={currentPage === 'create' ? 'page' : undefined} onClick={() => onNewProject('pitch')}>New project</button>
      </nav>
      <div className="account"><span>{user.name || user.email}</span><button type="button" onClick={onLogout}>Log out</button></div>
    </header>
  );
}

function AuthPage({ onAuthenticated }) {
  const [authMode, setAuthMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [state, setState] = useState({ status: 'idle', message: '' });

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const submit = async (event) => {
    event.preventDefault();
    const email = form.email.trim().toLowerCase();
    setState({ status: 'loading', message: '' });
    try {
      const response = authMode === 'register'
        ? await api.post('/auth/register', { full_name: form.name.trim(), email, password: form.password })
        : await api.post('/auth/login', { email, password: form.password });
      const data = response.data?.data;
      if (!data?.access_token || !data?.user) throw new Error('The server returned an incomplete sign-in response.');
      const authenticatedUser = {
        id: data.user.id,
        email: data.user.email,
        name: data.user.full_name,
        created_at: data.user.created_at,
      };
      sessionStorage.setItem('specmind_access_token', data.access_token);
      sessionStorage.setItem('specmind_user', JSON.stringify(authenticatedUser));
      onAuthenticated(authenticatedUser);
    } catch (error) {
      setState({ status: 'error', message: apiError(error, authMode === 'register' ? 'Unable to create your account. Please try again.' : 'Unable to sign in. Please check your details and try again.') });
    }
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
          <label>Password<input type="password" name="password" value={form.password} onChange={update} required minLength={authMode === 'register' ? 8 : 1} placeholder={authMode === 'register' ? 'At least 8 characters' : 'Your password'} /></label>
          <button className="primary auth-submit" disabled={state.status === 'loading'}>{state.status === 'loading' ? 'Working...' : authMode === 'login' ? 'Sign in' : 'Create account'}</button>
          {state.message && <p className={`status ${state.status}`}>{state.message}</p>}
        </form>
        <p className="auth-switch">
          {authMode === 'login' ? 'New to SpecMind?' : 'Already have an account?'}{' '}
          <button type="button" disabled={state.status === 'loading'} onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setState({ status: 'idle', message: '' }); }}>
            {authMode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
        <p className="demo-note">Your workspace is protected by your account.</p>
      </section>
    </main>
  );
}

function DashboardPage({ user, onLogout, onNewProject, onOpenProject }) {
  const [projects, setProjects] = useState([]);
  const [state, setState] = useState({ status: 'loading', message: 'Loading your projects...' });
  const [query, setQuery] = useState('');
  const [modeFilter, setModeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortOrder, setSortOrder] = useState('recent');

  const loadProjects = async () => {
    setState({ status: 'loading', message: 'Loading your projects...' });
    try {
      const response = await api.get('/projects');
      setProjects(Array.isArray(response.data?.data) ? response.data.data : []);
      setState({ status: 'idle', message: '' });
    } catch (error) {
      setState({ status: 'error', message: apiError(error, 'Unable to load projects. Check that the backend is running.') });
    }
  };

  React.useEffect(() => { loadProjects(); }, []);

  const modes = [...new Set(projects.map((project) => project.creation_mode).filter(Boolean))].sort();
  const statuses = [...new Set(projects.map((project) => project.status).filter(Boolean))].sort();
  const visibleProjects = projects
    .filter((project) => {
      const searchText = `${project.name || ''} ${project.description || ''}`.toLowerCase();
      return searchText.includes(query.trim().toLowerCase())
        && (modeFilter === 'all' || project.creation_mode === modeFilter)
        && (statusFilter === 'all' || project.status === statusFilter);
    })
    .sort((a, b) => {
      if (sortOrder === 'name') return String(a.name || '').localeCompare(String(b.name || ''));
      const aDate = dateSortValue(a.created_at);
      const bDate = dateSortValue(b.created_at);
      if (aDate === null || bDate === null) return aDate === bDate ? 0 : aDate === null ? 1 : -1;
      return sortOrder === 'oldest' ? aDate - bDate : bDate - aDate;
    });

  return (
    <main className="shell">
      <AppHeader user={user} onLogout={onLogout} onNavigateProjects={() => {}} onNewProject={onNewProject} currentPage="dashboard" />
      <section className="dashboard-heading">
        <div><p className="eyebrow">REQUIREMENTS WORKSPACE</p><h1>Welcome back, {user.name?.split(' ')[0] || 'builder'}.</h1><p className="lede">Turn an early idea into a testable specification, or strengthen an SRS you already have.</p></div>
      </section>
      <section className="dashboard-entry-points" aria-labelledby="start-project-heading">
        <div className="section-heading"><div><p className="eyebrow">START A WORKFLOW</p><h2 id="start-project-heading">What would you like to work on?</h2></div></div>
        <div className="entry-point-grid">
          <button className="entry-point-card" type="button" onClick={() => onNewProject('pitch')}>
            <span className="entry-point-label">IDEA TO SRS</span><strong>Create from an idea</strong><span>Shape a product concept into requirements, user stories, tests, and a structured SRS.</span><span className="entry-point-action">Start with an idea <span aria-hidden="true">→</span></span>
          </button>
          <button className="entry-point-card" type="button" onClick={() => onNewProject('upload')}>
            <span className="entry-point-label">SRS IMPROVEMENT</span><strong>Improve an existing SRS</strong><span>Upload a specification to find gaps, resolve ambiguity, and review improvements.</span><span className="entry-point-action">Choose a document <span aria-hidden="true">→</span></span>
          </button>
        </div>
      </section>
      <section className="dashboard-section">
        <div className="section-heading dashboard-project-heading"><div><p className="eyebrow">YOUR WORK</p><h2>Recent projects</h2></div><button className="refresh-button" type="button" onClick={loadProjects} disabled={state.status === 'loading'}>{state.status === 'loading' ? 'Refreshing…' : 'Refresh'}</button></div>
        {state.status === 'loading' && <div className="empty-state" role="status"><strong>Loading projects</strong><span>{state.message}</span></div>}
        {state.status === 'error' && <div className="dashboard-error" role="alert"><div><strong>Projects could not be loaded</strong><p>{state.message}</p></div><button className="secondary" type="button" onClick={loadProjects}>Try again</button></div>}
        {state.status === 'idle' && !projects.length && <div className="empty-state"><strong>No projects yet</strong><span>Your created projects will appear here.</span></div>}
        {state.status === 'idle' && !!projects.length && <>
          <div className="project-controls" role="search" aria-label="Search and filter projects">
            <label className="project-search">Search projects<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or description" /></label>
            <label>Workflow<select value={modeFilter} onChange={(event) => setModeFilter(event.target.value)}><option value="all">All workflows</option>{modes.map((mode) => <option key={mode} value={mode}>{workflowLabel(mode)}</option>)}</select></label>
            <label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All statuses</option>{statuses.map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
            <label>Sort by<select value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}><option value="recent">Most recent</option><option value="oldest">Oldest</option><option value="name">Name A–Z</option></select></label>
          </div>
          {!visibleProjects.length
            ? <div className="empty-state"><strong>No matching projects</strong><span>Try changing the search or filters.</span><button className="secondary" type="button" onClick={() => { setQuery(''); setModeFilter('all'); setStatusFilter('all'); }}>Clear search and filters</button></div>
            : <div className="project-grid">{visibleProjects.map((project) => <ProjectCard key={project.id} project={project} onOpen={() => onOpenProject(project.id)} />)}</div>}
        </>}
      </section>
    </main>
  );
}

function ProjectCard({ project, onOpen }) {
  const createdDate = formatProjectDate(project.created_at);
  return (
    <button className="project-card project-card-button" type="button" onClick={onOpen} aria-label={`Open ${project.name || 'project'} workspace, ${workflowLabel(project.creation_mode)}, status ${project.status || 'unavailable'}`}>
      <span className="project-card-top"><span className="project-mode">{workflowLabel(project.creation_mode)}</span><span className="project-status">{project.status || 'Status unavailable'}</span></span>
      <strong className="project-card-title">{project.name || 'Project name unavailable'}</strong>
      <span className="project-card-description">{project.description || 'Open the saved project workspace.'}</span>
      <span className="project-card-footer">{createdDate ? `Created ${createdDate} · ` : ''}Open workspace <span aria-hidden="true">→</span></span>
    </button>
  );
}

function workflowLabel(mode) {
  if (mode === 'pitch') return 'Idea to SRS';
  if (mode === 'upload') return 'SRS improvement';
  return mode || 'Workflow unavailable';
}

function formatProjectDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString();
}

function dateSortValue(value) {
  const timestamp = value ? new Date(value).getTime() : Number.NaN;
  if (!Number.isFinite(timestamp)) return null;
  return timestamp;
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return '';
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ProjectCreationPage({ user, initialMode = 'pitch', onLogout, onBack, onNewProject }) {
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState({ name: '', description: '', idea_pitch: '', title: '' });
  const [file, setFile] = useState(null);
  const [state, setState] = useState({ status: 'idle', message: '' });
  const [result, setResult] = useState(null);
  const [projectId, setProjectId] = useState(null);
  const [savedUpload, setSavedUpload] = useState(null);
  const submissionInProgress = useRef(false);

  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const changeMode = (nextMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    setProjectId(null);
    setResult(null);
    setSavedUpload(null);
    setState({ status: 'idle', message: '' });
  };

  const requestUploadReport = async (requirementId) => {
    const response = await api.post(`/requirements/${requirementId}/generate-report`);
    return response.data.data;
  };

  const retrySavedAnalysis = async () => {
    if (!savedUpload || submissionInProgress.current) return;
    submissionInProgress.current = true;
    setState({ status: 'loading', message: 'Retrying analysis for the uploaded document...' });
    try {
      const reportData = await requestUploadReport(savedUpload.requirementId);
      const generatedDraft = reportData?.generation_status === 'draft';
      setResult({ type: 'upload', requirementId: savedUpload.requirementId, data: reportData });
      setState({
        status: 'success',
        message: generatedDraft
          ? 'A source-based draft is ready; AI refinement can be retried from the report.'
          : 'Analysis completed successfully.',
      });
    } catch (error) {
      setState({ status: 'error', message: `Your document is uploaded and saved. Analysis did not finish: ${apiError(error, 'Try analysis again.')}` });
    } finally {
      submissionInProgress.current = false;
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    if (submissionInProgress.current) return;
    if (mode === 'upload' && savedUpload) {
      await retrySavedAnalysis();
      return;
    }
    submissionInProgress.current = true;
    setResult(null);
    setState({ status: 'loading', message: mode === 'upload' ? 'Preparing your SRS upload...' : 'Creating your project...' });
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
        const requirementId = requirement.data.data.id;
        setSavedUpload({ requirementId });
        setState({ status: 'loading', message: 'Analyzing requirements, test cases, and quality...' });
        const reportData = await requestUploadReport(requirementId);
        generatedDraft = reportData?.generation_status === 'draft';
        setResult({ type: 'upload', requirementId, data: reportData });
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
          ? `Your document is uploaded and saved. Use Retry analysis to continue: ${apiError(error, 'Analysis could not be completed.')}`
          : apiError(error, 'Something went wrong.'),
      });
    } finally {
      submissionInProgress.current = false;
    }
  };

  const startAnotherProject = () => {
    setForm({ name: '', description: '', idea_pitch: '', title: '' });
    setFile(null);
    setProjectId(null);
    setSavedUpload(null);
    setResult(null);
    setState({ status: 'idle', message: '' });
  };

  return (
    <main className="shell">
      <AppHeader user={user} onLogout={onLogout} onNavigateProjects={onBack} onNewProject={onNewProject} currentPage="create" />
      {result ? (
        <>
          <section className={`creation-result-transition ${result.data?.generation_status === 'draft' ? 'is-draft' : 'is-complete'}`} aria-live="polite">
            <p className="eyebrow">{result.data?.generation_status === 'draft' ? 'DRAFT READY' : 'WORKFLOW COMPLETE'}</p>
            <h1 className="creation-result-title">{result.data?.generation_status === 'draft' ? 'Your draft is ready to review' : mode === 'pitch' ? 'Your SRS is ready to review' : 'Your analysis is ready to review'}</h1>
            <p className="lede">{mode === 'upload'
              ? 'Review extracted information, generated content, and suggested improvements in the sections below. Suggestions are not marked as approved.'
              : 'Review the generated requirements, stories, risks, tests, diagrams, and SRS below.'}</p>
            <button className="secondary" type="button" onClick={startAnotherProject}>Start another project</button>
          </section>
          <ReportView result={result} projectId={projectId} project={{ name: form.name, description: form.description, creation_mode: mode }} onResultUpdate={(data) => setResult((current) => current ? { ...current, data } : current)} />
        </>
      ) : (
        <>
          <section className="hero">
            <p className="eyebrow">REQUIREMENTS INTELLIGENCE</p>
            <h1>{mode === 'pitch' ? 'Turn your idea into a plan your team can build.' : 'Make an existing SRS clearer and more complete.'}</h1>
            <p className="lede">{mode === 'pitch'
              ? 'Share the problem, users, and intended outcome. SpecMind will generate a structured SRS with requirements and supporting engineering artifacts.'
              : 'Upload a PDF or DOCX specification. SpecMind will analyze its content, identify gaps and ambiguity, and prepare recommendations for review.'}</p>
          </section>

          <section className="mode-grid" aria-label="Choose a project workflow">
            <button type="button" className={mode === 'pitch' ? 'mode-card active' : 'mode-card'} aria-pressed={mode === 'pitch'} disabled={state.status === 'loading'} onClick={() => changeMode('pitch')}>
              <span className="mode-icon" aria-hidden="true">✦</span>
              <strong>Create from an idea</strong>
              <span>Generate requirements, user stories, acceptance criteria, risks, diagrams, tests, and an SRS.</span>
            </button>
            <button type="button" className={mode === 'upload' ? 'mode-card active' : 'mode-card'} aria-pressed={mode === 'upload'} disabled={state.status === 'loading'} onClick={() => changeMode('upload')}>
              <span className="mode-icon" aria-hidden="true">↥</span>
              <strong>Improve an existing SRS</strong>
              <span>Analyze an existing specification, then review extracted information and proposed improvements.</span>
            </button>
          </section>

          <form className="panel creation-form" onSubmit={submit}>
            <div className="panel-heading">
              <div><p className="eyebrow">PROJECT SETUP</p><h2>{mode === 'pitch' ? 'Start with the project' : 'Set up your SRS review'}</h2></div>
              <span className="badge">{mode === 'pitch' ? 'IDEA TO SRS' : 'SRS IMPROVEMENT'}</span>
            </div>
            <section className="creation-field-group" aria-labelledby="project-details-heading">
              <div className="creation-group-heading"><h3 id="project-details-heading">1. Project details</h3><p>Give this work a name and add context if it will help shape the results.</p></div>
              <label>Project name<input name="name" value={form.name} onChange={update} required placeholder="e.g. Campus transport planner" /></label>
              <label><span className="field-label-title">Project context <span className="optional-label">Optional</span></span><textarea name="description" value={form.description} onChange={update} placeholder="Who is this for, and what outcome matters?" rows="3" /></label>
            </section>
            <section className="creation-field-group" aria-labelledby="source-details-heading">
              <div className="creation-group-heading"><h3 id="source-details-heading">{mode === 'pitch' ? '2. Describe the idea' : '2. Choose the SRS document'}</h3><p>{mode === 'pitch' ? 'A few sentences about the problem and intended experience are a useful starting point.' : 'The document text is extracted for analysis. You can add an optional title and context.'}</p></div>
              {mode === 'pitch' ? (
                <label>Idea pitch<textarea name="idea_pitch" value={form.idea_pitch} onChange={update} required placeholder="For example: help university students find available campus shuttles and plan accessible trips." rows="7" /></label>
              ) : (
                <>
                  <label><span className="field-label-title">Document title <span className="optional-label">Optional</span></span><input name="title" value={form.title} onChange={update} placeholder={file?.name || 'Uses the selected filename if left blank'} /></label>
                  <div className="file-picker">
                    <label className="upload" htmlFor="srs-document"><span className="upload-title">{file ? 'Replace selected document' : 'Choose an SRS document'}</span><span className="upload-cta" aria-hidden="true">Browse files</span><input id="srs-document" type="file" accept=".pdf,.docx" aria-describedby="upload-guidance" disabled={state.status === 'loading'} onChange={(event) => { setFile(event.target.files?.[0] || null); setSavedUpload(null); }} required={!savedUpload} /></label>
                    <p id="upload-guidance" className="field-help">PDF or DOCX, up to 10 MB. Text is extracted from PDF pages and DOCX content.</p>
                    {file && <p className="selected-file" role="status"><strong>Selected:</strong> {file.name} <span>({formatFileSize(file.size)})</span></p>}
                  </div>
                </>
              )}
            </section>
            <div className="creation-submit-row">
              <button className="primary" type="submit" disabled={state.status === 'loading'}>{state.status === 'loading' ? (savedUpload ? 'Retrying analysis…' : mode === 'pitch' ? 'Generating your SRS…' : 'Uploading and analyzing…') : savedUpload ? 'Retry analysis' : mode === 'pitch' ? 'Create project and generate SRS' : 'Upload and analyze SRS'}</button>
              {state.status === 'loading' && <span className="field-help" role="status">{state.message}</span>}
            </div>
            {state.status === 'error' && <p className="status error" role="alert">{state.message}</p>}
          </form>
        </>
      )}
    </main>
  );
}

function WorkspaceHeading({ project, result, documentName }) {
  const generationStatus = result?.generation_status;
  return (
    <section className="workspace-heading panel" aria-labelledby="workspace-title">
      <div className="workspace-heading-main">
        <p className="eyebrow">PROJECT WORKSPACE</p>
        <h1 id="workspace-title">{project.name}</h1>
        {project.description && <p className="lede">{project.description}</p>}
      </div>
      <div className="workspace-context" aria-label="Project context">
        {project.creation_mode && <span className="workspace-context-badge">{workflowLabel(project.creation_mode)}</span>}
        {documentName && <span className="workspace-context-detail">Source: {documentName}</span>}
        {project.status && <span className="workspace-context-detail">Project status: {project.status}</span>}
        {generationStatus && <span className={`workspace-status ${generationStatus === 'draft' ? 'is-draft' : ''}`}>{generationStatus}</span>}
      </div>
    </section>
  );
}

function WorkspacePage({ projectId, user, onLogout, onBack, onNewProject }) {
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
      const result = response.data.data || {};
      setWorkspace({ ...workspace, result });
      setState({
        status: result.generation_status === 'draft' ? 'error' : 'success',
        message: result.generation_status === 'draft'
          ? (result.generation_note || 'AI providers are still unavailable. The structured draft was preserved; retry when a provider is available.')
          : 'AI SRS generation completed.',
      });
    } catch (error) {
      setState({ status: 'error', message: apiError(error, 'SRS generation failed. Please try again.') });
    }
  };
  const retryWorkspace = () => workspace.project.creation_mode === 'pitch'
    ? retryGeneration()
    : setRetryCount((count) => count + 1);
  return <main className="shell">
    <AppHeader user={user} onLogout={onLogout} onNavigateProjects={onBack} onNewProject={onNewProject} currentPage="workspace" />
    {!workspace && state.status === 'loading' && <p className="empty-state" role="status">{state.message}</p>}
    {!workspace && state.status === 'error' && <div className="empty-state" role="alert"><p className="status error">{state.message}</p><button className="secondary" type="button" onClick={() => setRetryCount((count) => count + 1)}>Retry loading</button><button className="secondary" type="button" onClick={onBack}>Return to projects</button></div>}
    {workspace && <>
      <WorkspaceHeading project={workspace.project} result={workspace.result} documentName={workspace.document_name} />
      {state.status === 'loading' && <p className="workspace-inline-status" role="status">{state.message}</p>}
      {state.status === 'error' && <div className="workspace-retry-alert" role="alert"><p className="status error">{state.message}</p><button className="secondary" type="button" onClick={retryWorkspace}>{workspace.project.creation_mode === 'pitch' ? 'Retry generation' : 'Retry loading workspace'}</button></div>}
      {workspace.result
        ? <ReportView result={{ type: workspace.project.creation_mode, requirementId: workspace.requirement_id, data: workspace.result }} projectId={projectId} onResultUpdate={(result) => setWorkspace({ ...workspace, result })} />
        : <div className="workspace-empty panel"><h2>Results are not ready</h2><p className="muted">Generation has not returned results for this project. Retry to continue.</p><button className="primary" type="button" onClick={retryGeneration} disabled={state.status === 'loading'}>{state.status === 'loading' ? 'Working…' : 'Retry generation'}</button></div>}
    </>}
  </main>;
}

function ReportView({ result, projectId, project, onResultUpdate }) {
  const data = result.data || {};
  return <>
    {project && <WorkspaceHeading project={project} result={data} documentName={data.document_name} />}
    {result.type === 'pitch'
      ? <PitchResults data={data} projectId={projectId} onResultUpdate={onResultUpdate} />
      : <UploadResults requirementId={result.requirementId} data={data} projectId={projectId} onResultUpdate={onResultUpdate} />}
  </>;
}

function WorkspaceSectionNavigation({ sections, activeSection, onSelect }) {
  return (
    <nav className="workspace-section-nav" aria-label="Workspace sections">
      {sections.map(([id, label]) => <button key={id} type="button" aria-pressed={activeSection === id} aria-controls="workspace-section-panel" className={activeSection === id ? 'workspace-section-link active' : 'workspace-section-link'} onClick={() => onSelect(id)}>{label}</button>)}
    </nav>
  );
}

function UploadResults({ requirementId, data, projectId, onResultUpdate }) {
  const [tab, setTab] = useState('overview');
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
  const selectedUseCaseSource = buildUseCaseDiagram(requirements.filter((item) => selectedUseCases.includes(item.id)));
  const testCases = data.test_cases || [];
  const suggestions = data.suggested_additions || [];
  const improvedSrs = data.refactored_srs || {};
  const uploadSections = [
    ['overview', 'Overview'],
    ['analyzer', 'Requirements & analysis'],
    ...(questions.length ? [['qa', 'Clarifications']] : []),
    ...(Object.values(diagrams).some((source) => typeof source === 'string' && source.trim()) || requirements.length ? [['diagrams', 'Diagrams']] : []),
    ...(Array.isArray(data.test_cases) ? [['tests', 'Test cases']] : []),
    ['srs', 'SRS'],
    ['report', 'Report'],
  ];
  const uploadSectionIds = uploadSections.map(([id]) => id).join('|');
  React.useEffect(() => {
    if (!uploadSectionIds.split('|').includes(tab)) setTab('overview');
  }, [uploadSectionIds, tab]);
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
      <div className="panel-heading"><div><p className="eyebrow">SRS ANALYSIS</p><h2>{improvedSrs.title || 'Requirements analysis'}</h2><p className="result-summary">Review the source, analyzed requirements, clarification questions, diagrams, tests, and generated SRS.</p></div>{data.generation_status && <span className="badge">{data.generation_status}</span>}</div>
      {data.generation_status === 'draft' && <div className="document-warning" role="status"><strong>Saved analysis draft</strong><p>{data.generation_note}</p><button className="secondary" type="button" onClick={retryFullAnalysis} disabled={generationState.status === 'loading'}>{generationState.status === 'loading' ? 'Retrying…' : 'Retry AI refinement'}</button>{generationState.message && <p className={`status ${generationState.status}`} role={generationState.status === 'error' ? 'alert' : 'status'}>{generationState.message}</p>}</div>}
      {data.is_software_document === false && <div className="status error document-warning"><strong>This does not appear to be a software SRS.</strong><p>{data.message || 'The uploaded content could not be analyzed as software requirements.'}</p></div>}
      <div className="workspace-section-layout">
        <WorkspaceSectionNavigation sections={uploadSections} activeSection={tab} onSelect={setTab} />
        <div className="workspace-section-panel" id="workspace-section-panel">
      {tab === 'overview' && <div className="tab-content workspace-overview"><p className="workspace-summary">{data.summary || analysis.summary || 'Review the extracted source and the analysis sections to inspect this specification.'}</p><div className="score-grid"><InfoCard label="Completeness score" value={data.quality_score == null ? 'Not evaluated' : `${data.quality_score} / 100`} /><InfoCard label="Confidence score" value={data.confidence_score == null ? 'Not evaluated' : `${data.confidence_score} / 100`} /><InfoCard label="Functional requirements" value={requirements.length} /><InfoCard label="Test cases" value={testCases.length} /></div><p className="muted">Completeness reflects a structural checklist. Confidence is not evaluated automatically.</p><div className="workspace-overview-note"><strong>Source preserved</strong><span>{data.document_name || 'Uploaded document'}{data.source_text_length != null ? ` · ${data.source_text_length.toLocaleString()} extracted characters` : ''}</span></div></div>}
      {tab === 'analyzer' && <div className="tab-content"><div className="summary-grid"><InfoCard label="Suitable domain" value={data.suitable_domain} /><InfoCard label="Recommended tech stack" value={Object.entries(data.recommended_tech_stack || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' · ')} /></div><ResultSection title="Extracted source analysis"><p className="source-meta">{data.source_text_length ?? data.source_text?.length ?? 0} characters preserved from {data.document_name || 'uploaded document'}.</p><pre className="source-text">{data.source_text || 'No extracted source returned.'}</pre></ResultSection><div className="report-columns"><ResultSection title="Requirements from the source and refinement"><RequirementList items={requirements} /></ResultSection><ResultSection title="Non-functional requirements"><RequirementList items={nfrs} /></ResultSection></div><div className="report-columns"><ResultSection title="User stories"><List items={data.user_stories} /></ResultSection><ResultSection title="Acceptance criteria"><List items={data.acceptance_criteria} /></ResultSection></div><div className="report-columns"><ResultSection title="Risks and assumptions"><List items={[...(data.risks || []), ...(data.assumptions || [])]} /></ResultSection><ResultSection title="Missing requirements and suggestions"><List items={[...(data.missing_requirements || []), ...suggestions]} /></ResultSection></div></div>}
      {tab === 'qa' && <div className="tab-content"><ResultSection title="Clarification questions"><form onSubmit={submitAnswers} className="qa-form">{questions.length ? questions.map((question) => <label key={question.id}><span><b>{question.id}</b> {question.question}<small>{question.priority || 'medium'} priority · {question.reason}</small></span><textarea rows="2" value={answers[question.id] || ''} onChange={(event) => setAnswers({ ...answers, [question.id]: event.target.value })} placeholder="Add an answer for the improved SRS" /></label>) : <p className="muted">No clarification questions were returned.</p>}<button className="primary" type="submit" disabled={answerState.status === 'loading'}>Apply answers to SRS</button>{answerState.message && <p className={`status ${answerState.status}`}>{answerState.message}</p>}</form></ResultSection></div>}
      {tab === 'diagrams' && <div className="tab-content"><div className="diagram-picker">{Object.entries(DIAGRAM_LABELS).map(([id, label]) => <button type="button" key={id} aria-pressed={diagramType === id} className={diagramType === id ? 'diagram-button active' : 'diagram-button'} onClick={() => setDiagramType(id)}>{label}</button>)}</div>{diagramType === 'use_case_diagram' && <ResultSection title="Select use cases"><div className="use-case-picker">{requirements.map((item) => <label key={item.id}><input type="checkbox" checked={selectedUseCases.includes(item.id)} onChange={(event) => setSelectedUseCases(event.target.checked ? [...selectedUseCases, item.id] : selectedUseCases.filter((id) => id !== item.id))} />{item.id}: {item.title || item.description}</label>)}</div></ResultSection>}<ResultSection title={`${DIAGRAM_LABELS[diagramType]} preview`}><DiagramPreview source={diagramType === 'use_case_diagram' ? selectedUseCaseSource : selectDiagramSource(data, diagramType)} diagramType={diagramType} editable /></ResultSection></div>}
      {tab === 'tests' && <div className="tab-content"><ResultSection title="Generated test cases mapped to requirements"><TestCaseList items={testCases} /></ResultSection><ResultSection title="Suggested functionality covered"><List items={suggestions} /></ResultSection></div>}
      {tab === 'srs' && <div className="tab-content"><div className="document-actions"><button className="secondary" type="button" onClick={() => download('json', JSON.stringify({ ...data, original_source: data.source_text }, null, 2), 'application/json')}>Download JSON</button><button className="secondary" type="button" onClick={() => download('md', markdown, 'text/markdown')}>Download Markdown</button><button className="secondary" type="button" onClick={() => projectId && downloadDocx(projectId)}>Download DOCX</button><button className="secondary" type="button" onClick={() => window.print()}>Save as PDF</button></div><article className="srs-document"><h1>{improvedSrs.title || 'Improved SRS'}</h1><p>{improvedSrs.summary || analysis.summary}</p><p><b>Domain:</b> {data.suitable_domain || 'Not specified'}</p><p><b>Recommended technology:</b> {formatStack(data.recommended_tech_stack)}</p><h3>Functional requirements</h3><RequirementList items={requirements} /><h3>Non-functional requirements</h3><RequirementList items={nfrs} /><h3>User stories</h3><List items={data.user_stories} /><h3>Actors</h3><List items={data.actors} /><h3>Risks and assumptions</h3><List items={[...(data.risks || []), ...(data.assumptions || [])]} /><h3>Test cases</h3><TestCaseList items={testCases} /><h3>Diagrams</h3>{Object.entries(diagrams).map(([name, source]) => <section key={name}><h4>{DIAGRAM_LABELS[name] || name}</h4><DiagramPreview source={source} diagramType={name} editable /></section>)}<h3>Suggestions and additions</h3><List items={suggestions} /><h3>Original source preserved</h3><pre className="source-text">{data.source_text}</pre></article></div>}
      {tab === 'report' && <div className="tab-content"><div className="score-grid"><InfoCard label="Completeness score" value={data.quality_score == null ? 'Not evaluated' : `${data.quality_score} / 100`} /><InfoCard label="Confidence score" value={data.confidence_score == null ? 'Not evaluated' : `${data.confidence_score} / 100`} /><InfoCard label="Functional requirements" value={requirements.length} /><InfoCard label="Non-functional requirements" value={nfrs.length} /><InfoCard label="Test cases" value={testCases.length} /></div><p className="muted">Completeness reflects a structural checklist. Confidence is not evaluated automatically.</p><div className="report-columns"><ResultSection title="Confidence reasons"><List items={data.confidence_reasons} /></ResultSection><ResultSection title="Original vs improved changes"><List items={[...(data.change_summary?.improved || []), ...(data.change_summary?.added || []), ...(data.change_summary?.removed || []).map((item) => `Removed: ${item}`)]} /></ResultSection></div><ResultSection title="Quality issues"><List items={data.quality?.issues || []} /></ResultSection><ResultSection title="Suggestions for review"><List items={suggestions} /></ResultSection></div>}
        </div>
      </div>
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

function PitchResults({ data, projectId, onResultUpdate }) {
  const [tab, setTab] = useState('overview');
  const [diagramType, setDiagramType] = useState('architecture_diagram');
  const [generationState, setGenerationState] = useState({ status: 'idle', message: '' });
  const requirements = data.functional_requirements || [];
  const nfrs = data.non_functional_requirements || [];
  const [selectedUseCases, setSelectedUseCases] = useState(requirements.map((item) => item.id));
  React.useEffect(() => setSelectedUseCases(requirements.map((item) => item.id)), [data]);
  const diagrams = data.diagram_sources || {};
  const selectedUseCaseSource = buildUseCaseDiagram(requirements.filter((item) => selectedUseCases.includes(item.id)));
  const testCases = data.test_cases || [];
  const pitchReportAvailable = data.quality_score != null || data.confidence_score != null || data.confidence_reasons?.length || data.confidence_issues?.length || data.suggestions?.length;
  const pitchSections = [
    ['overview', 'Overview'],
    ...(Array.isArray(data.functional_requirements) || Array.isArray(data.non_functional_requirements) ? [['specification', 'Requirements & analysis']] : []),
    ...(Object.values(diagrams).some((source) => typeof source === 'string' && source.trim()) ? [['diagrams', 'Diagrams']] : []),
    ...(Array.isArray(data.test_cases) ? [['test-cases', 'Test cases']] : []),
    ['srs', 'SRS'],
    ...(pitchReportAvailable ? [['report', 'Report']] : []),
  ];
  const pitchSectionIds = pitchSections.map(([id]) => id).join('|');
  React.useEffect(() => {
    if (!pitchSectionIds.split('|').includes(tab)) setTab('overview');
  }, [pitchSectionIds, tab]);
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
      const result = response.data.data || {};
      onResultUpdate?.(result);
      setGenerationState({
        status: result.generation_status === 'draft' ? 'error' : 'success',
        message: result.generation_status === 'draft'
          ? 'Retry did not complete; the saved draft remains available.'
          : 'AI SRS generation completed.',
      });
    } catch (error) {
      setGenerationState({ status: 'error', message: apiError(error, 'AI generation is unavailable. Your saved draft remains available.') });
    }
  };

  const markdown = `# ${data.title || 'Software Requirements Specification'}\n\n## Summary\n${data.summary || ''}\n\n## Domain\n${data.suitable_domain || ''}\n\n## Recommended stack\n${Object.entries(data.recommended_tech_stack || {}).map(([key, value]) => `- **${key}:** ${Array.isArray(value) ? value.join(', ') : value}`).join('\n')}\n\n## Functional requirements\n${requirements.map((item) => `- **${item.id || ''} ${item.title || ''}:** ${item.description || ''}`).join('\n')}\n\n## Non-functional requirements\n${nfrs.map((item) => `- **${item.id || ''} ${item.category || ''}:** ${item.description || ''}`).join('\n')}\n\n## User stories\n${(data.user_stories || []).map((item) => `- ${item.story || item}`).join('\n')}\n\n## Acceptance criteria\n${requirements.flatMap((item) => item.acceptance_criteria || []).map((item) => `- ${item}`).join('\n')}\n\n## Risks and assumptions\n${[...(data.risks || []), ...(data.assumptions || [])].map((item) => `- ${typeof item === 'string' ? item : JSON.stringify(item)}`).join('\n')}`;

  return (
    <section className="results panel" aria-label="Mode 1 generated results">
      <div className="panel-heading"><div><p className="eyebrow">IDEA TO SRS</p><h2>{data.title || 'Generated requirements'}</h2><p className="result-summary">{data.summary}</p></div>{data.generation_status && <span className="badge">{data.generation_status}</span>}</div>
      {data.generation_status === 'draft' && <div className="document-warning" role="status"><strong>Pitch-based draft</strong><p>{isLegacyStoppedFailover ? 'This draft contains a saved result from the previous provider routing attempt. Retry to run it through the current NVIDIA → OpenRouter → Gemini failover chain.' : savedGenerationNote}</p><button className="secondary" type="button" onClick={retryAiGeneration} disabled={generationState.status === 'loading'}>{generationState.status === 'loading' ? 'Retrying…' : 'Retry AI generation'}</button>{generationState.message && <p className={`status ${generationState.status}`} role={generationState.status === 'error' ? 'alert' : 'status'}>{generationState.message}</p>}</div>}
      <div className="workspace-section-layout">
        <WorkspaceSectionNavigation sections={pitchSections} activeSection={tab} onSelect={setTab} />
        <div className="workspace-section-panel" id="workspace-section-panel">
      {tab === 'overview' && <div className="tab-content workspace-overview"><p className="workspace-summary">{data.summary || 'Review the generated specification and supporting engineering artifacts.'}</p><div className="score-grid"><InfoCard label="Completeness score" value={data.quality_score == null ? 'Not evaluated' : `${data.quality_score} / 100`} /><InfoCard label="Confidence score" value={data.confidence_score == null ? 'Not evaluated' : `${data.confidence_score} / 100`} /><InfoCard label="Functional requirements" value={requirements.length} /><InfoCard label="Non-functional requirements" value={nfrs.length} /><InfoCard label="Test cases" value={testCases.length} /></div><p className="muted">Completeness reflects a structural checklist. Confidence is not evaluated automatically.</p>{data.generation_status === 'draft' && <div className="workspace-overview-note is-review"><strong>Draft status</strong><span>{data.generation_note || 'Review and refine the generated draft before implementation.'}</span></div>}</div>}
      {tab === 'specification' && <div className="tab-content">
        <div className="summary-grid"><InfoCard label="Suitable domain" value={data.suitable_domain} /><InfoCard label="Recommended stack" value={Object.entries(data.recommended_tech_stack || {}).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' · ')} /></div>
        <ResultSection title="Functional requirements"><RequirementList items={requirements} /></ResultSection>
        <ResultSection title="Non-functional requirements"><RequirementList items={nfrs} /></ResultSection>
        <div className="report-columns"><ResultSection title="User stories"><List items={data.user_stories} /></ResultSection><ResultSection title="Acceptance criteria"><List items={requirements.flatMap((item) => item.acceptance_criteria || [])} /></ResultSection></div>
        <div className="report-columns"><ResultSection title="Predicted risks"><List items={data.risks} /></ResultSection><ResultSection title="Assumptions"><List items={data.assumptions} /></ResultSection></div>
      </div>}

      {tab === 'diagrams' && <div className="tab-content"><div className="diagram-picker">{Object.entries(DIAGRAM_LABELS).map(([id, label]) => <button type="button" key={id} aria-pressed={diagramType === id} className={diagramType === id ? 'diagram-button active' : 'diagram-button'} onClick={() => setDiagramType(id)}>{label}</button>)}</div>{diagramType === 'use_case_diagram' && <ResultSection title="Select use cases"><div className="use-case-picker">{requirements.map((item) => <label key={item.id}><input type="checkbox" checked={selectedUseCases.includes(item.id)} onChange={(event) => setSelectedUseCases(event.target.checked ? [...selectedUseCases, item.id] : selectedUseCases.filter((id) => id !== item.id))} />{item.id}: {item.title || item.description}</label>)}</div></ResultSection>}<ResultSection title={`${DIAGRAM_LABELS[diagramType]} preview`}><DiagramPreview source={diagramType === 'use_case_diagram' ? selectedUseCaseSource : selectDiagramSource(data, diagramType)} diagramType={diagramType} editable /></ResultSection></div>}

      {tab === 'test-cases' && <div className="tab-content"><ResultSection title="Test cases by functionality"><TestCaseList items={testCases} /></ResultSection></div>}

      {tab === 'srs' && <div className="tab-content"><div className="document-actions"><button className="secondary" type="button" onClick={() => download('json', JSON.stringify(srs, null, 2), 'application/json')}>Download JSON</button><button className="secondary" type="button" onClick={() => download('md', completeMarkdown, 'text/markdown')}>Download Markdown</button><button className="secondary" type="button" onClick={() => projectId && downloadDocx(projectId)}>Download DOCX</button><button className="secondary" type="button" onClick={() => window.print()}>Save as PDF</button></div><article className="srs-document"><h1>{data.title}</h1><p>{data.summary}</p><h3>Domain and technology</h3><p><b>{data.suitable_domain}</b></p><p>{formatStack(data.recommended_tech_stack)}</p><h3>Functional requirements</h3><RequirementList items={requirements} /><h3>Non-functional requirements</h3><RequirementList items={nfrs} /><h3>User stories</h3><List items={data.user_stories} /><h3>Actors</h3><List items={data.actors} /><h3>Risks and assumptions</h3><List items={[...(data.risks || []), ...(data.assumptions || [])]} /><h3>Test cases</h3><TestCaseList items={testCases} /><h3>Diagrams</h3>{Object.entries(diagrams).map(([name, source]) => <section key={name}><h4>{DIAGRAM_LABELS[name] || name}</h4><DiagramPreview source={source} diagramType={name} editable /></section>)}</article></div>}

      {tab === 'report' && <div className="tab-content"><div className="score-grid"><InfoCard label="Completeness score" value={data.quality_score == null ? 'Not evaluated' : `${data.quality_score} / 100`} /><InfoCard label="Confidence score" value={data.confidence_score == null ? 'Not evaluated' : `${data.confidence_score} / 100`} /><InfoCard label="Functional requirements" value={requirements.length} /><InfoCard label="Non-functional requirements" value={nfrs.length} /><InfoCard label="Test cases" value={testCases.length} /></div><p className="muted">Completeness reflects a structural checklist. Confidence is not evaluated automatically.</p><div className="report-columns"><ResultSection title="Confidence reasons"><List items={data.confidence_reasons} /></ResultSection><ResultSection title="Quality issues"><List items={data.quality_issues || []} /></ResultSection></div><ResultSection title="Suggestions for review"><List items={data.suggestions} /></ResultSection></div>}
        </div>
      </div>
    </section>
  );
}

function InfoCard({ label, value }) { return <div className="info-card"><span>{label}</span><strong>{value == null || value === '' ? 'Not specified' : value}</strong></div>; }
function apiError(error, fallback) {
  const detail = error.response?.data?.detail || error.response?.data?.message;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || item.message || String(item)).join(' ');
  if (detail) return typeof detail === 'string' ? detail : JSON.stringify(detail);
  if (!error.response && error.message === 'Network Error') return `Cannot reach the SpecMind API at ${api.defaults.baseURL}. Check that the backend is running on port 8000 and reload this page.`;
  return error.message || fallback;
}
function ResultSection({ title, children }) { return <section className="result-section"><h3>{title}</h3>{children}</section>; }
function RequirementList({ items }) { return <div className="requirement-list">{items?.length ? items.map((item, index) => { const origin = item.origin || 'generated'; return <article key={item.id || index}><strong>{item.id} {item.title || item.category}</strong><span className={`origin-tag origin-${origin}`}>{origin}</span><p>{item.description || item}</p>{item.source_trace && <small className="source-trace">Source: {item.source_trace}</small>}{item.acceptance_criteria?.length > 0 && <><b>Acceptance criteria</b><List items={item.acceptance_criteria} /></>}</article>; }) : <p className="muted">No items returned.</p>}</div>; }

function TestCaseList({ items }) {
  return <div className="test-case-list">{items?.length ? items.map((item, index) => <article className="test-case" key={item.id || index}><strong>{item.id || `TC-${index + 1}`}{item.requirement_id ? ` · ${item.requirement_id}` : ' · Requirement link unavailable'}</strong>{item.requirement && <span>{item.requirement}</span>}{item.priority && <small>Priority: {item.priority}</small>}{item.test_type && <small>Type: {item.test_type}</small>}{item.precondition && <small><b>Precondition:</b> {item.precondition}</small>}<ol>{(item.steps || []).map((step, stepIndex) => <li key={stepIndex}>{step}</li>)}</ol>{item.expected_result && <small><b>Expected:</b> {item.expected_result}</small>}</article>) : <p className="muted">No test cases returned.</p>}</div>;
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
