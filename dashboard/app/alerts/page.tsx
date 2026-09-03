'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Alert {
  alert_id: string
  slope_id: string
  level: string
  risk_score: number
  generated_at: string
  acknowledged: boolean
  contributing_evidence: string[]
  recommended_action: string
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    fetchAlerts()
  }, [])

  const fetchAlerts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/alerts')
      const data = await response.json()
      setAlerts(data.alerts || [])
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const evaluateAlert = async (slopeId: string) => {
    try {
      await fetch(`http://localhost:8000/api/alerts/evaluate/${slopeId}`, { method: 'POST' })
      fetchAlerts()
    } catch (error) {
      console.error('Failed to evaluate alert:', error)
    }
  }

  const getLevelBadge = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border border-red-500/30'
      case 'warning':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
      case 'watch':
        return 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
    }
  }

  const filteredAlerts = filter === 'all'
    ? alerts
    : alerts.filter((a) => a.level?.toLowerCase() === filter)

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900">
        <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
          Loading alerts...
        </div>
        <div className="p-6 flex items-center justify-center">
          <div className="text-slate-400">Loading alerts...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
        REAL DATA MODE — Alert Engine: Risk Score + Multi-Signal Trigger
      </div>

      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link href="/" className="text-cyan-400 hover:text-cyan-300 text-sm mb-2 inline-block">
              Back to Dashboard
            </Link>
            <h1 className="text-2xl font-bold text-white">Alert Management</h1>
            <p className="text-slate-400 mt-1">Candidate alerts for authority review — not public alerts</p>
          </div>
          <span className="provenance-badge provenance-observed">Model-Derived</span>
        </div>

        <div className="flex gap-2 mb-6">
          {['all', 'critical', 'warning', 'watch'].map((level) => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                filter === level
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {level.charAt(0).toUpperCase() + level.slice(1)}
              {level !== 'all' && (
                <span className="ml-2 text-xs opacity-75">
                  ({alerts.filter((a) => a.level?.toLowerCase() === level).length})
                </span>
              )}
            </button>
          ))}
        </div>

        {filteredAlerts.length === 0 ? (
          <div className="card-gradient rounded-xl p-12 border border-slate-700 text-center">
            <div className="text-4xl mb-4">No Alerts</div>
            <p className="text-slate-400">No {filter !== 'all' ? filter : ''} alerts at this time.</p>
            <p className="text-slate-500 text-sm mt-2">Alerts are generated when multi-signal conditions are met.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.alert_id}
                className="card-gradient rounded-xl p-4 border border-slate-700 hover:border-slate-600 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getLevelBadge(alert.level)}`}>
                        {alert.level}
                      </span>
                      <Link
                        href={`/slope/${alert.slope_id}`}
                        className="text-sm font-medium text-cyan-400 hover:text-cyan-300"
                      >
                        {alert.slope_id}
                      </Link>
                      <span className="text-sm text-slate-400">Risk: {alert.risk_score}/100</span>
                      <span className="text-xs text-slate-500">
                        {new Date(alert.generated_at).toLocaleString()}
                      </span>
                    </div>
                    {alert.contributing_evidence && (
                      <div className="text-xs text-slate-400 mb-2">
                        Evidence: {alert.contributing_evidence.join(' | ')}
                      </div>
                    )}
                    {alert.recommended_action && (
                      <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-2">
                        Action: {alert.recommended_action}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <span className={`text-xs px-2 py-1 rounded ${
                      alert.acknowledged
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      {alert.acknowledged ? 'Acknowledged' : 'Pending Review'}
                    </span>
                    <button
                      onClick={() => evaluateAlert(alert.slope_id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 bg-slate-800 px-3 py-1 rounded"
                    >
                      Re-evaluate
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
