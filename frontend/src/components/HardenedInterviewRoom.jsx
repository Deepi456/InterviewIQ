import { useEffect, useRef, useState } from 'react'
import { CircleHelp, Clock3, Lightbulb, LoaderCircle, Mic } from 'lucide-react'
import { interviewApi, getApiError } from '../services/api'

function Button({ children, variant = 'solid', icon: Icon, ...props }) { return <button className={`action action-${variant}`} {...props}>{children}{Icon && <Icon size={15} />}</button> }

const isoNow = () => new Date().toISOString()
const policy = {
  preventCopy: import.meta.env.VITE_INTERVIEW_PREVENT_COPY === 'true',
  preventPaste: import.meta.env.VITE_INTERVIEW_PREVENT_PASTE === 'true',
  preventCut: import.meta.env.VITE_INTERVIEW_PREVENT_CUT === 'true',
  preventContextMenu: import.meta.env.VITE_INTERVIEW_PREVENT_CONTEXT_MENU === 'true',
}
const fullscreenRequired = import.meta.env.VITE_INTERVIEW_FULLSCREEN_REQUIRED === 'true'

export default function HardenedInterviewRoom({ session: initialSession, sessionId, navigate, setup }) {
  const [session, setSession] = useState(initialSession)
  const [answer, setAnswer] = useState('')
  const [hint, setHint] = useState('')
  const [error, setError] = useState('')
  const [evaluationPending, setEvaluationPending] = useState(false)
  const [loading, setLoading] = useState(!initialSession)
  const [hintLoading, setHintLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [expired, setExpired] = useState(false)
  const [fullscreen, setFullscreen] = useState(Boolean(document.fullscreenElement))
  const [away, setAway] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const lastIntegrityEvent = useRef(0)
  const submitLock = useRef(false)
  const answerRef = useRef('')
  answerRef.current = answer

  useEffect(() => {
    if (session) return
    interviewApi.status(sessionId).then((nextSession) => {
      setSession(nextSession)
      if (nextSession.saved_answer) setAnswer(nextSession.saved_answer)
      if (nextSession.evaluation_status === 'failed' || nextSession.evaluation_status === 'pending') setEvaluationPending(true)
    }).catch((err) => setError(getApiError(err))).finally(() => setLoading(false))
  }, [session, sessionId])

  useEffect(() => {
    const started = session?.started_at ? new Date(session.started_at).getTime() : Date.now()
    const expiry = session?.expires_at ? new Date(session.expires_at).getTime() : null
    const update = () => {
      const remaining = expiry ? Math.max(0, Math.floor((expiry - Date.now()) / 1000)) : null
      setSeconds(expiry ? remaining : Math.max(0, Math.floor((Date.now() - started) / 1000)))
      if (remaining === 0 && !expired) { setExpired(true); interviewApi.expire(sessionId).catch(() => {}); if (answerRef.current.trim()) submit(null, true) }
    }
    update()
    const timer = setInterval(update, 1000)
    return () => clearInterval(timer)
  }, [session?.started_at, session?.expires_at, expired])

  useEffect(() => {
    const changed = () => setFullscreen(Boolean(document.fullscreenElement))
    document.addEventListener('fullscreenchange', changed)
    return () => document.removeEventListener('fullscreenchange', changed)
  }, [])

  useEffect(() => {
    if (!policy.preventCopy && !policy.preventPaste && !policy.preventCut && !policy.preventContextMenu) return undefined
    const block = (event) => {
      if ((event.type === 'copy' && policy.preventCopy) || (event.type === 'paste' && policy.preventPaste) || (event.type === 'cut' && policy.preventCut) || (event.type === 'contextmenu' && policy.preventContextMenu)) event.preventDefault()
    }
    for (const event of ['copy', 'paste', 'cut', 'contextmenu']) document.addEventListener(event, block)
    return () => { for (const event of ['copy', 'paste', 'cut', 'contextmenu']) document.removeEventListener(event, block) }
  }, [])

  useEffect(() => {
    const record = (type) => {
      const now = Date.now()
      if (now - lastIntegrityEvent.current < 1000) return
      lastIntegrityEvent.current = now
      setAway(type !== 'focus_return')
      interviewApi.recordIntegrity(sessionId, { type, timestamp: isoNow(), question_id: session?.current_question?.question_id }).catch(() => {})
    }
    const hidden = () => document.hidden && record('visibility_lost')
    const blur = () => document.hidden && record('window_blur')
    const focus = () => !document.hidden && record('focus_return')
    document.addEventListener('visibilitychange', hidden)
    window.addEventListener('blur', blur)
    window.addEventListener('focus', focus)
    return () => { document.removeEventListener('visibilitychange', hidden); window.removeEventListener('blur', blur); window.removeEventListener('focus', focus) }
  }, [sessionId, session?.current_question?.question_id])

  useEffect(() => {
    const warn = (event) => { if (!session || session.status === 'completed') return; event.preventDefault(); event.returnValue = 'Your interview is in progress.' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [session])

  const question = session?.current_question
  const requestHint = async () => {
    if (!question || hintLoading || submitting || hint) return
    setHintLoading(true); setError('')
    try { setHint((await interviewApi.hint(sessionId, question.question_id)).hint) } catch (err) { setError(getApiError(err)) } finally { setHintLoading(false) }
  }

  const submit = async (event, autoExpired = false) => {
    event?.preventDefault()
    if (!question || !answer.trim() || submitLock.current || submitting || (expired && !autoExpired)) return
    const submittedAnswer = answer.trim()
    submitLock.current = true; setSubmitting(true); setError(''); setEvaluationPending(false)
    const questionId = question.question_id
    try {
      const result = await interviewApi.answer({ session_id: sessionId, question_id: questionId, answer: submittedAnswer, auto_expired: autoExpired })
      setAnswer(''); setHint('')
      if (!result.evaluation) { setEvaluationPending(true); return }
      if (result.interview_complete) { navigate(`/results/${sessionId}`); return }
      setSession((current) => ({ ...current, current_question: result.next_question, current_question_number: result.question_number }))
    } catch (err) {
      setError(getApiError(err)); setEvaluationPending(Boolean(err?.response?.data?.detail?.answer_saved)); setAnswer(submittedAnswer)
    } finally { submitLock.current = false; setSubmitting(false) }
  }

  const retryEvaluation = async () => {
    if (!question || submitting) return
    setSubmitting(true); setError('')
    try {
      const result = await interviewApi.retryAnswer(sessionId, question.question_id)
      setEvaluationPending(false); setHint('')
      if (result.interview_complete) navigate(`/results/${sessionId}`)
      else setSession((current) => ({ ...current, current_question: result.next_question, current_question_number: result.question_number }))
    } catch (err) { setError(getApiError(err)); setEvaluationPending(true) } finally { setSubmitting(false) }
  }

  if (loading && !session) return <div className="loading-view"><LoaderCircle size={23} className="spin" /><h2>Preparing your studio...</h2></div>
  if (!question) return <div className="loading-view"><h2>{error || 'Interview question unavailable.'}</h2></div>
  const time = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  const enterFullscreen = async () => { try { await document.documentElement.requestFullscreen(); setFullscreen(true) } catch (err) { setError('Fullscreen is unavailable in this browser.') } }
  return <div className="studio">
    {fullscreenRequired && !fullscreen && <div className="coach-error">Please enter fullscreen mode to continue. <button type="button" onClick={enterFullscreen}>Enter fullscreen</button></div>}
    {(policy.preventCopy || policy.preventPaste || policy.preventCut || policy.preventContextMenu) && <div className="hint-note">Interview integrity policy: copy, paste, cut, or context menu actions may be restricted for this interview.</div>}
    {away && <div className="coach-error">Interview focus lost. Please return to the interview window.</div>}
    <div className="studio-bar"><div className="studio-brand"><span className="iq-mark small">IQ</span><span>Technical interview</span></div><div className="studio-count">{String(question.question_number).padStart(2, '0')} <span>/ {String(question.total_questions).padStart(2, '0')}</span></div><div className="studio-state"><span className="status-dot" /> Listening <Clock3 size={14} /> {time}</div></div>
    <div className="studio-grid"><aside className="studio-ai"><div className="listening-orb"><div /><span /><i /></div><span className="overline">InterviewIQ AI</span><h2>Listening.</h2><p>Your answer is saved before AI evaluation begins.</p><div className="studio-ai-foot"><span className="status-dot" /> Online</div></aside>
      <main className="studio-question"><span className="question-meta">Question {String(question.question_number).padStart(2, '0')} / {String(question.total_questions).padStart(2, '0')} <i /> {question.skill} <i /> {question.difficulty}</span><h1>{question.question}</h1>
        <form onSubmit={submit}><div className="answer-workspace"><label htmlFor="studio-answer">Your response</label><textarea id="studio-answer" value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Start typing your answer..." autoFocus disabled={submitting || evaluationPending || expired} /><div className="workspace-tools"><span>{answer.length} characters</span><button type="button"><Mic size={15} /> Voice <small>soon</small></button></div></div>
          {error && <span className="form-error">{error}</span>}{hint && <div className="hint-note"><Lightbulb size={14} /><span>{hint}</span></div>}{evaluationPending && <div className="hint-note"><CircleHelp size={14} /><span>Your answer was saved. AI evaluation is temporarily unavailable.</span><button type="button" onClick={retryEvaluation} disabled={submitting}>Retry evaluation</button></div>}
          <div className="studio-actions"><Button variant="quiet" type="button" onClick={() => setAnswer('')} disabled={submitting || evaluationPending || expired}>Clear response</Button><div><Button variant="quiet" type="button" icon={CircleHelp} onClick={requestHint} disabled={hintLoading || submitting || Boolean(hint) || expired}>{hintLoading ? 'Getting hint...' : 'Need a hint?'}</Button><Button type="submit" disabled={submitting || evaluationPending || expired || !answer.trim()}>{expired ? 'Time expired' : submitting ? 'Saving and evaluating...' : 'Submit answer'}</Button></div></div>
        </form>
      </main></div>
  </div>
}
