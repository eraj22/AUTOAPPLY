import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { companiesAPI } from './api/client'
import CompanyList from './components/CompanyList'
import Dashboard from './pages/Dashboard'
import JobMatches from './pages/JobMatches'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white shadow">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-blue-600">AutoApply 🚀</h1>
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded ${
                activeTab === 'dashboard'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('matches')}
              className={`px-4 py-2 rounded ${
                activeTab === 'matches'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Job Matches 🎯
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`px-4 py-2 rounded ${
                activeTab === 'settings'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Settings
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'matches' && <JobMatches />}
        {activeTab === 'settings' && (
          <div className="card">
            <h2 className="text-xl font-bold mb-4">Settings</h2>
            <p>Settings page coming soon...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
