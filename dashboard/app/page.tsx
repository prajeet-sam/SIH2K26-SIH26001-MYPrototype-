'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import SummaryCards from './components/SummaryCards'
import AlertPanel from './components/AlertPanel'
import DataQualityBadge from './components/DataQualityBadge'

const RiskMap = dynamic(() => import('./components/RiskMap'), {
  ssr: false,
  loading: () => (
    <div className="h-96 bg-slate-800 rounded-xl flex items-center justify-center border border-slate-700">
      <div className="text-slate-400">Loading map...</div>
    </div>
  ),
})

export default function DashboardPage() {
  const [summary, setSummary] = useState({
    totalSlopes: 0,
    slopesAtRisk: 0,
    activeAlerts: 0,
    dataQuality: 0,
  })
  const [slopes, setSlopes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [systemMode, setSystemMode] = useState('simulation')

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [slopesRes, alertsRes, qualityRes, healthRes] = await Promise.all([
        fetch('http://localhost:8000/api/slopes'),
        fetch('http://localhost:8000/api/alerts'),
        fetch('http://localhost:8000/api/quality/coverage'),
        fetch('http://localhost:8000/api/health'),
      ])

      const slopesData = await slopesRes.json()
      const alertsData = await alertsRes.json()
      const qualityData = await qualityRes.json()
      const healthData = await healthRes.json()

      const slopesList = slopesData.slopes || []
      const alertsList = alertsData.alerts || []
      const qualityOverall = qualityData.overall || {}

      setSlopes(slopesList)
      setSystemMode(healthData.mode || 'simulation')
      setSummary({
        totalSlopes: slopesList.length,
        slopesAtRisk: slopesList.filter((s: any) => s.risk_score && s.risk_score >= 30).length,
        activeAlerts: alertsList.length,
        dataQuality: qualityOverall.healthy_pct || 85,
      })
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      setSummary({ totalSlopes: 35, slopesAtRisk: 10, activeAlerts: 0, dataQuality: 98 })
    } finally {
      setLoading(false)
    }
  }

  const isReal = systemMode === 'real-data'

  return (
    <div className="min-h-screen">
      <div className={`text-white px-4 py-2 text-center font-semibold text-sm ${isReal ? 'real-data-banner' : 'demo-banner'}`}>
        {isReal
          ? 'REAL DATA MODE \u2014 Rainfall: Open-Meteo | Elevation: SRTM 90m | Soil: SoilGrids 250m | Labels: GSI/NIDM Landslide Catalog'
          : 'DEMO / SIMULATION MODE \u2014 All data shown is simulated for demonstration purposes'}
      </div>

      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Dashboard Overview</h1>
            <p className="text-slate-400 mt-1">AI-Based Landslide Risk Monitoring for Northeast India</p>
          </div>
          <DataQualityBadge
            coverageMode="modeled-only"
            sensorHealth={summary.dataQuality}
            provenance={isReal ? 'Observed (Open-Meteo + SRTM + SoilGrids)' : 'Simulated (Demo)'}
          />
        </div>

        <SummaryCards data={summary} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2">
            <div className="card-gradient rounded-xl p-4 border border-slate-700">
              <h2 className="text-lg font-semibold text-white mb-4">
                Risk Assessment Map
                <span className="text-xs bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded-full ml-2">
                  Northeast India
                </span>
              </h2>
              <RiskMap />
            </div>
          </div>

          <div>
            <AlertPanel />
          </div>
        </div>

        <div className="card-gradient rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Stats</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-cyan-400">25.5 N</div>
              <div className="text-xs text-slate-400">Center Latitude</div>
            </div>
            <div className="text-center p-4 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-cyan-400">92.0 E</div>
              <div className="text-xs text-slate-400">Center Longitude</div>
            </div>
            <div className="text-center p-4 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-cyan-400">{summary.totalSlopes || 35}</div>
              <div className="text-xs text-slate-400">NER Slope Units</div>
            </div>
            <div className="text-center p-4 bg-slate-800/50 rounded-lg">
              <div className="text-2xl font-bold text-cyan-400">72h</div>
              <div className="text-xs text-slate-400">Forecast Window</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
