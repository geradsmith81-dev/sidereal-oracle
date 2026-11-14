"""
charts.py - figures for the Astrosophy Birth Chart.

  draw_wheel(chart, helio=False, theme=None, compact=False)
        geocentric (or heliocentric) wheel: the 13 IAU zodiac constellations at their true widths,
        Ascendant at 9 o'clock.
  draw_prenatal(tracks, events, epoch, birth, theme=None, compact=False)
        Sucher's prenatal graph: planets moving through the IAU constellations from epoch to birth, with the
        Moon's sidereal returns marked as seven-year periods of life.
  legend_lines(helio=False)   the wheel's key as text (printed under the phone version instead of inside it)
  png_bytes(fig, theme)       PNG for downloading, on a solid background

compact=True is the phone version (the Sidereal Oracle's rule): a smaller figure, so that every label is relatively
larger; planet symbols sit inside a coloured ring, and the key is written under the picture instead of inside it.
Desktop and phone share the colours of theme.WHEEL_THEME / WHEEL_THEME_PHONE.
Off-zodiac bodies are drawn with an open circle and named, so the flag never depends on colour alone.
Uses matplotlib's Figure (not pyplot), so that repeated drawing in a long-running app does not pile up figures in memory.
"""
from __future__ import annotations

import io
import math

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import numpy as np

from . import astrosophy_engine as E
# the first theme of the app; any theme passed in overrides these keys
THEME = {
    "fig_bg": "#12141d", "bg": "#12141d", "face_alpha": 1.0, "panel": "#1b1e2b", "ring_a": "#262a3b",
    "ring_b": "#2f3448", "line": "#5d6482", "text": "#e6e8f0", "muted": "#a7adc4", "gold": "#e8c46a",
    "flag": "#d9a3c9", "spoke": "#a7adc4", "glyph_ring": False,
}
BODY_COLOUR = {"Sun": "#e8c46a", "Moon": "#c8d0e6", "Mercury": "#8fd3c8", "Venus": "#9ec27a",
               "Mars": "#e48a6a", "Jupiter": "#d9b37c", "Saturn": "#a99fd9", "Uranus": "#9ab6e0",
               "Neptune": "#7fa0d8", "Pluto": "#b9a6a0", "Earth": "#7fc0a0"}
FS = (11, 9, 8)  # titles/labels, annotations, ticks

# The two band shades alternate by constellation (the Sidereal Oracle's rule), so the pattern is the same wherever
# the wheel starts. Thirteen bands cannot all alternate, so one neighbouring pair must share a shade: Ophiuchus takes
# Scorpio's shade, and Pisces and Aries differ like all the other neighbours.
SHADE_ORDER = ("Ari", "Tau", "Gem", "Cnc", "Leo", "Vir", "Lib", "Sco", "Sgr", "Cap", "Aqr", "Psc")


def _th(theme):
    return dict(THEME, **(theme or {}))


def band_shade(abbr, i, th_):
    abbr = "Sco" if abbr == "Oph" else abbr
    k = SHADE_ORDER.index(abbr) if abbr in SHADE_ORDER else i
    return th_["ring_a"] if k % 2 == 0 else th_["ring_b"]


def _new_fig(size, th_, polar=False):
    fig = Figure(figsize=size, dpi=110)
    transparent = th_["fig_bg"] == "none"
    fig.patch.set_facecolor(th_["bg"] if transparent else th_["fig_bg"])
    fig.patch.set_alpha(0 if transparent else 1)
    ax = fig.add_subplot(111, projection="polar") if polar else fig.add_subplot(111)
    return fig, ax


def png_bytes(fig, theme=None, dpi=150) -> bytes:
    """PNG of a figure on a solid background (on screen the page background may show through)."""
    buf = io.BytesIO()
    alpha = fig.patch.get_alpha()
    fig.patch.set_alpha(1)
    try:
        fig.savefig(buf, format="png", facecolor=_th(theme)["bg"], dpi=dpi)
    finally:
        fig.patch.set_alpha(alpha)
    return buf.getvalue()


def _theta(lon, ref):
    """Ascendant (ref) at 9 o'clock, longitudes increasing counter-clockwise."""
    return math.radians(180.0 + (lon - ref))


def legend_lines(helio=False):
    lines = ["Outer ring: IAU zodiac constellations at their true widths. Short inner ticks: 30\u00b0 tropical signs.",
             "Open circle: body outside the zodiac band (its constellation is named)."]
    if not helio:
        lines.append("Asc = Ascendant (solid line), MC = Midheaven (dashed). \u260A = mean lunar node.")
    return lines


def draw_wheel(ch: dict, helio: bool = False, title: str | None = None, ax=None, theme=None, compact=False):
    th_ = _th(theme)
    ref = ch["asc"] if not helio else 0.0
    if ax is None:
        fig, ax = _new_fig((4.9, 5.2) if compact else (7.4, 7.4), th_, polar=True)
    else:
        fig = ax.figure
    ax.set_facecolor(th_["bg"])
    ax.patch.set_alpha(th_["face_alpha"])
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)
    ax.set_ylim(0, 1.0)
    ax.set_axis_off()
    fs_band = 7.2 if compact else FS[2]
    # the wheel's own dark face (on screen the page background shows through around it)
    ax.bar(0, 1.0, width=2 * math.pi, bottom=0, color=th_["bg"], edgecolor="none", alpha=th_["face_alpha"],
           zorder=0)
    # zodiac ring
    r_in, r_out = 0.80, 0.98
    for i, (ab, s, e) in enumerate(ch["bands"]):
        t0, t1 = _theta(s, ref), _theta(e, ref)
        ax.bar((t0 + t1) / 2, r_out - r_in, width=(t1 - t0), bottom=r_in, color=band_shade(ab, i, th_),
               edgecolor=th_["line"], linewidth=0.6, align="center")
        mid = (s + e) / 2
        tm = _theta(mid, ref)
        rot = (math.degrees(tm) - 90) % 360
        if 90 < rot < 270:
            rot -= 180
        name = E.con_name(ab)
        if compact and (e - s) < 9 * len(name) / 4:      # too narrow for the full name at phone size
            name = ab
        ax.text(tm, (r_in + r_out) / 2, name, color=th_["text"], fontsize=fs_band,
                ha="center", va="center", rotation=rot, rotation_mode="anchor")
    # tropical reference ticks (thin, inner)
    for k in range(12):
        tk = _theta(30 * k, ref)
        ax.plot([tk, tk], [0.775, 0.80], color=th_["muted"], lw=0.6)
    # inner disc
    ax.bar(0, 0.62, width=2 * math.pi, bottom=0, color=th_["panel"], edgecolor="none", alpha=th_["face_alpha"])
    if not helio:
        for lon_a, name in ((ch["asc"], "Asc"), (ch["mc"], "MC")):
            ta = _theta(lon_a, ref)
            ax.plot([ta, ta + math.pi], [0.80, 0.80], color=th_["muted"], lw=0.9,
                    ls="-" if name == "Asc" else "--")
            ax.text(ta, 1.04 if compact else 1.035, name, color=th_["gold"], fontsize=FS[1], ha="center",
                    va="center", fontweight="bold")
    # bodies
    items = []
    for b in ch["bodies"]:
        if helio:
            if b.helio_lon is None:
                continue
            items.append((b.name, b.helio_lon, b.helio_zodiac, False, ""))
        else:
            items.append((b.name, b.lon, b.zodiac, b.off_zodiac, E.con_name(b.iau_true) if b.off_zodiac else ""))
    if helio:
        items.append(("Earth", ch["earth_helio_lon"], ch["earth_helio_zodiac"], False, ""))
    items.sort(key=lambda x: x[1])
    rings = [0.70, 0.56, 0.42, 0.30] if not compact else [0.69, 0.53, 0.37, 0.22]
    near = 7 if not compact else 11
    placed = []
    for name, lon, z, off, true_c in items:
        level = 0
        while any(abs(E.wrap180(lon - pl)) < near and lv == level for pl, lv in placed) and level < len(rings) - 1:
            level += 1
        placed.append((lon, level))
        r = rings[level]
        th = _theta(lon, ref)
        c = BODY_COLOUR[name]
        ax.plot([th, th], [0.775, r + 0.05], color=c, lw=0.6, alpha=0.7)
        if th_.get("glyph_ring"):
            ax.text(th, r, E.GLYPH[name], color=c, fontsize=FS[0] + 2, ha="center", va="center", zorder=6,
                    bbox=dict(boxstyle="circle,pad=0.2", fc=th_["bg"], ec=th_["flag"] if off else c,
                              lw=1.6 if off else 1.0, ls="-"))
        else:
            if off:
                ax.plot(th, r, marker="o", ms=17, mfc="none", mec=th_["flag"], mew=1.4)
            ax.text(th, r, E.GLYPH[name], color=c, fontsize=FS[0] + 3, ha="center", va="center")
        if off:
            ax.annotate(f"in {true_c}", xy=(th, r), xytext=(0, -15 if compact else -17), textcoords="offset points",
                        color=th_["flag"], fontsize=FS[2], ha="center", va="top")
    if not helio:
        ax.text(_theta(ch["node"], ref), 0.80 - 0.035, E.GLYPH["Node"], color=th_["muted"],
                fontsize=FS[1], ha="center", va="center")
    if not compact:
        fig.text(0.02, 0.02, "Outer ring: IAU zodiac constellations at their true widths.  Short inner ticks: "
                 "30\u00b0 tropical signs.  Open circle: body outside the zodiac band (constellation named).",
                 color=th_["muted"], fontsize=FS[2], ha="left", va="bottom", wrap=True)
    ttl = title or ("Geocentric sky, IAU zodiac constellations" if not helio else
                    "Heliocentric view (seen from the Sun)")
    ax.set_title(ttl, color=th_["text"], fontsize=FS[1] if compact else FS[0], loc="left", pad=16 if compact else 18)
    if compact:
        fig.subplots_adjust(left=0.06, right=0.94, bottom=0.03, top=0.88)
    return fig


def draw_prenatal(tracks, events, epoch, birth_chart, title=None, theme=None, compact=False):
    """x = life age (years) derived from the prenatal lunar cycles;
    y = ecliptic longitude, with the IAU zodiac bands as horizontal stripes.
    compact=True: a taller, narrower figure for a phone, with the key under the graph."""
    th_ = _th(theme)
    fig, ax = _new_fig((5.6, 6.4) if compact else (10.5, 5.6), th_)
    ax.set_facecolor(th_["panel"])
    ax.patch.set_alpha(th_["face_alpha"])
    bands = tracks.attrs["bands"]
    for i, (ab, s, e) in enumerate(bands):
        for off in (0, -360):
            ax.axhspan(s + off, e + off, color=band_shade(ab, i, th_), lw=0, zorder=0)
        mid = ((s + e) / 2) % 360
        ax.text(-0.6, mid, ab if compact else E.con_name(ab), color=th_["muted"], fontsize=FS[2], ha="right",
                va="center")
    age = tracks["age"].values
    ends = []
    for p in E.CLASSICAL:
        if p == "Moon":
            continue
        y = tracks[p].values % 360
        yy = y.astype(float).copy()
        jumps = np.where(np.abs(np.diff(y)) > 180)[0]
        yy[jumps] = np.nan
        ax.plot(age, yy, color=BODY_COLOUR[p], lw=1.8, label=p, zorder=3)
        ends.append([float(y[-1]), p])
    ends.sort(reverse=True)
    for i in range(len(ends)):
        cap = 356.0 if i == 0 else ends[i - 1][0] - 14
        ends[i][0] = min(ends[i][0], cap)
    for yv, p in ends:
        ax.text(age[-1] + 0.8, yv, E.GLYPH[p], color=BODY_COLOUR[p], fontsize=FS[0], va="center")
    # Moon start positions: each return = start of a seven-year period
    n_cycles = len(tracks.attrs["cycle_starts"])
    for k in range(n_cycles):
        ax.axvline(7 * k, color=th_["line"], lw=0.7, ls=":", zorder=1)
        lab = f"{7 * k}" if compact else f"{7 * k}\u2013{7 * k + 7}"
        ax.text(7 * k + (0 if compact else 3.5), 366, lab, color=th_["muted"], fontsize=FS[2],
                ha="center", va="bottom")
    conj = events[events.event == "conjunction"] if len(events) else events
    for _, r in conj.iterrows():
        ax.plot(r.age, r.lon, marker="D", ms=5, mfc=th_["text"], mec=th_["bg"], zorder=4)
    stn = events[events.event == "station"] if len(events) else events
    for _, r in stn.iterrows():
        ax.plot(r.age, r.lon, marker="v" if "retro" in r.bodies else "^", ms=5,
                mfc="none", mec=th_["text"], zorder=4)
    ax.set_xlim(0, max(7 * n_cycles, age[-1]) + 2)
    ax.set_ylim(0, 360)
    ax.set_yticks([])
    ax.set_xlabel("Age in the coming life (years)" + ("" if compact else
                  "; each sidereal Moon cycle of gestation = seven years"), color=th_["text"], fontsize=FS[1])
    ax.tick_params(colors=th_["muted"], labelsize=FS[2])
    for s in ax.spines.values():
        s.set_color(th_["line"])
    handles = [Line2D([], [], color=BODY_COLOUR[p], lw=2, label=p) for p in E.CLASSICAL if p != "Moon"]
    handles += [Line2D([], [], marker="D", ls="", mfc=th_["text"], mec=th_["bg"], label="conjunction"),
                Line2D([], [], marker="v", ls="", mfc="none", mec=th_["text"], label="turns retrograde"),
                Line2D([], [], marker="^", ls="", mfc="none", mec=th_["text"], label="turns direct")]
    if compact:
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=3, frameon=False,
                  fontsize=FS[2], labelcolor=th_["text"])
    else:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.03, 1.0), frameon=False,
                  fontsize=FS[2], labelcolor=th_["text"])
    ttl = title or (f"Prenatal graph: epoch {epoch.utc:%d %b %Y} \u2192 birth "
                    f"{birth_chart['utc']:%d %b %Y} ({epoch.gestation_days:.0f} days)")
    if compact:
        ttl = title or (f"Prenatal graph: {epoch.utc:%d %b %Y} \u2192 {birth_chart['utc']:%d %b %Y}")
    ax.set_title(ttl, color=th_["text"], fontsize=FS[1] if compact else FS[0], loc="left", pad=20 if compact else 24)
    if compact:
        fig.subplots_adjust(left=0.13, right=0.9, top=0.9, bottom=0.27)
    else:
        fig.subplots_adjust(left=0.11, right=0.84, top=0.88, bottom=0.11)
    return fig
