import { getSDGColor, SDG_COUNT } from '../../constants/sdg-colors'

export function CoverageChart({ coverage }: { coverage: Record<number, number> }) {
  const sdgs = Array.from({ length: SDG_COUNT }, (_, i) => i + 1)
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-3">SDG Coverage</h3>
      <div className="grid grid-cols-17 gap-1">
        {sdgs.map((sdg) => {
          const pct = (coverage[sdg] ?? 0) * 100
          const color = getSDGColor(sdg)
          return (
            <div key={sdg} className="text-center">
              <div className="w-full bg-slate-200 rounded h-16 relative mb-1">
                <div
                  className="absolute bottom-0 left-0 right-0 rounded-b transition-all"
                  style={{ height: `${pct}%`, backgroundColor: color }}
                />
              </div>
              <span className="text-[10px] text-slate-500">{sdg}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
