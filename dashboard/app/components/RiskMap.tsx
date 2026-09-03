'use client'

import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

interface Slope {
  slope_id: string
  latitude: number
  longitude: number
  risk_score: number
  priority_class: string
  coverage_mode: string
}

export default function RiskMap() {
  const [slopes, setSlopes] = useState<Slope[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSlopes()
  }, [])

  const fetchSlopes = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/slopes')
      const data = await response.json()
      const slopesList = data.slopes || data || []
      setSlopes(slopesList.map((s: any) => ({
        slope_id: s.slope_id,
        latitude: s.latitude,
        longitude: s.longitude,
        risk_score: s.risk_score || 0,
        priority_class: s.priority_class || 'Low',
        coverage_mode: s.coverage_mode || 'modeled-only',
      })))
    } catch (error) {
      console.error('Failed to fetch slopes:', error)
      setSlopes([
        {
          slope_id: 'demo-slope-1',
          latitude: 27.5,
          longitude: 88.5,
          risk_score: 75,
          priority_class: 'High',
          coverage_mode: 'instrumented',
        },
        {
          slope_id: 'demo-slope-2',
          latitude: 27.6,
          longitude: 88.6,
          risk_score: 45,
          priority_class: 'Moderate',
          coverage_mode: 'modeled-only',
        },
        {
          slope_id: 'demo-slope-3',
          latitude: 27.4,
          longitude: 88.4,
          risk_score: 90,
          priority_class: 'Critical',
          coverage_mode: 'hybrid',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
        return '#ef4444'
      case 'high':
        return '#f97316'
      case 'moderate':
        return '#eab308'
      case 'low':
        return '#22c55e'
      default:
        return '#6b7280'
    }
  }

  const getRadius = (score: number) => {
    if (score >= 80) return 12
    if (score >= 60) return 10
    if (score >= 40) return 8
    return 6
  }

  if (loading) {
    return (
      <div className="h-96 bg-slate-800 rounded-xl flex items-center justify-center border border-slate-700">
        <div className="text-slate-400">Loading map data...</div>
      </div>
    )
  }

  return (
    <div className="h-96 rounded-xl overflow-hidden border border-slate-700 shadow-lg">
      <MapContainer
        center={[27.5, 88.5]}
        zoom={8}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {slopes.map((slope) => (
          <CircleMarker
            key={slope.slope_id}
            center={[slope.latitude, slope.longitude]}
            radius={getRadius(slope.risk_score)}
            fillColor={getPriorityColor(slope.priority_class)}
            color={getPriorityColor(slope.priority_class)}
            weight={2}
            opacity={1}
            fillOpacity={0.7}
          >
            <Popup>
              <div className="p-2 min-w-[200px]">
                <h3 className="font-bold text-slate-900 mb-2">{slope.slope_id}</h3>
                <div className="space-y-1 text-sm">
                  <p>
                    <span className="font-medium">Risk Score:</span>{' '}
                    <span className="font-bold text-red-600">{slope.risk_score}</span>
                  </p>
                  <p>
                    <span className="font-medium">Priority:</span>{' '}
                    <span style={{ color: getPriorityColor(slope.priority_class) }}>
                      {slope.priority_class}
                    </span>
                  </p>
                  <p>
                    <span className="font-medium">Coverage:</span>{' '}
                    <span className="capitalize">{slope.coverage_mode}</span>
                  </p>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
