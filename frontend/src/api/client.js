import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Companies API
export const companiesAPI = {
  list: () => api.get('/companies'),
  create: (data) => api.post('/companies', data),
  get: (id) => api.get(`/companies/${id}`),
  update: (id, data) => api.put(`/companies/${id}`, data),
  delete: (id) => api.delete(`/companies/${id}`),
}

// Jobs API
export const jobsAPI = {
  list: () => api.get('/jobs'),
  get: (id) => api.get(`/jobs/${id}`),
  getMatches: () => api.get('/jobs/matches'),
  parseResume: (text) => api.post('/jobs/parse-resume-text', { resume_text: text }),
  saveResume: (resumeData) => api.post('/jobs/resume', resumeData),
  updateResume: (skillsToAdd) => api.put('/jobs/resume', { skills_to_add: skillsToAdd }),
  applyToJob: (jobId) => api.post(`/applications/apply/${jobId}`),
  generateCoverLetter: (jobId) => api.post(`/jobs/generate-cover-letter/${jobId}`),
  analyzeResumeForOptimization: (jobId) => api.post(`/jobs/optimize-resume/${jobId}`),
  approve: (token) => api.get(`/apply/approve?token=${token}`),
  skip: (token) => api.get(`/apply/skip?token=${token}`),
}

// Resume API
export const resumeAPI = {
  upload: (data) => api.post('/resume', data),
  get: () => api.get('/resume'),
}

// Applications API
export const applicationsAPI = {
  list: () => api.get('/applications'),
  get: (id) => api.get(`/applications/${id}`),
}

// Settings API
export const settingsAPI = {
  get: () => api.get('/settings'),
  update: (data) => api.put(`/settings/${data.id}`, data),
}

export default api
