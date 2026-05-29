import React, { useState, useEffect } from 'react'
import '../styles/Dashboard.css'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStats()
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || '/_/backend'
      const response = await fetch(
        `${API_URL}/api/emissions/dashboard_stats/`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
          }
        }
      )

      if (!response.ok) throw new Error('Failed to fetch stats')
      const data = await response.json()
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">Loading dashboard...</div>
  if (error) return <div className="error">Error: {error}</div>
  if (!stats) return <div>No data available</div>

  const emissionsByScopePercentages = {
    SCOPE_1: (stats.emissions_by_scope.SCOPE_1 / stats.total_emissions * 100) || 0,
    SCOPE_2: (stats.emissions_by_scope.SCOPE_2 / stats.total_emissions * 100) || 0,
    SCOPE_3: (stats.emissions_by_scope.SCOPE_3 / stats.total_emissions * 100) || 0,
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <p>Emissions data ingestion overview</p>
      </div>

      {/* Key Metrics */}
      <div className="metrics-grid">
        <div className="metric-card total">
          <div className="metric-icon">📊</div>
          <div className="metric-content">
            <div className="metric-label">Total Records</div>
            <div className="metric-value">{stats.total_records}</div>
            <div className="metric-detail">
              All imported records
            </div>
          </div>
        </div>

        <div className="metric-card pending">
          <div className="metric-icon">⏳</div>
          <div className="metric-content">
            <div className="metric-label">Pending Review</div>
            <div className="metric-value">{stats.pending_review}</div>
            <div className="metric-detail">
              Awaiting approval
            </div>
          </div>
        </div>

        <div className="metric-card warning">
          <div className="metric-icon">⚠️</div>
          <div className="metric-content">
            <div className="metric-label">Flagged Suspicious</div>
            <div className="metric-value">{stats.flagged_suspicious}</div>
            <div className="metric-detail">
              Require attention
            </div>
          </div>
        </div>

        <div className="metric-card approved">
          <div className="metric-icon">✓</div>
          <div className="metric-content">
            <div className="metric-label">Approved</div>
            <div className="metric-value">{stats.approved}</div>
            <div className="metric-detail">
              Locked for audit
            </div>
          </div>
        </div>

        <div className="metric-card rejected">
          <div className="metric-icon">✕</div>
          <div className="metric-content">
            <div className="metric-label">Rejected</div>
            <div className="metric-value">{stats.rejected}</div>
            <div className="metric-detail">
              Sent back to source
            </div>
          </div>
        </div>
      </div>

      {/* Emissions Summary */}
      <div className="emissions-section">
        <h3>Total Emissions</h3>
        
        <div className="emissions-overview">
          <div className="total-emissions-card">
            <div className="total-value">
              {(stats.total_emissions / 1000).toFixed(1)} tonnes
            </div>
            <div className="total-label">CO₂e</div>
            <div className="total-detail">
              {stats.total_emissions.toLocaleString('en-IN', { maximumFractionDigits: 0 })} kg
            </div>
          </div>

          <div className="scope-breakdown">
            <h4>By Scope</h4>
            
            <div className="scope-item">
              <div className="scope-label">
                <span className="scope-name">Scope 1 (Direct)</span>
                <span className="scope-percent">{emissionsByScopePercentages.SCOPE_1.toFixed(1)}%</span>
              </div>
              <div className="scope-bar">
                <div 
                  className="scope-fill scope-1"
                  style={{ width: emissionsByScopePercentages.SCOPE_1 + '%' }}
                ></div>
              </div>
              <div className="scope-value">
                {(stats.emissions_by_scope.SCOPE_1 / 1000).toFixed(1)} tonnes
              </div>
            </div>

            <div className="scope-item">
              <div className="scope-label">
                <span className="scope-name">Scope 2 (Electricity)</span>
                <span className="scope-percent">{emissionsByScopePercentages.SCOPE_2.toFixed(1)}%</span>
              </div>
              <div className="scope-bar">
                <div 
                  className="scope-fill scope-2"
                  style={{ width: emissionsByScopePercentages.SCOPE_2 + '%' }}
                ></div>
              </div>
              <div className="scope-value">
                {(stats.emissions_by_scope.SCOPE_2 / 1000).toFixed(1)} tonnes
              </div>
            </div>

            <div className="scope-item">
              <div className="scope-label">
                <span className="scope-name">Scope 3 (Travel)</span>
                <span className="scope-percent">{emissionsByScopePercentages.SCOPE_3.toFixed(1)}%</span>
              </div>
              <div className="scope-bar">
                <div 
                  className="scope-fill scope-3"
                  style={{ width: emissionsByScopePercentages.SCOPE_3 + '%' }}
                ></div>
              </div>
              <div className="scope-value">
                {(stats.emissions_by_scope.SCOPE_3 / 1000).toFixed(1)} tonnes
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Prompts */}
      <div className="action-section">
        <h3>Next Steps</h3>
        
        <div className="action-cards">
          {stats.pending_review > 0 && (
            <div className="action-card">
              <div className="action-icon">👁️</div>
              <h4>Review Pending Records</h4>
              <p>{stats.pending_review} records waiting for approval</p>
              <a href="/review" className="btn-small">Go to Review</a>
            </div>
          )}

          {stats.flagged_suspicious > 0 && (
            <div className="action-card warning">
              <div className="action-icon">🚨</div>
              <h4>Address Flagged Records</h4>
              <p>{stats.flagged_suspicious} records marked as suspicious</p>
              <a href="/review?status=FLAGGED" className="btn-small">Review Flagged</a>
            </div>
          )}

          {stats.total_records === 0 && (
            <div className="action-card info">
              <div className="action-icon">📤</div>
              <h4>Upload Data</h4>
              <p>Start by uploading emissions data from your sources</p>
              <a href="/upload" className="btn-small">Upload Data</a>
            </div>
          )}
        </div>
      </div>

      {/* Data Quality Info */}
      <div className="info-section">
        <h3>Data Quality</h3>
        
        <div className="info-content">
          <div className="info-item">
            <h4>Confidence Scores</h4>
            <p>
              Records are scored 0-100% based on data completeness and consistency.
              High-confidence records can be approved quickly. Low-confidence records 
              may require analyst review.
            </p>
          </div>

          <div className="info-item">
            <h4>Suspicious Flags</h4>
            <p>
              Records flagged for issues like missing data, unusual values, or 
              inconsistent units. These are highlighted for analyst attention but 
              can still be approved if deemed acceptable.
            </p>
          </div>

          <div className="info-item">
            <h4>Audit Trail</h4>
            <p>
              Every approved record is locked for audit with complete history of 
              who approved it and when. Raw data is preserved for traceability.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
