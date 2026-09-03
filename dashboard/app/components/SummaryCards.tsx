'use client'

interface SummaryData {
  totalSlopes: number
  slopesAtRisk: number
  activeAlerts: number
  dataQuality: number
}

export default function SummaryCards({ data }: { data: SummaryData }) {
  const cards = [
    {
      title: 'Total Slopes',
      value: data.totalSlopes,
      icon: '🗻',
      color: 'from-blue-500 to-blue-600',
      provenance: 'Observed',
    },
    {
      title: 'Slopes at Risk',
      value: data.slopesAtRisk,
      icon: '⚠️',
      color: 'from-orange-500 to-red-500',
      provenance: 'Model-derived',
    },
    {
      title: 'Active Alerts',
      value: data.activeAlerts,
      icon: '🚨',
      color: 'from-red-500 to-pink-500',
      provenance: 'Observed',
    },
    {
      title: 'Data Quality',
      value: `${data.dataQuality}%`,
      icon: '📡',
      color: 'from-emerald-500 to-teal-500',
      provenance: 'Observed',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, index) => (
        <div
          key={index}
          className="card-gradient rounded-xl p-4 border border-slate-700 shadow-lg hover:shadow-xl transition-shadow"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-2xl">{card.icon}</span>
            <span
              className={`provenance-badge ${
                card.provenance === 'Observed'
                  ? 'provenance-observed'
                  : 'provenance-model'
              }`}
            >
              {card.provenance}
            </span>
          </div>
          <div className={`text-3xl font-bold bg-gradient-to-r ${card.color} bg-clip-text text-transparent`}>
            {card.value}
          </div>
          <div className="text-sm text-slate-400 mt-1">{card.title}</div>
        </div>
      ))}
    </div>
  )
}
