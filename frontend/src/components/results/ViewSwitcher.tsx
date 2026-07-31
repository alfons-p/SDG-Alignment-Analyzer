export type ResultsView = 'ledger' | 'statement' | 'depth' | 'trend'

const VIEWS: { key: ResultsView; label: string; note: string }[] = [
  {
    key: 'ledger',
    label: 'Evidence ledger',
    note: 'Every goal ranked, every claim opens the passage that produced it.',
  },
  {
    key: 'statement',
    label: 'Published statement',
    note: 'The same data read as a page of the council’s own annual report.',
  },
  {
    key: 'depth',
    label: 'Breadth vs depth',
    note: 'Where coverage and mean score disagree.',
  },
  {
    key: 'trend',
    label: 'Three-year trend',
    note: 'How the account changed across years.',
  },
]

export function ViewSwitcher({
  view,
  onChange,
}: {
  view: ResultsView
  onChange: (v: ResultsView) => void
}) {
  const note = VIEWS.find((v) => v.key === view)?.note ?? ''
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '22px 44px 0' }}>
      <div className="rx-views">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            type="button"
            className="rx-view"
            data-active={v.key === view}
            onClick={() => onChange(v.key)}
          >
            {v.label}
          </button>
        ))}
      </div>
      <span className="rx-viewnote">{note}</span>
    </div>
  )
}
