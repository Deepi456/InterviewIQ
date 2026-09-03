export default function JobAnalysisResults({ results, jobRole, onBack }) {
  if (!results) {
    return null
  }

  // Group skills by importance level
  const skillsByImportance = {
    high: results.skills.filter(s => s.importance === 'high'),
    medium: results.skills.filter(s => s.importance === 'medium'),
    low: results.skills.filter(s => s.importance === 'low'),
  }

  const getImportanceColor = (importance) => {
    switch (importance) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
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
            ← Back to Setup
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Title */}
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Job Analysis Results</h1>
          <p className="text-lg text-gray-600 mb-8">Target Role: <span className="font-semibold">{jobRole}</span></p>

          {/* Skills Section */}
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Required Skills</h2>

            {/* High Importance */}
            {skillsByImportance.high.length > 0 && (
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-red-700 mb-3">High Priority Skills</h3>
                <div className="flex flex-wrap gap-3">
                  {skillsByImportance.high.map((skill, idx) => (
                    <div
                      key={idx}
                      className={`px-4 py-2 rounded-full font-medium text-sm border ${getImportanceColor(skill.importance)}`}
                      title={`Category: ${skill.category}`}
                    >
                      {skill.name}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Medium Importance */}
            {skillsByImportance.medium.length > 0 && (
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-yellow-700 mb-3">Medium Priority Skills</h3>
                <div className="flex flex-wrap gap-3">
                  {skillsByImportance.medium.map((skill, idx) => (
                    <div
                      key={idx}
                      className={`px-4 py-2 rounded-full font-medium text-sm border ${getImportanceColor(skill.importance)}`}
                      title={`Category: ${skill.category}`}
                    >
                      {skill.name}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Low Importance */}
            {skillsByImportance.low.length > 0 && (
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-green-700 mb-3">Nice-to-Have Skills</h3>
                <div className="flex flex-wrap gap-3">
                  {skillsByImportance.low.map((skill, idx) => (
                    <div
                      key={idx}
                      className={`px-4 py-2 rounded-full font-medium text-sm border ${getImportanceColor(skill.importance)}`}
                      title={`Category: ${skill.category}`}
                    >
                      {skill.name}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Topics Section */}
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Recommended Interview Topics</h2>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <ol className="space-y-3">
                {results.recommended_topics.map((topic, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-semibold mr-3 mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="text-gray-700 text-lg">{topic}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4 pt-6 border-t border-gray-200">
            <button
              onClick={onBack}
              className="flex-1 py-3 px-6 rounded-lg font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 transition"
            >
              Analyze Different Job
            </button>
            <button
              disabled
              className="flex-1 py-3 px-6 rounded-lg font-semibold text-white bg-gray-400 cursor-not-allowed"
              title="Coming in Phase 3"
            >
              Start Mock Interview (Phase 3)
            </button>
          </div>

          {/* Info Box */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Next Step:</strong> In Phase 3, you'll answer adaptive interview questions based on these skills and topics. The system will adjust difficulty based on your performance.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
