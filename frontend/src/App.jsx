import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Upload from './pages/Upload'
import Dashboard from './pages/Dashboard'
import Review from './pages/Review'
import './App.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if already logged in
    const token = localStorage.getItem('authToken')
    if (token) {
      setIsAuthenticated(true)
      setUser({ username: localStorage.getItem('username') })
    }
    setLoading(false)
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('username')
    setIsAuthenticated(false)
    setUser(null)
  }

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  if (!isAuthenticated) {
    return <LoginPage setIsAuthenticated={setIsAuthenticated} setUser={setUser} />
  }

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">
            <h1>Breathe ESG</h1>
            <p className="subtitle">Emissions Data Ingestion</p>
          </div>
          <ul className="nav-links">
            <li><Link to="/dashboard">Dashboard</Link></li>
            <li><Link to="/upload">Upload</Link></li>
            <li><Link to="/review">Review</Link></li>
            <li className="user-info">
              {user?.username} <button onClick={handleLogout}>Logout</button>
            </li>
          </ul>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/review" element={<Review />} />
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

function LoginPage({ setIsAuthenticated, setUser }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const API_URL = import.meta.env.VITE_API_URL || '/_/backend'
      const response = await fetch(`${API_URL}/api/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('authToken', data.access)
        localStorage.setItem('username', username)
        setIsAuthenticated(true)
        setUser({ username })
      } else {
        setError('Invalid credentials')
      }
    } catch (err) {
      setError('Login failed: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <h1>Breathe ESG</h1>
        <p>Emissions Data Ingestion Platform</p>
        
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="demo-login">
          <p>Demo credentials (use any for MVP):</p>
          <code>analyst1 / password123</code>
        </div>
      </div>
    </div>
  )
}

export default App
