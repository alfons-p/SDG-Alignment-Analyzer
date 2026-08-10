import { useNavigate, Link } from 'react-router-dom'
import './council.css'

const muted = 'color-mix(in srgb, var(--color-text) 68%, transparent)'

const SECTIONS = [
  ['read', 'What we read'],
  ['match', 'What a match means'],
  ['cannot', 'What this cannot tell you'],
]

/**
 * "How it works" — the case for trusting the number, in three parts. Split out
 * from Limitations (the case against) so the Method label delivers the
 * mechanism; the third part hands off to the Limitations page, which keeps the
 * caveats as its home. (Landing critique #4.)
 */
export function HowItWorksPage() {
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

        <div style={{ display: 'flex', flexDirection: 'column', gap: 40, maxWidth: 760 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <span style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-accent-700)' }}>How it works</span>
            <h1 style={{ fontSize: 38, lineHeight: 1.08 }}>How a report becomes a set of Goals</h1>
            <p style={{ margin: 0, fontSize: 17, lineHeight: 1.65, color: muted, textWrap: 'pretty' }}>
              Every figure on this site is produced the same way, by software, from a published annual report. Nothing is
              hand-scored. Here is exactly what the tool reads, what a match to a Goal means, and where that reading stops.
            </p>
          </div>

          {/* 01 — What we read */}
          <section id="read" style={{ display: 'flex', flexDirection: 'column', gap: 14, scrollMarginTop: 24 }}>
            <Kicker n="01" title="What we read" />
            <P>
              We read what a report <strong>describes</strong> — the sentences that state an activity the council carried out.
              A report's PDF is turned into text, split into sentences, and each sentence is classified as either a described
              activity or not. Headings, financial tables, contents pages and boilerplate are set aside; scanned pages with no
              text layer are read with OCR so image-only reports are not silently empty.
            </P>
            <P>
              This is why format matters. A report written as prose yields many described activities; one written as tables and
              status grids yields few, for the same underlying work. The tool measures the <strong>account</strong> a council
              gives of itself, not the work in the world.
            </P>
          </section>

          {/* 02 — What a match means */}
          <section id="match" style={{ display: 'flex', flexDirection: 'column', gap: 14, scrollMarginTop: 24 }}>
            <Kicker n="02" title="What a match means" />
            <P>
              Each described activity is compared against the language of the 17 Goals — their official targets and indicators —
              by an ensemble of two models: a sentence-transformer and a domain model tuned on SDG text. That produces a
              similarity score for every Goal.
            </P>
            <P>
              An activity is recorded as aligned to a Goal when its score clears a <strong>threshold set for that Goal</strong>.
              A match therefore means one thing precisely: the language of the activity resembles the language of the Goal,
              closely enough to pass a stated bar. It is not a judgement that the work is effective, material, or complete. Every
              match on the site is shown with the passage that produced it and the threshold it cleared, so you can read the
              evidence yourself — that is the intended way to use this tool.
            </P>
          </section>

          {/* 03 — What this cannot tell you → hands off to Limitations */}
          <section id="cannot" style={{ display: 'flex', flexDirection: 'column', gap: 14, scrollMarginTop: 24 }}>
            <Kicker n="03" title="What this cannot tell you" />
            <P>
              Because it reads language, the tool cannot tell you what a council achieved, only what its report described. A Goal
              with no evidence means the report did not describe qualifying work — not that none was done. Coverage varies by
              council and by year, thresholds are chosen rather than discovered, some Goals are far easier to detect than others,
              and individual matches can be wrong in either direction.
            </P>
            <div className="card" style={{ padding: '18px 22px', background: 'color-mix(in srgb, var(--color-text) 4%, transparent)', gap: 8 }}>
              <span style={{ fontSize: 15, fontWeight: 600 }}>The full case against the number</span>
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: muted, textWrap: 'pretty' }}>
                Every limitation, in detail — what it measures, what it is not, how thresholds and coverage shape a result, and how
                to have a match corrected.
              </p>
              <Link to="/limitations" style={{ fontSize: 14, alignSelf: 'flex-start' }}>Read the limitations →</Link>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function Kicker({ n, title }: { n: string; title: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
      <span style={{ fontFamily: 'var(--font-heading)', fontSize: 15, color: 'var(--color-accent-700)' }}>{n}</span>
      <h2 style={{ fontSize: 24, margin: 0 }}>{title}</h2>
    </div>
  )
}

function P({ children }: { children: React.ReactNode }) {
  return <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, color: muted, textWrap: 'pretty' }}>{children}</p>
}
