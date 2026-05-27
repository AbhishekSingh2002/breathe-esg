import React from 'react'

function StatusBadge({ status, size = 'normal' }) {
  const statusColors = {
    PENDING: { bg: '#fef3c7', text: '#d97706', label: 'Pending' },
    FLAGGED: { bg: '#fee2e2', text: '#dc2626', label: 'Flagged' },
    APPROVED: { bg: '#dcfce7', text: '#16a34a', label: 'Approved' },
    REJECTED: { bg: '#f3f4f6', text: '#6b7280', label: 'Rejected' }
  }

  const colors = statusColors[status] || statusColors.PENDING
  const sizeStyles = {
    small: { padding: '0.25rem 0.5rem', fontSize: '0.75rem' },
    normal: { padding: '0.35rem 0.75rem', fontSize: '0.85rem' },
    large: { padding: '0.5rem 1rem', fontSize: '0.95rem' }
  }

  return (
    <span style={{
      background: colors.bg,
      color: colors.text,
      borderRadius: '0.375rem',
      fontWeight: 600,
      display: 'inline-block',
      ...sizeStyles[size]
    }}>
      {colors.label}
    </span>
  )
}

export default StatusBadge