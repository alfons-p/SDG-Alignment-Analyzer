import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getSDGColor } from '../../constants/sdg-colors'

interface Props {
  data: { sdg: number; score: number; label?: string }[]
  title?: string
}

export function SDGBarChart({ data, title }: Props) {
  const chartData = data.map((d) => ({
    ...d,
    fill: getSDGColor(d.sdg),
  }))

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      {title && <h3 className="text-sm font-semibold text-slate-900 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="sdg"
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(v) => String(v)}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickFormatter={(v) => v.toFixed(1)}
          />
          <Tooltip
            formatter={(value: number) => [value.toFixed(3), 'Score']}
            labelFormatter={(label) => `SDG ${label}`}
          />
          <Bar dataKey="score" fill="#3b82f6" radius={[2, 2, 0, 0]}>
            {chartData.map((entry, idx) => (
              <cell key={idx} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
