import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { jobsAPI } from '../api/client'

export default function CoverLetterPreview({ match, onClose, onApplyWithLetter }) {
  const [generatedLetter, setGeneratedLetter] = useState(null)
  const [editedLetter, setEditedLetter] = useState('')
  const [showEditor, setShowEditor] = useState(false)

  // Mutation to generate cover letter
  const generateMutation = useMutation({
    mutationFn: (jobId) => jobsAPI.generateCoverLetter(jobId),
    onSuccess: (response) => {
      setGeneratedLetter(response.data.cover_letter)
      setEditedLetter(response.data.cover_letter)
    },
    onError: (error) => {
      alert(`Error generating cover letter: ${error.response?.data?.detail || error.message}`)
    },
  })

  const handleGenerateLetter = () => {
    generateMutation.mutate(match.job_id)
  }

  const handleApplyWithLetter = () => {
    onApplyWithLetter(editedLetter)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-50 to-indigo-50 border-b p-6 flex justify-between items-start">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Cover Letter</h2>
            <p className="text-gray-600 mt-1">{match.job_title} at {match.company_name}</p>
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
          {!generatedLetter ? (
            // Generate state
            <div className="text-center py-12">
              <div className="text-5xl mb-4">📝</div>
              <p className="text-gray-600 mb-6">
                Generate a personalized cover letter for this position using AI
              </p>
              <button
                onClick={handleGenerateLetter}
                disabled={generateMutation.isPending}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-3 px-8 rounded-lg transition disabled:cursor-not-allowed"
              >
                {generateMutation.isPending ? '✨ Generating...' : '✨ Generate Cover Letter'}
              </button>
            </div>
          ) : (
            // Letter display state
            <div>
              <div className="mb-6">
                <div className="flex justify-between items-center mb-3">
                  <label className="text-sm font-semibold text-gray-700">Generated Cover Letter</label>
                  <button
                    onClick={() => setShowEditor(!showEditor)}
                    className="text-xs bg-gray-200 hover:bg-gray-300 text-gray-800 px-3 py-1 rounded transition"
                  >
                    {showEditor ? '📖 Preview' : '✏️ Edit'}
                  </button>
                </div>

                {showEditor ? (
                  // Editor mode
                  <textarea
                    value={editedLetter}
                    onChange={(e) => setEditedLetter(e.target.value)}
                    className="w-full h-80 p-4 border-2 border-indigo-300 rounded-lg focus:border-indigo-500 focus:outline-none resize-none"
                  />
                ) : (
                  // Preview mode
                  <div className="bg-gray-50 p-4 rounded-lg border-2 border-gray-200 h-80 overflow-y-auto">
                    <div className="prose prose-sm max-w-none whitespace-pre-wrap text-gray-700">
                      {generatedLetter}
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-6">
                <p className="text-sm text-blue-800">
                  💡 Tip: You can edit the cover letter above before applying. Make it even more personalized!
                </p>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 p-3 rounded text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {editedLetter.split(' ').length}
                  </div>
                  <div className="text-xs text-gray-600">Words</div>
                </div>
                <div className="bg-gray-50 p-3 rounded text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {editedLetter.split('\n').length}
                  </div>
                  <div className="text-xs text-gray-600">Paragraphs</div>
                </div>
                <div className="bg-gray-50 p-3 rounded text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {editedLetter.length}
                  </div>
                  <div className="text-xs text-gray-600">Characters</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer - Actions */}
        {generatedLetter && (
          <div className="sticky bottom-0 bg-gray-50 border-t p-6 flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-6 py-2 border-2 border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-100 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleApplyWithLetter}
              className="px-6 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold rounded-lg transition"
            >
              🚀 Apply with Letter
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
