// Date formatting
export const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

export const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Number formatting
export const formatNumber = (num) => {
  if (num === null || num === undefined) return '-'
  return Number(num).toLocaleString('en-US')
}

export const formatDecimal = (num, decimals = 2) => {
  if (num === null || num === undefined) return '-'
  return Number(num).toFixed(decimals)
}

export const formatCurrency = (num, currency = 'USD') => {
  if (num === null || num === undefined) return '-'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(num)
}

// Emissions formatting
export const formatEmissions = (value) => {
  if (!value) return '0 kg'
  const num = Number(value)
  if (num >= 1000) {
    return `${(num / 1000).toFixed(2)} tonnes`
  }
  return `${num.toFixed(0)} kg`
}

// Percentage formatting
export const formatPercent = (value, decimals = 1) => {
  if (value === null || value === undefined) return '-'
  return `${(Number(value) * 100).toFixed(decimals)}%`
}

// File size formatting
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// Status label formatting
export const formatStatus = (status) => {
  const labels = {
    PENDING: 'Pending Review',
    FLAGGED: 'Flagged',
    APPROVED: 'Approved',
    REJECTED: 'Rejected',
    PROCESSING: 'Processing'
  }
  return labels[status] || status
}

// Category formatting
export const formatCategory = (category) => {
  return category
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

// Scope formatting
export const formatScope = (scope) => {
  const labels = {
    SCOPE_1: 'Scope 1 (Direct)',
    SCOPE_2: 'Scope 2 (Indirect)',
    SCOPE_3: 'Scope 3 (Other)'
  }
  return labels[scope] || scope
}

// Confidence score formatting
export const formatConfidence = (score) => {
  if (!score) return 'Unknown'
  const percent = Number(score) * 100
  if (percent >= 80) return 'High'
  if (percent >= 50) return 'Medium'
  return 'Low'
}

// Truncate text
export const truncate = (text, length = 50) => {
  if (!text) return '-'
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

// CSV download helper
export const downloadCSV = (data, filename = 'export.csv') => {
  const csv = [
    Object.keys(data[0]).join(','),
    ...data.map(row =>
      Object.values(row)
        .map(value => `"${value}"`)
        .join(',')
    )
  ].join('\n')

  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

// JSON to CSV
export const jsonToCSV = (jsonData) => {
  if (!jsonData || jsonData.length === 0) return ''

  const headers = Object.keys(jsonData[0])
  const rows = jsonData.map(obj =>
    headers.map(header => {
      const value = obj[header]
      if (typeof value === 'string' && value.includes(',')) {
        return `"${value}"`
      }
      return value
    }).join(',')
  )

  return [headers.join(','), ...rows].join('\n')
}