"""Biography chart: the whole life, year by year, as a U-shaped chart (after George and Gisela O'Neil's life chart).

The arrangement follows the life chart in George and Gisela O'Neil's *The Human Life* (ed. Florin Lowndes, Mercury Press
1990): years 1-21 run down the left arm, years 22-42 round the bottom, years 43-63 up the right arm, so that year k sits
beside year 64 - k, and years 64-84 run down the middle. Each year has four boxes for one's own notes:
Destiny & health, Interests & studies, People & family, Places & work. The chart is drawn afresh in the app's own style;
its wording is the app's own (data/biography_periods.csv), with Steiner's sayings tagged as his.

On top of the chart the app marks
  * the present year of life (a gold outline),
  * the planetary events of Sucher's prenatal graph at the age they stand for (conjunctions and stations), and
  * a dot in every box that has a note.

Notes belong to the user's own chart (the profile's birth) and are kept like the profile: on the computer in the
app's profile folder; online only while the app is open, unless "Remember me on this device" is ticked.
"""
from __future__ import annotations

import io
import math
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
import pandas as pd
import streamlit as st

from . import astrosophy_engine as E
from . import astrosophy_layer as L
from . import charts as C
import device
import user_profile as UP

HERE = os.path.dirname(os.path.abspath(__file__))
ASPECTS = UP.LIFE_ASPECTS          # (key, label) x 4
YEARS = 84
H = 3.0                            # height of one year on the arms
# the seven tints of a seven-year period (one per year), from the app's palette
TINTS = ["#e2789c", "#ef7d5c", "#e8c46a", "#8fbf7a", "#6fb7c9", "#7f95d8", "#c7a2e0"]
PRINT_THEME = dict(fig_bg="#ffffff", bg="#ffffff", face_alpha=1.0, panel="#ffffff", line="#6b5a63",
                   text="#1d1a1c", muted="#4a4448", gold="#9a6b00", flag="#2a6fb0", tint_alpha=0.42, dot="#1d1a1c",
                   ink_only=True)   # on paper, planet symbols and event markers in dark ink (pastels fade on white)
FS = (11, 7, 6)                    # title, labels, small


@st.cache_data(show_spinner=False)
def periods() -> pd.DataFrame:
    return pd.read_csv(os.path.join(HERE, "data", "biography_periods.csv"), encoding="utf-8-sig").fillna("")


def period_of(year: int) -> dict:
    P = periods()
    r = P[(P.first_year <= year) & (year <= P.last_year)]
    return r.iloc[0].to_dict() if len(r) else {}


def mirror(year: int):
    """The year that sits beside this one on the chart (year k beside 64 - k), or None after 63."""
    return 64 - year if 1 <= year <= 63 else None


def year_now(birth_utc, now_utc):
    """(year of life 1..84 or None, age in years)."""
    age = L.age_years(birth_utc, now_utc)
    return (int(age) + 1 if 0 <= age < YEARS else None), age


def calendar_years(birth_utc, year: int) -> str:
    y0 = birth_utc.year + year - 1
    return f"{y0}\u2013{str(y0 + 1)[-2:]}" if (birth_utc.month, birth_utc.day) != (1, 1) else f"{y0}"


# ------------------------------------------------------------------ geometry
# Across a year: u = 0 at the outer edge; four boxes of 7 (Destiny, Interests, People, Places), the age strip 28-32,
# the event strip 32-35, then the text strip inside. Along a year: v = 0..1 in the direction of time.
def _pt(year: int, u: float, v: float):
    if year <= 21:                                    # left arm, downwards
        return u, -(year - 1 + v) * H
    if year <= 42:                                    # the bottom arc, from left to right
        th = math.pi - (year - 22 + v) * math.pi / 21
        r = 60.0 - u
        return 60.0 + r * math.cos(th), -63.0 - r * math.sin(th)
    if year <= 63:                                    # right arm, upwards
        return 120.0 - u, -(63 - year + (1 - v)) * H
    # the middle column, downwards: age strip 45-48, boxes 48-72 (4 x 6), event strip 72-75
    if u <= 28:
        x = 48.0 + u * 24.0 / 28.0
    elif u <= 32:
        x = 45.0 + (u - 28.0) * 0.75
    else:
        x = 72.0 + (u - 32.0)
    return x, -(year - 64 + v) * H


def _poly(year, u0, u1, n=None):
    n = n or (9 if 22 <= year <= 42 else 2)
    vs = [i / (n - 1) for i in range(n)]
    pts = [_pt(year, u0, v) for v in vs] + [_pt(year, u1, v) for v in reversed(vs)]
    return pts


def _box(c):
    return 7.0 * c, 7.0 * c + 7.0


# ------------------------------------------------------------------ drawing
def draw(birth_utc, now_utc=None, events=None, notes=None, theme=None, title="", sub="", compact=False):
    """The biography chart. theme: charts.py / theme.py keys (bg, panel, line, text, muted, gold, flag), or
    PRINT_THEME for the printable version. events: Sucher's prenatal events (age, event, bodies)."""
    th = {**C.THEME, "tint_alpha": 0.30, "dot": "#ffffff", **(theme or {})}
    fig = Figure(figsize=(7.2, 8.6) if compact else (9.0, 10.5), dpi=110)
    transparent = th["fig_bg"] == "none"
    fig.patch.set_facecolor(th["bg"] if transparent else th["fig_bg"])
    fig.patch.set_alpha(0 if transparent else 1)
    ax = fig.add_axes([0.02, 0.065, 0.96, 0.915])
    ax.set_xlim(-2, 122)
    ax.set_ylim(-126, 14)
    ax.set_aspect("equal")
    ax.set_axis_off()
    notes = notes or {}
    fs_l, fs_s = (FS[1] + 0.5, FS[2] + 0.5) if compact else (FS[1], FS[2])

    # the U's own dark face
    face = ([_pt(y, 0, 0) for y in range(1, 22)] + [_pt(y, 0, v / 8) for y in range(22, 43) for v in range(9)]
            + [_pt(y, 0, 1) for y in range(43, 64)] + [(120, 0), (0, 0)])
    ax.add_patch(Polygon(face, closed=True, fc=th["bg"], ec="none", alpha=th["face_alpha"], zorder=0))

    yn, age = year_now(birth_utc, now_utc) if now_utc is not None else (None, None)
    for year in range(1, YEARS + 1):
        tint = TINTS[(year - 1) % 7]
        for c in range(4):
            u0, u1 = _box(c)
            ax.add_patch(Polygon(_poly(year, u0, u1), closed=True, fc=tint, alpha=th["tint_alpha"], ec="none", zorder=1))
            ax.add_patch(Polygon(_poly(year, u0, u1), closed=True, fc="none", ec=th["line"], lw=0.25, zorder=2))
            if notes.get(str(year), {}).get(ASPECTS[c][0]):
                x, y = _pt(year, (u0 + u1) / 2, 0.5)
                ax.plot(x, y, "o", ms=2.6 if not compact else 3.2, color=th["dot"], zorder=4)
        ax.add_patch(Polygon(_poly(year, 28, 35), closed=True, fc="none", ec=th["line"], lw=0.25, zorder=2))
        x, y = _pt(year, 30, 0.5)
        ax.text(x, y, str(year), ha="center", va="center", fontsize=fs_s - 0.5, color=th["text"], zorder=3)

    # seven-year and 21-year boundaries
    for year in (8, 15, 22, 29, 36, 43, 50, 57, 64, 71, 78):
        lw = 1.3 if year in (22, 43, 64) else 0.8
        pts = [_pt(year, u, 0) for u in (0, 35)]
        ax.plot(*zip(*pts), color=th["line"], lw=lw, zorder=3)
    for year in (1, 64):
        pts = [_pt(year, u, 0) for u in (0, 35)]
        ax.plot(*zip(*pts), color=th["line"], lw=1.3, zorder=3)
    for edge in (0, 35):
        ax.plot(*zip(*([_pt(y, edge, v / 8) for y in range(1, 64) for v in range(9)])), color=th["line"], lw=1.1, zorder=3)
    ax.plot(*zip(*[_pt(84, u, 1) for u in (0, 35)]), color=th["line"], lw=1.3, zorder=3)
    for u in (0, 35):
        ax.plot(*zip(*[_pt(y, u, v) for y in range(64, 85) for v in (0, 1)]), color=th["line"], lw=1.1, zorder=3)

    # the present year
    if yn:
        ax.add_patch(Polygon(_poly(yn, 0, 35), closed=True, fc="none", ec=th["gold"], lw=1.8, zorder=6))
        x, y = _pt(yn, 38.5, 0.5) if yn <= 63 else (77.5, _pt(yn, 0, 0.5)[1])
        ax.text(x, y, "now", ha="center", va="center", fontsize=fs_s, color=th["gold"], fontweight="bold", zorder=6)

    # Sucher's prenatal events at the age they stand for
    if events is not None and len(events):
        ev = events[events.event.isin(["conjunction", "station"])]
        for _, r in ev.iterrows():
            a = float(r.age)
            if not (0 <= a < YEARS):
                continue
            year, v = int(a) + 1, a - int(a)
            x, y = _pt(year, 33.5, v)
            first = str(r.bodies).split(" ")[0]
            col = th["text"] if th.get("ink_only") else C.BODY_COLOUR.get(first, th["text"])
            if r.event == "conjunction":
                ax.plot(x, y, "D", ms=3.0, mfc=col, mec=th["bg"], mew=0.4, zorder=5)
            else:
                ax.plot(x, y, "v" if "retro" in str(r.bodies) else "^", ms=3.2, mfc="none", mec=col, mew=0.8, zorder=5)

    # period labels in the inner strips
    P = periods()
    for _, p in P.iterrows():
        a, b = int(p.first_year), int(p.last_year)
        if b <= 21 or a >= 43 and b <= 63:
            ys = [_pt(y, 40, 0.5)[1] for y in (a, b)]
            x = 40.0 if b <= 21 else 80.0
            yc = (ys[0] + ys[1]) / 2
            g = E.GLYPH.get(p.planet, "")
            cal = f"{birth_utc.year + a - 1}\u2013{birth_utc.year + b}"
            ax.text(x, yc + 6.2, g, ha="center", va="center", fontsize=FS[0] + 5,
                    color=th["text"] if th.get("ink_only") else C.BODY_COLOUR.get(p.planet, th["text"]))
            ax.text(x, yc + 2.0, f"Years {a}\u2013{b}", ha="center", va="center", fontsize=fs_s - (0.6 if compact else -0.4),
                    color=th["text"], fontweight="bold")
            ax.text(x, yc - 0.6, cal, ha="center", va="center", fontsize=fs_s, color=th["muted"])
            ax.text(x, yc - 4.6, "\n".join(textwrap.wrap(p.keyword, 13)), ha="center", va="center",
                    fontsize=fs_s, color=th["gold"], linespacing=1.15)
            ax.text(x, yc - 8.8, "\n".join(textwrap.wrap(p.member, 14)), ha="center", va="center",
                    fontsize=fs_s - 0.3, color=th["muted"], style="italic", linespacing=1.1)
    # the Sun years at the bottom, inside the arc
    ax.text(60, -67.5, E.GLYPH["Sun"], ha="center", va="center", fontsize=FS[0] + 6,
            color=th["text"] if th.get("ink_only") else C.BODY_COLOUR["Sun"])
    ax.text(60, -72.5, f"Years 22\u201342 \u00b7 {birth_utc.year + 21}\u2013{birth_utc.year + 42}", ha="center",
            va="center", fontsize=fs_l, color=th["text"], fontweight="bold")
    for k, (_, p) in enumerate(P[(P.first_year >= 22) & (P.last_year <= 42)].iterrows()):
        ax.text(60, -76.3 - 3.0 * k, f"{int(p.first_year)}\u2013{int(p.last_year)}  {p.member}", ha="center",
                va="center", fontsize=fs_s, color=th["muted"])
    # the middle column's heading, and the column headings above the arms
    ax.text(60, 6.0, "Years 64\u201384", ha="center", va="center", fontsize=fs_l, color=th["text"], fontweight="bold")
    ax.text(60, 3.0, "beyond the seven periods", ha="center", va="center", fontsize=fs_s, color=th["muted"])
    short = ["Destiny &\nhealth", "Interests\n& studies", "People &\nfamily", "Places &\nwork"]
    for c in range(4):
        u = 7.0 * c + 3.5
        for x in (u, 120.0 - u):
            ax.text(x, 2.6, short[c], ha="center", va="center", fontsize=fs_s - (2.2 if compact else 0.7),
                    color=th["muted"], linespacing=1.0)
    for x, lab in ((30, "Year"), (90, "Year")):
        ax.text(x, 2.6, lab, ha="center", va="center", fontsize=fs_s - 0.7, color=th["muted"])
    ax.text(0, 12.0, title or "Biography chart", ha="left", va="center", fontsize=FS[0] + 1, color=th["text"])
    if sub:
        ax.text(0, 8.8, sub, ha="left", va="center", fontsize=fs_s, color=th["muted"])

    # the key, under the chart
    handles = [Line2D([], [], color=th["gold"], lw=1.8, label="this year of life"),
               Line2D([], [], marker="o", ls="", ms=3.5, color=th["dot"], mec=th["line"], label="a note in this box"),
               Line2D([], [], marker="D", ls="", ms=4, mfc=th["text"], mec=th["bg"], label="conjunction (Sucher)"),
               Line2D([], [], marker="v", ls="", ms=4, mfc="none", mec=th["text"], label="turns retrograde"),
               Line2D([], [], marker="^", ls="", ms=4, mfc="none", mec=th["text"], label="turns direct")]
    fig.legend(handles=handles, loc="lower center", ncol=3 if compact else 5, frameon=False, fontsize=fs_s,
               labelcolor=th["text"], bbox_to_anchor=(0.5, 0.025))
    fig.text(0.5, 0.008, "Year k of life sits beside year 64 \u2212 k. Arrangement after George and Gisela O'Neil's life "
             "chart (The Human Life, ed. F. Lowndes, 1990); drawn afresh for this app. Event markers: the prenatal "
             "graph of W. Sucher at the age each event stands for.", ha="center", va="bottom", fontsize=fs_s - 1,
             color=th["muted"], wrap=True)
    return fig


def pdf_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", facecolor="#ffffff")
    return buf.getvalue()


# ------------------------------------------------------------------ notes as a table (CSV)
def notes_table(birth_utc, notes) -> pd.DataFrame:
    rows = []
    for year in range(1, YEARS + 1):
        n = notes.get(str(year), {})
        p = period_of(year)
        rows.append({"year of life": year, "calendar years": calendar_years(birth_utc, year),
                     "age": f"{year - 1}\u2013{year}", "period": p.get("keyword", ""),
                     **{lab: n.get(k, "") for k, lab in ASPECTS}})
    return pd.DataFrame(rows)


def read_notes_csv(data: bytes) -> dict:
    """Notes from a CSV saved by this app (or edited in Excel). Raises ValueError with a plain message."""
    try:
        df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        raise ValueError("That file could not be read as a table (CSV). Use the file from 'Download my notes'.")
    if "year of life" not in df.columns:
        raise ValueError("That table has no 'year of life' column. Use the file from 'Download my notes'.")
    out = {}
    for _, r in df.iterrows():
        try:
            year = int(float(r["year of life"]))
        except ValueError:
            continue
        out[str(year)] = {k: r.get(lab, "") for k, lab in ASPECTS}
    return UP._valid_life(out)


# ------------------------------------------------------------------ the tab
def show_tab(ch, ev, now_utc, mine, who, phone, wheel_theme):
    birth = ch["utc"]
    st.markdown("Your whole life at a glance, one band for each year. Years 1\u201321 run down the left, 22\u201342 "
                "round the bottom and 43\u201363 up the right, so that each later year sits beside an earlier one; "
                "the years from 64 run down the middle. Each year has four boxes for your own notes. The arrangement "
                "follows George and Gisela O'Neil's life chart, which is widely used in biography work.")
    yn, age = year_now(birth, now_utc)
    notes = UP.life_notes() if mine else {}
    name = UP.get().get("name", "") if mine else ""
    title = f"Biography chart \u00b7 {name or who}"
    sub = f"Born {ch['utc']:%d %B %Y} \u00b7 year of life 1 = {calendar_years(birth, 1)}"
    if yn:
        p = period_of(yn)
        m = mirror(yn)
        line = (f"**{'You are' if mine else 'This life is'} in year {yn} of life** (age {yn - 1} to {yn}, "
                f"{calendar_years(birth, yn)}): {p.get('keyword', '').lower()}"
                + (f", the {p['planet']} years {int(p['first_year'])}\u2013{int(p['last_year'])}" if p.get("planet") else "")
                + ".")
        if m and m != yn:
            line += (f" On the chart it sits beside year {m} ({calendar_years(birth, m)})"
                     + (", which is still to come." if m > yn else "."))
        elif m == yn:
            line += " It is the middle year of the chart, at the bottom of the arc."
        st.markdown(line)
    elif age < 0:
        st.markdown("This moment lies in the future, so the chart shows no year of life yet.")
    fig = draw(birth, now_utc, ev, notes, theme=wheel_theme, title=title, sub=sub, compact=phone)
    st.pyplot(fig, width="stretch")
    if phone:
        st.caption("Pinch the picture to zoom in, or download it below.")
    c1, c2 = st.columns(2)
    c1.download_button("Download chart (PNG)", C.png_bytes(fig, wheel_theme), file_name="biography_chart.png",
                       mime="image/png", on_click="ignore", width="stretch")
    pfig = draw(birth, now_utc, ev, notes, theme=PRINT_THEME, title=title, sub=sub)
    c2.download_button("Printable chart (PDF)", pdf_bytes(pfig), file_name="biography_chart.pdf",
                       mime="application/pdf", on_click="ignore", width="stretch",
                       help="On white paper, for writing on by hand, as the life chart is meant to be used.")

    st.subheader("Your notes, year by year" if mine else "Notes")
    if not mine:
        st.caption("Notes can be kept for your own chart only: add your birth date, time and place in your profile "
                   "(Edit profile, top of the sidebar) and choose 'My birth chart'.")
        return
    labels = {y: f"Year {y} of life \u00b7 age {y - 1}\u2013{y} \u00b7 {calendar_years(birth, y)}"
              + (" \u00b7 now" if y == yn else "") for y in range(1, YEARS + 1)}
    if "life_year" not in st.session_state:
        st.session_state["life_year"] = yn or 1
    year = st.selectbox("Year", list(labels), format_func=labels.get, key="life_year")
    p = period_of(year)
    m = mirror(year)
    st.caption(f"{p.get('keyword', '')}"
               + (f" \u00b7 {p['planet']} years {int(p['first_year'])}\u2013{int(p['last_year'])}" if p.get("planet") else "")
               + (f" \u00b7 sits beside year {m} ({calendar_years(birth, m)})" if m and m != year else ""))
    cur = notes.get(str(year), {})
    with st.form(key=f"life_form_{year}"):
        vals = {}
        cols = (st.container(), st.container(), st.container(), st.container()) if phone else st.columns(2) * 2
        for (k, lab), col in zip(ASPECTS, cols):
            vals[k] = col.text_area(lab, cur.get(k, ""), key=f"life_{year}_{k}", height=110,
                                    max_chars=UP.MAX_NOTE)
        if st.form_submit_button("Save notes for this year", type="primary", width="stretch"):
            UP.save_life_year(year, vals)
            st.toast(f"Notes for year {year} saved.")
            st.rerun()
    st.caption(UP.life_storage_text())
    tbl = notes_table(birth, UP.life_notes())
    filled = tbl[(tbl[[lab for _, lab in ASPECTS]] != "").any(axis=1)]
    if len(filled):
        with st.expander(f"All my notes ({len(filled)} year{'s' if len(filled) != 1 else ''})"):
            device.table(filled, phone_cols=["year of life", "calendar years"] + [lab for _, lab in ASPECTS])
    a, b = st.columns(2)
    a.download_button("Download my notes (CSV)", tbl.to_csv(index=False).encode("utf-8-sig"),
                      file_name="biography_notes.csv", mime="text/csv", on_click="ignore", width="stretch",
                      help="All 84 years as a table that opens in Excel. Keep it as a backup; you can load it again "
                           "here.")
    with b.popover("Load notes from a file", width="stretch"):
        up = st.file_uploader("Notes file (CSV from 'Download my notes')", type=["csv"], key="life_upload")
        if up is not None:
            try:
                got = read_notes_csv(up.getvalue())
            except ValueError as e:
                st.error(str(e))
            else:
                st.caption(f"{len(got)} years with notes in this file. Loading replaces the notes shown now.")
                if st.button("Load these notes", key="life_load", type="primary"):
                    UP.save_life(got)
                    st.toast("Notes loaded.")
                    st.rerun()
