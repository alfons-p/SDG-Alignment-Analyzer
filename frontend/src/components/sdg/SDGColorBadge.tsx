import { getSDGColor } from '../../constants/sdg-colors'

export function SDGColorBadge({ sdg, size = 'md' }: { sdg: number; size?: 'sm' | 'md' | 'lg' }) {
  const color = getSDGColor(sdg)
  const sizeClasses = {
    sm: 'w-5 h-5 text-[10px]',
    md: 'w-7 h-7 text-xs',
    lg: 'w-9 h-9 text-sm',
  }
  return (
    <span
      className={`${sizeClasses[size]} rounded-full flex items-center justify-center font-bold text-white shrink-0`}
      style={{ backgroundColor: color }}
      title={`SDG ${sdg}`}
    >
      {sdg}
    </span>
  )
}
