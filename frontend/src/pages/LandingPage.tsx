import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import * as d3 from 'd3'
import { feature } from 'topojson-client'
import { getPublicCoverage } from '../api/public'
import './landing.css'

/**
 * Public landing page — the front door, no auth. Recreated from
 * design_handoff/Landing.html. The page composes its own headline from the
 * published dataset (self-writing copy, see headlineFor); nothing here needs
 * editing when councils are added. Data comes from GET /api/public/coverage
 * (falls back to the built-in SAMPLE when the backend has nothing published),
 * boundaries from /data/lga2025.topo.json.
 *
 * The prototype's markup and imperative d3/DOM logic are ported near-verbatim:
 * the JSX below is the design's HTML, and the effect runs its script scoped to
 * the root ref instead of `document`. Kept imperative on purpose — a faithful
 * port beats a rewrite for a self-contained page like this.
 */

// prettier-ignore
const PAGE_HTML = `
  <div class="nav2" style="display:flex;align-items:center;gap:24px;padding:20px 56px">
    <span class="brand" data-nav="home" style="font-family:var(--font-heading);font-size:21px;line-height:1">SDG Alignment Analyser</span>
    <span class="navlink" data-nav="browse">The dataset</span>
    <span class="navlink" data-nav="howitworks">How it works</span>
    <div style="margin-left:auto;display:flex;align-items:center;gap:12px">
      <button class="btn btn-ghost" style="border-radius:999px" data-nav="login">Sign in</button>
      <button class="btn btn-primary" style="border-radius:999px" data-nav="upload">Upload a report</button>
    </div>
  </div>

  <!-- ── Above the fold: finding left, dataset right ── -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:52px;padding:26px 56px 44px;align-items:start">
    <div style="display:flex;flex-direction:column;gap:18px">
      <span style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--color-accent-700)" data-stat="kicker">Australian council annual reports</span>
      <h1 style="margin:0;font-size:38px;line-height:1.07;text-wrap:pretty" data-stat="headline">Two activities in every five describe the same Goal.</h1>

      <div style="display:flex;flex-direction:column;margin-top:6px">
        <div style="display:flex;align-items:baseline;gap:16px;padding:10px 0;border-top:1px solid color-mix(in srgb, var(--color-text) 13%, transparent)">
          <span style="font-family:var(--font-heading);font-size:30px;line-height:1;width:84px;flex:0 0 auto" data-stat="goal11">&mdash;</span>
          <div style="display:flex;flex-direction:column;gap:3px">
            <span style="font-size:14px;font-weight:600;line-height:1.4" data-stat="goal11label">share of activities on the leading Goal</span>
            <span style="font-size:12.5px;line-height:1.5;color:color-mix(in srgb, var(--color-text) 60%, transparent)" data-stat="goal11note">Computed from the published dataset.</span>
          </div>
        </div>
        <div style="display:flex;align-items:baseline;gap:16px;padding:10px 0;border-top:1px solid color-mix(in srgb, var(--color-text) 13%, transparent)">
          <span style="font-family:var(--font-heading);font-size:30px;line-height:1;width:84px;flex:0 0 auto" data-stat="goal14">&mdash;</span>
          <div style="display:flex;flex-direction:column;gap:3px">
            <span style="font-size:14px;font-weight:600;line-height:1.4" data-stat="goal14label">the least-evidenced Goals</span>
            <span style="font-size:12.5px;line-height:1.5;color:color-mix(in srgb, var(--color-text) 60%, transparent)" data-stat="goal14note">Computed from the published dataset.</span>
          </div>
        </div>
        <div style="display:flex;align-items:baseline;gap:16px;padding:10px 0;border-top:1px solid color-mix(in srgb, var(--color-text) 13%, transparent);border-bottom:1px solid color-mix(in srgb, var(--color-text) 13%, transparent)">
          <span style="font-family:var(--font-heading);font-size:30px;line-height:1;width:84px;flex:0 0 auto;color:var(--color-accent-700)" data-stat="median">&mdash;</span>
          <div style="display:flex;flex-direction:column;gap:3px">
            <span style="font-size:14px;font-weight:600;line-height:1.4">Goals evidenced by the median council</span>
            <span style="font-size:12.5px;line-height:1.5;color:color-mix(in srgb, var(--color-text) 60%, transparent)" data-stat="mediannote">Computed from the published dataset.</span>
          </div>
        </div>
      </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="searchwrap" data-search>
        <input class="input" placeholder="Find your council" style="width:100%;border-radius:999px;font-size:15px;padding:14px 20px" data-input>
        <div class="results" data-results></div>
      </div>
      <div style="border-radius:30px;background:var(--color-surface);box-shadow:var(--shadow-sm);padding:10px" data-map></div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <span style="font-size:12.5px;color:color-mix(in srgb, var(--color-text) 58%, transparent)" data-maphint>Shaded by Goals evidenced in the council's most recent report.</span>
        <button class="chip" style="padding:6px 13px;font-size:12px" data-mapreset>Reset view</button>
        <div style="margin-left:auto;display:flex;align-items:center;gap:8px">
          <span style="font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:color-mix(in srgb, var(--color-text) 50%, transparent)">few</span>
          <div style="display:flex;gap:3px" data-legend></div>
          <span style="font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:color-mix(in srgb, var(--color-text) 50%, transparent)">many</span>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <div style="display:flex;gap:6px" data-years></div>
        <div style="display:flex;flex-wrap:wrap;gap:6px" data-states></div>
      </div>
    </div>
  </div>

  <!-- ── Below the fold ── -->
  <p id="findings" style="margin:0;padding:4px 56px 30px;max-width:860px;font-size:18px;line-height:1.6;color:color-mix(in srgb, var(--color-text) 74%, transparent);text-wrap:pretty;scroll-margin-top:80px" data-stat="lead">The findings below are computed from every report analysed.</p>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:52px;padding:8px 56px 48px;align-items:start">
    <div style="display:flex;flex-direction:column;gap:22px">
      <div style="display:flex;flex-direction:column;gap:12px">
        <h2 style="margin:0;font-size:24px">Compare like with like</h2>
        <p style="margin:0;font-size:15px;line-height:1.6;color:color-mix(in srgb, var(--color-text) 68%, transparent);text-wrap:pretty" data-stat="findblurb">Published analysis, with the passage behind every match. No account needed.</p>
        <div style="display:flex;flex-wrap:wrap;gap:7px" data-classes>
          <button class="chip" data-goto="">All councils</button>
        </div>
        <span style="font-size:12.5px;line-height:1.5;color:color-mix(in srgb, var(--color-text) 58%, transparent);text-wrap:pretty">You choose the peer group. Comparing a capital city with a rural shire on raw counts misleads, so we never rank councils for you.</span>
      </div>
      <span style="font-size:12px;line-height:1.5;color:color-mix(in srgb, var(--color-text) 52%, transparent)" data-mapsource></span>
    </div>

    <div style="display:flex;flex-direction:column;gap:20px">
      <div style="display:flex;flex-direction:column;gap:12px;padding:24px 28px;border-radius:28px;background:color-mix(in srgb, var(--color-text) 3.5%, transparent)">
        <span style="font-size:11px;letter-spacing:0.09em;text-transform:uppercase;color:color-mix(in srgb, var(--color-text) 52%, transparent)">Recently added</span>
        <div style="display:flex;align-items:baseline;gap:12px">
          <span style="font-family:var(--font-heading);font-size:20px">City of Melbourne</span>
          <span style="font-size:13px;color:color-mix(in srgb, var(--color-text) 58%, transparent)">2024&ndash;25</span>
        </div>
        <span style="font-size:14px;line-height:1.55;color:color-mix(in srgb, var(--color-text) 68%, transparent);text-wrap:pretty">176 activities described, 13 of 17 Goals evidenced. Half of everything reported is city-shaping work.</span>
        <a href="#" data-nav="login" style="font-size:14px;align-self:flex-start">Open the analysis</a>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;padding:28px 30px;border-radius:28px;background:var(--color-accent-100)">
        <h2 style="margin:0;font-size:24px;color:var(--color-accent-800)">Or add this year's report</h2>
        <p style="margin:0;font-size:14.5px;line-height:1.6;color:var(--color-accent-800);text-wrap:pretty">Council officers can upload a newly published annual report and see the analysis in minutes. Your result stays private until you choose to publish it.</p>
        <div style="display:flex;align-items:center;gap:14px;padding-top:2px;flex-wrap:wrap">
          <button class="btn btn-primary" style="border-radius:999px" data-nav="upload">Upload a report</button>
          <span style="font-size:13px;color:var(--color-accent-800)">Verified council accounts</span>
        </div>
      </div>
    </div>
  </div>

  <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;padding:22px 30px;margin:0 56px 56px;border-radius:28px;background:color-mix(in srgb, var(--color-text) 4%, transparent);font-size:12.5px;line-height:1.55;color:color-mix(in srgb, var(--color-text) 62%, transparent)">
    <span style="flex:1 1 520px;text-wrap:pretty">This analysis reads what council annual reports <strong>describe</strong>. A Goal with no evidence means the report did not describe qualifying work &mdash; not that the council did none.</span>
    <div style="display:flex;align-items:center;gap:20px;margin-left:auto;white-space:nowrap">
      <a href="#" data-nav="limits">About this analysis and its limits</a>
      <span style="color:color-mix(in srgb, var(--color-text) 45%, transparent)">Boundaries &copy; ABS, ASGS Ed. 3</span>
    </div>
  </div>
`

export function LandingPage() {
  const rootRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    // React StrictMode double-invokes this effect in dev. The map is built in an
    // async .then; without this guard both invocations race to draw/wipe the SVG
    // and rebind the year pills, leaving them wired to a detached SVG's repaint
    // (year clicks then re-shade nothing). Cancel the torn-down invocation.
    let cancelled = false
    const page = root.querySelector<HTMLDivElement>('.page')!
    const tip = root.querySelector<HTMLDivElement>('#tip')!

    // ── data (mirrors the built-in fallback SAMPLE from the prototype) ──
    // name, state, type, class, lat, lon, goals evidenced (latest), years available
    const C: [string, string, string, string, number, number, number, number][] = [
      ['City of Melbourne', 'VIC', 'City', 'Metro', -37.814, 144.963, 13, 3],
      ['City of Greater Bendigo', 'VIC', 'City', 'Regional', -36.758, 144.28, 4, 3],
      ['City of Sydney', 'NSW', 'City', 'Metro', -33.868, 151.209, 15, 3],
      ['Brisbane City', 'QLD', 'City', 'Metro', -27.47, 153.021, 14, 3],
      ['City of Perth', 'WA', 'City', 'Metro', -31.953, 115.857, 11, 3],
      ['City of Adelaide', 'SA', 'City', 'Metro', -34.928, 138.6, 12, 3],
      ['City of Hobart', 'TAS', 'City', 'Metro', -42.883, 147.331, 9, 3],
      ['City of Darwin', 'NT', 'City', 'Metro', -12.462, 130.842, 8, 2],
      ['Unincorporated ACT', 'ACT', 'Territory', 'Metro', -35.282, 149.128, 14, 3],
      ['City of Greater Geelong', 'VIC', 'City', 'Regional', -38.149, 144.361, 14, 3],
      ['City of Ballarat', 'VIC', 'City', 'Regional', -37.562, 143.85, 10, 3],
      ['City of Newcastle', 'NSW', 'City', 'Regional', -32.927, 151.776, 12, 3],
      ['Wollongong City', 'NSW', 'City', 'Regional', -34.424, 150.893, 11, 3],
      ['Cairns Regional', 'QLD', 'Regional', 'Regional', -16.92, 145.771, 9, 3],
      ['Townsville City', 'QLD', 'City', 'Regional', -19.259, 146.818, 10, 2],
      ['Toowoomba Regional', 'QLD', 'Regional', 'Regional', -27.56, 151.954, 8, 3],
      ['Gold Coast City', 'QLD', 'City', 'Metro', -28.002, 153.43, 13, 3],
      ['Sunshine Coast Regional', 'QLD', 'Regional', 'Regional', -26.65, 153.066, 12, 3],
      ['City of Launceston', 'TAS', 'City', 'Regional', -41.439, 147.139, 7, 3],
      ['Alice Springs Town', 'NT', 'Town', 'Rural', -23.698, 133.881, 5, 2],
      ['Shire of Broome', 'WA', 'Shire', 'Rural', -17.958, 122.236, 6, 2],
      ['City of Kalgoorlie-Boulder', 'WA', 'City', 'Rural', -30.749, 121.466, 5, 3],
      ['City of Bunbury', 'WA', 'City', 'Regional', -33.327, 115.641, 7, 3],
      ['Mildura Rural City', 'VIC', 'Rural City', 'Rural', -34.186, 142.158, 6, 3],
      ['Greater Shepparton City', 'VIC', 'City', 'Regional', -36.383, 145.398, 7, 3],
      ['Wagga Wagga City', 'NSW', 'City', 'Regional', -35.108, 147.369, 8, 3],
      ['Albury City', 'NSW', 'City', 'Regional', -36.081, 146.916, 7, 3],
      ['Dubbo Regional', 'NSW', 'Regional', 'Rural', -32.246, 148.601, 6, 2],
      ['Tamworth Regional', 'NSW', 'Regional', 'Rural', -31.09, 150.929, 6, 3],
      ['Coffs Harbour City', 'NSW', 'City', 'Regional', -30.296, 153.114, 8, 3],
      ['Port Macquarie-Hastings', 'NSW', 'Council', 'Regional', -31.431, 152.909, 7, 3],
      ['Rockhampton Regional', 'QLD', 'Regional', 'Regional', -23.378, 150.512, 7, 3],
      ['Mackay Regional', 'QLD', 'Regional', 'Regional', -21.144, 149.187, 6, 2],
      ['Bundaberg Regional', 'QLD', 'Regional', 'Regional', -24.866, 152.351, 7, 3],
      ['Whyalla City', 'SA', 'City', 'Rural', -33.033, 137.564, 4, 2],
      ['Mount Gambier City', 'SA', 'City', 'Regional', -37.829, 140.783, 6, 3],
      ['Port Lincoln City', 'SA', 'City', 'Rural', -34.726, 135.858, 4, 2],
      ['City of Greater Geraldton', 'WA', 'City', 'Rural', -28.775, 114.615, 6, 3],
      ['City of Karratha', 'WA', 'City', 'Rural', -20.736, 116.846, 5, 2],
      ['Devonport City', 'TAS', 'City', 'Regional', -41.181, 146.35, 6, 3],
      ['Burnie City', 'TAS', 'City', 'Regional', -41.052, 145.904, 5, 2],
      ['Katherine Town', 'NT', 'Town', 'Rural', -14.465, 132.263, 3, 1],
      ['Warrnambool City', 'VIC', 'City', 'Regional', -38.381, 142.487, 7, 3],
      ['Latrobe City', 'VIC', 'City', 'Regional', -38.194, 146.54, 8, 3],
      ['Horsham Rural City', 'VIC', 'Rural City', 'Rural', -36.712, 142.199, 5, 3],
      ['Orange City', 'NSW', 'City', 'Regional', -33.283, 149.101, 6, 3],
      ['Bathurst Regional', 'NSW', 'Regional', 'Regional', -33.42, 149.577, 6, 2],
      ['Griffith City', 'NSW', 'City', 'Rural', -34.288, 146.05, 5, 2],
      ['Broken Hill City', 'NSW', 'City', 'Rural', -31.96, 141.467, 3, 2],
      ['Shire of Esperance', 'WA', 'Shire', 'Rural', -33.861, 121.891, 4, 2],
      ['District Council of Ceduna', 'SA', 'District', 'Rural', -32.126, 133.674, 3, 1],
      ['Longreach Regional', 'QLD', 'Regional', 'Rural', -23.442, 144.251, 3, 2],
      ['Mount Isa City', 'QLD', 'City', 'Rural', -20.725, 139.492, 4, 2],
      ['Murweh Shire', 'QLD', 'Shire', 'Rural', -26.403, 146.242, 2, 1],
      ['Weipa Town', 'QLD', 'Town', 'Rural', -12.621, 141.879, 2, 1],
      ['Shire of Wyndham-East Kimberley', 'WA', 'Shire', 'Rural', -15.772, 128.739, 4, 2],
      ['Barkly Regional', 'NT', 'Regional', 'Rural', -19.648, 134.19, 3, 1],
      ['District Council of Coober Pedy', 'SA', 'District', 'Rural', -29.013, 134.754, 2, 1],
      ['Renmark Paringa', 'SA', 'Council', 'Rural', -34.174, 140.748, 4, 2],
      ['Swan Hill Rural City', 'VIC', 'Rural City', 'Rural', -35.338, 143.554, 5, 2],
      ['Wellington Shire', 'VIC', 'Shire', 'Rural', -38.106, 147.068, 6, 3],
      ['West Coast', 'TAS', 'Council', 'Rural', -42.081, 145.55, 3, 1],
    ]
    const STATES = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'NT', 'ACT']
    const ST: Record<string, string> = {
      'New South Wales': 'NSW', Victoria: 'VIC', Queensland: 'QLD', 'South Australia': 'SA',
      'Western Australia': 'WA', Tasmania: 'TAS', 'Northern Territory': 'NT',
      'Australian Capital Territory': 'ACT',
    }
    const W = 600, H = 430

    const norm = (s: string) => s.toLowerCase()
      .replace(/\((vic|tas|nsw|qld|wa|sa|nt|act)\.?\)/g, '')
      .replace(/\b(city of|shire of|district council of|regional council|city council|council|shire|city|regional|town|rural)\b/g, '')
      .replace(/[^a-z]/g, '')

    type Rec = {
      code?: string; lga_code: string | null; name: string; state: string | null; type?: string; class?: string
      lat?: number | null; lon?: number | null; goals_evidenced: number | null
      years_available: number; by_year?: Record<string, { goals_evidenced: number; goals?: number[] }>
      postcodes?: (string | number)[]
    }
    const goCouncil = (d: Rec | null | undefined) => { if (d?.code) navigate('/council/' + d.code) }
    const SAMPLE: Rec[] = C.map((c) => ({
      lga_code: null, name: c[0], state: c[1], type: c[2], class: c[3],
      lat: c[4], lon: c[5], goals_evidenced: c[6], years_available: c[7],
    }))

    let DATA: Rec[] = SAMPLE
    let YEARS: number[] = []
    let YEAR: number | null = null
    let LIVE = false
    let byCode = new Map<string, Rec>(), byName = new Map<string, Rec>()

    function indexData() {
      byCode = new Map(); byName = new Map()
      DATA.forEach((d) => {
        if (d.lga_code) byCode.set(String(d.lga_code), d)
        byName.set(norm(d.name) + '|' + d.state, d)
      })
    }
    function goalsOf(d: Rec | undefined | null): number | null {
      if (!d) return null
      if (YEAR && d.by_year) return d.by_year[YEAR] ? d.by_year[YEAR].goals_evidenced : null
      // No year selected = every analysed year combined: a Goal counts if any
      // report evidenced it. Councils with more reports have more chances, so
      // this view is for coverage, not for comparing councils.
      if (d.by_year) {
        const u = new Set<number>()
        Object.values(d.by_year).forEach((r) => (r.goals || []).forEach((g) => u.add(g)))
        if (u.size) return u.size
      }
      return d.goals_evidenced != null ? d.goals_evidenced : null
    }
    function yearsOf(d: Rec | undefined | null): number {
      if (!d) return 0
      if (d.by_year) return Object.keys(d.by_year).length
      return d.years_available || 0
    }
    function shade(g: number | null): string {
      // Unmatched LGAs at 13% (not 5%): with a partial dataset most of the
      // country is unmatched, and at 5% the map read as blank.
      if (g == null) return 'color-mix(in srgb, var(--color-text) 13%, transparent)'
      const t = Math.max(0, Math.min(1, (g - 2) / 13))
      return 'color-mix(in srgb, #FD9D24 ' + Math.round(20 + t * 80) + '%, var(--color-surface))'
    }
    function showTip(e: MouseEvent, html: string) {
      tip.innerHTML = html; tip.classList.add('on')
      tip.style.left = Math.min(e.clientX + 14, window.innerWidth - 260) + 'px'
      tip.style.top = (e.clientY - 12) + 'px'
    }
    const hideTip = () => tip.classList.remove('on')
    const fmt = (n: number | null) => (n == null ? '—' : n.toLocaleString())

    const GOAL_FULL: Record<number, string> = { 1: 'No Poverty', 2: 'Zero Hunger', 3: 'Good Health and Well-being', 4: 'Quality Education', 5: 'Gender Equality', 6: 'Clean Water and Sanitation', 7: 'Affordable and Clean Energy', 8: 'Decent Work and Economic Growth', 9: 'Industry, Innovation and Infrastructure', 10: 'Reduced Inequalities', 11: 'Sustainable Cities and Communities', 12: 'Responsible Consumption and Production', 13: 'Climate Action', 14: 'Life Below Water', 15: 'Life on Land', 16: 'Peace, Justice and Strong Institutions', 17: 'Partnerships for the Goals' }
    const GOAL_COLORS: Record<number, string> = { 1: '#E5243B', 2: '#DDA63A', 3: '#4C9F38', 4: '#C5192D', 5: '#FF3A21', 6: '#26BDE2', 7: '#FCC30B', 8: '#A21942', 9: '#FD6925', 10: '#DD1367', 11: '#FD9D24', 12: '#BF8B2E', 13: '#3F7E44', 14: '#0A97D9', 15: '#56C02B', 16: '#00689D', 17: '#19486A' }
    const set = (k: string, v: string | null, colour?: string) => {
      const el = page.querySelector<HTMLElement>('[data-stat="' + k + '"]')
      if (!el || v == null) return
      el.textContent = v
      if (colour) el.style.color = colour
    }

    // A sweeping claim about "Australian councils" is only honest once the
    // dataset is broad enough. Below NATIONAL_MIN_COUNCILS the same finding is
    // stated as an observation about the councils analysed, not about the country.
    const NATIONAL_MIN_COUNCILS = 40

    function headlineFor(share: number, goalNum: number, goalName: string, councilCount: number): string {
      const subject = goalNum === 11 ? 'cities' : goalName.toLowerCase()
      const national = (councilCount || 0) >= NATIONAL_MIN_COUNCILS
      if (!national) {
        // Provisional voice: describes the sample, never the country.
        if (share >= 0.45) return 'In one activity out of every two, the same Goal. Councils describe ' + subject + ' plainly, and everything else obliquely.'
        if (share >= 0.35) return 'In two activities out of every five, the same Goal. Councils describe ' + subject + ' plainly, and everything else obliquely.'
        if (share >= 0.25) return goalName + ' leads what these councils describe — one activity in every three.'
        return 'No single Goal dominates the councils analysed so far.'
      }
      if (share >= 0.6) return 'Three activities in every five describe the same Goal. Australian councils write about ' + subject + ' plainly, and everything else obliquely.'
      if (share >= 0.45) return 'One activity in every two describes the same Goal. Australian councils write about ' + subject + ' plainly, and everything else obliquely.'
      if (share >= 0.35) return 'Two activities in every five describe the same Goal. Australian councils write about ' + subject + ' plainly, and everything else obliquely.'
      if (share >= 0.25) return 'One activity in every three describes the same Goal — ' + goalName + ' leads what Australian councils describe.'
      if (share >= 0.15) return 'No single Goal dominates, though ' + goalName + ' leads what Australian councils describe.'
      return 'No single Goal dominates. Coverage is spread across the seventeen Goals.'
    }

    // "A", "A and B", "A, B and C" — never "A and B and C".
    const listWords = (items: string[]): string => {
      if (items.length === 0) return ''
      if (items.length === 1) return items[0]
      return items.slice(0, -1).join(', ') + ' and ' + items[items.length - 1]
    }
    function shareWords(share: number): string {
      if (share >= 0.62 && share <= 0.68) return 'close to two thirds'
      if (share >= 0.47 && share <= 0.53) return 'roughly half'
      if (share >= 0.38 && share <= 0.42) return 'two in every five'
      if (share >= 0.31 && share <= 0.36) return 'roughly a third'
      return Math.round(share * 100) + '%'
    }

    type National = { goal_shares?: Record<string, number>; median_goals_evidenced?: number; reports?: number; councils?: number }
    type Narrative = { headline?: string; lead?: string; cards?: { leading?: string; trailing?: string; median?: string } }

    function paintNational(n: National | null, councils: Rec[] | null, narrative?: Narrative) {
      if (!n && !councils) return
      n = n || {}
      const councilCount = (n as { councils?: number }).councils || (councils?.length ?? 0)
      const shares = n.goal_shares || null
      let top: [number, number] | null = null, bottom: [number, number] | null = null
      if (shares) {
        const entries = Object.entries(shares).map(([k, v]) => [+k, v] as [number, number]).sort((a, b) => b[1] - a[1])
        top = entries[0]; bottom = entries[entries.length - 1]
      }
      if (top) {
        set('goal11', Math.round(top[1] * 100) + '%', GOAL_COLORS[top[0]])
        set('goal11label', 'of described activities align to Goal ' + top[0] + ', ' + GOAL_FULL[top[0]])
        set('goal11note', 'Counted per activity. An activity may align to more than one Goal, so the seventeen shares do not sum to 100%.')
      }
      if (shares) {
        const zeros = Object.entries(shares).filter(([, v]) => v === 0).map(([k]) => +k)
        if (zeros.length) {
          set('goal14', String(zeros.length), GOAL_COLORS[zeros[0]])
          set('goal14label', zeros.length === 1 ? 'Goal reaches no described activity at all' : 'Goals reach no described activity at all')
          set('goal14note', listWords(zeros.map((z) => GOAL_FULL[z])) + ' — not absent from council work, absent from the language councils use to describe it.')
        } else if (bottom) {
          const pct = bottom[1] * 100
          set('goal14', (pct < 10 ? pct.toFixed(1) : Math.round(pct)) + '%', GOAL_COLORS[bottom[0]])
          set('goal14label', 'of described activities reach Goal ' + bottom[0] + ', ' + GOAL_FULL[bottom[0]])
          set('goal14note', 'The least-evidenced Goal nationally — rarely absent from council work, almost always absent from council language.')
        }
      }
      let median = n.median_goals_evidenced
      let lo: number | null = null, hi: number | null = null
      if (councils && councils.length) {
        const gs = councils.map((c) => c.goals_evidenced).filter((g): g is number => g != null).sort((a, b) => a - b)
        if (gs.length) {
          if (median == null) median = gs[Math.floor(gs.length / 2)]
          lo = gs[0]; hi = gs[gs.length - 1]
        }
      }
      if (median != null) {
        set('median', Number(median).toFixed(1))
        if (lo != null && hi != null) set('mediannote', 'Ranging from ' + lo + ' to ' + hi + ' — and how a report is written explains much of that spread.')
      }
      if (n.reports != null) {
        const span = YEARS.length ? ', ' + YEARS[0] + '–' + YEARS[YEARS.length - 1] : ''
        set('kicker', fmt(n.reports) + ' annual reports from ' + fmt(n.councils ?? null) + ' councils' + span)
      }
      if (narrative && narrative.headline) {
        set('headline', narrative.headline)
        if (narrative.lead) set('lead', narrative.lead)
        if (narrative.cards) {
          if (narrative.cards.leading) set('goal11note', narrative.cards.leading)
          if (narrative.cards.trailing) set('goal14note', narrative.cards.trailing)
          if (narrative.cards.median) set('mediannote', narrative.cards.median)
        }
        return
      }
      if (councilCount) {
        const yrs = YEARS.length
        set('findblurb',
          councilCount + (councilCount === 1 ? ' council' : ' councils') +
          (yrs ? ', ' + yrs + (yrs === 1 ? ' reporting year' : ' reporting years') : '') +
          ' analysed so far, with the passage behind every match. No account needed.')
      }
      if (top) {
        set('headline', headlineFor(top[1], top[0], GOAL_FULL[top[0]], councilCount))
        set('lead', (councilCount >= NATIONAL_MIN_COUNCILS ? 'Across the councils analysed so far, ' : 'Across the ' + councilCount + ' councils analysed so far, ') + shareWords(top[1]) + ' of the activities described in their annual reports align to Goal ' + top[0] + ', ' + GOAL_FULL[top[0]] + '. The work behind the other sixteen Goals is being done — it just isn’t being written down in language that credits it.')
      }
    }

    // ── search ──
    page.querySelectorAll<HTMLDivElement>('[data-search]').forEach((w) => {
      const input = w.querySelector<HTMLInputElement>('[data-input]')!
      const out = w.querySelector<HTMLDivElement>('[data-results]')!
      const render = (q: string) => {
        const hits = q.length < 2 ? [] : DATA.filter((d) =>
          d.name.toLowerCase().includes(q.toLowerCase()) ||
          (d.postcodes || []).some((p) => String(p).startsWith(q))).slice(0, 7)
        out.innerHTML = hits.map((d) => {
          const g = goalsOf(d)
          return '<div class="rrow" data-code="' + (d.code ?? '') + '"><span style="width:20px;height:20px;border-radius:999px;background:' + shade(g) + '"></span>' +
            '<span class="rname">' + d.name + '</span><span class="rmeta">' + d.state + ' · ' +
            (g == null ? 'no analysis' : g + '/17 Goals') + ' · ' + yearsOf(d) + ' yr</span></div>'
        }).join('')
        out.classList.toggle('on', hits.length > 0)
      }
      // Navigate on mousedown — the input's blur handler swallows a click.
      out.addEventListener('mousedown', (e) => {
        const row = (e.target as HTMLElement).closest<HTMLElement>('[data-code]')
        if (row?.dataset.code) navigate('/council/' + row.dataset.code)
      })
      input.addEventListener('input', () => render(input.value))
      input.addEventListener('focus', () => render(input.value))
      input.addEventListener('blur', () => setTimeout(() => out.classList.remove('on'), 160))
    })

    page.querySelectorAll<HTMLElement>('[data-states]').forEach((el) => {
      el.innerHTML = STATES.map((s) => '<button class="chip" data-goto="state=' + s + '">' + s + '</button>').join('')
    })
    // Setting chips are generated from the classes the data actually holds — the
    // same values Browse filters on — so a chip can never point at a value that
    // returns zero councils. Re-run after live data loads (sample classes differ).
    function paintClasses() {
      const cls = Array.from(new Set(DATA.map((d) => d.class).filter(Boolean))) as string[]
      page.querySelectorAll<HTMLElement>('[data-classes]').forEach((el) => {
        el.innerHTML = '<button class="chip" data-goto="">All councils</button>' +
          cls.sort().map((c) => '<button class="chip" data-goto="class=' + c + '">' + c + '</button>').join('')
      })
    }
    paintClasses()
    page.querySelectorAll<HTMLElement>('[data-legend]').forEach((el) => {
      el.innerHTML = [2, 5, 8, 11, 14, 17].map((g) =>
        '<span style="width:18px;height:18px;border-radius:999px;background:' + shade(g) + '"></span>').join('')
    })

    function mapHint() {
      const el = page.querySelector<HTMLElement>('[data-maphint]')
      if (!el) return
      el.textContent = YEAR
        ? "Goals evidenced in each council's " + YEAR + ' report.'
        : 'Goals evidenced in any report from ' + (YEARS[0] || '') + ' to ' + (YEARS[YEARS.length - 1] || '') +
          ' — councils with more reports have more chances to evidence one.'
    }

    function paintYears() {
      const el = page.querySelector<HTMLElement>('[data-years]')
      if (!el) return
      if (!YEARS.length) { (el.parentElement as HTMLElement).style.display = 'none'; return }
      ;(el.parentElement as HTMLElement).style.display = 'flex'
      el.innerHTML = YEARS.map((y) => '<button class="chip' + (y === YEAR ? ' on' : '') + '" data-year="' + y + '">' + y + '</button>').join('') +
        '<button class="chip' + (YEAR === null ? ' on' : '') + '" data-year="">All years</button>'
      el.querySelectorAll<HTMLButtonElement>('[data-year]').forEach((b) => b.addEventListener('click', () => {
        YEAR = b.dataset.year ? +b.dataset.year : null
        paintYears(); mapHint(); repaint()
      }))
    }

    // ── map ──
    const host = page.querySelector<HTMLDivElement>('[data-map]')!
    host.innerHTML = ''
    const svg = d3.select(host).append('svg')
      .attr('viewBox', '0 0 ' + W + ' ' + H)
      .style('display', 'block').style('width', '100%').style('height', 'auto')
    let repaint: () => void = () => {}

    // Pan + zoom. Strokes divide by the scale so borders stay hairline when
    // zoomed in; double-click or the Reset button returns to the full country.
    function attachZoom(layer: any, strokeAt1: number) {
      const z = d3.zoom<SVGSVGElement, unknown>().scaleExtent([1, 12])
        .translateExtent([[0, 0], [W, H]]).extent([[0, 0], [W, H]])
        .on('zoom', (e: any) => {
          layer.attr('transform', e.transform)
          if (strokeAt1) layer.selectAll('path,circle').attr('stroke-width', strokeAt1 / e.transform.k)
          hideTip()
        })
      svg.style('cursor', 'grab').call(z as any).on('dblclick.zoom', null)
        .on('dblclick', () => svg.transition().duration(400).call(z.transform as any, d3.zoomIdentity))
      const reset = page.querySelector<HTMLButtonElement>('[data-mapreset]')
      if (reset) reset.onclick = () => svg.transition().duration(400).call(z.transform as any, d3.zoomIdentity)
    }

    Promise.all([
      getPublicCoverage().catch(() => null),
      fetch('/data/lga2025.topo.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]).then(([cov, topo]) => {
      if (cancelled) return
      if (cov && Array.isArray(cov.councils) && cov.councils.length) {
        DATA = cov.councils as unknown as Rec[]; LIVE = true
        YEARS = (cov.years || []).slice().sort()
        paintNational(cov.national, DATA, cov.narrative)
      }
      indexData()
      paintYears(); mapHint(); paintClasses()
      if (topo && topo.objects) drawLGA(topo); else drawPoints()
    })

    function drawLGA(topo: any) {
      const key = Object.keys(topo.objects)[0]
      const feats = (feature(topo, topo.objects[key]) as any).features.filter((f: any) => {
        const st = (f.properties || {}).STE_NAME21 || (f.properties || {}).STATE_NAME_2021 || ''
        return !/other territories|outside australia/i.test(st)
      })
      const proj = d3.geoMercator().fitExtent([[10, 10], [W - 10, H - 10]], { type: 'FeatureCollection', features: feats })
      const path = d3.geoPath(proj)
      const nameOf = (p: any) => p.LGA_NAME21 || p.LGA_NAME_2025 || p.LGA_NAME_2024 || p.LGA_NAME_2023 || p.LGA_NAME_2021 || ''
      const codeOf = (p: any) => p.LGA_CODE21 || p.LGA_CODE_2025 || p.LGA_CODE_2024 || p.LGA_CODE_2021 || null
      const lookup = (p: any) => (codeOf(p) && byCode.get(String(codeOf(p)))) ||
        byName.get(norm(nameOf(p)) + '|' + (ST[p.STE_NAME21 || p.STATE_NAME_2021] || ''))

      const layer = svg.append('g')
      const shapes = layer.selectAll('path').data(feats).join('path')
        .attr('class', 'lga').attr('d', path as any)
        .attr('stroke', 'var(--color-surface)').attr('stroke-width', 0.35)
        .on('mousemove', (e: MouseEvent, d: any) => {
          const g = goalsOf(lookup(d.properties))
          showTip(e, '<strong>' + nameOf(d.properties) + '</strong><br>' +
            (g == null ? (LIVE ? 'No report analysed' + (YEAR ? ' for ' + YEAR : '') : 'Not in this sample') : g + ' of 17 Goals evidenced'))
        })
        .on('mouseleave', hideTip)
        .on('click', (_e: MouseEvent, d: any) => goCouncil(lookup(d.properties)))
        .style('cursor', (d: any) => (lookup(d.properties)?.code ? 'pointer' : 'default'))

      repaint = () => shapes.attr('fill', (d: any) => shade(goalsOf(lookup(d.properties))))
      repaint()
      attachZoom(layer, 0.35)

      const matched = feats.filter((f: any) => lookup(f.properties)).length
      page.querySelector('[data-mapsource]')!.textContent =
        'Local Government Areas, ASGS Edition 3 (ABS), simplified for the web. ' +
        (LIVE ? matched + ' of ' + feats.length + ' LGAs have an analysed report'
          : 'Showing a sample of ' + matched + ' councils — publish the coverage feed to fill every LGA') + '.'
    }

    function drawPoints() {
      d3.json<any>('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json').then((topo) => {
        const aus = (feature(topo, topo.objects.countries) as any).features.find((f: any) => f.properties.name === 'Australia')
        const proj = d3.geoMercator().fitExtent([[16, 16], [W - 16, H - 16]], aus)
        const layer = svg.append('g')
        layer.append('path').datum(aus).attr('d', d3.geoPath(proj) as any)
          .attr('fill', 'color-mix(in srgb, var(--color-text) 6%, transparent)')
          .attr('stroke', 'color-mix(in srgb, var(--color-text) 20%, transparent)').attr('stroke-width', 1)

        const pts = DATA.filter((d) => d.lat != null && d.lon != null)
        const dots = layer.append('g').selectAll('circle').data(pts).join('circle')
          .attr('class', 'dot')
          .attr('cx', (d) => proj([d.lon!, d.lat!])![0]).attr('cy', (d) => proj([d.lon!, d.lat!])![1])
          .attr('r', (d) => 5 + (yearsOf(d) - 1) * 2.2)
          .attr('stroke', 'var(--color-surface)').attr('stroke-width', 1.2)
          .on('mousemove', (e: MouseEvent, d: Rec) => showTip(e, '<strong>' + d.name + '</strong><br>' +
            (goalsOf(d) == null ? 'No report analysed' : goalsOf(d) + ' of 17 Goals evidenced') + ' · ' + yearsOf(d) + ' years'))
          .on('mouseleave', hideTip)

        repaint = () => dots.attr('fill', (d) => shade(goalsOf(d)))
        repaint()
        attachZoom(layer, 1.2)

        page.querySelector('[data-maphint]')!.textContent =
          'One point per analysed council, shaded by Goals evidenced and sized by years available.'
        page.querySelector('[data-mapsource]')!.textContent =
          'Add data/lga2025.topo.json (ABS Local Government Areas) to render every LGA boundary.'
      }).catch(() => {
        host.innerHTML = '<div style="padding:80px 30px;text-align:center;font-size:14px;color:color-mix(in srgb, var(--color-text) 55%, transparent)">Map geometry could not be loaded.</div>'
      })
    }

    // A chip that changes WHICH councils you're looking at goes to Browse.
    const onGoto = (e: Event) => {
      const g = (e.target as HTMLElement).closest<HTMLElement>('[data-goto]')
      if (!g) return
      const query = g.dataset.goto
      navigate('/councils' + (query ? '?' + query : ''))
    }
    page.addEventListener('click', onGoto)

    // ── in-app navigation for the design's buttons/links ──
    const onNav = (e: Event) => {
      const t = (e.target as HTMLElement).closest<HTMLElement>('[data-nav]')
      if (!t) return
      const nav = t.dataset.nav
      if (nav === 'find') {
        e.preventDefault()
        page.querySelector<HTMLInputElement>('[data-input]')?.focus()
      } else if (nav === 'howitworks') {
        e.preventDefault(); navigate('/how-it-works')
      } else if (nav === 'browse') {
        e.preventDefault(); navigate('/councils')
      } else if (nav === 'upload') {
        e.preventDefault(); navigate('/upload')
      } else if (nav === 'login') {
        e.preventDefault(); navigate('/access')
      } else if (nav === 'limits') {
        e.preventDefault(); navigate('/limitations')
      }
    }
    page.addEventListener('click', onNav)

    return () => {
      cancelled = true
      page.removeEventListener('click', onNav)
      page.removeEventListener('click', onGoto)
    }
  }, [navigate])

  return (
    <div className="landing" ref={rootRef}>
      <div className="page" dangerouslySetInnerHTML={{ __html: PAGE_HTML }} />
      <div className="landing-tip" id="tip" />
    </div>
  )
}
