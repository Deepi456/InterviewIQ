import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowUpRight, BarChart3, Bell, BookOpen, BrainCircuit, Check, ChevronRight, CircleHelp, Clock3, Download, FileText, LayoutDashboard, Lightbulb, LoaderCircle, Mail, Menu, Mic, Plus, Search, Send, Settings, Sparkles, Target, TrendingUp, Trophy, UserRound, X } from 'lucide-react'
import { authApi, coachApi, downloadReportFile, getApiError, interviewApi } from './services/api'
import { createSubmitGuard } from './coachSubmitGuard'
import './App.css'
import HardenedInterviewRoom from './components/HardenedInterviewRoom'

const roles = ['Data Scientist', 'Data Analyst', 'Machine Learning Engineer', 'Software Engineer', 'Backend Developer', 'Frontend Developer']
const roleSkills = { 'Frontend Developer': ['HTML', 'CSS', 'JavaScript', 'TypeScript', 'React', 'React Hooks', 'REST APIs', 'Browser/Web fundamentals', 'Git', 'Testing', 'Performance'], 'Backend Developer': ['Python', 'Java', 'Node.js', 'REST APIs', 'Databases', 'SQL', 'Authentication & Authorization', 'API design', 'Backend architecture', 'Caching', 'Error handling', 'Testing', 'Git'], 'Software Engineer': ['Programming fundamentals', 'Data Structures', 'Algorithms', 'OOP', 'Problem solving', 'SQL', 'Operating Systems', 'Computer Networks', 'DBMS', 'System Design', 'Git', 'Testing'], 'Data Analyst': ['Python', 'SQL', 'Excel', 'Pandas', 'NumPy', 'Data Cleaning', 'EDA', 'Statistics', 'Data Visualization', 'Power BI/Tableau', 'Business interpretation'], 'Data Scientist': ['Python', 'Pandas', 'NumPy', 'Statistics', 'Probability', 'SQL', 'Machine Learning', 'Feature Engineering', 'Feature Selection', 'Model Evaluation', 'Data Preprocessing', 'Data Visualization', 'NLP basics'], 'Machine Learning Engineer': ['Python', 'Machine Learning', 'Deep Learning', 'Feature Engineering', 'Model Evaluation', 'Model Deployment', 'APIs', 'MLOps', 'Docker', 'Model Monitoring', 'Data Pipelines', 'Cloud/Deployment'] }
const navItems = [{ label: 'Overview', to: '/', icon: LayoutDashboard }, { label: 'Interviews', to: '/interviews', icon: BookOpen }, { label: 'Reports', to: '/reports', icon: FileText }, { label: 'Insights', to: '/analytics', icon: BarChart3 }, { label: 'AI Coach', to: '/coach', icon: BrainCircuit }]
  const activeUserKey = () => { try { return JSON.parse(localStorage.getItem('interviewiq_user') || '{}').id || 'anonymous' } catch { return 'anonymous' } }
  const scopedKey = (name) => `interviewiq_${name}_${activeUserKey()}`
  const loadHistory = () => JSON.parse(localStorage.getItem(scopedKey('history')) || '[]')
  const saveHistory = (item) => localStorage.setItem(scopedKey('history'), JSON.stringify([item, ...loadHistory().filter((entry) => entry.sessionId !== item.sessionId)].slice(0, 20)))
const formatDate = (value) => value ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) : 'Just now'
const percent = (value) => Math.round(Number(value || 0))
const downloadBlob = async (sessionId, format = 'pdf') => { const blob = await downloadReportFile(sessionId, format); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `InterviewIQ_Report_${sessionId}.${format}`; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url) }
const fadeUp = { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] } }
const AuthContext = createContext(null)
const initials = (name = '') => name.split(/\s+/).filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || '?'

function App() { return <BrowserRouter><AuthProvider><Routes><Route path="/login" element={<AuthPage mode="login" />} /><Route path="/register" element={<AuthPage mode="register" />} /><Route path="*" element={<Shell />} /></Routes></AuthProvider></BrowserRouter> }

function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => { if (!localStorage.getItem('interviewiq_access_token')) return setLoading(false); authApi.me().then((current) => { setUser(current); localStorage.setItem('interviewiq_user', JSON.stringify(current)) }).catch(() => { localStorage.removeItem('interviewiq_access_token'); localStorage.removeItem('interviewiq_user') }).finally(() => setLoading(false)) }, [])
  return <AuthContext.Provider value={{ user, setUser, loading }}>{children}</AuthContext.Provider>
}

function useUserHistory() {
  const { user } = useContext(AuthContext)
  const [history, setHistory] = useState([])
  useEffect(() => {
    let active = true
    if (!user) { setHistory([]); return () => { active = false } }
    interviewApi.history().then((items) => {
      if (!active) return
      setHistory(items)
      localStorage.setItem(scopedKey('history'), JSON.stringify(items.slice(0, 20)))
    }).catch(() => { if (active) setHistory([]) })
    return () => { active = false }
  }, [user?.id])
  return history
}

function Shell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, setUser, loading } = useContext(AuthContext)
  const location = useLocation()
  const navigate = useNavigate()
  useEffect(() => { if (!loading && !user) navigate('/login', { replace: true }) }, [loading, navigate, user])
  if (loading || !user) return null
  const title = location.pathname === '/' ? 'Overview' : location.pathname.startsWith('/analytics') ? 'Insights' : location.pathname.split('/')[1]?.replace('-', ' ') || 'Overview'
  return <div className="command-shell">
    <aside className={`command-rail ${mobileOpen ? 'open' : ''}`}>
      <Link className="iq-lockup" to="/"><span className="iq-mark">IQ</span><span>InterviewIQ</span></Link>
      <div className="rail-context"><span className="status-dot" /> Candidate workspace</div>
      <nav className="rail-nav" aria-label="Primary navigation"><span className="rail-label">Navigate</span>{navItems.map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} onClick={() => setMobileOpen(false)} className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}><Icon size={16} /><span>{label}</span></NavLink>)}</nav>
      <div className="rail-bottom"><NavLink to="/settings" onClick={() => setMobileOpen(false)} className={({ isActive }) => `rail-link ${isActive ? 'active' : ''}`}><Settings size={16} /><span>Settings</span></NavLink><button className="rail-profile rail-profile-button" type="button" onClick={() => { localStorage.removeItem('interviewiq_access_token'); localStorage.removeItem('interviewiq_user'); setUser(null); navigate('/login') }}><span>{initials(user.name)}</span><div><strong>{user.name}</strong><small>{user.email}</small></div></button></div>
    </aside>
    {mobileOpen && <button className="rail-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <main className="command-main"><header className="command-header"><button className="mobile-trigger" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={19} /></button><div className="header-path"><span>InterviewIQ</span><ChevronRight size={13} /><strong>{title.charAt(0).toUpperCase() + title.slice(1)}</strong></div><div className="header-tools"><button className="command-search"><Search size={15} /><span>Search workspace</span><kbd>Ctrl K</kbd></button><button className="quiet-button" aria-label="Notifications"><Bell size={17} /></button><span className="header-avatar">{initials(user.name)}</span></div></header><div className="command-page"><Routes><Route path="/" element={<Dashboard />} /><Route path="/new" element={<NewInterview />} /><Route path="/interview/:sessionId" element={<InterviewRoom />} /><Route path="/results/:sessionId" element={<Results />} /><Route path="/interviews" element={<Reports />} /><Route path="/reports" element={<Reports />} /><Route path="/reports/:sessionId" element={<ReportDetails />} /><Route path="/analytics" element={<Analytics />} /><Route path="/coach" element={<Coach user={user} />} /><Route path="/settings" element={<UserSettingsPage user={user} />} /></Routes></div><nav className="mobile-bottom-nav" aria-label="Mobile navigation">{[navItems[0], navItems[1], navItems[4], navItems[3]].map(({ label, to, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'active' : ''}><Icon size={17} /><span>{label === 'Overview' ? 'Home' : label === 'AI Coach' ? 'Coach' : label}</span></NavLink>)}</nav></main>
  </div>
}

function Button({ children, variant = 'solid', icon: Icon, ...props }) { return <button className={`action action-${variant}`} {...props}>{children}{Icon && <Icon size={15} />}</button> }
function Intro({ overline, title, description, action }) { return <motion.div className="editorial-intro" {...fadeUp}><div><span className="overline">{overline}</span><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</motion.div> }
function Empty({ icon: Icon = FileText, title, text, action }) { return <div className="empty-line"><Icon size={19} /><div><strong>{title}</strong><p>{text}</p></div>{action}</div> }
function ErrorLine({ message, retry }) { return <div className="error-line"><CircleHelp size={19} /><span>{message}</span><Button variant="quiet" onClick={retry}>Retry</Button></div> }
function IntelligenceMap() { return <div className="intelligence-map" aria-label="Interview intelligence visualization"><svg viewBox="0 0 520 360" role="img"><defs><linearGradient id="line" x1="0" x2="1"><stop stopColor="#766fff" stopOpacity=".1" /><stop offset=".5" stopColor="#8e88ff" stopOpacity=".75" /><stop offset="1" stopColor="#6aa9ff" stopOpacity=".08" /></linearGradient><radialGradient id="core"><stop stopColor="#b5b0ff" /><stop offset=".45" stopColor="#736bfa" /><stop offset="1" stopColor="#302e74" /></radialGradient></defs><ellipse cx="260" cy="180" rx="190" ry="80" fill="none" stroke="url(#line)" /><ellipse cx="260" cy="180" rx="115" ry="165" fill="none" stroke="url(#line)" transform="rotate(-38 260 180)" /><ellipse cx="260" cy="180" rx="205" ry="145" fill="none" stroke="url(#line)" transform="rotate(33 260 180)" /><path d="M48 250 C142 165 178 225 260 180 S389 114 474 74" fill="none" stroke="#7770ff" strokeOpacity=".42" strokeDasharray="3 8" /><circle cx="260" cy="180" r="40" fill="url(#core)" opacity=".85" /><circle cx="260" cy="180" r="11" fill="#fff" opacity=".9" /><circle cx="80" cy="233" r="5" fill="#68aaff" /><circle cx="134" cy="117" r="4" fill="#b1adff" /><circle cx="424" cy="112" r="6" fill="#6de0b4" /><circle cx="455" cy="279" r="4" fill="#f1bd69" /><circle cx="146" cy="288" r="3" fill="#fff" opacity=".7" /></svg><div className="map-center"><BrainCircuit size={22} /><span>IQ ENGINE</span></div><span className="map-label label-role">Role signal</span><span className="map-label label-skill">Skill graph</span><span className="map-label label-score">Answer signal</span></div> }

const coachQuickActions = [
  ['Practice Python', 'Give me 5 Python interview questions.'],
  ['Practice SQL', 'How can I improve my SQL interview performance?'],
  ['Mock interview', 'Start a mock interview for a Data Scientist role.'],
  ['Analyze performance', 'What should I improve from my latest interview?'],
  ['Improve weaknesses', 'Create a practice plan for my weakest interview skills.'],
  ['Explain a concept', 'Explain normalization simply for an interview.'],
]

function ResumeTailor() {
  const [file, setFile] = useState(null); const [jobDescription, setJobDescription] = useState(''); const [result, setResult] = useState(null); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const analyze = async (event) => { event.preventDefault(); if (!file || !jobDescription.trim()) return setError('Choose a resume and add a job description.'); setBusy(true); setError(''); try { setResult(await coachApi.tailorResume(file, jobDescription)) } catch (err) { setError(getApiError(err)) } finally { setBusy(false) } }
  const download = async () => { const blob = await coachApi.tailoredResumePdf(result.tailoring_id); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'InterviewIQ_Tailored_Resume.pdf'; link.click(); URL.revokeObjectURL(url) }
  return <section className="resume-tailor"><div><span className="overline">Resume studio</span><h2>Tailor resume for a job</h2><p>Grounded in your original resume. Nothing is invented or overwritten.</p></div><form onSubmit={analyze}><label>Upload resume<input type="file" accept=".pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><label>Job description<textarea value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste the job description here..." /></label><Button type="submit" disabled={busy}>{busy ? 'Analyzing...' : 'Analyze & tailor'} <Sparkles size={15} /></Button></form>{error && <div className="form-error">{error}</div>}{result && <div className="resume-result"><strong>Job match: {result.job_match_score}%</strong><div><b>Strong matches</b><p>{result.strong_matches.join(' · ') || 'None found'}</p></div><div><b>Skill gaps</b><p>{result.skill_gaps.join(' · ') || 'None identified'}</p></div><div><b>Recommendations</b><p>{result.recommendations.join(' ')}</p></div><details><summary>Preview tailored resume</summary><pre>{result.tailored_resume}</pre></details><Button type="button" variant="outline" onClick={download} icon={Download}>Download tailored resume PDF</Button></div>}</section>
}

function Coach({ user }) { return <><ResumeTailor /><CoachChat user={user} /></> }

function CoachChat({ user }) {
  const history = useUserHistory(); const latestSession = history[0]?.sessionId; const coachMessagesKey = scopedKey('coach_messages'); const coachConversationKey = scopedKey('coach_conversation'); const [messages, setMessages] = useState(() => JSON.parse(localStorage.getItem(coachMessagesKey) || '[]')); const [conversationId, setConversationId] = useState(() => localStorage.getItem(coachConversationKey) || ''); const [draft, setDraft] = useState(''); const [thinking, setThinking] = useState(false); const [error, setError] = useState(''); const [failedMessage, setFailedMessage] = useState(''); const [report, setReport] = useState(null)
  useEffect(() => { localStorage.setItem(coachMessagesKey, JSON.stringify(messages)) }, [coachMessagesKey, messages])
  useEffect(() => { if (latestSession) interviewApi.report(latestSession).then(setReport).catch(() => {}) }, [latestSession])
  const submitGuardRef = useRef(createSubmitGuard())
  const submitGuard = useMemo(() => submitGuardRef.current, [])

  const sendMessage = async (text = draft, retry = false) => {
    const message = String(text ?? '').trim()
    if (thinking) return
    const allowed = submitGuard.begin(message)
    if (!allowed) return

    setDraft('')
    setError('')
    if (!retry) setMessages((current) => [...current, { role: 'user', text: message }])
    setThinking(true)

    try {
      const result = await coachApi.chat({ message, conversation_id: conversationId || undefined, session_id: latestSession || undefined })
      setConversationId(result.conversation_id)
      localStorage.setItem(coachConversationKey, result.conversation_id)
      setFailedMessage('')
      setMessages((current) => [...current, { role: 'assistant', text: result.response, suggestions: result.suggestions, mode: result.mode }])
    } catch (err) {
      setFailedMessage(message)
      setError(getApiError(err))
    } finally {
      submitGuard.finish()
      setThinking(false)
    }
  }
  const reset = () => { submitGuard.reset(); setMessages([]); setConversationId(''); setError(''); setFailedMessage(''); localStorage.removeItem(coachMessagesKey); localStorage.removeItem(coachConversationKey) }
  const submitCurrent = (event) => {
    if (event) event.preventDefault()
    if (thinking) return
    const trimmed = draft.trim()
    if (!trimmed) return
    sendMessage(trimmed)
  }
  return <div className="coach-page"><div className="coach-heading"><div><span className="overline"><span className="status-dot" /> AI Coach online</span><h1>InterviewIQ AI Coach</h1><p>Your personal interview preparation assistant.</p></div><div className="coach-heading-actions"><Button variant="quiet" onClick={reset} disabled={thinking}>New conversation</Button><Button variant="outline" onClick={reset} disabled={thinking}>Clear</Button></div></div><div className="coach-layout"><aside className="coach-history"><div className="coach-history-head"><span className="overline">Conversations</span><button type="button" onClick={reset} aria-label="New conversation" disabled={thinking}><Plus size={15} /></button></div><div className="coach-history-item active"><BrainCircuit size={15} /><span>AI Coach</span></div><p>Current session</p><div className="coach-history-note">Conversations are saved locally for this workspace.</div></aside><main className="coach-chat"><div className="coach-messages">{messages.length === 0 ? <CoachWelcome onSelect={sendMessage} disabled={thinking} /> : messages.map((message, index) => <CoachMessage key={`${message.role}-${index}`} message={message} user={user} onSuggest={sendMessage} disabled={thinking} />)}{thinking && <div className="coach-message assistant"><div className="coach-message-avatar"><BrainCircuit size={14} /></div><div><span className="message-author">InterviewIQ AI</span><div className="thinking"><i /><i /><i /><span>AI Coach is thinking</span></div></div></div>}{error && <div className="coach-error"><CircleHelp size={15} />{error}<button type="button" disabled={thinking || !failedMessage} onClick={() => sendMessage(failedMessage, true)}>Retry</button></div>}</div><form className="coach-composer" onSubmit={submitCurrent}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submitCurrent(event) } }} placeholder="Ask your AI Coach..." rows="1" disabled={thinking} /><div className="composer-footer"><span>Enter to send / Shift + Enter for a new line</span><button type="submit" aria-label="Send message" disabled={!draft.trim() || thinking}><Send size={16} /></button></div></form></main><aside className="coach-context"><span className="overline">Current context</span>{report ? <><h2>{report.job_role}</h2><div className="coach-context-score"><span>Recent score</span><strong>{percent(report.overall_score)}%</strong></div><div className="context-rule" /><span className="overline">Focus areas</span>{report.weak_areas?.length ? report.weak_areas.slice(0, 3).map((item) => <div className="context-item" key={item.skill}><Target size={13} /><span>{item.skill}</span></div>) : <p className="coach-muted">No weak areas returned.</p>}</> : <><h2>Open context</h2><p className="coach-muted">Complete an interview and the Coach can ground advice in your real report.</p><div className="context-rule" /><span className="overline">Coach modes</span>{['Technical preparation', 'Behavioral preparation', 'Mock interviews', 'Performance analysis'].map((item) => <div className="context-item" key={item}><Sparkles size={13} /><span>{item}</span></div>)}</>}</aside></div></div>
}
function CoachWelcome({ onSelect, disabled }) { return <div className="coach-welcome"><div className="coach-welcome-orb"><BrainCircuit size={28} /></div><span className="overline">InterviewIQ AI Coach</span><h2>Prepare smarter.<br /><i>Interview better.</i></h2><p>Ask for a concept breakdown, practice questions, a mock interview, or grounded feedback on your latest report.</p><div className="coach-quick-actions">{coachQuickActions.map(([label, prompt]) => <button type="button" key={label} disabled={disabled} onClick={() => onSelect(prompt)}>{label}<ArrowUpRight size={14} /></button>)}</div></div> }
function renderInlineMarkdown(text) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>
    return <span key={index}>{part}</span>
  })
}

function MarkdownMessage({ text }) {
  const blocks = text.split(/(```[\s\S]*?```)/g).filter(Boolean)
  return <div className="coach-markdown">{blocks.map((block, index) => {
    if (block.startsWith('```')) return <pre key={index}><code>{block.replace(/^```\w*\n?/, '').replace(/```$/, '')}</code></pre>
    return block.split('\n').map((line, lineIndex) => {
      const key = `${index}-${lineIndex}`
      if (/^####\s+/.test(line)) return <h4 key={key}>{renderInlineMarkdown(line.replace(/^####\s+/, ''))}</h4>
      if (/^###\s+/.test(line)) return <h4 key={key}>{renderInlineMarkdown(line.replace(/^###\s+/, ''))}</h4>
      if (/^##\s+/.test(line)) return <h3 key={key}>{renderInlineMarkdown(line.replace(/^##\s+/, ''))}</h3>
      if (/^#\s+/.test(line)) return <h3 key={key}>{renderInlineMarkdown(line.replace(/^#\s+/, ''))}</h3>
      if (/^[-*]\s+/.test(line)) return <div className="coach-markdown-item" key={key}><span>•</span><span>{renderInlineMarkdown(line.replace(/^[-*]\s+/, ''))}</span></div>
      if (/^\d+\.\s+/.test(line)) return <div className="coach-markdown-item" key={key}><span>{line.match(/^\d+/)[0]}.</span><span>{renderInlineMarkdown(line.replace(/^\d+\.\s+/, ''))}</span></div>
      if (/^---+$/.test(line.trim())) return <hr key={key} />
      return <p key={key}>{line ? renderInlineMarkdown(line) : <br />}</p>
    })
  })}</div>
}

function CoachMessage({ message, onSuggest, user, disabled }) { return <div className={`coach-message ${message.role}`}><div className="coach-message-avatar">{message.role === 'assistant' ? <BrainCircuit size={14} /> : initials(user?.name)}</div><div className="coach-message-body"><span className="message-author">{message.role === 'assistant' ? 'InterviewIQ AI' : 'You'}</span>{message.role === 'assistant' ? <MarkdownMessage text={message.text} /> : <p>{message.text}</p>}{message.suggestions?.length > 0 && <div className="coach-suggestions">{message.suggestions.map((suggestion) => <button type="button" key={suggestion} disabled={disabled} onClick={() => onSuggest(suggestion)}>{suggestion}</button>)}</div>}</div></div> }

function Dashboard() {
  const history = useUserHistory(); const [latest, setLatest] = useState(null)
  useEffect(() => { if (history[0]?.sessionId) interviewApi.report(history[0].sessionId).then(setLatest).catch(() => {}) }, [history])
  const score = latest ? percent(latest.overall_score) : null
  return <div className="dashboard-command"><section className="command-hero"><motion.div className="hero-copy" {...fadeUp}><span className="overline"><span className="status-dot" /> AI interview command center</span><h1>Ready for your<br /><i>next interview?</i></h1><p>Practice with an AI interviewer that adapts to your role, evaluates your answers, and shows exactly where to improve.</p><div className="hero-actions"><Link className="action action-solid" to="/new">Start an interview <ArrowUpRight size={16} /></Link><Link className="text-action" to="/reports">View performance <ChevronRight size={15} /></Link></div></motion.div><motion.div className="hero-visual" initial={{ opacity: 0, scale: .94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: .8, delay: .12 }}><IntelligenceMap /></motion.div></section><section className="progress-section"><div className="section-kicker"><span>01</span><strong>Your progress</strong><small>Signal across your latest practice</small></div><div className="progress-main"><div className="progress-score"><strong>{score ?? '--'}<small>{score ? '%' : ''}</small></strong><span>Average interview score</span><em>{score ? 'Latest report' : 'Complete an interview to establish your baseline'}</em></div><div className="trend-visual"><div className="trend-axis"><span>100</span><span>50</span><span>0</span></div><svg viewBox="0 0 600 150" preserveAspectRatio="none"><path d="M0 125 C70 120 83 105 145 110 S226 75 285 87 S355 42 408 65 S500 22 600 32" fill="none" stroke="url(#trend)" strokeWidth="2" /><defs><linearGradient id="trend"><stop stopColor="#726bff" /><stop offset="1" stopColor="#69b3ff" /></linearGradient></defs></svg>{!score && <span className="chart-note">Your trajectory appears after your first completed interview.</span>}</div></div><div className="skill-spectrum"><span className="spectrum-label">Skill overview</span>{['Python', 'SQL', 'Machine Learning', 'Communication'].map((skill, index) => <div className="spectrum-row" key={skill}><span>{skill}</span><div><i style={{ width: `${score ? [86, 72, 81, 69][index] : 0}%` }} /></div><strong>{score ? `${[86, 72, 81, 69][index]}` : '--'}</strong></div>)}</div></section><section className="recent-section"><div className="section-kicker"><span>02</span><strong>Recent interviews</strong><small>Practice history</small><Link className="text-action" to="/reports">Open archive <ArrowUpRight size={14} /></Link></div>{history.length ? <div className="timeline-list">{history.slice(0, 5).map((item) => <InterviewLine key={item.sessionId} item={item} />)}</div> : <Empty icon={Sparkles} title="Your first signal is waiting" text="Start an interview to build a personal performance history." action={<Link className="text-action" to="/new">Begin setup <ArrowUpRight size={14} /></Link>} />}</section></div>
}
function InterviewLine({ item }) { return <Link className="timeline-line" to={`/reports/${item.sessionId}`}><span className="timeline-mark" /><div><span className="timeline-role">{item.jobRole}</span><small>{item.type || 'Technical interview'} / {formatDate(item.date)}</small></div><strong>{item.score ? `${item.score}%` : '--'}</strong><span className="timeline-performance">{item.performance || 'Completed'}</span><ArrowUpRight size={15} /></Link> }

function NewInterview() {
  const navigate = useNavigate(); const [form, setForm] = useState({ jobRole: '', experience: '0-2 years', type: 'Technical', difficulty: 'Medium', skills: [], totalQuestions: 10 }); const [loading, setLoading] = useState(false); const [error, setError] = useState('')
  const availableSkills = roleSkills[form.jobRole] || []
  const skills = availableSkills
  useEffect(() => { setForm((current) => ({ ...current, skills: (roleSkills[current.jobRole] || []).slice(0, 5) })) }, [form.jobRole])
  const toggle = (skill) => setForm((current) => ({ ...current, skills: current.skills.includes(skill) ? current.skills.filter((item) => item !== skill) : [...current.skills, skill] }))
  const begin = async (event) => { event.preventDefault(); if (!form.jobRole || !form.skills.length) return setError('Choose a role and at least one skill.'); setLoading(true); setError(''); try { const data = await interviewApi.start({ job_role: form.jobRole, skills: form.skills, total_questions: form.totalQuestions, interview_type: form.type, difficulty: form.difficulty }); navigate(`/interview/${data.session_id}`, { state: { session: data, setup: form } }) } catch (err) { setError(getApiError(err)) } finally { setLoading(false) } }
  return <div className="setup-command"><Intro overline="New interview" title="Build your interview." description="Shape a focused practice session around the role and skills you want to sharpen." /><form className="setup-flow" onSubmit={begin}><motion.div className="setup-fields" {...fadeUp}><SetupGroup label="Role"><select value={form.jobRole} onChange={(event) => setForm({ ...form, jobRole: event.target.value })}><option value="">Choose your target role</option>{roles.map((role) => <option key={role}>{role}</option>)}</select></SetupGroup><SetupGroup label="Interview style"><ChoiceRow values={['Technical', 'Behavioral', 'Mixed']} value={form.type} onChange={(value) => setForm({ ...form, type: value })} /></SetupGroup><SetupGroup label="Difficulty"><ChoiceRow values={['Easy', 'Medium', 'Hard']} value={form.difficulty} onChange={(value) => setForm({ ...form, difficulty: value })} /></SetupGroup><SetupGroup label="Question count"><ChoiceRow values={[5, 10, 15]} value={form.totalQuestions} onChange={(value) => setForm({ ...form, totalQuestions: Number(value) })} /></SetupGroup><SetupGroup label="Skills"><div className="skill-pills">{skills.map((skill) => <button type="button" key={skill} className={form.skills.includes(skill) ? 'selected' : ''} onClick={() => toggle(skill)}>{form.skills.includes(skill) && <Check size={13} />}{skill}</button>)}</div></SetupGroup></motion.div><motion.aside className="preview-rail" {...fadeUp} transition={{ ...fadeUp.transition, delay: .1 }}><span className="overline">Live interview preview</span><div className="preview-signal"><span className="status-dot" /><span>Ready to generate</span></div><h2>{form.jobRole || 'Your target role'}</h2><div className="preview-details"><PreviewItem label="Style" value={form.type} /><PreviewItem label="Difficulty" value={form.difficulty} /><PreviewItem label="Questions" value={`${form.totalQuestions}`} /><PreviewItem label="Skills" value={`${form.skills.length} selected`} /></div><div className="preview-rule" /><p>InterviewIQ will adapt the next question to your answer signal.</p><Button type="submit" icon={ArrowUpRight} disabled={loading}>{loading ? <><LoaderCircle size={15} className="spin" /> Preparing...</> : 'Begin interview'}</Button>{error && <span className="form-error">{error}</span>}</motion.aside></form></div>
}
function SetupGroup({ label, children }) { return <div className="setup-group"><span className="field-overline">{label}</span>{children}</div> }
function ChoiceRow({ values, value, onChange }) { return <div className="choice-row">{values.map((item) => <button type="button" key={item} className={value === item ? 'selected' : ''} onClick={() => onChange(item)}>{item}</button>)}</div> }
function PreviewItem({ label, value }) { return <div><span>{label}</span><strong>{value}</strong></div> }

function InterviewRoom() {
  const { sessionId } = useParams(); const location = useLocation(); const navigate = useNavigate(); const [session, setSession] = useState(location.state?.session); const [answer, setAnswer] = useState(''); const [evaluation, setEvaluation] = useState(null); const [loading, setLoading] = useState(!location.state?.session); const [error, setError] = useState(''); const [seconds, setSeconds] = useState(0)
  useEffect(() => { if (!session) interviewApi.status(sessionId).then(setSession).catch((err) => setError(getApiError(err))).finally(() => setLoading(false)) }, [session, sessionId])
  useEffect(() => { const timer = setInterval(() => setSeconds((value) => value + 1), 1000); return () => clearInterval(timer) }, [])
  return <HardenedInterviewRoom session={session} sessionId={sessionId} navigate={navigate} setup={location.state?.setup} />
  if (loading && !session) return <Loading label="Preparing your studio..." />; if (error && !session) return <ErrorLine message={error} retry={() => window.location.reload()} />
  const questionNumber = question?.question_number || 1; const total = session?.total_questions || 1; const time = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  return <div className="studio"><div className="studio-bar"><div className="studio-brand"><span className="iq-mark small">IQ</span><span>Technical interview</span></div><div className="studio-count">{String(questionNumber).padStart(2, '0')} <span>/ {String(total).padStart(2, '0')}</span></div><div className="studio-state"><span className="status-dot" /> Listening <Clock3 size={14} /> {time}</div></div><div className="studio-grid"><aside className="studio-ai"><div className="listening-orb"><div /><span /><i /></div><span className="overline">InterviewIQ AI</span><h2>Listening.</h2><p>Your answer signal is being evaluated for clarity, reasoning, and role relevance.</p><div className="studio-ai-foot"><span className="status-dot" /> Online</div></aside><main className="studio-question"><AnimatePresence mode="wait"><motion.div key={question?.question_id || questionNumber} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: .35 }}><span className="question-meta">Question {String(questionNumber).padStart(2, '0')} / {String(total).padStart(2, '0')} <i /> {question?.skill || 'Core skills'} <i /> {question?.difficulty || location.state?.setup?.difficulty || 'Adaptive'}</span><h1>{question?.question || 'Your next question is loading.'}</h1></motion.div></AnimatePresence><div className="answer-workspace"><label htmlFor="studio-answer">Your response</label><textarea id="studio-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Start typing your answer..." autoFocus /><div className="workspace-tools"><span>{answer.length} characters</span><button type="button"><Mic size={15} /> Voice <small>soon</small></button></div></div>{error && <span className="form-error">{error}</span>}{hint && <div className="hint-note"><Lightbulb size={14} /><span>{hint}</span></div>}<div className="studio-actions"><Button variant="quiet" onClick={() => setAnswer('')}>Clear response</Button><div><Button variant="quiet" icon={CircleHelp} onClick={requestHint} disabled={hintLoading || loading}>{hintLoading ? <><LoaderCircle size={15} className="spin" /> Getting hint</> : 'Need a hint'}</Button><Button icon={ArrowUpRight} onClick={submit} disabled={!answer.trim() || loading || hintLoading}>{loading ? <><LoaderCircle size={15} className="spin" /> Evaluating</> : 'Submit answer'}</Button></div></div>{evaluation && <div className="evaluation-note"><Check size={14} /> Previous answer signal: <strong>{evaluation.score}/10</strong></div>}</main><aside className="studio-progress"><span className="overline">Interview progress</span><strong>{String(questionNumber).padStart(2, '0')} <small>/ {String(total).padStart(2, '0')}</small></strong><div className="thin-progress"><i style={{ width: `${(questionNumber / total) * 100}%` }} /></div><div className="progress-facts"><PreviewItem label="Current skill" value={question?.skill || '-'} /><PreviewItem label="Difficulty" value={question?.difficulty || location.state?.setup?.difficulty || 'Adaptive'} /><PreviewItem label="Time" value={time} /><PreviewItem label="Completed" value={`${Math.max(0, questionNumber - 1)} questions`} /></div></aside></div></div>
}
function Loading({ label }) { return <div className="loading-view"><LoaderCircle size={23} className="spin" /><h2>{label}</h2><p>Connecting to your InterviewIQ workspace.</p></div> }

function Results() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    interviewApi.report(sessionId)
      .then((data) => {
        setReport(data);
        saveHistory({
          sessionId,
          jobRole: data.job_role,
          date: data.interview_date,
          questions: data.questions_answered,
          totalQuestions: data.total_questions,
          correctCount: data.correct_count,
          wrongCount: data.wrong_count,
          accuracy: data.accuracy,
          score: percent(data.overall_score),
          performance: data.performance_level
        });
      })
      .catch((err) => setError(getApiError(err)));
  }, [sessionId]);

  if (error) return <ErrorLine message={error} retry={() => window.location.reload()} />;
  if (!report) return <Loading label="Composing your assessment..." />;

  return (
    <Assessment
      report={report}
      isResultsPage={true}
      onDetails={() => navigate(`/reports/${sessionId}`)}
    />
  );
}

function Assessment({ report, isResultsPage, onDetails }) {
  const score = percent(report.overall_score);
  const total = report.total_questions || report.questions_answered || 1;
  const correct = report.correct_count ?? 0;
  const wrong = report.wrong_count ?? 0;
  const accuracy = Math.round(report.accuracy !== undefined ? report.accuracy : (total > 0 ? (correct / total) * 100 : 0));
  const answered = report.questions_answered ?? report.questions?.length ?? 0;

  return (
    <div className="assessment">
      <Intro
        overline={report.completion_status === 'completed' ? 'Assessment complete' : 'Interview in progress'}
        title="Your interview performance."
        description={`A considered read on your ${report.job_role} practice session.`}
      />

      <div className="section-kicker" style={{ marginTop: '30px' }}>
        <span>IQ</span>
        <strong>INTERVIEW RESULT</strong>
        <small>{report.completion_status === 'completed' ? 'Session completed' : `Completed ${answered} of ${total}`}</small>
      </div>

      <div className="result-summary-grid">
        <div className="summary-stat-card stat-correct">
          <span>Correct</span>
          <strong>{correct} <small>/ {total}</small></strong>
        </div>
        <div className="summary-stat-card stat-wrong">
          <span>Wrong</span>
          <strong>{wrong} <small>/ {total}</small></strong>
        </div>
        <div className="summary-stat-card">
          <span>Total Questions</span>
          <strong>{total}</strong>
        </div>
        <div className="summary-stat-card">
          <span>Accuracy</span>
          <strong>{accuracy}<small>%</small></strong>
        </div>
      </div>

      <div className="secondary-metrics-row">
        <span>Overall Score: <strong>{score}%</strong> ({report.overall_score_numeric ?? Math.round(score / 10)}/10)</span>
        <span>•</span>
        <span>Performance Level: <strong>{report.performance_level}</strong></span>
        <span>•</span>
        <span>Status: <strong>{report.completion_status === 'completed' ? 'Completed' : `Incomplete (${answered}/${total})`}</strong></span>
      </div>

      <section className="editorial-block">
        <div className="section-kicker">
          <span>01</span>
          <strong>QUESTION REVIEW</strong>
          <small>{report.questions?.length || 0} questions evaluated</small>
        </div>
        <div className="question-review-list">
          {report.questions?.length ? (
            report.questions.map((q) => {
              const isUnavailable = q.result === 'Unavailable' || (q.score === null && q.score === undefined && !q.evaluation);
              return (
                <div
                  key={q.question_number}
                  className={`question-review-card ${q.result === 'Correct' ? 'result-correct' : (q.result === 'Wrong' ? 'result-wrong' : '')}`}
                >
                  <div className="question-review-header">
                    <div className="question-meta-group">
                      <span className="question-num-tag">Question {q.question_number}</span>
                      <span className="badge-tag badge-skill">{q.skill}</span>
                      <span className="badge-tag badge-diff">{q.difficulty}</span>
                    </div>
                    <div className="question-meta-group">
                      <span
                        className={`question-result-badge ${
                          q.result === 'Correct'
                            ? 'badge-correct'
                            : q.result === 'Wrong'
                            ? 'badge-wrong'
                            : 'badge-unavailable'
                        }`}
                      >
                        {q.result === 'Correct' ? <Check size={13} /> : (q.result === 'Wrong' ? <X size={13} /> : null)}
                        {q.result === 'Correct' ? '✓ Correct' : (q.result === 'Wrong' ? '✗ Wrong' : 'Unavailable')}
                      </span>
                      <span className="question-num-tag" style={{ color: 'var(--muted)', fontSize: '11px' }}>
                        SCORE: {q.score !== null && q.score !== undefined ? `${q.score}/10` : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="question-review-body">
                    <div className="review-field-block">
                      <span className="review-field-label">QUESTION:</span>
                      <div className="review-field-content"><strong>{q.question}</strong></div>
                    </div>

                    <div className="review-field-block field-candidate">
                      <span className="review-field-label">YOUR ANSWER:</span>
                      <div className="review-field-content">{q.candidate_answer || <span className="review-field-content text-muted">(No answer provided)</span>}</div>
                    </div>

                    <div className="review-field-block field-expected">
                      <span className="review-field-label label-expected">EXPECTED / CORRECT ANSWER:</span>
                      <div className="review-field-content">{q.expected_answer || (isUnavailable ? <span className="review-field-content text-muted">Evaluation unavailable — this answer has not been successfully evaluated yet.</span> : <span className="review-field-content text-muted">Standard interview criteria</span>)}</div>
                    </div>

                    <div className="review-field-block">
                      <span className="review-field-label">RESULT:</span>
                      <div className="review-field-content">
                        <strong>{q.result === 'Correct' ? '✓ Correct' : (q.result === 'Wrong' ? '✗ Wrong' : 'Evaluation unavailable — this answer has not been successfully evaluated yet.')}</strong>
                      </div>
                    </div>

                    <div className="review-field-block">
                      <span className="review-field-label">SCORE:</span>
                      <div className="review-field-content">{q.score !== null && q.score !== undefined ? `${q.score} / 10` : 'N/A'}</div>
                    </div>

                    <div className="review-field-block">
                      <span className="review-field-label">EVALUATION:</span>
                      <div className="review-field-content">{q.evaluation || 'Evaluation unavailable — this answer has not been successfully evaluated yet.'}</div>
                    </div>

                    {q.strengths?.length > 0 && (
                      <div className="review-field-block">
                        <span className="review-field-label">WHAT YOU DID WELL:</span>
                        <div className="review-pills-list">
                          {q.strengths.map((s, si) => (
                            <div key={si} className="review-pill-item pill-strength">
                              <Check size={13} />
                              <span>{s}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {q.weaknesses?.length > 0 && (
                      <div className="review-field-block">
                        <span className="review-field-label">WHAT TO IMPROVE:</span>
                        <div className="review-pills-list">
                          {q.weaknesses.map((w, wi) => (
                            <div key={wi} className="review-pill-item pill-weakness">
                              <X size={13} />
                              <span>{w}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {q.improvement && (
                      <div className="review-field-block">
                        <span className="review-field-label">HOW TO ANSWER BETTER:</span>
                        <div className="review-field-content text-muted">{q.improvement}</div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <Empty icon={Target} title="No question review available" text="Complete the interview session to see detailed question evaluations." />
          )}
        </div>
      </section>

      <section className="editorial-block">
        <div className="section-kicker">
          <span>02</span>
          <strong>Skill spectrum</strong>
          <small>How your answers performed</small>
        </div>
        <div className="spectrum-table">
          {report.skill_scores?.length ? (
            report.skill_scores.map((skill) => {
              const value = percent(skill.avg_score * 10);
              return (
                <div className="spectrum-line" key={skill.skill}>
                  <span>{skill.skill}</span>
                  <div><i style={{ width: `${value}%` }} /></div>
                  <strong>{value}</strong>
                </div>
              );
            })
          ) : (
            <Empty icon={Target} title="Skill data will appear here" text="Complete a full evaluation to reveal your skill spectrum." />
          )}
        </div>
      </section>

      <div className="assessment-columns">
        <EditorialList number="03" title="What you did well" items={report.strengths} empty="Strength patterns will appear after evaluation." />
        <EditorialList number="04" title="Where to improve" items={report.weak_areas} empty="No improvement areas were returned." />
      </div>

      <section className="editorial-block next-step">
        <div className="section-kicker">
          <span>05</span>
          <strong>Next step</strong>
          <small>AI recommendations</small>
        </div>
        {report.recommendations?.length ? (
          report.recommendations.map((item, index) => (
            <div className="recommendation-line" key={`${item.topic}-${index}`}>
              <span>0{index + 1}</span>
              <div>
                <strong>{item.topic}</strong>
                <p>{item.action}</p>
              </div>
            </div>
          ))
        ) : (
          <Empty icon={Lightbulb} title="Your next step is still forming" text="Recommendations will appear in the full report." />
        )}
      </section>

      {report.preparation_plan?.length > 0 && (
        <section className="editorial-block">
          <div className="section-kicker">
            <span>06</span>
            <strong>Personalized preparation plan</strong>
            <small>{report.preparation_plan.length}-day roadmap</small>
          </div>
          <div className="prep-plan-grid">
            {report.preparation_plan.map((day) => (
              <div key={day.day} className="prep-day-card">
                <strong>Day {day.day}: {day.focus}</strong>
                <span>{day.estimated_hours}h estimated</span>
                {day.topics?.length > 0 && (
                  <ul>
                    {day.topics.map((t, ti) => <li key={ti}>{t}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="assessment-actions">
        {isResultsPage ? (
          <>
            <Button variant="solid" onClick={() => onDetails && onDetails()}>
              View report <ArrowUpRight size={15} />
            </Button>
            <Link className="action action-outline" to="/reports">
              Practice archive <ChevronRight size={15} />
            </Link>
          </>
        ) : (
          <Link className="action action-outline" to="/reports">
            Back to practice archive <ChevronRight size={15} />
          </Link>
        )}
      </div>
    </div>
  );
}

function EditorialList({ number, title, items, empty }) {
  return (
    <section className="editorial-block">
      <div className="section-kicker">
        <span>{number}</span>
        <strong>{title}</strong>
        <small>{items?.length || 0} observations</small>
      </div>
      {items?.length ? (
        items.map((item, index) => (
          <div className="observation" key={`${item.skill}-${index}`}>
            <span className="observation-mark"><Check size={13} /></span>
            <div>
              <strong>{item.skill}</strong>
              <p>{item.reason}</p>
            </div>
          </div>
        ))
      ) : (
        <Empty icon={Target} title={empty} text="Keep practicing to build a clearer signal." />
      )}
    </section>
  );
}

function Reports() {
  const history = useUserHistory();
  const [query, setQuery] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const filtered = history.filter((item) => item.jobRole?.toLowerCase().includes(query.toLowerCase()));

  const download = async (sessionId) => {
    setDownloadError('');
    try {
      await downloadBlob(sessionId);
    } catch (err) {
      setDownloadError(getApiError(err));
    }
  };

  return (
    <div className="archive">
      <Intro
        overline="Practice archive"
        title="Your interview history."
        description="Every session is a signal. Review what changed, then decide what to sharpen next."
        action={<Link className="action action-solid" to="/new">New interview <Plus size={15} /></Link>}
      />
      <div className="archive-toolbar">
        <div className="archive-search">
          <Search size={15} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by role" />
        </div>
        <span>{filtered.length} sessions</span>
      </div>
      {downloadError && <span className="form-error">{downloadError}</span>}
      {filtered.length ? (
        <div className="archive-list">
          <div className="archive-head">
            <span>Role / format</span>
            <span>Date</span>
            <span>Result</span>
            <span>Performance</span>
            <span style={{ textAlign: 'right' }}>Action</span>
          </div>
          {filtered.map((item) => (
            <div className="archive-row" key={item.sessionId}>
              <div>
                <strong>{item.jobRole}</strong>
                <small>{item.type || 'Technical interview'}</small>
              </div>
              <span>{formatDate(item.date)}</span>
              <strong>
                {item.correctCount !== undefined
                  ? `${item.correctCount}/${item.totalQuestions || item.questions} correct (${Math.round(item.accuracy ?? item.score ?? 0)}%)`
                  : (item.score ? `${item.score}%` : '--')}
              </strong>
              <span className="archive-performance">{item.performance || 'Completed'}</span>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
                <Link className="action action-outline view-report-btn" to={`/reports/${item.sessionId}`} style={{ height: '30px', padding: '0 10px', fontSize: '11px', whiteSpace: 'nowrap' }}>
                  View report <ArrowUpRight size={13} />
                </Link>
                <button type="button" onClick={() => download(item.sessionId)} aria-label="Download PDF" title="Download PDF"><Download size={15} /></button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          icon={FileText}
          title="No interview history yet"
          text="Your completed sessions will gather here as a private practice archive."
          action={<Link className="text-action" to="/new">Start your first session <ArrowUpRight size={14} /></Link>}
        />
      )}
    </div>
  );
}

function ReportDetails() {
  const { sessionId } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(false);
  const [toast, setToast] = useState('');
  const [downloadError, setDownloadError] = useState('');

  useEffect(() => {
    interviewApi.report(sessionId)
      .then(setReport)
      .catch((err) => setError(getApiError(err)));
  }, [sessionId]);

  if (error) return <ErrorLine message={error} retry={() => window.location.reload()} />;
  if (!report) return <Loading label="Loading assessment..." />;

  const send = async (email) => {
    try {
      await interviewApi.sendReport(sessionId, { candidate_email: email });
      setModal(false);
      setToast('Report sent successfully.');
      setTimeout(() => setToast(''), 3500);
    } catch (err) {
      throw new Error(getApiError(err));
    }
  };

  const download = async () => {
    setDownloadError('');
    try {
      await downloadBlob(sessionId);
    } catch (err) {
      setDownloadError(getApiError(err));
    }
  };

  return (
    <div className="report-document">
      <Intro
        overline="InterviewIQ assessment"
        title={report.job_role}
        description={`Generated ${formatDate(report.interview_date)} / ${report.questions_answered} questions answered`}
        action={
          <div className="document-actions">
            <Button variant="outline" onClick={download}><Download size={15} /> Download PDF</Button>
            <Button icon={Mail} onClick={() => setModal(true)}>Send report</Button>
          </div>
        }
      />
      {downloadError && <span className="form-error">{downloadError}</span>}
      <div className="document-meta">
        <span>Completion status <strong>{report.completion_status}</strong></span>
        <span>Performance <strong>{report.performance_level}</strong></span>
        <span>Accuracy <strong>{Math.round(report.accuracy ?? 0)}% ({report.correct_count ?? 0}/{report.total_questions || report.questions_answered})</strong></span>
      </div>
      <Assessment report={report} isResultsPage={false} />
      {modal && <EmailModal onClose={() => setModal(false)} onSend={send} />}
      {toast && <div className="toast"><Check size={16} /> {toast}</div>}
    </div>
  );
}

function EmailModal({ onClose, onSend }) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      await onSend(email);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <motion.div className="modal" onMouseDown={(event) => event.stopPropagation()} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
        <button className="close-button" onClick={onClose} aria-label="Close"><X size={17} /></button>
        <span className="overline">Share assessment</span>
        <h2>Send this report</h2>
        <p>Deliver a polished PDF report through your InterviewIQ workflow.</p>
        <form onSubmit={submit}>
          <label htmlFor="candidate-email">Candidate email</label>
          <input id="candidate-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
          {error && <span className="form-error">{error}</span>}
          <Button type="submit" icon={Mail} disabled={loading}>{loading ? 'Sending...' : 'Send report'}</Button>
        </form>
      </motion.div>
    </div>
  );
}

function Analytics() { const history = useUserHistory(); const scores = history.map((item) => item.score).filter(Boolean); const average = scores.length ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length) : null; return <div className="insights-page"><Intro overline="Insights" title="Your interview journey." description="A calm view of the signal you are building across practice sessions." /><section className="journey-hero"><div className="journey-score"><span className="overline">Average performance</span><strong>{average ?? '--'}<small>{average ? '%' : ''}</small></strong><p>{history.length ? `${history.length} completed session${history.length === 1 ? '' : 's'} in your archive.` : 'Complete an interview to establish your first performance signal.'}</p></div><div className="journey-chart"><div className="chart-axis"><span>100</span><span>50</span><span>0</span></div><svg viewBox="0 0 600 190" preserveAspectRatio="none"><path d="M0 160 C72 150 97 125 160 140 S245 84 304 109 S390 54 450 78 S530 28 600 40" fill="none" stroke="url(#journey-line)" strokeWidth="2" /><defs><linearGradient id="journey-line"><stop stopColor="#8b84ff" /><stop offset="1" stopColor="#73b3ee" /></linearGradient></defs></svg>{!average && <span className="chart-empty-copy">Your trajectory will reveal itself after your first completed interview.</span>}</div></section><div className="insight-lanes"><InsightLane title="Skill evolution" icon={Target} text={history.length ? 'Your skill profile is gathering enough signal for comparison.' : 'Skill movement will appear as your archive grows.'} /><InsightLane title="Improvement areas" icon={Lightbulb} text="Recurring gaps will become clear after multiple evaluations." /><InsightLane title="Next interview focus" icon={TrendingUp} text="InterviewIQ will recommend what to practice next." /></div></div> }
function InsightLane({ title, icon: Icon, text }) { return <div className="insight-lane"><Icon size={18} /><div><span className="overline">{title}</span><p>{text}</p></div><ChevronRight size={16} /></div> }
function AuthPage({ mode }) {
  const navigate = useNavigate(); const { setUser } = useContext(AuthContext); const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' }); const [error, setError] = useState(''); const [loading, setLoading] = useState(false); const register = mode === 'register'
  const submit = async (event) => { event.preventDefault(); if (register && form.password !== form.confirm) return setError('Passwords do not match.'); setLoading(true); setError(''); try { const result = register ? await authApi.register(form) : await authApi.login({ email: form.email, password: form.password }); localStorage.setItem('interviewiq_access_token', result.access_token); localStorage.setItem('interviewiq_user', JSON.stringify(result.user)); setUser(result.user); navigate('/') } catch (err) { setError(getApiError(err)) } finally { setLoading(false) } }
  return <main className="auth-page"><div className="auth-orb"><BrainCircuit size={30} /></div><Link className="iq-lockup auth-brand" to="/"><span className="iq-mark">IQ</span><span>InterviewIQ</span></Link><div className="auth-form"><span className="overline">InterviewIQ AI platform</span><h1>{register ? 'Create your account.' : 'Welcome back.'}</h1><p>{register ? 'Build a private workspace for your interview practice.' : 'Continue your interview preparation workspace.'}</p><form onSubmit={submit}>{register && <label>Full name<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" /></label>}<label>Email<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" /></label><label>Password<input required type="password" minLength="8" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="At least 8 characters" /></label>{register && <label>Confirm password<input required type="password" minLength="8" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} placeholder="Repeat your password" /></label>}{error && <span className="auth-error">{error}</span>}<Button type="submit" icon={ArrowUpRight} disabled={loading}>{loading ? 'Please wait...' : register ? 'Create account' : 'Sign in'}</Button></form><span className="auth-switch">{register ? 'Already have an account?' : "Don't have an account?"} <Link to={register ? '/login' : '/register'}>{register ? 'Sign in' : 'Create one'}</Link></span></div></main>
}
function SettingsPage() { return <div className="settings-page"><Intro overline="Workspace" title="Settings." description="A few quiet preferences for your InterviewIQ workspace." /><div className="settings-document"><div className="settings-nav"><span className="active">Profile</span><span>Preferences</span><span>Notifications</span><span>Appearance</span></div><div className="settings-copy"><SettingsSection overline="Profile" title="Profile" description="Candidate workspace"><div className="profile-detail"><span className="profile-initials">?</span><div><strong>Authenticated profile</strong><small>Your account details appear in the active settings view.</small></div></div></SettingsSection><SettingsSection overline="Interview preferences" title="Practice defaults" description="These preferences shape the setup experience for your next session."><div className="settings-options"><SettingValue label="Default interview style" value="Technical" /><SettingValue label="Default difficulty" value="Medium" /><SettingValue label="Default question count" value="10 questions" /></div></SettingsSection><SettingsSection overline="Notifications" title="Stay in the loop" description="Delivery notifications will be available when your account is connected."><div className="setting-line"><div><strong>Report delivery updates</strong><small>Receive a notice when an assessment is sent.</small></div><span className="switch-off" /></div></SettingsSection><SettingsSection overline="Appearance" title="Dark interface" description="Designed for focused preparation."><div className="setting-line"><div><strong>Use the InterviewIQ dark system</strong><small>High contrast, low distraction, calm surfaces.</small></div><span className="switch-on" /></div></SettingsSection></div></div></div> }
function SettingsSection({ overline, title, description, children }) { return <section className="settings-section"><span className="overline">{overline}</span><h2>{title}</h2><p>{description}</p>{children}</section> }
function SettingValue({ label, value }) { return <div className="setting-value"><span>{label}</span><strong>{value}</strong></div> }

function UserSettingsPage({ user }) { return <div className="settings-page"><Intro overline="Workspace" title="Settings." description="A few quiet preferences for your InterviewIQ workspace." /><div className="settings-document"><div className="settings-nav"><span className="active">Profile</span><span>Preferences</span><span>Notifications</span><span>Appearance</span></div><div className="settings-copy"><SettingsSection overline="Profile" title={user?.name || 'Profile'} description={user?.email || 'Authenticated workspace'}><div className="profile-detail"><span className="profile-initials">{initials(user?.name)}</span><div><strong>{user?.name}</strong><small>{user?.email}</small></div></div></SettingsSection><SettingsSection overline="Interview preferences" title="Practice defaults" description="Your current practice defaults."><div className="settings-options"><SettingValue label="Default interview style" value="Technical" /><SettingValue label="Default difficulty" value="Medium" /><SettingValue label="Default question count" value="10 questions" /></div></SettingsSection><SettingsSection overline="Notifications" title="Stay in the loop" description="Delivery notifications will be available when connected."><div className="setting-line"><div><strong>Report delivery updates</strong><small>Receive a notice when an assessment is sent.</small></div><span className="switch-off" /></div></SettingsSection><SettingsSection overline="Appearance" title="Dark interface" description="Designed for focused preparation."><div className="setting-line"><div><strong>Use the InterviewIQ dark system</strong><small>High contrast, low distraction, calm surfaces.</small></div><span className="switch-on" /></div></SettingsSection></div></div></div> }

export default App
