import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/Upload.css'

function Upload() {
  const [sourceType, setSourceType] = useState('SAP')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')
  const [results, setResults] = useState(null)
  const navigate = useNavigate()

  const sourceDescriptions = {
    SAP: 'Fuel and procurement data from SAP exports',
    UTILITY: 'Electricity consumption from utility portals',
    TRAVEL: 'Corporate travel data from Concur/Navan'
  }

  const sampleFiles = {
    SAP: '/sample_data/sap.csv',
    UTILITY: '/sample_data/utility.csv',
    TRAVEL: '/sample_data/travel.csv'
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      if (selectedFile.type !== 'text/csv' && selectedFile.type !== 'text/plain') {
        setMessage('Please select a CSV file')
        return
      }
      setFile(selectedFile)
      setMessage('')
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    
    if (!file) {
      setMessage('Please select a file')
      return
    }

    setUploading(true)
    setMessage('Uploading and processing...')

    try {
      const API_URL = import.meta.env.VITE_API_URL || '/_/backend'
      // Step 1: Create data source
      const dsResponse = await fetch(
        `${API_URL}/api/data-sources/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            source_type: sourceType,
            raw_file_name: file.name,
            raw_file_size: file.size
          })
        }
      )

      if (!dsResponse.ok) {
        throw new Error('Failed to create data source')
      }

      const dataSource = await dsResponse.json()

      // Step 2: Upload file and process
      const formData = new FormData()
      formData.append('file', file)

      const processResponse = await fetch(
        `${API_URL}/api/data-sources/${dataSource.id}/process/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('authToken')}`
          },
          body: formData
        }
      )

      if (!processResponse.ok) {
        const errorData = await processResponse.json()
        throw new Error(errorData.error || 'Processing failed')
      }

      const result = await processResponse.json()
      
      setResults({
        total: result.total_rows,
        successful: result.successful_rows,
        failed: result.failed_rows,
        records: result.emission_records
      })

      setMessage(`✓ Processed ${result.successful_rows}/${result.total_rows} records successfully`)

      // Redirect to review after 2 seconds
      setTimeout(() => {
        navigate('/review')
      }, 2000)

    } catch (error) {
      setMessage(`Error: ${error.message}`)
      setUploading(false)
    }
  }

  const downloadSample = () => {
    const link = document.createElement('a')
    link.href = sampleFiles[sourceType]
    link.download = `sample_${sourceType.toLowerCase()}.csv`
    link.click()
  }

  return (
    <div className="upload-container">
      <div className="upload-header">
        <h2>Upload Emissions Data</h2>
        <p>Choose a data source and upload your CSV file for normalization and review</p>
      </div>

      <div className="upload-grid">
        {/* Source Selection */}
        <div className="source-selector">
          <h3>1. Select Data Source</h3>
          
          <div className="source-options">
            {['SAP', 'UTILITY', 'TRAVEL'].map(type => (
              <div
                key={type}
                className={`source-card ${sourceType === type ? 'active' : ''}`}
                onClick={() => setSourceType(type)}
              >
                <div className="source-icon">
                  {type === 'SAP' && '⚙️'}
                  {type === 'UTILITY' && '⚡'}
                  {type === 'TRAVEL' && '✈️'}
                </div>
                <h4>{type}</h4>
                <p>{sourceDescriptions[type]}</p>
              </div>
            ))}
          </div>
        </div>

        {/* File Upload */}
        <div className="file-upload">
          <h3>2. Upload File</h3>
          
          <form onSubmit={handleUpload}>
            <div className="file-input-wrapper">
              <label className="file-label">
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileChange}
                  disabled={uploading}
                />
                <span className="file-label-text">
                  {file ? `Selected: ${file.name}` : 'Click to select CSV file'}
                </span>
              </label>
            </div>

            <div className="button-group">
              <button
                type="submit"
                disabled={!file || uploading}
                className="btn-primary"
              >
                {uploading ? 'Processing...' : 'Upload & Process'}
              </button>
              
              <button
                type="button"
                onClick={downloadSample}
                className="btn-secondary"
              >
                Download Sample
              </button>
            </div>
          </form>

          {message && (
            <div className={`message ${results ? 'success' : 'info'}`}>
              {message}
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="upload-results">
          <h3>Processing Results</h3>
          
          <div className="results-metrics">
            <div className="metric">
              <div className="metric-label">Total Rows</div>
              <div className="metric-value">{results.total}</div>
            </div>
            
            <div className="metric success">
              <div className="metric-label">Successful</div>
              <div className="metric-value">{results.successful}</div>
            </div>
            
            <div className="metric error">
              <div className="metric-label">Failed</div>
              <div className="metric-value">{results.failed}</div>
            </div>
          </div>

          <div className="results-table">
            <h4>Preview of First 5 Processed Records</h4>
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Category</th>
                  <th>Value</th>
                  <th>Unit</th>
                  <th>Emissions (kg CO2e)</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {results.records.slice(0, 5).map((record, idx) => (
                  <tr key={idx}>
                    <td>{new Date(record.activity_date).toLocaleDateString()}</td>
                    <td>{record.category.replace('_', ' ')}</td>
                    <td>{parseFloat(record.normalized_value).toFixed(2)}</td>
                    <td>{record.normalized_unit}</td>
                    <td>{parseFloat(record.calculated_emissions).toFixed(2)}</td>
                    <td>
                      <span className={`badge ${record.confidence_score > 0.8 ? 'high' : record.confidence_score > 0.5 ? 'medium' : 'low'}`}>
                        {(record.confidence_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td>
                      <span className={`status ${record.review_status.toLowerCase()}`}>
                        {record.review_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="results-note">
            📊 {results.successful} records ready for analyst review. Flagged records marked as "suspicious" require attention.
          </p>
        </div>
      )}

      {/* Help Section */}
      <div className="upload-help">
        <h3>File Format Requirements</h3>
        
        <div className="help-content">
          <div className="help-section">
            <h4>SAP Data</h4>
            <p>Required columns: Date, Material Group, Quantity, Unit, Plant Code</p>
            <p className="example">Example: Diesel, 500 liters, Plant BLR01</p>
          </div>

          <div className="help-section">
            <h4>Utility Data</h4>
            <p>Required columns: Meter ID, Billing Start/End, Consumption, Unit</p>
            <p className="example">Example: MTR001, 2025-02-10 - 2025-03-09, 1200 kWh</p>
          </div>

          <div className="help-section">
            <h4>Travel Data</h4>
            <p>Required columns: Employee ID, Travel Type, Origin, Destination, Cost</p>
            <p className="example">Example: Flight, DEL to BLR, 12000 INR</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Upload
