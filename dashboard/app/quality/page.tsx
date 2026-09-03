'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface QualityOverview {
  total: number
  healthy_pct: number
  stale_pct: number
  missing_pct: number
  inconsistent_pct: number
}

interface SensorInfo {
  status: string
  last_reading: string
  record_count: number
}

export default function QualityPage() {
  const [quality, setQuality] = useState<QualityOverview | null>(null)
  const [sensorSummary, setSensorSummary] = useState<any>(null)
  const [perSlope, setPerSlope] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchQualityData()
  }, [])

  const fetchQualityData = async () => {
    try {
      const [coverageRes, sensorRes] = await Promise.all([
        fetch('http://localhost:8000/api/quality/coverage'),
        fetch('http://localhost:8000/api/quality/sensors'),
      ])

      const coverageData = await coverageRes.json()
      const sensorData = await sensorRes.json()

      setQuality(coverageData.overall)
      setSensorSummary(sensorData.summary)
      setPerSlope(coverageData.per_slope || {})
    } catch (error) {
      console.error('Failed to fetch quality data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
      case 'stale':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
      case 'missing':
        return 'bg-red-500/20 text-red-400 border border-red-500/30'
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900">
        <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
          Loading quality data...
        </div>
        <div className="p-6 flex items-center justify-center">
          <div className="text-slate-400">Loading quality data...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
        REAL DATA MODE — 37,800+ records from Open-Meteo, SoilGrids, Simulated Sensors
      </div>

      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link href="/" className="text-cyan-400 hover:text-cyan-300 text-sm mb-2 inline-block">
              Back to Dashboard
            </Link>
            <h1 className="text-2xl font-bold text-white">Data Quality Dashboard</h1>
            <p className="text-slate-400 mt-1">Monitor sensor health and data coverage</p>
          </div>
          <span className="provenance-badge provenance-observed">Observed + Simulated</span>
        </div>

        {quality && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="card-gradient rounded-xl p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Healthy Records</div>
              <div className="text-3xl font-bold text-emerald-400">{quality.healthy_pct}%</div>
              <div className="text-xs text-slate-500 mt-1">{quality.total} total records</div>
            </div>
            <div className="card-gradient rounded-xl p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Stale Records</div>
              <div className="text-3xl font-bold text-amber-400">{quality.stale_pct}%</div>
            </div>
            <div className="card-gradient rounded-xl p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Missing Records</div>
              <div className="text-3xl font-bold text-red-400">{quality.missing_pct}%</div>
            </div>
            <div className="card-gradient rounded-xl p-4 border border-slate-700">
              <div className="text-sm text-slate-400 mb-1">Inconsistent</div>
              <div className="text-3xl font-bold text-orange-400">{quality.inconsistent_pct}%</div>
            </div>
          </div>
        )}

        {sensorSummary && (
          <div className="card-gradient rounded-xl p-6 border border-slate-700 mb-6">
            <h2 className="text-lg font-semibold text-white mb-4">Sensor Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {[
                ['Total Sensors', sensorSummary.total_sensors, 'text-cyan-400'],
                ['Healthy', sensorSummary.healthy, 'text-emerald-400'],
                ['Stale', sensorSummary.stale, 'text-amber-400'],
                ['Missing', sensorSummary.missing, 'text-red-400'],
                ['Inconsistent', sensorSummary.inconsistent, 'text-orange-400'],
              ].map(([label, value, colorClass]) => (
                <div key={label as string} className="text-center p-3 bg-slate-800/50 rounded-lg">
                  <div className={`text-2xl font-bold ${colorClass}`}>{value as number}</div>
                  <div className="text-xs text-slate-400">{label as string}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="card-gradient rounded-xl border border-slate-700 overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white">Per-Slope Sensor Status</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-800/50">
                  <th className="text-left p-3 text-sm font-semibold text-slate-300">Slope ID</th>
                  <th className="text-left p-3 text-sm font-semibold text-slate-300">Rainfall</th>
                  <th className="text-left p-3 text-sm font-semibold text-slate-300">Soil Moisture</th>
                  <th className="text-left p-3 text-sm font-semibold text-slate-300">Deformation</th>
                  <th className="text-left p-3 text-sm font-semibold text-slate-300">Quality %</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(perSlope).slice(0, 10).map(([slopeId, slopeQuality]: [string, any]) => (
                  <tr key={slopeId} className="border-t border-slate-700 hover:bg-slate-800/30">
                    <td className="p-3 text-sm text-cyan-400 font-mono">{slopeId}</td>
                    <td className="p-3">
                      <span className={`text-xs px-2 py-1 rounded ${getStatusColor(slopeQuality.stale_pct > 5 ? 'stale' : 'healthy')}`}>
                        {slopeQuality.healthy_pct}% healthy
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="text-xs text-slate-400">{slopeQuality.total} records</span>
                    </td>
                    <td className="p-3">
                      <span className="text-xs text-slate-400">{slopeQuality.stale_pct}% stale</span>
                    </td>
                    <td className="p-3">
                      <span className="text-sm font-medium text-emerald-400">{slopeQuality.healthy_pct}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
