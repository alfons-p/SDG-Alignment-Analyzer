import { useNavigate, Link } from 'react-router-dom'
import './council.css'

const muted = 'color-mix(in srgb, var(--color-text) 68%, transparent)'

const LIMITS = [
  ['Extraction', 'Activities are read from prose. Reports written as tables, objective codes or status grids yield far fewer described activities than narrative reports — in our data, by a factor of three or more between comparable councils. Where this materially affects a result, the council’s page says so.'],
  ['Coverage differs by council and by year', 'Not every council has an analysed report for every year, and reporting formats change between years. Comparisons across councils or across time carry both effects.'],
  ['Thresholds are set, not discovered', 'A passage is matched to a Goal when its similarity score passes a threshold calibrated for that Goal. Different thresholds would produce different results. Every threshold in use is shown alongside a result, so you can see the bar a passage had to clear.'],
  ['Goals are not equally detectable', 'Some Goals are expressed in language that overlaps heavily with ordinary local-government writing, and are matched readily. Others rarely appear in council reports at all. A low result for a Goal partly reflects this, not only the work behind it.'],
  ['Automated matching makes errors', 'Individual matches may be wrong in either direction. Every claim on this site is shown alongside the passage that produced it so you can judge it yourself — the intended way to read these results.'],
  ['Source documents', 'Analysis is performed on annual reports as published. We do not correct, supplement or verify their contents, and errors in a source report carry into the analysis.'],
]

const SECTIONS = [
  ['measures', 'What it measures'],
  ['limitations', 'Known limitations'],
  ['not', 'What this is not'],
  ['corrections', 'Corrections'],
  ['data', 'Data and licensing'],
]

export function LimitationsPage() {
  const navigate = useNavigate()
  return (
    <div className="cx">
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '18px 44px' }}>
        <span onClick={() => navigate('/')} style={{ fontFamily: 'var(--font-heading)', fontSize: 20, cursor: 'pointer' }}>SDG Alignment Analyser</span>
      </div>

      <div className="page" style={{ display: 'grid', gridTemplateColumns: '200px minmax(0, 1fr)', gap: 48, padding: '20px 44px 72px', alignItems: 'start' }}>
        {/* contents rail */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 8, position: 'sticky', top: 24 }}>
          <span style={{ fontSize: 11, letterSpacing: '0.09em', textTransform: 'uppercase', color: 'color-mix(in srgb, var(--color-text) 50%, transparent)', marginBottom: 4 }}>On this page</span>
          {SECTIONS.map(([id, label]) => (
            <a key={id} href={`#${id}`} style={{ borderBottom: 'none', fontSize: 13.5, color: muted }}>{label}</a>
          ))}
        </nav>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 34, maxWidth: 760 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <span style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-accent-700)' }}>About this analysis</span>
            <h1 style={{ fontSize: 38, lineHeight: 1.08 }}>What this tool measures, and what it cannot</h1>
            <p style={{ margin: 0, fontSize: 17, lineHeight: 1.65, color: muted, textWrap: 'pretty' }}>
              The SDG Alignment Analyser is a research project. It applies automated text analysis to published Australian council
              annual reports, identifying the activities each report describes and matching them against the 17 UN Sustainable
              Development Goals. No part of it has been reviewed or endorsed by the councils analysed, by the United Nations, or by
              any government body.
            </p>
          </div>

          <section id="measures" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 style={{ fontSize: 24 }}>What the analysis measures</h2>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, textWrap: 'pretty' }}>
              It measures language, not activity. The unit is a passage of text, and a match means that passage reads as describing
              work relevant to a Goal. A council may do substantial work on a Goal and receive no evidence for it here, simply
              because the report described it in other terms — and the reverse also happens.
            </p>
            <p style={{ margin: 0, fontSize: 20, lineHeight: 1.5, padding: '18px 24px', borderRadius: 22, background: 'var(--color-accent-100)', color: 'var(--color-accent-800)', fontFamily: 'var(--font-heading)', textWrap: 'pretty' }}>
              A Goal with no evidence is a statement about a document, not about a council.
            </p>
          </section>

          <section id="limitations" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <h2 style={{ fontSize: 24 }}>Known limitations</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {LIMITS.map(([h, b]) => (
                <div key={h} className="card">
                  <h3 style={{ fontSize: 17 }}>{h}</h3>
                  <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.6, color: muted, textWrap: 'pretty' }}>{b}</p>
                </div>
              ))}
            </div>
          </section>

          <section id="not" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 style={{ fontSize: 24 }}>What this is not</h2>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, textWrap: 'pretty' }}>
              This is not a ranking, a scorecard, an audit or a compliance assessment. We do not publish league tables and do not
              order councils by performance. Where a list is sorted, the sort is a convenience and is labelled as such. Results
              should not be used to allocate funding, assess a council’s performance, or support a claim of compliance with any
              standard or reporting framework.
            </p>
          </section>

          <section id="corrections" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 style={{ fontSize: 24 }}>Corrections</h2>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, textWrap: 'pretty' }}>
              If a result appears wrong, tell us. Council officers may request a re-analysis, submit a corrected or superseded
              report, or ask for a specific match to be reviewed.
            </p>
          </section>

          <section id="data" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h2 style={{ fontSize: 24 }}>Data and licensing</h2>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, color: muted, textWrap: 'pretty' }}>
              Council annual reports are published documents and remain the copyright of their councils. Boundary data is © Commonwealth
              of Australia (Australian Bureau of Statistics), Australian Statistical Geography Standard Edition 3, used under CC BY 4.0.
            </p>
            <Link to="/">← Back to the map</Link>
          </section>
        </div>
      </div>
    </div>
  )
}
