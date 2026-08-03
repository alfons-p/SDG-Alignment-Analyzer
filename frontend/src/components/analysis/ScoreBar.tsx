import { getSDGColor } from '../../constants/sdg-colors'

export function ScoreBar({
  sdg,
  score,
  label,
}: {
  sdg: number
  score: number
  label?: string
}) {
  const pct = Math.min(score * 100, 100)
  const color = getSDGColor(sdg)
  return (
    <div className="flex items-center gap-3">
      <span
        className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
        style={{ backgroundColor: color }}
      >
        {sdg}
      </span>
      <span className="w-24 truncate" style={{ fontSize: 12, color: 'color-mix(in srgb, var(--color-text) 62%, transparent)' }}>{label ?? `SDG ${sdg}`}</span>
      <div className="flex-1 rounded-full h-2.5" style={{ background: 'color-mix(in srgb, var(--color-text) 12%, transparent)' }}>
        <div
          className="h-2.5 rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="font-mono w-10 text-right" style={{ fontSize: 12, color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>
        {score.toFixed(2)}
      </span>
    </div>
  )
}
