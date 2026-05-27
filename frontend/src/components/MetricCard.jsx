import React from 'react'

function MetricCard({ icon, label, value, detail, color = 'primary' }) {
  const colorMap = {
    primary: '#2563eb',
    success: '#16a34a',
    warning: '#ea580c',
    danger: '#dc2626',
    info: '#0891b2'
  }

  const borderColor = colorMap[color] || colorMap.primary

  return (
    <div style={{
      background: 'white',
      padding: '1.5rem',
      borderRadius: '0.75rem',
      borderLeft: `4px solid ${borderColor}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      display: 'flex',
      gap: '1rem',
      alignItems: 'flex-start'
    }}>
      <div style={{
        fontSize: '2rem',
        lineHeight: '1'
      }}>
        {icon}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{
          fontSize: '0.875rem',
          color: '#475569',
          fontWeight: 500,
          marginBottom: '0.25rem'
        }}>
          {label}
        </div>

        <div style={{
          fontSize: '2rem',
          fontWeight: 700,
          color: '#1e293b',
          lineHeight: '1',
          marginBottom: '0.5rem'
        }}>
          {value}
        </div>

        <div style={{
          fontSize: '0.8rem',
          color: '#475569'
        }}>
          {detail}
        </div>
      </div>
    </div>
  )
}

export default MetricCard