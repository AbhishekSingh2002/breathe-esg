import React, { useState } from 'react'

function UploadCard({ sourceType, onSelect, isSelected }) {
  const icons = {
    SAP: '⚙️',
    UTILITY: '⚡',
    TRAVEL: '✈️'
  }

  const descriptions = {
    SAP: 'Fuel and procurement data from SAP exports',
    UTILITY: 'Electricity consumption from utility portals',
    TRAVEL: 'Corporate travel data from Concur/Navan'
  }

  return (
    <div
      className={`source-card ${isSelected ? 'active' : ''}`}
      onClick={() => onSelect(sourceType)}
      style={{
        padding: '1.5rem',
        border: isSelected ? '2px solid #2563eb' : '2px solid #e2e8f0',
        borderRadius: '0.5rem',
        cursor: 'pointer',
        background: isSelected ? '#eff6ff' : 'white',
        transition: 'all 0.2s',
        textAlign: 'center'
      }}
    >
      <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>
        {icons[sourceType]}
      </div>
      <h4 style={{ marginBottom: '0.5rem', color: '#1e293b' }}>
        {sourceType}
      </h4>
      <p style={{ color: '#475569', fontSize: '0.85rem', lineHeight: '1.4' }}>
        {descriptions[sourceType]}
      </p>
    </div>
  )
}

export default UploadCard