"""Shared pieces of the two calendar pages (Auspicious dates and Friends): the cached scan, the day x hour heat map,
and short reason lists."""
import datetime as dt
from zoneinfo import ZoneInfo
import numpy as np
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap

import electional as el
import theme

PAL = theme.PALETTE
GRADE_COL = theme.GRADE_COLOURS
GRADE_TXT = {'best': 'Best', 'good': 'Good', 'fair': 'Fair', 'avoid': 'Avoid'}


@st.cache_data(show_spinner=False, max_entries=8, ttl=3600)
def compute(kind, lat, lon, elev, tzkey, start, days, h0, h1, step, beams_rule):
    tz = ZoneInfo(tzkey) if not tzkey.startswith('UTC') else dt.timezone(dt.timedelta(hours=float(tzkey[3:])))
    res, bands = el.scan(kind, lat, lon, elev, tz, start, days, h0, h1, step, beams_rule)
    q = el.grade(res)
    return res, bands, q


def heatmap(res, start, days, h0, h1, step, compact=False):
    """Day x hour grid of grades. compact=True: drawn for a phone held upright (about 4 inches wide, so that
    at a phone's screen width the labels are still about 11 pixels high; hours labelled every 3 hours)."""
    slots = len(range(h0 * 60, min(h1 * 60, 24 * 60 - 1) + 1, step))
    grid = np.full((days, slots), -1)
    code = {'avoid': 0, 'fair': 1, 'good': 2, 'best': 3}
    for r in res:
        i = (r['date'] - start).days
        j = int(((r['local'].hour - h0) * 60 + r['local'].minute) / step)
        if 0 <= i < days and 0 <= j < slots:
            grid[i, j] = code[r['grade']]
    width, row, fs = (4.0, 0.26, 8.5) if compact else (9.5, 0.24, 7)
    ink, ink2 = (theme.WHITE, theme.WHITE) if compact else (PAL['starlight'], PAL['dust'])   # phone: all labels white
    height = max(3.2 if not compact else 2.6, row * days + 1.2)
    fig = Figure(figsize=(width, height))
    fig.patch.set_alpha(0)
    ax = fig.add_subplot()
    ax.set_facecolor('none')
    cmap = ListedColormap([GRADE_COL['avoid'], GRADE_COL['fair'], GRADE_COL['good'], GRADE_COL['best']])
    ax.imshow(np.ma.masked_less(grid, 0), aspect='auto', cmap=cmap, vmin=0, vmax=3, interpolation='nearest',
              extent=(h0 - step / 120, h0 + (slots - 0.5) * step / 60, days - 0.5, -0.5))
    ax.set_yticks(range(days))
    ax.set_yticklabels([f"{(start + dt.timedelta(days=i)):{'%a %d' if compact else '%a %d %b'}}" for i in range(days)],
                       fontsize=fs, color=ink)
    hours = list(range(h0, h1 + 1, 3 if compact else 1))
    ax.set_xticks(hours)
    ax.set_xticklabels([f'{h:02d}' if compact else f'{h:02d}:00' for h in hours], fontsize=fs, color=ink, rotation=0)
    ax.tick_params(colors=ink2, length=2)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel('Local clock hour' if compact else 'Local clock time', fontsize=fs + 0.5 if compact else 8, color=ink2)
    gap, x0, lfs = (0.22, 0.06, 9) if compact else (0.12, 0.13, 8)
    for k, (g, c) in enumerate(GRADE_COL.items()):
        fig.text(x0 + gap * k, 0.008, '■', color=c, fontsize=12 if not compact else 13, va='bottom')
        fig.text((x0 + 0.056 if compact else 0.155) + gap * k, 0.012, GRADE_TXT[g], color=ink,
                 fontsize=lfs, va='bottom')
    fig.subplots_adjust(left=0.15 if compact else 0.12, right=0.98 if compact else 0.99, top=0.985 if compact else 0.98,
                        bottom=max(0.06, (1.0 / height) if compact else 0.9 / (row * days + 1.2)))
    return fig


def badge(g):
    """A grade as a small coloured label (HTML), in the calendar colours."""
    fg = PAL['void'] if g in ('good', 'best') else PAL['starlight']
    return f"<span class='lilly-badge' data-g='{g}' style='background:{GRADE_COL[g]};color:{fg}'>{GRADE_TXT[g]}</span>"


def day_list(res, wins, start, days, step, per_day=3):
    """Phone view of a calendar: one line per day with its best windows (Best and Good), in large text.
    Returns HTML for st.markdown(..., unsafe_allow_html=True)."""
    by_day = {}
    for w in wins:
        by_day.setdefault(w['date'], []).append(w)
    avoid_all = {}
    for r in res:
        avoid_all.setdefault(r['date'], True)
        if not r['avoid']:
            avoid_all[r['date']] = False
    lines = []
    for i in range(days):
        d = start + dt.timedelta(days=i)
        ws = sorted(by_day.get(d, []), key=lambda w: (w['grade'] != 'best', -w['score']))[:per_day]
        ws.sort(key=lambda w: w['start'])
        if ws:
            body = ' '.join(f"{badge(w['grade'])}{w['start']:%H:%M}–{(w['end'] + dt.timedelta(minutes=step)):%H:%M}&ensp;"
                            for w in ws)
        elif avoid_all.get(d, False):
            body = f"{badge('avoid')}all day"
        else:
            body = "<span style='color:%s'>no Good or Best time</span>" % PAL['dust']
        lines.append(f"<div class='lilly-day'><b>{d:%a %d %b}</b> {body}</div>")
    return '\n'.join(lines)


def reasons(items, kinds=('good',), n=3):
    xs = [(p, t) for _, t, p, _, k in items if k in kinds]
    xs.sort(key=lambda x: -abs(x[0]))
    return ' · '.join(t.split(':')[0] if len(t) > 90 else t for _, t in xs[:n])
