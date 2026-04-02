import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { resumeAPI, jobsAPI } from '../api/client'

export default function ResumeUpload({ onResumeUploaded }) {
  const [mode, setMode] = useState('paste') // 'paste' or 'file'
  const [resumeText, setResumeText] = useState('')
  const [parsedResume, setParsedResume] = useState(null)
  const [step, setStep] = useState(1) // 1: input, 2: preview, 3: confirm

  const parseMutation = useMutation({
    mutationFn: async (text) => {
      const response = await jobsAPI.parseResume(text)
      return response.data
    },
    onSuccess: (data) => {
      setParsedResume(data)
      setStep(2)
    },
    onError: (error) => {
      alert('Failed to parse resume: ' + (error.response?.data?.detail || error.message))
    },
  })

  const saveMutation = useMutation({
    mutationFn: async (resumeData) => {
      const response = await jobsAPI.saveResume(resumeData)
      return response.data
    },
    onSuccess: () => {
      alert('Resume uploaded successfully! Refreshing job matches...')
      setParsedResume(null)
      setResumeText('')
      setStep(1)
      setMode('paste')
      onResumeUploaded?.()
    },
    onError: (error) => {
      alert('Failed to save resume: ' + (error.response?.data?.detail || error.message))
    },
  })

  const handleParse = () => {
    if (!resumeText.trim()) {
      alert('Please enter or upload resume text')
      return
    }
    parseMutation.mutate(resumeText)
  }

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result
      setResumeText(text)
      setMode('file')
    }
    reader.readAsText(file)
  }

  const handleConfirm = () => {
    saveMutation.mutate(parsedResume)
  }

  const handleReset = () => {
    setStep(1)
    setParsedResume(null)
    setResumeText('')
    setMode('paste')
  }

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6">📄 Upload Your Resume</h2>

      {/* Step 1: Input */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setMode('paste')}
              className={`px-4 py-2 rounded ${
                mode === 'paste'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Paste Text
            </button>
            <button
              onClick={() => setMode('file')}
              className={`px-4 py-2 rounded ${
                mode === 'file'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Upload File
            </button>
          </div>

          {mode === 'paste' ? (
            <div>
              <label className="block text-sm font-semibold mb-2">Paste Resume Text</label>
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste your resume content here...

Example:
John Smith
Senior Software Engineer
5+ years experience

Skills: Python, React, AWS, Docker, PostgreSQL

Experience:
- Senior Engineer at TechCorp (2021-Present)
- Engineer at StartupXYZ (2019-2021)"
                className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-semibold mb-2">Upload Resume File</label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition cursor-pointer">
                <input
                  type="file"
                  accept=".txt,.pdf,.doc,.docx"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="resume-file"
                />
                <label htmlFor="resume-file" className="cursor-pointer block">
                  <div className="text-4xl mb-2">📁</div>
                  <p className="font-semibold text-gray-700">
                    Drop file here or click to upload
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    Supported: TXT, PDF
                  </p>
                </label>
              </div>
              {resumeText && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-700">
                    ✓ File uploaded: {resumeText.length} characters
                  </p>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleParse}
            disabled={parseMutation.isPending}
            className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {parseMutation.isPending ? '🔄 Parsing Resume...' : '🚀 Parse Resume'}
          </button>
        </div>
      )}

      {/* Step 2: Preview */}
      {step === 2 && parsedResume && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold mb-4">✓ Resume Preview</h3>

          <div className="bg-gray-50 p-4 rounded-lg space-y-3">
            {parsedResume.name && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Name</p>
                <p className="text-lg font-bold">{parsedResume.name}</p>
              </div>
            )}

            {parsedResume.email && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Email</p>
                <p>{parsedResume.email}</p>
              </div>
            )}

            {parsedResume.current_title && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Current Title</p>
                <p>{parsedResume.current_title}</p>
              </div>
            )}

            {parsedResume.years_experience && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Experience</p>
                <p>{parsedResume.years_experience} years</p>
              </div>
            )}

            {parsedResume.seniority_level && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Seniority</p>
                <p className="capitalize">{parsedResume.seniority_level}</p>
              </div>
            )}

            {parsedResume.skills && parsedResume.skills.length > 0 && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Skills</p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {parsedResume.skills.map((skill, i) => (
                    <span key={i} className="bg-blue-100 text-blue-700 px-3 py-1 rounded text-sm">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {parsedResume.target_industries && parsedResume.target_industries.length > 0 && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Target Industries</p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {parsedResume.target_industries.map((ind, i) => (
                    <span key={i} className="bg-purple-100 text-purple-700 px-3 py-1 rounded text-sm">
                      {ind}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {parsedResume.preferred_remote && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Remote Preference</p>
                <p className="capitalize">{parsedResume.preferred_remote}</p>
              </div>
            )}

            {parsedResume.salary_range_min && parsedResume.salary_range_max && (
              <div>
                <p className="text-xs text-gray-600 uppercase font-semibold">Salary Range</p>
                <p>
                  ${parsedResume.salary_range_min?.toLocaleString()} - $
                  {parsedResume.salary_range_max?.toLocaleString()}
                </p>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep(3)}
              className="flex-1 btn-primary"
            >
              ✓ Looks Good - Save Resume
            </button>
            <button
              onClick={handleReset}
              className="btn-secondary"
            >
              ✎ Edit
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Confirm */}
      {step === 3 && parsedResume && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <p className="text-blue-900">
              ✓ Resume is ready to save. This will update your profile and recalculate job matches.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleConfirm}
              disabled={saveMutation.isPending}
              className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saveMutation.isPending ? '💾 Saving...' : '💾 Save Resume'}
            </button>
            <button
              onClick={() => setStep(2)}
              disabled={saveMutation.isPending}
              className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
