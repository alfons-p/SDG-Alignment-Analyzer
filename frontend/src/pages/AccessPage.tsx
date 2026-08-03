import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, register } from '../api/auth'
import './council.css'

const muted = 'color-mix(in srgb, var(--color-text) 65%, transparent)'

const LADDER: { role: string; how: string; can: string[]; cant?: string }[] = [
  { role: 'Anyone', how: 'no account', can: ['Browse every council, every analysed year', 'Read the passage behind every match', 'Compare councils you choose'] },
  { role: 'Registered', how: 'free, sign up in a minute', can: ['Everything above', 'Export results as PDF, CSV or JSON', 'Save comparisons and return to them'] },
  { role: 'Council officer', how: 'verified work email', can: ['Everything above', 'Upload your own council’s annual report', 'Keep a result private until you publish it'], cant: 'Cannot upload for another council, or change a published result' },
]

const TICKS = [
  'I understand these results are indicative, not authoritative — produced by automated text analysis, not reviewed or endorsed by the councils, the UN, or any government body.',
  'They measure reporting, not performance. I will not present them as a measure of a council’s performance, compliance, or contribution to the Goals.',
  'I will not rank or score councils using this data, including league tables and grades.',
  'I will carry the attribution and the limitations with any figure I publish, quote or circulate, including the report year it refers to.',
]

const input: React.CSSProperties = {
  width: '100%', background: 'var(--color-surface)', border: '1px solid var(--color-divider)',
  borderRadius: 999, padding: '11px 16px', fontSize: 14, color: 'var(--color-text)', fontFamily: 'var(--font-body)',
}

export function AccessPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'in' | 'up'>('in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [ticks, setTicks] = useState([false, false, false, false])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const allTicked = ticks.every(Boolean)

  async function submit() {
    setErr('')
    if (mode === 'up' && !allTicked) return
    setBusy(true)
    try {
      const r = mode === 'in' ? await login(email, password) : await register(email, password)
      localStorage.setItem('token', r.access_token)
      navigate('/dashboard')
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(detail || (mode === 'in' ? 'Sign-in failed.' : 'Could not create account.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="cx">
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '18px 44px' }}>
        <span onClick={() => navigate('/')} style={{ fontFamily: 'var(--font-heading)', fontSize: 20, cursor: 'pointer' }}>SDG Alignment Analyser</span>
      </div>

      <div className="page" style={{ display: 'grid', gridTemplateColumns: 'minmax(380px, 1fr) minmax(340px, 440px)', gap: 52, padding: '20px 44px 72px', alignItems: 'start' }}>
        {/* left — the model */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <span style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-accent-700)' }}>Accounts</span>
            <h1 style={{ fontSize: 34, lineHeight: 1.1 }}>Reading the analysis needs no account</h1>
            <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, color: muted, textWrap: 'pretty' }}>
              Every published result is open to anyone. An account exists for the two things that carry an obligation: taking data
              off the site, and putting a report on it.
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {LADDER.map((r) => (
              <div key={r.role} className="card">
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
                  <span style={{ fontFamily: 'var(--font-heading)', fontSize: 19 }}>{r.role}</span>
                  <span style={{ fontSize: 12.5, color: muted }}>{r.how}</span>
                </div>
                {r.can.map((c) => (
                  <span key={c} style={{ fontSize: 13.5, lineHeight: 1.5 }}><span style={{ color: 'var(--color-accent-2-700)' }}>✓ </span>{c}</span>
                ))}
                {r.cant && <span style={{ fontSize: 13.5, lineHeight: 1.5, color: muted }}><span style={{ color: 'var(--color-accent-700)' }}>✕ </span>{r.cant}</span>}
              </div>
            ))}
          </div>
          <span style={{ fontSize: 12.5, lineHeight: 1.5, color: muted, textWrap: 'pretty' }}>
            No account can alter an analysis — results are produced by the classifier and are the same for everyone. <Link to="/limitations">About this analysis and its limits</Link>
          </span>
        </div>

        {/* right — auth */}
        <div className="card" style={{ padding: 28, gap: 16 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className={`pill${mode === 'in' ? ' on' : ''}`} onClick={() => setMode('in')}>Sign in</button>
            <button className={`pill${mode === 'up' ? ' on' : ''}`} onClick={() => setMode('up')}>Create an account</button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input style={input} type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <input style={input} type="password" placeholder={mode === 'in' ? 'Password' : 'Choose a password'} value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          {mode === 'up' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '14px 16px', borderRadius: 18, background: 'var(--color-accent-100)' }}>
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 16, color: 'var(--color-accent-800)' }}>Before you can export</span>
              <span style={{ fontSize: 12.5, lineHeight: 1.5, color: 'var(--color-accent-800)', textWrap: 'pretty' }}>
                Exported files leave this site and are easily forwarded without the context around them. These conditions apply to every file you export.
              </span>
              {TICKS.map((t, i) => (
                <label key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13, lineHeight: 1.5, color: 'var(--color-accent-800)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={ticks[i]} onChange={(e) => setTicks((s) => s.map((v, j) => (j === i ? e.target.checked : v)))} style={{ marginTop: 3 }} />
                  <span style={{ textWrap: 'pretty' }}>{t}</span>
                </label>
              ))}
            </div>
          )}

          {err && <span style={{ fontSize: 13, color: '#b91c1c' }}>{err}</span>}

          <button
            onClick={submit}
            disabled={busy || !email || !password || (mode === 'up' && !allTicked)}
            style={{ border: 'none', cursor: 'pointer', fontFamily: 'var(--font-heading)', fontSize: 15, padding: '12px 18px', borderRadius: 999, background: 'var(--color-accent)', color: 'var(--color-bg)', opacity: busy || !email || !password || (mode === 'up' && !allTicked) ? 0.5 : 1 }}
          >
            {busy ? '…' : mode === 'in' ? 'Sign in' : 'Agree and create account'}
          </button>

          <span style={{ fontSize: 12.5, color: muted, textAlign: 'center' }}>
            {mode === 'in'
              ? <>No account yet? <button onClick={() => setMode('up')} style={linkBtn}>Create one</button> — free, export straight away.</>
              : <>Already have an account? <button onClick={() => setMode('in')} style={linkBtn}>Sign in</button></>}
          </span>
        </div>
      </div>
    </div>
  )
}

const linkBtn: React.CSSProperties = { border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--color-accent-700)', fontSize: 12.5, fontWeight: 600, padding: 0 }
