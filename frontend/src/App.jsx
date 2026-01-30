import React, { useState } from 'react'
import './App.css'
import ATSCharts from './ATSCharts'

export default function App() {
  const [file, setFile] = useState(null)
  const [jdText, setJdText] = useState('')
  const [loading, setLoading] = useState(false)
  const [parsed, setParsed] = useState(null)
  const [skills, setSkills] = useState([])
  const [keywords, setKeywords] = useState([])
  const [matchScore, setMatchScore] = useState(null)
  const [missingKeywords, setMissingKeywords] = useState(null)
  const [atsScore, setAtsScore] = useState(null)

  const onFileChange = (e) => {
    setFile(e.target.files[0])
    // Reset results
    setParsed(null)
    setSkills([])
    setKeywords([])
    setMatchScore(null)
    setMissingKeywords(null)
    setAtsScore(null)
  }

  const upload = async () => {
    if (!file) return alert('Select a resume file first')
    setLoading(true)
    const form = new FormData()
    form.append('file', file, file.name)

    try {
      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const t = await res.text()
        console.error('Upload failed', res.status, t)
        alert('Upload failed: ' + res.status)
        setLoading(false)
        return
      }

      const data = await res.json()
      console.log('Parsed resume JSON:', data)
      setParsed(data)

      // Extract skills and keywords from backend response
      if (data.extracted_skills) {
        setSkills(data.extracted_skills)
      }
      if (data.extracted_keywords) {
        setKeywords(data.extracted_keywords)
      }
      // Extract ATS score
      if (data.ats_score) {
        setAtsScore(data.ats_score)
      }

    } catch (err) {
      console.error(err)
      alert('Error connecting to backend — is it running on port 8000?')
    }

    setLoading(false)
  }

  const analyzeJD = async () => {
    if (!parsed || !jdText.trim()) {
      alert('Upload a resume and enter a job description first')
      return
    }

    setLoading(true)
    
    try {
      // Use raw_text first, then fallback to lines joined
      const resumeText = parsed.raw_text || parsed.lines?.join('\n') || parsed.lines?.join(' ') || ''
      
      console.log('Parsed object:', parsed)
      console.log('Resume text length:', resumeText.length)
      console.log('Resume text preview:', resumeText.substring(0, 200))
      console.log('JD text length:', jdText.length)
      
      if (!resumeText || resumeText.length < 50) {
        alert('Resume text is too short or empty. Please re-upload your resume.')
        setLoading(false)
        return
      }
      
      const res = await fetch('http://localhost:8000/match', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resume_text: resumeText,
          jd_text: jdText
        })
      })

      if (!res.ok) {
        alert('Failed to analyze job description')
        setLoading(false)
        return
      }

      const data = await res.json()
      
      console.log('Match result:', data)
      
      if (data.error) {
        alert('Error: ' + data.error)
        setLoading(false)
        return
      }

      setMatchScore((data.score * 100).toFixed(1))
      setMissingKeywords(data.missing_keywords)
      
    } catch (err) {
      console.error(err)
      alert('Error connecting to backend')
    }
    
    setLoading(false)
  }

  return (
    <div className="app-container">
      <header>
        <h1>SmartCV — AI Powered Resume Optimizer</h1>
        <p>Upload your resume and optimize it against a job description</p>
      </header>

      <div className="upload-section">
        <h2>Upload Resume</h2>
        <input type="file" accept=".pdf,.docx,.txt" onChange={onFileChange} />
        <button onClick={upload} disabled={loading || !file}>
          {loading ? 'Processing...' : 'Upload & Parse'}
        </button>
      </div>

      {parsed && (
        <>
          <div className="section">
            <h2>Candidate</h2>
            <p><strong>Name:</strong> {parsed.name || 'Unknown'}</p>
            <div>
              <strong>Contact:</strong>
              <ul>
                {parsed.contact?.emails?.length > 0 && <li>Email: {parsed.contact.emails.join(', ')}</li>}
                {parsed.contact?.phones?.length > 0 && <li>Phone: {parsed.contact.phones.join(', ')}</li>}
                {parsed.contact?.links?.length > 0 && <li>Links: {parsed.contact.links.join(', ')}</li>}
              </ul>
            </div>
          </div>

          <div className="section">
            <h2>Extracted Skills</h2>
            <div className="tags">
              {skills.length > 0 ? skills.map((s, i) => <span key={i} className="tag">{s}</span>) : 'No skills detected'}
            </div>
          </div>

          <div className="section">
            <h2>Top Keywords</h2>
            <div className="tags">
              {keywords.slice(0, 30).map((k, i) => <span key={i} className="tag-keyword">{k}</span>)}
            </div>
          </div>

          {atsScore && (
            <div className="section ats-score-section">
              <h2>ATS Compliance Score</h2>
              <div className="ats-score-display">
                <div className="score-circle">
                  <div className="score-value">{atsScore.total_score}</div>
                  <div className="score-label">/ 100</div>
                </div>
                <div className="score-grade">{atsScore.grade}</div>
              </div>
              
              <div className="score-breakdown">
                <h3>Score Breakdown</h3>
                <div className="breakdown-item">
                  <span>Rule-Based Score:</span>
                  <strong>{atsScore.rule_based_score} / 70</strong>
                </div>
                <div className="breakdown-item">
                  <span>LLM Score:</span>
                  <strong>{atsScore.llm_score} / 30</strong>
                </div>
                
                {/* Add Charts */}
                <ATSCharts atsScore={atsScore} />
                
                {atsScore.rule_breakdown && (
                  <>
                    <div className="detailed-breakdown">
                      <h4>Detailed Analysis</h4>
                      {Object.entries(atsScore.rule_breakdown).map(([key, value]) => (
                        <div key={key} className="detail-item">
                          <span>{key.replace(/_/g, ' ').toUpperCase()}:</span>
                          <span>{value.score} / {value.max}</span>
                        </div>
                      ))}
                    </div>

                    <div className="heatmap-container">
                      <h4>Performance Heatmap</h4>
                      <div className="heatmap-grid">
                        {Object.entries(atsScore.rule_breakdown).map(([key, value]) => {
                          const percentage = (value.score / value.max) * 100;
                          let heatClass = 'heat-low';
                          if (percentage >= 80) heatClass = 'heat-high';
                          else if (percentage >= 50) heatClass = 'heat-medium';
                          
                          return (
                            <div key={key} className={`heatmap-cell ${heatClass}`}>
                              <div className="cell-label">{key.replace(/_/g, ' ')}</div>
                              <div className="cell-value">{percentage.toFixed(0)}%</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
                
                {atsScore.llm_feedback && (
                  <div className="llm-feedback">
                    <h4>AI Feedback</h4>
                    <div className="feedback-content">
                      {atsScore.llm_feedback.split('\n').map((line, index) => {
                        const trimmedLine = line.trim();
                        if (!trimmedLine) return null;
                        
                        // Check if it's a section header (bold text)
                        if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
                          const headerText = trimmedLine.replace(/\*\*/g, '');
                          return <h5 key={index} className="feedback-header">{headerText}</h5>;
                        }
                        
                        // Check if it's a bullet point
                        if (trimmedLine.startsWith('-')) {
                          const bulletText = trimmedLine.substring(1).trim();
                          return <li key={index}>{bulletText}</li>;
                        }
                        
                        // Regular text
                        return <p key={index}>{trimmedLine}</p>;
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="section">
            <h2>Job Description Match</h2>
            <textarea
              rows="8"
              placeholder="Paste job description here..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
            />
            <button onClick={analyzeJD} disabled={!jdText.trim() || loading}>
              {loading ? 'Analyzing...' : 'Analyze Match'}
            </button>

            {matchScore !== null && (
              <div className="match-results">
                <h3>Match Score: {matchScore}%</h3>
                
                {missingKeywords && missingKeywords.detected_roles && missingKeywords.detected_roles.length > 0 && (
                  <div className="detected-roles">
                    <h4>Detected Roles from Your Skills</h4>
                    <p>
                      {missingKeywords.detected_roles.join(' • ')}
                    </p>
                  </div>
                )}
                
                {missingKeywords && missingKeywords.matched && (
                  <div className="matched-keywords">
                    <h4>Keywords You Already Have</h4>
                    {(missingKeywords.matched.critical?.length > 0 || 
                      missingKeywords.matched.good?.length > 0 || 
                      missingKeywords.matched.optional?.length > 0) ? (
                      <>
                        {missingKeywords.matched.critical?.length > 0 && (
                          <p><strong>Critical:</strong> {missingKeywords.matched.critical.join(', ')}</p>
                        )}
                        {missingKeywords.matched.good?.length > 0 && (
                          <p><strong>Good-to-Have:</strong> {missingKeywords.matched.good.join(', ')}</p>
                        )}
                        {missingKeywords.matched.optional?.length > 0 && (
                          <p><strong>Optional:</strong> {missingKeywords.matched.optional.slice(0, 15).join(', ')}</p>
                        )}
                      </>
                    ) : (
                      <p>Great! You have most of the key skills.</p>
                    )}
                  </div>
                )}
                
                {missingKeywords && missingKeywords.missing && (
                  <div className="missing-keywords">
                    <h4>Missing Keywords (Add These!)</h4>
                    {(missingKeywords.missing.critical?.length > 0 || 
                      missingKeywords.missing.good?.length > 0 || 
                      missingKeywords.missing.optional?.length > 0) ? (
                      <>
                        {missingKeywords.missing.critical?.length > 0 && (
                          <p><strong>Critical:</strong> {missingKeywords.missing.critical.join(', ')}</p>
                        )}
                        {missingKeywords.missing.good?.length > 0 && (
                          <p><strong>Good-to-Have:</strong> {missingKeywords.missing.good.join(', ')}</p>
                        )}
                        {missingKeywords.missing.optional?.length > 0 && (
                          <p><strong>Optional:</strong> {missingKeywords.missing.optional.slice(0, 20).join(', ')}</p>
                        )}
                      </>
                    ) : (
                      <p>Excellent! You have all the required keywords.</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
