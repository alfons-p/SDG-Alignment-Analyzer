import type { CSSProperties } from 'react'

const styles: Record<string, CSSProperties> = {
  queued: { background: 'color-mix(in srgb, var(--color-text) 8%, transparent)', color: 'color-mix(in srgb, var(--color-text) 62%, transparent)' },
  processing: { background: 'var(--color-accent-100)', color: 'var(--color-accent-800)' },
  completed: { background: 'var(--color-accent-2-100)', color: 'var(--color-accent-2-700)' },
  failed: { background: '#fbe4e0', color: '#8a2a1c' },
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', padding: '3px 11px', borderRadius: 999,
        fontSize: 11.5, fontWeight: 600, letterSpacing: '0.02em', textTransform: 'capitalize',
        ...(styles[status] ?? styles.queued),
      }}
    >
      {status}
    </span>
  )
}
