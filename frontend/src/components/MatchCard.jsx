import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { jobsAPI } from '../api/client'

export default function MatchCard({ match, compact = false, onApplySuccess }) {
  const [isApplied, setIsApplied] = useState(false)
  
  const applyMutation = useMutation({
    mutationFn: async (jobId) => {
      const response = await jobsAPI.applyToJob(jobId)
      return response.data
    },
    onSuccess: (data) => {
      setIsApplied(true)
      onApplySuccess?.()
    },
    onError: (error) => {
      alert('Failed to apply: ' + (error.response?.data?.detail || error.message))
    },
  })

  const handleApply = () => {
    applyMutation.mutate(match.job_id)
  }

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-50'
    if (score >= 60) return 'text-yellow-600 bg-yellow-50'
    return 'text-orange-600 bg-orange-50'
  }

  const getScoreBg = (score) => {
    if (score >= 80) return 'bg-green-100'
    if (score >= 60) return 'bg-yellow-100'
    return 'bg-orange-100'
  }

  if (compact) {
    return (
      <div className="card hover:shadow-lg transition cursor-pointer">
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <h4 className="font-bold text-gray-900">{match.job_title}</h4>
            {match.company_name && (
              <p className="text-sm text-gray-600">{match.company_name}</p>
            )}
          </div>
          <div className={`text-2xl font-bold px-3 py-1 rounded ${getScoreBg(match.match_score)}`}>
            <span className={getScoreColor(match.match_score)}>{match.match_score}</span>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap mb-3">
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
            Skills: {match.skill_match_score}%
          </span>
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
            Seniority: {match.seniority_match_score}%
          </span>
          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
            Salary: {match.salary_match_score}%
          </span>
        </div>
        <p className="text-sm text-gray-600 italic mb-3">{match.recommendation}</p>
        <button
          onClick={handleApply}
          disabled={applyMutation.isPending || isApplied}
          className={`w-full py-2 rounded text-sm font-semibold ${
            isApplied
              ? 'bg-green-100 text-green-700 cursor-default'
              : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50'
          }`}
        >
          {isApplied ? '✓ Applied' : applyMutation.isPending ? '⏳ Applying...' : '🚀 Apply'}
        </button>
      </div>
    )
  }

  return (
    <div className="card hover:shadow-md transition">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-bold text-gray-900">{match.job_title}</h3>
          {match.company_name && (
            <p className="text-gray-600">{match.company_name}</p>
          )}
        </div>
        <div className={`text-3xl font-bold px-4 py-2 rounded ${getScoreBg(match.match_score)}`}>
          <span className={getScoreColor(match.match_score)}>{match.match_score}</span>
        </div>
      </div>

      {/* Score Breakdown */}
      <div className="bg-gray-50 p-4 rounded-lg mb-4">
        <h4 className="font-semibold text-sm mb-3 text-gray-700">Score Breakdown</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Skills', value: match.skill_match_score, color: 'bg-blue-500' },
            { label: 'Seniority', value: match.seniority_match_score, color: 'bg-purple-500' },
            { label: 'Salary', value: match.salary_match_score, color: 'bg-green-500' },
            { label: 'Remote', value: match.remote_match_score, color: 'bg-orange-500' },
          ].map((item) => (
            <div key={item.label} className="text-center">
              <div className="relative w-12 h-12 mx-auto mb-2">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                  <circle
                    cx="18"
                    cy="18"
                    r="15.915"
                    fill="none"
                    stroke={item.color}
                    strokeWidth="3"
                    strokeDasharray={`${item.value * 1.6593} 167.5`}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold">{item.value}%</span>
                </div>
              </div>
              <p className="text-xs text-gray-600">{item.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Positive Matches */}
      {match.positive_matches?.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-sm text-green-700 mb-2">✓ Strengths</h4>
          <ul className="space-y-1">
            {match.positive_matches.map((item, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start">
                <span className="text-green-600 mr-2">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {match.concerns?.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-sm text-orange-700 mb-2">⚠ Concerns</h4>
          <ul className="space-y-1">
            {match.concerns.map((item, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start">
                <span className="text-orange-600 mr-2">⚠</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Missing Skills */}
      {match.missing_skills?.length > 0 && (
        <div className="mb-4">
          <h4 className="font-semibold text-sm text-red-700 mb-2">Skills to Learn</h4>
          <div className="flex flex-wrap gap-2">
            {match.missing_skills.map((skill, i) => (
              <span key={i} className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recommendation */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-sm text-blue-900">
          <span className="font-semibold">Recommendation:</span> {match.recommendation}
        </p>
      </div>

      {/* Action Button */}
      <div className="mt-4 flex gap-2">
        {isApplied ? (
          <button disabled className="flex-1 bg-green-100 text-green-700 py-2 rounded font-semibold cursor-default">
            ✓ Applied
          </button>
        ) : (
          <button
            onClick={handleApply}
            disabled={applyMutation.isPending}
            className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {applyMutation.isPending ? '⏳ Applying...' : '🚀 Apply Now'}
          </button>
        )}
        <button className="btn-secondary">💾 Save</button>
      </div>
    </div>
  )
}
