import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { jobsAPI } from '../api/client'

export default function ResumeOptimizer({ match, onClose, onResumeUpdated }) {
  const [selectedSkills, setSelectedSkills] = useState([])
  const [optimizationData, setOptimizationData] = useState(null)
  const [showSaved, setShowSaved] = useState(false)

  // Mutation to analyze resume
  const analyzeMutation = useMutation({
    mutationFn: (jobId) => jobsAPI.analyzeResumeForOptimization(jobId),
    onSuccess: (response) => {
      setOptimizationData(response.data)
      // Pre-select all missing required skills
      setSelectedSkills(response.data.missing_required_skills || [])
    },
    onError: (error) => {
      alert(`Error analyzing resume: ${error.response?.data?.detail || error.message}`)
    },
  })

  // Mutation to update resume
  const updateMutation = useMutation({
    mutationFn: (skillsToAdd) => jobsAPI.updateResume(skillsToAdd),
    onSuccess: (response) => {
      setShowSaved(true)
      onResumeUpdated?.()
      setTimeout(() => {
        onClose()
      }, 1500)
    },
    onError: (error) => {
      alert(`Error updating resume: ${error.response?.data?.detail || error.message}`)
    },
  })

  const handleAnalyze = () => {
    analyzeMutation.mutate(match.job_id)
  }

  const toggleSkill = (skill) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    )
  }

  const handleSaveResume = () => {
    if (selectedSkills.length === 0) {
      alert('Please select at least one skill to add')
      return
    }
    updateMutation.mutate(selectedSkills)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-50 to-indigo-50 border-b p-6 flex justify-between items-start">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Resume ATS Optimizer</h2>
            <p className="text-gray-600 mt-1">Improve your match score for {match.job_title}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {showSaved ? (
            // Success state
            <div className="text-center py-12">
              <div className="text-5xl mb-4">✅</div>
              <p className="text-xl font-semibold text-green-700 mb-2">Resume Updated!</p>
              <p className="text-gray-600">
                Your resume has been optimized with {selectedSkills.length} new skills
              </p>
              <p className="text-sm text-gray-500 mt-4">Closing in a moment...</p>
            </div>
          ) : !optimizationData ? (
            // Analyze state
            <div className="text-center py-12">
              <div className="text-5xl mb-4">🔍</div>
              <p className="text-gray-600 mb-6">
                Let's analyze your resume against this job and find keywords to add
              </p>
              <button
                onClick={handleAnalyze}
                disabled={analyzeMutation.isPending}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-8 rounded-lg transition disabled:cursor-not-allowed"
              >
                {analyzeMutation.isPending ? '🔄 Analyzing...' : '🔍 Analyze Resume'}
              </button>
            </div>
          ) : (
            // Results state
            <div>
              {/* Score Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-orange-50 border-2 border-orange-200 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-orange-600">
                    {optimizationData.current_score}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">Current Score</div>
                </div>
                <div className="flex items-center justify-center">
                  <div className="text-2xl">→</div>
                </div>
                <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-600">
                    {optimizationData.potential_score}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">Potential Score</div>
                </div>
              </div>

              {/* Improvement Badge */}
              <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
                <p className="text-blue-900">
                  <span className="font-semibold text-lg">
                    +{optimizationData.score_improvement.toFixed(1)} points
                  </span>
                  {' '}potential improvement by adding {optimizationData.total_missing} skills
                </p>
              </div>

              {/* Missing Required Skills */}
              {optimizationData.missing_required_skills?.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-lg text-gray-900 mb-3">
                    Required Skills to Add ⭐
                  </h3>
                  <p className="text-sm text-gray-600 mb-3">
                    These skills are required for the job but missing from your resume. Highly recommended!
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {optimizationData.missing_required_skills.map((skill) => (
                      <button
                        key={skill}
                        onClick={() => toggleSkill(skill)}
                        className={`px-4 py-2 rounded-full text-sm font-semibold transition cursor-pointer ${
                          selectedSkills.includes(skill)
                            ? 'bg-green-500 text-white border-2 border-green-600'
                            : 'bg-gray-100 text-gray-700 border-2 border-gray-300 hover:bg-gray-200'
                        }`}
                      >
                        {selectedSkills.includes(skill) ? '✓' : '+'} {skill}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Nice to Have Skills */}
              {optimizationData.nice_to_have_skills?.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-lg text-gray-900 mb-3">
                    Nice to Have Skills
                  </h3>
                  <p className="text-sm text-gray-600 mb-3">
                    Optional skills that could improve your profile
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {optimizationData.nice_to_have_skills.map((skill) => (
                      <button
                        key={skill}
                        onClick={() => toggleSkill(skill)}
                        className={`px-4 py-2 rounded-full text-sm font-semibold transition cursor-pointer ${
                          selectedSkills.includes(skill)
                            ? 'bg-blue-500 text-white border-2 border-blue-600'
                            : 'bg-blue-50 text-blue-700 border-2 border-blue-200 hover:bg-blue-100'
                        }`}
                      >
                        {selectedSkills.includes(skill) ? '✓' : '+'} {skill}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Selected Summary */}
              <div className="bg-gray-50 p-4 rounded-lg mb-4">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">
                    {selectedSkills.length} skill{selectedSkills.length !== 1 ? 's' : ''} selected
                  </span>
                  {selectedSkills.length > 0 && (
                    <>
                      <br/>
                      <span className="text-xs text-gray-600 mt-2 block">
                        {selectedSkills.join(', ')}
                      </span>
                    </>
                  )}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer - Actions */}
        {optimizationData && !showSaved && (
          <div className="sticky bottom-0 bg-gray-50 border-t p-6 flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-6 py-2 border-2 border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-100 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveResume}
              disabled={updateMutation.isPending || selectedSkills.length === 0}
              className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold rounded-lg transition disabled:cursor-not-allowed"
            >
              {updateMutation.isPending ? '💾 Saving...' : '💾 Save to Resume'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
