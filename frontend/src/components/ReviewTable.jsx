import React from 'react'

function ReviewTable({ records, selected, onSelect, onSelectAll }) {
  if (!records || records.length === 0) {
    return (
      <div style={{
        padding: '3rem',
        textAlign: 'center',
        color: '#475569'
      }}>
        No records found
      </div>
    )
  }

  const allSelected = selected.size === records.length && records.length > 0

  return (
    <table style={{
      width: '100%',
      borderCollapse: 'collapse',
      minWidth: '900px'
    }}>
      <thead style={{
        background: '#f1f5f9',
        borderBottom: '2px solid #e2e8f0',
        position: 'sticky',
        top: 0
      }}>
        <tr>
          <th style={{ padding: '1rem', textAlign: 'left', width: '40px' }}>
            <input
              type="checkbox"
              checked={allSelected}
              onChange={onSelectAll}
              style={{ cursor: 'pointer', width: '18px', height: '18px' }}
            />
          </th>
          <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>Date</th>
          <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>Category</th>
          <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>Value</th>
          <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>Emissions</th>
          <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>Confidence</th>
          <th style={{ padding: '1rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>Status</th>
        </tr>
      </thead>
      <tbody>
        {records.map((record) => (
          <tr
            key={record.id}
            style={{
              borderBottom: '1px solid #e2e8f0',
              background: selected.has(record.id) ? '#f0f9ff' : 'white'
            }}
          >
            <td style={{ padding: '1rem' }}>
              <input
                type="checkbox"
                checked={selected.has(record.id)}
                onChange={() => onSelect(record.id)}
                style={{ cursor: 'pointer', width: '18px', height: '18px' }}
              />
            </td>
            <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
              {new Date(record.activity_date).toLocaleDateString()}
            </td>
            <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
              <span style={{
                background: '#e0e7ff',
                color: '#4f46e5',
                padding: '0.35rem 0.75rem',
                borderRadius: '0.25rem',
                fontWeight: 500,
                fontSize: '0.85rem'
              }}>
                {record.category.replace(/_/g, ' ')}
              </span>
            </td>
            <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
              {parseFloat(record.normalized_value).toFixed(2)} {record.normalized_unit}
            </td>
            <td style={{ padding: '1rem', fontSize: '0.9rem', fontWeight: 'bold' }}>
              {parseFloat(record.calculated_emissions).toFixed(0)} kg
            </td>
            <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
              <span style={{
                padding: '0.35rem 0.75rem',
                borderRadius: '0.25rem',
                fontWeight: 600,
                fontSize: '0.8rem',
                background: record.confidence_score > 0.8 ? '#dcfce7' : record.confidence_score > 0.5 ? '#fef3c7' : '#fee2e2',
                color: record.confidence_score > 0.8 ? '#16a34a' : record.confidence_score > 0.5 ? '#d97706' : '#dc2626'
              }}>
                {(record.confidence_score * 100).toFixed(0)}%
              </span>
            </td>
            <td style={{ padding: '1rem', fontSize: '0.9rem' }}>
              <span style={{
                padding: '0.35rem 0.85rem',
                borderRadius: '0.25rem',
                color: 'white',
                fontSize: '0.8rem',
                fontWeight: 600,
                background: record.review_status === 'APPROVED' ? '#16a34a' : 
                           record.review_status === 'FLAGGED' ? '#dc2626' :
                           record.review_status === 'REJECTED' ? '#6b7280' : '#ea580c'
              }}>
                {record.review_status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default ReviewTable