'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Alert {
  alert_id: string
  slope_id: string
  level: string
  risk_score: number
  created_at: string
  status: string
}

export default function AlertPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAlerts()
  }, [])

  const fetchAlerts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/alerts')
      const data = await response.json()
      const alertsList = data.alerts || data || []
      setAlerts(alertsList.map((a: any) => ({
        alert_id: a.alert_id,
        slope_id: a.slope_id,
        level: a.level,
        risk_score: a.risk_score,
        created_at: a.generated_at || a.created_at || new Date().toISOString(),
        status: a.acknowledged ? 'acknowledged' : 'pending',
      })))
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
      setAlerts([
        {
          alert_id: 'alert-001',
          slope_id: 'slope-manali-01',
          level: 'Critical',
          risk_score: 92,
          created_at: '2024-01-15T10:30:00Z',
          status: 'pending',
        },
        {
          alert_id: 'alert-002',
          slope_id: 'slope-shimla-03',
          level: 'High',
          risk_score: 78,
          created_at: '2024-01-15T09:15:00Z',
          status: 'pending',
        },
        {
          alert_id: 'alert-003',
          slope_id: 'slope-darjeeling-02',
          level: 'Moderate',
          risk_score: 55,
          created_at: '2024-01-15T08:00:00Z',
          status: 'evaluated',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const getLevelBadge = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border border-red-500/30'
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
      case 'moderate':
        return 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
      case 'low':
        return 'bg-green-500/20 text-green-400 border border-green-500/30'
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
    }
  }

  if (loading) {
    return (
      <div className="card-gradient rounded-xl p-6 border border-slate-700">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-slate-700 rounded w-1/4"></div>
          <div className="space-y-3">
            <div className="h-12 bg-slate-700 rounded"></div>
            <div className="h-12 bg-slate-700 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card-gradient rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          🚨 Active Alerts
          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full">
            {alerts.length} pending
          </span>
        </h2>
        <Link
          href="/alerts"
          className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-3 max-h-80 overflow-y-auto">
        {alerts.slice(0, 5).map((alert) => (
          <div
            key={alert.alert_id}
            className="bg-slate-800/50 rounded-lg p-3 border border-slate-600/50 hover:border-slate-500 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-1 text-xs font-medium rounded ${getLevelBadge(alert.level)}`}>
                  {alert.level}
                </span>
                <div>
                  <Link
                    href={`/slope/${alert.slope_id}`}
                    className="text-sm font-medium text-white hover:text-cyan-400 transition-colors"
                  >
                    {alert.slope_id}
                  </Link>
                  <p className="text-xs text-slate-400">
                    Risk: {alert.risk_score} • {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded ${
                  alert.status === 'pending'
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-emerald-500/20 text-emerald-400'
                }`}
              >
                {alert.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
