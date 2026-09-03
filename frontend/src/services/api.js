import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('interviewiq_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const interviewApi = {
  start: (payload) => api.post('/api/interview/start', payload).then(({ data }) => data),
  answer: (payload) => api.post('/api/interview/answer', payload).then(({ data }) => data),
  retryAnswer: (sessionId, questionId) => api.post(`/api/interview/${sessionId}/answers/${questionId}/retry`).then(({ data }) => data),
  recordIntegrity: (sessionId, payload) => api.post(`/api/interview/${sessionId}/integrity`, payload).then(({ data }) => data),
  expire: (sessionId) => api.post(`/api/interview/${sessionId}/expire`).then(({ data }) => data),
  status: (sessionId) => api.get(`/api/interview/${sessionId}`).then(({ data }) => data),
  history: () => api.get('/api/interview/history').then(({ data }) => data),
  finish: (sessionId) => api.post(`/api/interview/${sessionId}/finish`).then(({ data }) => data),
  hint: (sessionId, questionId) => api.post(`/api/interview/${sessionId}/hint`, { question_id: questionId }).then(({ data }) => data),
  report: (sessionId) => api.get(`/api/interview/${sessionId}/report`).then(({ data }) => data),
  sendReport: (sessionId, payload) => api.post(`/api/interview/${sessionId}/send-report`, payload).then(({ data }) => data),
}

export const coachApi = {
  chat: (payload) => api.post('/api/chat', payload).then(({ data }) => data),
  tailorResume: (file, jobDescription) => { const form = new FormData(); form.append('resume', file); form.append('job_description', jobDescription); return api.post('/api/coach/resume/tailor', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then(({ data }) => data) },
  tailoredResumePdf: (id) => api.get(`/api/coach/resume/${id}/pdf`, { responseType: 'blob' }).then(({ data }) => data),
}

export const authApi = {
  register: (payload) => api.post('/api/auth/register', payload).then(({ data }) => data),
  login: (payload) => api.post('/api/auth/login', payload).then(({ data }) => data),
  me: () => api.get('/api/auth/me').then(({ data }) => data),
}

export const reportPdfUrl = (sessionId) => {
  const base = import.meta.env.VITE_PUBLIC_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return `${base.replace(/\/$/, '')}/api/interview/${sessionId}/report/pdf`
}

export const downloadReportFile = (sessionId, format = 'pdf') => {
  const path = format === 'docx' ? `/api/interview/${sessionId}/report/download/docx` : `/api/interview/${sessionId}/report/pdf`
  return api.get(path, { responseType: 'blob' }).then(({ data }) => data)
}

export const getApiError = (error) => {
  const status = error?.response?.status
  const detail = error?.response?.data?.detail
  if (detail && typeof detail === 'object' && detail.message) return detail.message
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have access to this resource.'
  if (status === 404) return 'The requested interview data was not found.'
  if (status === 429) return 'The AI service is temporarily busy. Please try again shortly.'
  if (status >= 500) return 'The service is temporarily unavailable. Please try again shortly.'
  if (!error?.response && error?.request) return 'The backend is unreachable. Check that the InterviewIQ server is running.'
  return error?.response?.data?.message || error?.response?.data?.detail || error?.message || 'Something went wrong. Please try again.'
}

export default api
