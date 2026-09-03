'use client'

interface DataQualityBadgeProps {
  coverageMode: 'instrumented' | 'modeled-only' | 'hybrid'
  sensorHealth?: number
  provenance?: string
}

export default function DataQualityBadge({
  coverageMode,
  sensorHealth,
  provenance = 'Simulated (Demo)',
}: DataQualityBadgeProps) {
  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'instrumented':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200'
      case 'modeled-only':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'hybrid':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200'
    }
  }

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case 'instrumented':
        return '📡 Instrumented'
      case 'modeled-only':
        return '🔬 Modeled-only'
      case 'hybrid':
        return '🔄 Hybrid'
      default:
        return mode
    }
  }

  const getProvenanceColor = (prov: string) => {
    if (prov.includes('Observed')) return 'provenance-observed'
    if (prov.includes('Forecast')) return 'provenance-forecast'
    if (prov.includes('Model')) return 'provenance-model'
    return 'provenance-simulated'
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span
        className={`provenance-badge border ${getModeColor(coverageMode)}`}
        title={`Data coverage mode: ${coverageMode}`}
      >
        {getModeLabel(coverageMode)}
      </span>

      <span
        className={`provenance-badge ${getProvenanceColor(provenance)}`}
        title={`Data provenance: ${provenance}`}
      >
        {provenance}
      </span>

      {sensorHealth !== undefined && (
        <span
          className={`provenance-badge ${
            sensorHealth >= 80
              ? 'provenance-observed'
              : sensorHealth >= 50
              ? 'provenance-forecast'
              : 'bg-red-100 text-red-800'
          }`}
          title={`Sensor health: ${sensorHealth}%`}
        >
          🩺 {sensorHealth}% Health
        </span>
      )}
    </div>
  )
}
