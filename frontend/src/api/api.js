const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const getAuthToken = () => localStorage.getItem('authToken')

export const apiCall = async (method, endpoint, data = null) => {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAuthToken()}`
  }

  const options = {
    method,
    headers
  }

  if (data) {
    options.body = JSON.stringify(data)
  }

  try {
    const response = await fetch(`${API_URL}${endpoint}`, options)
    
    if (response.status === 401) {
      // Token expired
      localStorage.removeItem('authToken')
      window.location.href = '/'
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `API Error: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

export const get = (endpoint) => apiCall('GET', endpoint)
export const post = (endpoint, data) => apiCall('POST', endpoint, data)
export const put = (endpoint, data) => apiCall('PUT', endpoint, data)
export const patch = (endpoint, data) => apiCall('PATCH', endpoint, data)
export const delete_ = (endpoint) => apiCall('DELETE', endpoint)
