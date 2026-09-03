'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'

interface SlopeDetail {
  slope: any
  risk: any
  susceptibility: any
  exposure: any
  latest_signals: any
}

interface TimeSeriesData {
  timestamp: string
  rainfall_mm: number
  volumetric_water_content: number
  displacement_mm: number
}

export default function SlopeDetailPage() {
  const params = useParams()
  const slopeId = params.slope_id as string

  const [detail, setDetail] = useState<SlopeDetail | null>(null)
  const [timeSeries, setTimeSeries] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (slopeId) fetchSlopeData()
  }, [slopeId])

  const fetchSlopeData = async () => {
    try {
      const [detailRes, tsRes] = await Promise.all([
        fetch(`http://localhost:8000/api/slopes/${slopeId}`),
        fetch(`http://localhost:8000/api/slopes/${slopeId}/timeseries`),
      ])

      if (!detailRes.ok) throw new Error(`Slope not found: ${detailRes.status}`)

      const detailData = await detailRes.json()
      const tsData = await tsRes.json()

      setDetail(detailData)
      setTimeSeries(tsData)
    } catch (err: any) {
      console.error('Failed to fetch slope data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (score: number) => {
    if (score >= 80) return '#ef4444'
    if (score >= 60) return '#f97316'
    if (score >= 40) return '#eab308'
    return '#22c55e'
  }

  const getRiskTextClass = (score: number) => {
    if (score >= 80) return 'text-red-400'
    if (score >= 60) return 'text-orange-400'
    if (score >= 40) return 'text-yellow-400'
    return 'text-green-400'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900">
        <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
          Loading real data...
        </div>
        <div className="p-6 flex items-center justify-center">
          <div className="text-slate-400">Loading slope data...</div>
        </div>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-slate-900">
        <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
          Real Data Mode
        </div>
        <div className="p-6">
          <div className="text-red-400 mb-4">Error: {error || 'Slope not found'}</div>
          <Link href="/" className="text-cyan-400 hover:text-cyan-300">Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  const slope = detail.slope
  const risk = detail.risk
  const riskScore = risk?.risk_score || 0
  const hazardScore = risk?.hazard_component ? Math.round(risk.hazard_component * 100) : 0
  const exposureScore = risk?.exposure_component ? Math.round(risk.exposure_component * 100) : 0
  const priorityClass = risk?.priority_class || 'Low'

  const rainfallData = timeSeries?.rainfall || []
  const smData = timeSeries?.soil_moisture || []
  const defData = timeSeries?.deformation || []

  const chartData = rainfallData.map((r: any, i: number) => ({
    time: new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    rainfall: r.rainfall_mm || 0,
    soil_moisture: smData[i]?.volumetric_water_content ? smData[i].volumetric_water_content * 100 : 0,
    deformation: defData[i]?.displacement_mm || 0,
  }))

  const maxRainfall = Math.max(...chartData.map((d: any) => d.rainfall), 1)

  return (
    <div className="min-h-screen bg-slate-900">
      <div className="real-data-banner text-white px-4 py-2 text-center font-semibold text-sm">
        REAL DATA MODE — Rainfall: Open-Meteo | Elevation: SRTM 90m | Soil: SoilGrids 250m
      </div>

      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link href="/" className="text-cyan-400 hover:text-cyan-300 text-sm mb-2 inline-block">
              Back to Dashboard
            </Link>
            <h1 className="text-2xl font-bold text-white">{slope.name || slope.slope_id}</h1>
            <p className="text-slate-400 mt-1">
              {slope.latitude?.toFixed(4)} N, {slope.longitude?.toFixed(4)} E | {slope.district}, {slope.state}
            </p>
          </div>
          <div className="text-right">
            <span className={`provenance-badge ${(slope.quality?.provenance || '').includes('Observed') ? 'provenance-observed' : 'provenance-simulated'}`}>
              {slope.quality?.provenance || 'Unknown'}
            </span>
            <div className="text-xs text-slate-400 mt-1">Coverage: {slope.coverage_mode}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="card-gradient rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4">Risk Score</h2>
            <div className="flex flex-col items-center">
              <svg width="200" height="120" viewBox="0 0 200 120">
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#334155" strokeWidth="12" />
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke={getRiskColor(riskScore)}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray="251.2"
                  strokeDashoffset={251.2 - (riskScore / 100) * 251.2}
                />
                <text x="100" y="85" textAnchor="middle" fill="white" fontSize="32" fontWeight="bold">
                  {riskScore}
                </text>
                <text x="100" y="105" textAnchor="middle" fill="#94a3b8" fontSize="12">
                  Risk Score (0-100)
                </text>
              </svg>

              <div className="grid grid-cols-2 gap-4 mt-4 w-full">
                <div className="text-center p-3 bg-slate-800/50 rounded-lg">
                  <div className={`text-xl font-bold ${getRiskTextClass(hazardScore)}`}>{hazardScore}</div>
                  <div className="text-xs text-slate-400">Hazard</div>
                </div>
                <div className="text-center p-3 bg-slate-800/50 rounded-lg">
                  <div className={`text-xl font-bold ${getRiskTextClass(exposureScore)}`}>{exposureScore}</div>
                  <div className="text-xs text-slate-400">Exposure</div>
                </div>
              </div>

              <div className="mt-4">
                <span className={`px-3 py-1 text-sm font-medium rounded-full ${
                  priorityClass === 'Critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                  priorityClass === 'High' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                  priorityClass === 'Moderate' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  'bg-green-500/20 text-green-400 border border-green-500/30'
                }`}>
                  {priorityClass} Priority
                </span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 card-gradient rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4">Time Series (72h)</h2>
            <div className="space-y-4">
              <div>
                <div className="text-xs text-slate-400 mb-1">Rainfall (mm)</div>
                <div className="flex items-end gap-px h-16">
                  {chartData.map((d: any, i: number) => (
                    <div
                      key={i}
                      className="flex-1 bg-blue-500 rounded-t"
                      style={{ height: `${(d.rainfall / maxRainfall) * 100}%`, minHeight: d.rainfall > 0 ? '2px' : '0' }}
                      title={`${d.time}: ${d.rainfall.toFixed(1)}mm`}
                    />
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 mb-1">Soil Moisture (%)</div>
                <div className="flex items-end gap-px h-12">
                  {chartData.map((d: any, i: number) => (
                    <div
                      key={i}
                      className="flex-1 bg-green-500/70 rounded-t"
                      style={{ height: `${d.soil_moisture}%`, minHeight: '1px' }}
                      title={`${d.time}: ${d.soil_moisture.toFixed(1)}%`}
                    />
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 mb-1">Deformation (mm)</div>
                <div className="flex items-end gap-px h-10">
                  {chartData.map((d: any, i: number) => {
                    const maxDef = Math.max(...chartData.map((x: any) => x.deformation), 1)
                    return (
                      <div
                        key={i}
                        className="flex-1 bg-red-500/70 rounded-t"
                        style={{ height: `${(d.deformation / maxDef) * 100}%`, minHeight: d.deformation > 0 ? '1px' : '0' }}
                        title={`${d.time}: ${d.deformation.toFixed(2)}mm`}
                      />
                    )
                  })}
                </div>
              </div>
            </div>
            <div className="flex gap-4 mt-3 text-xs text-slate-400">
              <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded"></span> Rainfall</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-500/70 rounded"></span> Soil Moisture</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500/70 rounded"></span> Deformation</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card-gradient rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-2">Feature Contributions</h2>
            <p className="text-xs text-slate-400 mb-4">SHAP-style explainability breakdown</p>
            <div className="space-y-3">
              {detail.susceptibility?.feature_contributions && Object.entries(detail.susceptibility.feature_contributions).slice(0, 6).map(([feat, val]: [string, any]) => {
                const absVal = Math.abs(val)
                const maxAbs = 1
                const pct = Math.min((absVal / maxAbs) * 100, 100)
                return (
                  <div key={feat} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-300">{feat}</span>
                      <span className="text-slate-400">
                        <span className="provenance-badge provenance-model mr-2">Model</span>
                        {val > 0 ? '+' : ''}{(val * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${val > 0 ? 'bg-gradient-to-r from-cyan-500 to-blue-500' : 'bg-gradient-to-r from-blue-500 to-cyan-500'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
              {(!detail.susceptibility?.feature_contributions || Object.keys(detail.susceptibility.feature_contributions).length === 0) && (
                <div className="text-slate-400 text-sm">No feature contributions available</div>
              )}
            </div>
          </div>

          <div className="card-gradient rounded-xl p-6 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4">Slope Properties</h2>
            <div className="space-y-2">
              {[
                ['Elevation', `${slope.elevation_m} m`],
                ['Slope Angle', `${slope.slope_angle_deg} degrees`],
                ['Lithology', slope.lithology],
                ['Soil Type', slope.soil_type],
                ['Land Cover', slope.land_cover],
                ['Coverage Mode', slope.coverage_mode],
                ['Confidence', risk?.confidence ? `${(risk.confidence * 100).toFixed(1)}%` : 'N/A'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between py-2 border-b border-slate-700/50">
                  <span className="text-sm text-slate-400">{label}</span>
                  <span className="text-sm text-white font-medium">{value}</span>
                </div>
              ))}
            </div>
            {risk?.uncertainty_notes && (
              <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <div className="text-xs text-amber-400">{risk.uncertainty_notes}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
