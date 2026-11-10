"""Sidereal chart wheel: 13 IAU ecliptic constellations at their true widths, Regiomontanus houses,
planets with Lilly's net dignity score, and Lilly's aspects in the centre.

Ecliptic longitude runs counter-clockwise; the Ascendant sits at 9 o'clock (the usual chart convention).
Filled marker = body above the local horizon; open marker = below. Bodies lying in a constellation outside
the zodiac (e.g. Cetus) are labelled with that constellation. Uses matplotlib Figure (not pyplot), so
repeated drawing in a long-running app does not accumulate figures in memory.
"""
from math import radians
import numpy as np
import matplotlib
from matplotlib.figure import Figure

ZODIACAL = {'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpius',
            'Ophiuchus', 'Sagittarius', 'Capricornus', 'Aquarius', 'Pisces'}
INK, GREY, ACCENT = '#222222', '#8a8a8a', '#7a3b8f'
LIGHT = dict(fig_bg='white', face='white', band_a='#ececec', band_b='#dcdcdc', band_edge='white', band_text=INK,
             ring=GREY, ink=INK, grey=GREY, up=INK, down_face='white', accent=ACCENT, label_bg='white',
             harmony='#3c7d3c', tension='#b04a5a', house_line='#9a9a9a',
             harmony_name='green', tension_name='red', accent_name='Purple')
GLYPH = {'Sun': '☉', 'Moon': '☽', 'Mercury': '☿', 'Venus': '♀', 'Mars': '♂', 'Jupiter': '♃', 'Saturn': '♄',
         'Uranus': '♅', 'Neptune': '♆', 'Pluto': '♇'}
AR = 0.30   # radius of the aspect circle


def _style():
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.titlesize': 10, 'savefig.dpi': 300})


def legend_lines(theme=None):
    """The key printed under the wheel (also shown as text under the phone version)."""
    th_ = dict(LIGHT, **(theme or {}))
    return ['Filled = above horizon · open = below · number = Lilly net score (p.115) · R = retrograde · ☊ ☋ nodes · ⊗ Part of Fortune',
            f"Aspects: {th_['harmony_name']} = sextile/trine, {th_['tension_name']} = square/opposition; "
            "solid = applying, dashed = separating",
            f"{th_['accent_name']} {th_.get('accent_what', 'label')} = body outside the 13 ecliptic constellations "
            "(read by its ecliptic band)"]


# The two band shades alternate by constellation name (user request), so the pattern is the same wherever the wheel
# starts. Thirteen bands cannot all alternate, so one neighbouring pair must share a shade: Ophiuchus takes Scorpius'
# shade, and Pisces and Aries differ like all the other neighbours.
SHADE_ORDER = ('Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpius', 'Sagittarius', 'Capricornus',
               'Aquarius', 'Pisces')


def band_shade(name, i, th_):
    name = 'Scorpius' if name == 'Ophiuchus' else name
    k = SHADE_ORDER.index(name) if name in SHADE_ORDER else i
    return th_['band_a'] if k % 2 == 0 else th_['band_b']


def draw_wheel(rows, bands, title, asc, mc, cusps=None, scores=None, aspects=None, ax=None, theme=None, compact=False):
    """rows: chart rows (body, ecl_lon, alt, constellation); bands: [(start, abbr, name)];
    cusps: 12 house cusps; scores: {planet: net}; aspects: lilly_layer aspect dicts.
    compact=True: for a phone screen. A smaller figure, so every label is relatively larger; planets are labelled
    by symbol and score only, and the key is left out of the picture (show legend_lines() as text instead)."""
    _style()
    th_ = dict(LIGHT, **(theme or {}))
    F = dict(band=7.0, house=7.5, angle=8.5, planet=9.5, node=10.5, title=9, ms=6.5, band_name_min=18) if compact else \
        dict(band=7.5, house=6.5, angle=7.5, planet=7, node=9, title=10, ms=7, band_name_min=12)
    if ax is None:
        fig = Figure(figsize=(4.8, 4.8) if compact else (6.6, 6.6))
        ax = fig.add_subplot(projection='polar')
    fig = ax.figure
    fig.patch.set_facecolor(th_['fig_bg']); fig.patch.set_alpha(0 if th_['fig_bg'] == 'none' else 1)
    ax.set_facecolor(th_['face']); ax.patch.set_alpha(th_.get('face_alpha', 1.0))
    ax.set_theta_direction(1)
    ax.set_theta_offset(np.pi - radians(asc))
    ax.set_ylim(0, 1.0)
    ax.set_xticks([]); ax.set_yticks([]); ax.spines['polar'].set_visible(False); ax.grid(False)

    # constellation ring (true unequal widths)
    starts = [b[0] for b in bands]
    ends = starts[1:] + [starts[0] + 360]
    for i, ((s, abbr, name), e) in enumerate(zip(bands, ends)):
        th = np.radians(np.linspace(s, e, 80))
        shade = band_shade(name, i, th_)
        ax.fill_between(th, 0.86, 1.0, color=shade, lw=0)
        ax.plot([np.radians(s)] * 2, [0.86, 1.0], color=th_['band_edge'], lw=1.2)
        mid = np.radians((s + e) / 2)
        lab = name if (e - s) > F['band_name_min'] else abbr
        rot = np.degrees(mid + ax.get_theta_offset()) - 90
        rot = (rot + 180) % 360 - 180
        if abs(rot) > 90:
            rot += 180
        ax.text(mid, 0.93, lab, ha='center', va='center', fontsize=F['band'], color=th_['band_text'], rotation=rot,
                rotation_mode='anchor')
    ring = np.radians(np.linspace(0, 360, 361))
    ax.plot(ring, [0.86] * 361, color=th_['ring'], lw=0.6)
    ax.plot(ring, [AR] * 361, color=th_['ring'], lw=0.5)

    # Regiomontanus houses
    if cusps:
        for i, c in enumerate(cusps):
            ang = i in (0, 3, 6, 9)
            ax.plot([np.radians(c)] * 2, [AR, 0.86], color=th_['house_line'], lw=0.9 if ang else 0.45,
                    ls='-' if ang else (0, (2, 3)), alpha=0.9)
            nxt = cusps[(i + 1) % 12]
            mid = c + ((nxt - c) % 360) / 2
            ax.text(np.radians(mid), AR + 0.045, str(i + 1), ha='center', va='center', fontsize=F['house'], color=th_['grey'])
    for lon, lab in ((asc, 'Asc'), (mc, 'MC')):
        ax.text(np.radians(lon), 1.07, lab, ha='center', va='center', fontsize=F['angle'], color=th_['ink'],
                bbox=dict(fc=th_['label_bg'], ec='none', pad=0.8), zorder=7, clip_on=False)
        ax.plot([np.radians(lon)] * 2, [0.86, 1.0], color=th_['ink'], lw=1.6, zorder=6)

    # aspects (Lilly's five) in the centre
    lon_of = {r['body']: r['ecl_lon'] for r in rows}
    if aspects:
        for a in aspects:
            if a['aspect'] == 'conjunction':
                continue
            col = th_['harmony'] if a['aspect'] in ('sextile', 'trine') else th_['tension']
            t1, t2 = np.radians(lon_of[a['a']]), np.radians(lon_of[a['b']])
            x = np.linspace(AR * np.cos(t1), AR * np.cos(t2), 60)
            y = np.linspace(AR * np.sin(t1), AR * np.sin(t2), 60)
            ax.plot(np.arctan2(y, x), np.hypot(x, y), color=col, lw=1.4 if a['partile'] else 0.8,
                    ls='-' if a['applying'] else (0, (3, 2)), alpha=0.95, zorder=2)

    # bodies, staggered radially when crowded
    bodies = [r for r in rows if r['body'] in GLYPH]
    bodies.sort(key=lambda r: r['ecl_lon'])
    radii, last = [], {}
    for r in bodies:
        lvl = 0
        while any(abs(((r['ecl_lon'] - l + 180) % 360) - 180) < (20 if compact else 11) for l in last.get(lvl, [])):
            lvl += 1
        last.setdefault(lvl, []).append(r['ecl_lon'])
        radii.append(0.75 - (0.135 if compact else 0.13) * lvl)
    for r, rad in zip(bodies, radii):
        th = np.radians(r['ecl_lon'])
        up = r.get('alt', 0) > 0
        off = r['constellation'] not in ZODIACAL
        col = th_['accent'] if off else th_['up']
        sc = scores.get(r['body']) if scores else None
        cx, sy = np.cos(th + ax.get_theta_offset()), np.sin(th + ax.get_theta_offset())
        right_half = cx > 0
        if compact:
            # the planet's symbol is the marker (filled = above the horizon); its score sits beside it, across the
            # ring, so that planets bunched together (staggered towards the centre) do not cover each other
            ax.plot([th, th], [AR, rad - 0.05], color=th_.get('spoke', th_['grey']), lw=0.3, alpha=0.6, zorder=1)
            ax.text(th, rad, GLYPH[r['body']], ha='center', va='center', fontsize=F['planet'] + 0.5,
                    color=th_['label_bg'] if up else th_.get('glyph_open', col), zorder=6,
                    bbox=dict(boxstyle='circle,pad=0.22', fc=col if up else th_['down_face'], ec=col, lw=1.1))
            lab = (f"{sc:+d}" if sc is not None else '') + (' R' if r.get('retrograde') else '')
            if lab:
                if abs(cx) >= 0.4:      # left or right of the wheel: score below the symbol
                    xy, ha, va = (0, -10), 'center', 'top'
                else:                   # top or bottom: score to the side
                    xy, ha, va = (10, 0), 'left', 'center'
                ax.annotate(lab, (th, rad), xytext=xy, textcoords='offset points', ha=ha, va=va,
                            fontsize=F['planet'] - 1.5, color=th_['ink'], zorder=7,
                            bbox=dict(fc=th_['label_bg'], ec='none', alpha=0.65, pad=0.4))
            continue
        ax.plot(th, rad, marker='o', ms=F['ms'], mfc=col if up else th_['down_face'], mec=col, mew=1.4, ls='none', zorder=5)
        ax.plot([th, th], [AR, rad - 0.03], color=th_['grey'], lw=0.3, alpha=0.6, zorder=1)
        lab = f"{GLYPH[r['body']]} {r['body']}" + (f" {sc:+d}" if sc is not None else '') + (' R' if r.get('retrograde') else '')
        if off:
            lab += f"\n(in {r['constellation']})"
        ax.annotate(lab, (th, rad), xytext=(-8 if right_half else 8, 0), textcoords='offset points',
                    ha='right' if right_half else 'left', va='center',
                    fontsize=F['planet'], color=th_['accent'] if off else th_['ink'], zorder=6)
    # nodes and Part of Fortune, small, just inside the band ring
    for name, sym in (('North Node', '☊'), ('South Node', '☋'), ('Part of Fortune', '⊗')):
        if name in lon_of:
            ax.text(np.radians(lon_of[name]), 0.82, sym, ha='center',
                    va='center', fontsize=F['node'], color=th_['grey'], zorder=6)

    ax.set_title(title, loc='left', fontsize=F['title'], color=th_['ink'], pad=14)
    if compact:
        fig.subplots_adjust(left=0.05, right=0.95, bottom=0.02, top=0.90)
    if not compact:
        for y, line in zip((0.058, 0.035, 0.012), legend_lines(theme)):
            fig.text(0.02, y, line, fontsize=6.3, color=th_['grey'])
    return fig
