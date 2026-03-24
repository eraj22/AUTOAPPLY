import { useQueryClient } from '@tanstack/react-query'
import ResumeUpload from '../components/ResumeUpload'

export default function ResumeManagement() {
  const queryClient = useQueryClient()

  const handleResumeUploaded = () => {
    // Invalidate queries to trigger refetch
    queryClient.invalidateQueries(['jobMatches'])
  }

  return (
    <div className="space-y-6">
      <ResumeUpload onResumeUploaded={handleResumeUploaded} />

      <div className="card">
        <h2 className="text-2xl font-bold mb-4">ℹ️ How This Works</h2>
        <div className="space-y-4 text-gray-700">
          <div>
            <h3 className="font-bold text-lg mb-2">1. Upload Your Resume</h3>
            <p>Paste your resume text or upload a .txt/.pdf file. The AI will automatically extract and parse your information.</p>
          </div>
          <div>
            <h3 className="font-bold text-lg mb-2">2. AI Parsing</h3>
            <p>Our TinyLlama AI model extracts: skills, experience, education, salary expectations, and job preferences.</p>
          </div>
          <div>
            <h3 className="font-bold text-lg mb-2">3. Smart Matching</h3>
            <p>Once parsed, your resume is instantly matched against all available jobs with a detailed score breakdown.</p>
          </div>
          <div>
            <h3 className="font-bold text-lg mb-2">4. View Matches</h3>
            <p>Go to the "Job Matches" tab to see all jobs ranked by how well they fit your profile.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
