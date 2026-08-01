"""PDF export — the two document types the Export screen offers (design_handoff
screen 9): a published *statement* that reads like a page of the council's own
report, and an evidence *ledger* of all 17 Goals ranked by aligned-activity
count. Both are generated server-side with reportlab.

Numbers are computed to match the on-screen Results views exactly (see
frontend/src/lib/results.ts): a Goal's count is round(coverage[n] * total), the
leading Goal is the one with the highest coverage share, and coverage bands use
the same 5 / 15 thresholds. Colours are the UN Goal palette used in the UI.
"""

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.config.sdg_definitions import SDG_DEFINITIONS

# — organic palette (index.css) —
BG = colors.HexColor("#f5ead8")
SURFACE = colors.HexColor("#ebddc5")
TEXT = colors.HexColor("#201e1d")
ACCENT = colors.HexColor("#c67139")
ACCENT_700 = colors.HexColor("#8c491a")
ACCENT_800 = colors.HexColor("#643312")
ACCENT_100 = colors.HexColor("#fff2eb")
ACCENT2_700 = colors.HexColor("#56633f")
MUTED = colors.HexColor("#6b6a66")

# — UN Goal palette (frontend/src/constants/sdg-colors.ts) —
GOAL_COLORS = {
    1: "#E5243B", 2: "#DDA63A", 3: "#4C9F38", 4: "#C5192D", 5: "#FF3A21",
    6: "#26BDE2", 7: "#FCC30B", 8: "#A21942", 9: "#FD6925", 10: "#DD1367",
    11: "#FD9D24", 12: "#BF8B2E", 13: "#3F7E44", 14: "#0A97D9", 15: "#56C02B",
    16: "#00689D", 17: "#19486A",
}


def _goal_color(n: int) -> colors.Color:
    return colors.HexColor(GOAL_COLORS.get(n, "#6b7280"))


def _goal_name(n: int) -> str:
    return SDG_DEFINITIONS[n]["name"]


def _blend(a: colors.Color, pct: float, b: colors.Color) -> colors.Color:
    """color-mix(in srgb, a pct%, b) — linear RGB blend, pct in [0,1]."""
    return colors.Color(
        a.red * pct + b.red * (1 - pct),
        a.green * pct + b.green * (1 - pct),
        a.blue * pct + b.blue * (1 - pct),
    )


def _band(count: int) -> str:
    if count == 0:
        return "Not evidenced"
    if count < 5:
        return "Isolated"
    if count < 15:
        return "Emerging"
    return "Substantial"


# ── shared data prep (mirrors lib/results.ts) ──


def _summary(results: dict[str, Any]) -> dict[str, Any]:
    return results.get("report_alignment", {}) or {}


def _count(summary: dict, n: int) -> int:
    frac = (summary.get("coverage") or {}).get(n, (summary.get("coverage") or {}).get(str(n), 0)) or 0
    return round(float(frac) * int(summary.get("total_activities", 0)))


def _mean(summary: dict, n: int) -> float:
    ms = summary.get("mean_scores") or {}
    return float(ms.get(n, ms.get(str(n), 0)) or 0)


def _ledger(summary: dict) -> list[dict]:
    rows = [
        {"sdg": n, "name": _goal_name(n), "count": _count(summary, n), "mean": _mean(summary, n)}
        for n in range(1, 18)
    ]
    rows.sort(key=lambda r: (-r["count"], -r["mean"]))
    return rows


def _goals_evidenced(summary: dict) -> int:
    return sum(1 for n in range(1, 18) if _count(summary, n) > 0)


def _leading_goal(summary: dict) -> tuple[int, float] | None:
    cov = summary.get("coverage") or {}
    best, best_frac = -1, -1.0
    for n in range(1, 18):
        frac = float(cov.get(n, cov.get(str(n), 0)) or 0)
        if frac > best_frac:
            best, best_frac = n, frac
    return (best, best_frac) if best > 0 and best_frac > 0 else None


def _strongest_passage(results: dict, sdg: int) -> str:
    best_text, best_score = "", -1.0
    for a in results.get("activities", []):
        sc = a.get("sdg_scores", {})
        cell = sc.get(sdg, sc.get(str(sdg), {})) or {}
        if cell.get("is_aligned") and float(cell.get("score", 0)) > best_score:
            best_score, best_text = float(cell.get("score", 0)), a.get("activity_text", "")
    return best_text


def _identity(council: str | None, state: str | None, year: int | None, filename: str) -> tuple[str, str]:
    name = council or filename.rsplit(".", 1)[0].replace("_alignment", "").replace("_", " ").strip() or "Council report"
    bits = [b for b in [state, f"{year} annual report" if year else None] if b]
    return name, " · ".join(bits)


# ── flowables ──


class Bar(Flowable):
    """A single proportional horizontal bar for a ledger row."""

    def __init__(self, pct: float, color: colors.Color, width: float, height: float = 7):
        super().__init__()
        self.pct, self.color, self.width, self.height = pct, color, width, height

    def draw(self):
        c = self.canv
        c.setFillColor(_blend(TEXT, 0.06, BG))
        c.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
        w = max(self.height, self.width * self.pct)
        c.setFillColor(self.color)
        c.roundRect(0, 0, w, self.height, self.height / 2, stroke=0, fill=1)


def _chip(n: int, styles) -> Table:
    """Small colored square carrying the two-digit Goal number, white text."""
    t = Table([[Paragraph(f"{n:02d}", styles["chip"])]], colWidths=[9 * mm], rowHeights=[9 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _goal_color(n)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=8.5, textColor=ACCENT_700, leading=11, spaceAfter=6),
        "kicker2": ParagraphStyle("kicker2", fontName="Helvetica-Bold", fontSize=8.5, textColor=ACCENT2_700, leading=11, spaceAfter=6),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=26, textColor=TEXT, leading=29, spaceAfter=10),
        "council": ParagraphStyle("council", fontName="Helvetica-Bold", fontSize=22, textColor=TEXT, leading=25),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=10.5, textColor=MUTED, leading=15, spaceAfter=4),
        "lead": ParagraphStyle("lead", fontName="Helvetica", fontSize=12, textColor=TEXT, leading=18, spaceAfter=14, alignment=TA_LEFT),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=13, textColor=TEXT, leading=17, spaceBefore=6, spaceAfter=8),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=10, textColor=TEXT, leading=13),
        "cellName": ParagraphStyle("cellName", fontName="Helvetica-Bold", fontSize=10, textColor=TEXT, leading=13),
        "cellR": ParagraphStyle("cellR", fontName="Helvetica", fontSize=10, textColor=MUTED, leading=13, alignment=2),
        "chip": ParagraphStyle("chip", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, leading=10, alignment=1),
        "quote": ParagraphStyle("quote", fontName="Helvetica", fontSize=10.5, textColor=TEXT, leading=15),
        "mos": ParagraphStyle("mos", fontName="Helvetica-Bold", fontSize=7.5, textColor=TEXT, leading=9),
        "mosCount": ParagraphStyle("mosCount", fontName="Helvetica-Bold", fontSize=13, textColor=TEXT, leading=14),
        "absent": ParagraphStyle("absent", fontName="Helvetica", fontSize=10, textColor=ACCENT_800, leading=15),
        "foot": ParagraphStyle("foot", fontName="Helvetica", fontSize=8, textColor=MUTED, leading=11),
    }


def _doc(buf: io.BytesIO) -> BaseDocTemplate:
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")

    def _bg(canvas, _doc):
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_bg)])
    return doc


_CAVEAT = (
    "Analysis reads the published annual report only. A Goal with no evidence means the "
    "report did not describe qualifying work — not that the council did none."
)


# ── documents ──


def generate_ledger_pdf(results: dict[str, Any], council=None, state=None, year=None, filename="report") -> io.BytesIO:
    buf = io.BytesIO()
    doc = _doc(buf)
    st = _styles()
    s = _summary(results)
    name, sub = _identity(council, state, year, filename)
    total = int(s.get("total_activities", 0))
    evid = _goals_evidenced(s)
    mean = float(s.get("mean_alignment_score", 0) or 0)
    ledger = _ledger(s)
    max_count = max(1, *[r["count"] for r in ledger])

    story: list = [
        Paragraph("Evidence ledger", st["kicker"]),
        Paragraph(name, st["council"]),
        Paragraph(sub, st["sub"]),
        Paragraph(f"{total} activities described · {evid} of 17 Goals evidenced · mean alignment {mean:.3f}", st["sub"]),
        Spacer(1, 10),
    ]

    bar_w = doc.width - (9 * mm + 60 * mm + 22 * mm + 26 * mm) - 8 * mm
    data = [[
        Paragraph("", st["cell"]), Paragraph("Goal", st["cellName"]),
        Paragraph("", st["cell"]), Paragraph("Activities", st["cellR"]),
        Paragraph("Band", st["cellR"]),
    ]]
    for r in ledger:
        pct = 0 if r["count"] == 0 else max(0.02, r["count"] / max_count)
        data.append([
            _chip(r["sdg"], st),
            Paragraph(r["name"], st["cellName"]),
            Bar(pct, _goal_color(r["sdg"]), bar_w) if r["count"] else Paragraph("", st["cell"]),
            Paragraph(str(r["count"]) if r["count"] else "—", st["cellR"]),
            Paragraph(_band(r["count"]), st["cellR"]),
        ])

    tbl = Table(data, colWidths=[9 * mm, 60 * mm, bar_w, 22 * mm, 26 * mm], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, _blend(TEXT, 0.2, BG)),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, _blend(TEXT, 0.08, BG)),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
    ]))
    story.append(tbl)
    story += [Spacer(1, 14), Paragraph(_CAVEAT, st["foot"]),
              Paragraph("Boundaries and coverage © the analysing tool. Counts are activities whose language aligns to each Goal.", st["foot"])]

    doc.build(story)
    buf.seek(0)
    return buf


def generate_statement_pdf(results: dict[str, Any], council=None, state=None, year=None, filename="report") -> io.BytesIO:
    buf = io.BytesIO()
    doc = _doc(buf)
    st = _styles()
    s = _summary(results)
    name, sub = _identity(council, state, year, filename)
    total = int(s.get("total_activities", 0))
    evid = _goals_evidenced(s)
    ledger = _ledger(s)
    max_count = max(1, *[r["count"] for r in ledger])
    lead = _leading_goal(s)

    if lead:
        lead_txt = (f"Of the {total} activities described in this report, {evid} of the 17 Goals carry "
                    f"evidence. {_goal_name(lead[0])} accounts for the largest share, at {round(lead[1] * 100)}%.")
    else:
        lead_txt = f"This report describes {total} activities across {evid} of the 17 Goals."

    story: list = [
        Paragraph(sub or name, st["kicker2"]),
        Paragraph("Where our work met the Goals", st["h1"]),
        Paragraph(lead_txt, st["lead"]),
        Paragraph("EVERY GOAL, SIZED BY THE WORK BEHIND IT", st["kicker"]),
        Spacer(1, 4),
    ]

    # Mosaic: 4-wide grid, cells tinted by count (matches the on-screen mosaic).
    cells = []
    for r in sorted(ledger, key=lambda x: x["sdg"]):
        pct = (15 + (r["count"] / max_count) * 55) / 100
        inner = Table(
            [[Paragraph(f"{r['sdg']:02d}  {r['name']}", st["mos"])],
             [Paragraph(str(r["count"]) if r["count"] else "—", st["mosCount"])]],
            colWidths=[(doc.width - 3 * 4 * mm) / 4 - 6],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _blend(_goal_color(r["sdg"]), pct, SURFACE)),
            ("BOX", (0, 0), (-1, -1), 0.5, _blend(_goal_color(r["sdg"]), 0.4, BG)),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        cells.append(inner)
    grid_rows = [cells[i:i + 4] for i in range(0, len(cells), 4)]
    grid_rows[-1] += [""] * (4 - len(grid_rows[-1]))
    col_w = (doc.width) / 4
    mosaic = Table(grid_rows, colWidths=[col_w] * 4)
    mosaic.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [mosaic, Spacer(1, 16)]

    # Highlights: strongest passage of the top three evidenced goals.
    story.append(Paragraph("What the year evidenced", st["h3"]))
    highlights = [r for r in ledger if r["count"] > 0][:3]
    for r in highlights:
        quote = _strongest_passage(results, r["sdg"])
        if not quote:
            continue
        body = [
            Paragraph(r["name"].upper(), ParagraphStyle("hl", parent=st["kicker"], textColor=_goal_color(r["sdg"]))),
            Paragraph(quote, st["quote"]),
        ]
        hl = Table([[body]], colWidths=[doc.width])
        hl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBEFORE", (0, 0), (0, -1), 3, _goal_color(r["sdg"])),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(KeepTogether(hl))

    # Absent panel.
    absent = [r for r in ledger if r["count"] == 0]
    if absent:
        lines = [Paragraph("Absent from this year’s account", st["h3"]),
                 Paragraph("These Goals appear in no described activity this year — the report did not "
                           "describe qualifying work, which is not the same as none being done.", st["absent"]),
                 Spacer(1, 6)]
        for r in absent[:6]:
            lines.append(Paragraph(f"{r['sdg']:02d}  {r['name']}", st["absent"]))
        if len(absent) > 6:
            lines.append(Paragraph(f"and {len(absent) - 6} more", st["absent"]))
        panel = Table([[lines]], colWidths=[doc.width])
        panel.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ACCENT_100),
            ("LEFTPADDING", (0, 0), (-1, -1), 16), ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story += [Spacer(1, 6), panel]

    story += [Spacer(1, 14), Paragraph(_CAVEAT, st["foot"])]
    doc.build(story)
    buf.seek(0)
    return buf
