import React, { useState, useEffect } from 'react'
import '../styles/Review.css'

function Review() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    status: 'PENDING',
    scope: '',
    source: ''
  })
  const [selected, setSelected] = useState(new Set())
  const [reviewNote, setReviewNote] = useState('')
  const [reviewAction, setReviewAction] = useState('APPROVE')
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    fetchRecords()
  }, [filters])

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const API_URL = import.meta.env.VITE_API_URL || '/_/backend'
      let url = `${API_URL}/api/emissions/?ordering=-activity_date`
      
      if (filters.status) url += `&review_status=${filters.status}`
      if (filters.scope) url += `&scope=${filters.scope}`
      if (filters.source) url += `&source_type=${filters.source}`

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      })

      if (!response.ok) throw new Error('Failed to fetch records')
      const data = await response.json()
      setRecords(data.results || data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectRecord = (id) => {
    const newSelected = new Set(selected)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelected(newSelected)
  }

  const handleSelectAll = () => {
    if (selected.size === records.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(records.map(r => r.id)))
    }
  }

  const handleBatchAction = async () => {
    if (selected.size === 0) {
      alert('Please select at least one record')
      return
    }

    setActionLoading(true)
    try {
      const API_URL = import.meta.env.VITE_API_URL || '/_/backend'
      const response = await fetch(
        `${API_URL}/api/emissions/batch_approve/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            record_ids: Array.from(selected),
            action: reviewAction,
            notes: reviewNote
          })
        }
      )

      if (!response.ok) throw new Error('Action failed')
      
      setReviewNote('')
      setSelected(new Set())
      await fetchRecords()
      alert(`✓ ${selected.size} records ${reviewAction.toLowerCase()}ed successfully`)
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const getStatusBadge = (status) => {
    const colors = {
      'PENDING': '#ffa500',
      'FLAGGED': '#ff6b6b',
      'APPROVED': '#51cf66',
      'REJECTED': '#868e96'
    }
    return colors[status] || '#999'
  }

  const getCategoryLabel = (category) => {
    return category.replace(/_/g, ' ').toLowerCase()
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  if (loading && records.length === 0) {
    return <div className="loading">Loading records...</div>
  }

  return (
    <div className="review-container">
      <div className="review-header">
        <h2>Review Queue</h2>
        <p>Analyze and approve emissions records</p>
      </div>

      {/* Filters */}
      <div className="filters">
        <div className="filter-group">
          <label>Review Status</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">All</option>
            <option value="PENDING">Pending</option>
            <option value="FLAGGED">Flagged</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Scope</label>
          <select
            value={filters.scope}
            onChange={(e) => setFilters({ ...filters, scope: e.target.value })}
          >
            <option value="">All</option>
            <option value="SCOPE_1">Scope 1 (Direct)</option>
            <option value="SCOPE_2">Scope 2 (Energy)</option>
            <option value="SCOPE_3">Scope 3 (Travel)</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Source</label>
          <select
            value={filters.source}
            onChange={(e) => setFilters({ ...filters, source: e.target.value })}
          >
            <option value="">All</option>
            <option value="SAP">SAP</option>
            <option value="UTILITY">Utility</option>
            <option value="TRAVEL">Travel</option>
          </select>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Batch Actions */}
      {selected.size > 0 && (
        <div className="batch-actions">
          <span className="selection-info">
            {selected.size} record{selected.size !== 1 ? 's' : ''} selected
          </span>
          
          <div className="action-controls">
            <select
              value={reviewAction}
              onChange={(e) => setReviewAction(e.target.value)}
              disabled={actionLoading}
            >
              <option value="APPROVE">Approve</option>
              <option value="REJECT">Reject</option>
              <option value="FLAG">Flag</option>
            </select>

            <textarea
              placeholder="Optional notes..."
              value={reviewNote}
              onChange={(e) => setReviewNote(e.target.value)}
              disabled={actionLoading}
              maxLength="500"
            />

            <button
              onClick={handleBatchAction}
              disabled={actionLoading}
              className="btn-primary"
            >
              {actionLoading ? 'Processing...' : `${reviewAction} Selected`}
            </button>
          </div>
        </div>
      )}

      {/* Records Table */}
      <div className="records-table-wrapper">
        <table className="records-table">
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={selected.size === records.length && records.length > 0}
                  onChange={handleSelectAll}
                />
              </th>
              <th>Date</th>
              <th>Category</th>
              <th>Value</th>
              <th>Emissions</th>
              <th>Confidence</th>
              <th>Flags</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td colSpan="9" className="no-records">
                  No records found
                </td>
              </tr>
            ) : (
              records.map(record => (
                <tr key={record.id} className={`record-row ${record.review_status.toLowerCase()}`}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(record.id)}
                      onChange={() => handleSelectRecord(record.id)}
                    />
                  </td>
                  <td>
                    {new Date(record.activity_date).toLocaleDateString()}
                  </td>
                  <td>
                    <span className="category-badge">
                      {getCategoryLabel(record.category)}
                    </span>
                  </td>
                  <td>
                    {parseFloat(record.normalized_value).toFixed(2)} {record.normalized_unit}
                  </td>
                  <td>
                    <strong>{parseFloat(record.calculated_emissions).toFixed(0)}</strong> kg
                  </td>
                  <td>
                    <span className={`confidence ${
                      record.confidence_score > 0.8 ? 'high' :
                      record.confidence_score > 0.5 ? 'medium' : 'low'
                    }`}>
                      {(record.confidence_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    {Object.keys(record.suspicious_flags || {}).filter(
                      k => record.suspicious_flags[k]
                    ).length > 0 ? (
                      <span className="flag-indicator" title={
                        Object.keys(record.suspicious_flags)
                          .filter(k => record.suspicious_flags[k])
                          .join(', ')
                      }>
                        ⚠️ {Object.keys(record.suspicious_flags).filter(k => record.suspicious_flags[k]).length}
                      </span>
                    ) : (
                      <span className="no-flags">-</span>
                    )}
                  </td>
                  <td>
                    <span
                      className="status-badge"
                      style={{ backgroundColor: getStatusBadge(record.review_status) }}
                    >
                      {record.review_status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Help Section */}
      <div className="review-help">
        <h3>Review Guide</h3>
        
        <div className="help-grid">
          <div className="help-card">
            <h4>Confidence Score</h4>
            <p>
              <strong>80-100%:</strong> High quality, safe to auto-approve<br/>
              <strong>50-80%:</strong> Review recommended<br/>
              <strong>&lt;50%:</strong> Requires detailed review
            </p>
          </div>

          <div className="help-card">
            <h4>Suspicious Flags</h4>
            <p>
              Records may be flagged for missing data, unusual values, or inconsistencies.
              Review the detail view to understand why it was flagged.
            </p>
          </div>

          <div className="help-card">
            <h4>Batch Approval</h4>
            <p>
              Select multiple records and approve/reject together for efficiency.
              Add notes explaining your decision for the audit trail.
            </p>
          </div>

          <div className="help-card">
            <h4>Audit Trail</h4>
            <p>
              Every action is logged with timestamp, your username, and notes.
              Approved records are locked and cannot be edited.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Review
