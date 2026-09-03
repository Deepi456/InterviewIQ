import { useState } from 'react'
import axios from 'axios'

export default function JobAnalysisForm({ onSuccess, onBack }) {
  const [jobRole, setJobRole] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAnalyze = async (e) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (!jobRole.trim()) {
      setError('Please enter a job role')
      return
    }
    if (!jobDescription.trim() || jobDescription.trim().length < 10) {
      setError('Please enter a valid job description (at least 10 characters)')
      return
    }

    setLoading(true)

    try {
      const response = await axios.post('/api/job/analyze', {
        job_role: jobRole,
        job_description: jobDescription
      })

      // Call success handler with results
      onSuccess(response.data, jobRole)
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else if (err.message) {
        setError(`Error: ${err.message}`)
      } else {
        setError('Failed to analyze job description. Please check your API key and try again.')
      }
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button
            onClick={onBack}
            className="text-blue-600 hover:text-blue-700 font-semibold"
          >
            ← Back to Home
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Interview Setup</h1>

          <form onSubmit={handleAnalyze} className="space-y-6">
            {/* Job Role Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Job Role
              </label>
              <input
                type="text"
                value={jobRole}
                onChange={(e) => setJobRole(e.target.value)}
                placeholder="e.g., AI/ML Intern, Senior Python Developer"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                disabled={loading}
              />
            </div>

            {/* Job Description Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Job Description
              </label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the complete job description here..."
                rows={10}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
                disabled={loading}
              />
              <p className="text-sm text-gray-500 mt-1">
                Minimum 10 characters
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-4 pt-4">
              <button
                type="submit"
                disabled={loading}
                className={`flex-1 py-3 px-6 rounded-lg font-semibold text-white transition ${
                  loading
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {loading ? 'Analyzing with AI...' : 'Analyze Job Description'}
              </button>
              <button
                type="button"
                onClick={onBack}
                disabled={loading}
                className="py-3 px-6 rounded-lg font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 transition disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </form>

          {/* Info Box */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">How it works:</h3>
            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
              <li>Enter the target job role</li>
              <li>Paste the complete job description</li>
              <li>AI analyzes the description to extract required skills</li>
              <li>View recommended interview topics and required skills</li>
            </ol>
          </div>
        </div>
      </main>
    </div>
  )
}
