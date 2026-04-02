import { useQuery } from '@tanstack/react-query'
import { jobsAPI } from '../api/client'
import MatchCard from '../components/MatchCard'

export default function JobMatches() {
  const { data: matchData = {}, isLoading, error } = useQuery({
    queryKey: ['jobMatches'],
    queryFn: () => jobsAPI.getMatches().then(res => res.data),
    refetchInterval: 10000,
  })

  const matches = matchData.matches || []
  const topMatches = matchData.top_matches || []

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card bg-red-50 border border-red-200">
        <h3 className="text-lg font-bold text-red-700 mb-2">Error Loading Matches</h3>
        <p className="text-red-600">{error?.response?.data?.detail || error.message}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Job Matches</h2>
        <p className="text-gray-600">
          Your resume matched with {matches.length} job{matches.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* No matches */}
      {matches.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No matching jobs found yet</p>
          <p className="text-sm text-gray-500">Upload your resume to get started</p>
        </div>
      ) : (
        <>
          {/* Top Matches Summary */}
          {topMatches.length > 0 && (
            <div className="mb-8">
              <h3 className="text-xl font-bold mb-4">🏆 Top Recommendations</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {topMatches.slice(0, 3).map((match) => (
                  <MatchCard key={match.job_id} match={match} compact />
                ))}
              </div>
            </div>
          )}

          {/* All Matches */}
          <div>
            <h3 className="text-xl font-bold mb-4">All Matches</h3>
            <div className="space-y-4">
              {matches.map((match) => (
                <MatchCard key={match.job_id} match={match} />
              ))}
            </div>
          </div>
        </>
      )}

      {/* Stats Footer */}
      {matches.length > 0 && (
        <div className="mt-12 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card text-center">
            <div className="text-3xl font-bold text-blue-600">{matches.length}</div>
            <div className="text-sm text-gray-600">Total Matches</div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-green-600">
              {Math.round(matches.reduce((sum, m) => sum + m.match_score, 0) / matches.length)}
            </div>
            <div className="text-sm text-gray-600">Avg Score</div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-purple-600">
              {matches.filter(m => m.match_score >= 80).length}
            </div>
            <div className="text-sm text-gray-600">80+ Score</div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-orange-600">
              {matches.filter(m => m.remote_match_score >= 75).length}
            </div>
            <div className="text-sm text-gray-600">Remote Friendly</div>
          </div>
        </div>
      )}
    </div>
  )
}
