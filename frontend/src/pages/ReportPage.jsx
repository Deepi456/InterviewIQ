import React, { useState, useEffect } from 'react';
import './ReportPage.css';

const ReportPage = ({ sessionId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloadingPDF, setDownloadingPDF] = useState(false);
  const [downloadingDOCX, setDownloadingDOCX] = useState(false);

  useEffect(() => {
    fetchReport();
  }, [sessionId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`http://localhost:8000/api/interview/${sessionId}/report?preparation_days=5`);
      
      if (!response.ok) {
        throw new Error(`Failed to load report: ${response.statusText}`);
      }
      
      const reportData = await response.json();
      setReport(reportData);
    } catch (err) {
      setError(err.message);
      console.error('Report fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      setDownloadingPDF(true);
      const response = await fetch(`http://localhost:8000/api/interview/${sessionId}/report/download/pdf?preparation_days=5`);
      
      if (!response.ok) {
        throw new Error('Failed to download PDF');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `InterviewIQ_Report_${sessionId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setDownloadingPDF(false);
    }
  };

  const handleDownloadDOCX = async () => {
    try {
      setDownloadingDOCX(true);
      const response = await fetch(`http://localhost:8000/api/interview/${sessionId}/report/download/docx?preparation_days=5`);
      
      if (!response.ok) {
        throw new Error('Failed to download DOCX');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `InterviewIQ_Report_${sessionId}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setDownloadingDOCX(false);
    }
  };

  if (loading) {
    return (
      <div className="report-container">
        <div className="loading">
          <h2>Generating your report...</h2>
          <p>Our AI is analyzing your interview performance and creating personalized recommendations.</p>
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="report-container">
        <div className="error">
          <h2>Error Loading Report</h2>
          <p>{error}</p>
          <button onClick={fetchReport} className="btn-retry">Try Again</button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="report-container">
        <div className="error">
          <h2>No Report Found</h2>
          <p>Unable to load your interview report.</p>
        </div>
      </div>
    );
  }

  const getPerformanceBadge = (level) => {
    switch (level) {
      case 'Strong':
        return 'badge-strong';
      case 'Developing':
        return 'badge-developing';
      case 'Needs Improvement':
        return 'badge-weak';
      default:
        return 'badge-developing';
    }
  };

  return (
    <div className="report-container">
      {/* Header Section */}
      <div className="report-header">
        <h1>InterviewIQ</h1>
        <h2>Interview Performance Report</h2>
      </div>

      {/* Interview Info Section */}
      <section className="report-section">
        <h3>Interview Information</h3>
        <div className="info-grid">
          <div className="info-item">
            <label>Target Role</label>
            <p>{report.job_role}</p>
          </div>
          <div className="info-item">
            <label>Interview Date</label>
            <p>{new Date(report.interview_date).toLocaleDateString()}</p>
          </div>
          <div className="info-item">
            <label>Questions Answered</label>
            <p>{report.questions_answered} / {report.total_questions}</p>
          </div>
          <div className="info-item">
            <label>Status</label>
            <p className="status-badge">{report.completion_status.toUpperCase()}</p>
          </div>
        </div>
      </section>

      {/* Overall Performance Section */}
      <section className="report-section performance-section">
        <h3>Overall Performance</h3>
        <div className="performance-card">
          <div className="score-display">
            <div className="score-number">{Math.round(report.overall_score)}%</div>
            <div className="score-label">Overall Score</div>
          </div>
          <div className="performance-info">
            <div className="performance-badge">
              <span className={`badge ${getPerformanceBadge(report.performance_level)}`}>
                {report.performance_level}
              </span>
            </div>
            <div className="performance-summary">
              <p>{report.summary}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Skill Performance Section */}
      <section className="report-section">
        <h3>Skill Performance</h3>
        <div className="skills-table">
          <div className="skills-header">
            <div className="skill-col-name">Skill</div>
            <div className="skill-col-score">Score</div>
            <div className="skill-col-count">Questions</div>
            <div className="skill-col-level">Level</div>
          </div>
          {report.skill_scores.map((skill, idx) => (
            <div key={idx} className="skills-row">
              <div className="skill-col-name">{skill.skill}</div>
              <div className="skill-col-score">{skill.avg_score.toFixed(1)}/10</div>
              <div className="skill-col-count">{skill.question_count}</div>
              <div className={`skill-col-level badge ${getPerformanceBadge(skill.performance_level)}`}>
                {skill.performance_level}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Strengths Section */}
      {report.strengths.length > 0 && (
        <section className="report-section">
          <h3>✓ Your Strengths</h3>
          <div className="strengths-list">
            {report.strengths.map((strength, idx) => (
              <div key={idx} className="strength-item">
                <div className="strength-icon">✓</div>
                <div className="strength-content">
                  <strong>{strength.skill}</strong>
                  <p>{strength.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Weak Areas Section */}
      {report.weak_areas.length > 0 && (
        <section className="report-section">
          <h3>⚠ Areas to Improve</h3>
          <div className="weak-areas-list">
            {report.weak_areas.map((weak, idx) => (
              <div key={idx} className="weak-item">
                <div className={`weak-icon priority-${weak.priority.toLowerCase()}`}>⚠</div>
                <div className="weak-content">
                  <strong>{weak.skill}</strong>
                  <p>{weak.reason}</p>
                  <span className={`priority-badge priority-${weak.priority.toLowerCase()}`}>
                    {weak.priority} Priority
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Concept Gaps Section */}
      {report.concept_gaps.length > 0 && (
        <section className="report-section">
          <h3>Concept Gaps</h3>
          <div className="concepts-list">
            {report.concept_gaps.map((gap, idx) => (
              <div key={idx} className="concept-item">
                <div className="concept-skill">{gap.skill}</div>
                <div className="concept-arrow">→</div>
                <div className="concept-name">{gap.concept}</div>
                <div className="concept-reason">{gap.reason}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recommendations Section */}
      {report.recommendations.length > 0 && (
        <section className="report-section">
          <h3>Personalized Recommendations</h3>
          <div className="recommendations-list">
            {report.recommendations.map((rec, idx) => (
              <div key={idx} className="recommendation-item">
                <div className="rec-number">{idx + 1}</div>
                <div className="rec-content">
                  <strong>{rec.topic}</strong>
                  <p>{rec.action}</p>
                  <span className={`priority-badge priority-${rec.priority.toLowerCase()}`}>
                    {rec.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Preparation Plan Section */}
      {report.preparation_plan.length > 0 && (
        <section className="report-section">
          <h3>Preparation Plan</h3>
          <div className="prep-plan">
            {report.preparation_plan.map((day, idx) => (
              <div key={idx} className="prep-day">
                <div className="prep-day-header">
                  <h4>Day {day.day}: {day.focus}</h4>
                  <span className="prep-hours">~{day.estimated_hours.toFixed(1)} hours</span>
                </div>
                <div className="prep-topics">
                  <strong>Topics:</strong>
                  <p>{day.topics.join(', ')}</p>
                </div>
                <div className="prep-tasks">
                  <strong>Tasks:</strong>
                  <ul>
                    {day.tasks.map((task, taskIdx) => (
                      <li key={taskIdx}>{task}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Download Buttons Section */}
      <section className="report-section download-section">
        <h3>Download Report</h3>
        <div className="download-buttons">
          <button 
            onClick={handleDownloadPDF} 
            className="btn btn-primary"
            disabled={downloadingPDF}
          >
            {downloadingPDF ? 'Generating PDF...' : '📄 Download PDF'}
          </button>
          <button 
            onClick={handleDownloadDOCX} 
            className="btn btn-primary"
            disabled={downloadingDOCX}
          >
            {downloadingDOCX ? 'Generating DOCX...' : '📋 Download DOCX'}
          </button>
        </div>
      </section>

      {/* Footer */}
      <section className="report-footer">
        <p>Report generated {new Date(report.generated_at).toLocaleDateString()} at {new Date(report.generated_at).toLocaleTimeString()}</p>
        {!report.ai_generated && <p className="fallback-notice">⚠ AI analysis unavailable - using fallback analysis</p>}
      </section>
    </div>
  );
};

export default ReportPage;
