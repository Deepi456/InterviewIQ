import { useState } from 'react'
import JobAnalysisForm from '../components/JobAnalysisForm'
import JobAnalysisResults from '../components/JobAnalysisResults'

export default function LandingPage() {
  const [currentStep, setCurrentStep] = useState('home') // home, setup, results
  const [analysisResults, setAnalysisResults] = useState(null)
  const [selectedRole, setSelectedRole] = useState('')

  const handleStartInterview = () => {
    setCurrentStep('setup')
  }

  const handleAnalysisSuccess = (results, role) => {
    setAnalysisResults(results)
    setSelectedRole(role)
    setCurrentStep('results')
  }

  const handleBackToHome = () => {
    setCurrentStep('home')
    setAnalysisResults(null)
    setSelectedRole('')
  }

  const handleBackToSetup = () => {
    setCurrentStep('setup')
  }

  if (currentStep === 'setup') {
    return (
      <JobAnalysisForm 
        onSuccess={handleAnalysisSuccess}
        onBack={handleBackToHome}
      />
    )
  }

  if (currentStep === 'results') {
    return (
      <JobAnalysisResults 
        results={analysisResults}
        jobRole={selectedRole}
        onBack={handleBackToSetup}
      />
    )
  }

  // Home/Landing Page
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="text-2xl font-bold text-blue-600">InterviewIQ</div>
            <div className="text-sm text-gray-600">Phase 2 - AI Job Analysis</div>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="py-20 sm:py-24">
          {/* Title */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-center text-gray-900 mb-6">
            InterviewIQ
          </h1>

          {/* Subtitle */}
          <p className="text-xl sm:text-2xl text-center text-gray-700 mb-8">
            AI-Powered Adaptive Career &amp; Interview Coach
          </p>

          {/* Description */}
          <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-8 mb-12">
            <p className="text-lg text-gray-700 leading-relaxed">
              Practice smarter with personalized AI interviews, skill analysis, real-time feedback, and adaptive questions.
            </p>
          </div>

          {/* CTA Button */}
          <div className="flex justify-center">
            <button
              onClick={handleStartInterview}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-10 rounded-lg text-lg transition duration-200 shadow-lg hover:shadow-xl"
            >
              Start Interview
            </button>
          </div>

          {/* Feature Highlights */}
          <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-blue-50 rounded-lg p-6">
              <div className="text-3xl mb-4">🎯</div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">AI Job Analysis</h3>
              <p className="text-gray-600">Paste any job description and AI extracts required skills.</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-6">
              <div className="text-3xl mb-4">📊</div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">Adaptive Questions</h3>
              <p className="text-gray-600">Get personalized interview questions based on the job.</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-6">
              <div className="text-3xl mb-4">📈</div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">Performance Report</h3>
              <p className="text-gray-600">Detailed feedback and improvement suggestions.</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-600">
            InterviewIQ Phase 2 © 2026. AI-Powered Interview Prep.
          </p>
        </div>
      </footer>
    </div>
  )
}
