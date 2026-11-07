"""Forecast box: a written summary of the chart in Lilly's terms, with strengths and weaknesses.

The strengths and weaknesses come from Lilly's own "Considerations before Judgment" (Christian
Astrology pp.121-123), his scoring tables (p.115, p.181), and his remarks on reception (p.112) and the
Part of Fortune (p.143). The wording of each rule is in data/forecast_rules.csv and can be edited or
switched off there (enabled = False); the conditions that trigger each rule are in this file.
Where the app has had to adapt a rule to the unequal IAU bands, the CSV 'basis' column says so.
"""
import math
import os
import pandas as pd
import lilly_layer as ll

HERE = os.path.dirname(os.path.abspath(__file__))
# Natures of the planets (Lilly, planet chapters pp.57-83): used for the "same nature" radical test.
NATURE = {'Saturn': ('cold', 'dry'), 'Jupiter': ('hot', 'moist'), 'Mars': ('hot', 'dry'), 'Sun': ('hot', 'dry'),
          'Venus': ('cold', 'moist'), 'Mercury': ('cold', 'dry'), 'Moon': ('cold', 'moist')}
BENEFIC, MALEFIC = ('Jupiter', 'Venus'), ('Saturn', 'Mars')
SHORT_ASC = {'Capricorn', 'Aquarius', 'Pisces', 'Aries', 'Taurus', 'Gemini'}
ORD = ll._ord


def _join(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def radical(hour, lord, asc_sign):
    if not lord:
        return None, ''
    if hour == lord:
        return True, 'are one and the same planet'
    r = ll.BY_SIGN.loc[asc_sign]
    if hour in (r['triplicity_day'], r['triplicity_night']):
        return True, f'are of one triplicity ({hour} rules the triplicity of {asc_sign})'
    if NATURE[hour] == NATURE[lord]:
        return True, f'are of the same nature ({" and ".join(NATURE[hour])})'
    return False, ''


def moon_void(rows, bands, horizon_days=4.0):
    """Lilly p.112: void of course = the Moon perfects no aspect while she remains in that sign.
    App: 'sign' = the IAU band; motions are extrapolated linearly from the daily speeds."""
    by = {r['body']: r for r in rows}
    m = by['Moon']
    name, s, w, f = ll.band_of(m['ecl_lon'], bands)
    remaining = (s + w - m['ecl_lon']) % 360
    t_exit = remaining / max(m['speed'], 1e-6)
    for p in ll.PLANETS:
        if p == 'Moon':
            continue
        o = by[p]
        rel = m['speed'] - o['speed']
        for _, ang in ll.ASPECTS:
            for target in ({ang, -ang} if ang not in (0, 180) else {ang}):
                d = ((o['ecl_lon'] + target - m['ecl_lon']) % 360)   # degrees the Moon must gain
                if rel > 0 and d / rel <= min(t_exit, horizon_days) and d / rel >= 0:
                    return False, name, t_exit
    return True, name, t_exit


PHASES = [(0, 'New Moon', '\U0001F311'), (45, 'Waxing crescent', '\U0001F312'), (90, 'First quarter', '\U0001F313'),
          (135, 'Waxing gibbous', '\U0001F314'), (180, 'Full Moon', '\U0001F315'), (225, 'Waning gibbous', '\U0001F316'),
          (270, 'Last quarter', '\U0001F317'), (315, 'Waning crescent', '\U0001F318')]


def moon_next(rows, bands, horizon_days=4.0):
    """The Moon's next aspect to a planet before she leaves her constellation band (same reckoning as moon_void).
    Returns (planet, aspect name, days) or None when she is void of course."""
    by = {r['body']: r for r in rows}
    m = by['Moon']
    name, s, w, f = ll.band_of(m['ecl_lon'], bands)
    t_exit = ((s + w - m['ecl_lon']) % 360) / max(m['speed'], 1e-6)
    best = None
    for p in ll.PLANETS:
        if p == 'Moon':
            continue
        o = by[p]
        rel = m['speed'] - o['speed']
        if rel <= 0:
            continue
        for asp, ang in ll.ASPECTS:
            for target in ({ang, -ang} if ang not in (0, 180) else {ang}):
                days = ((o['ecl_lon'] + target - m['ecl_lon']) % 360) / rel
                if days <= min(t_exit, horizon_days) and (best is None or days < best[2]):
                    best = (p, asp, days)
    return best


def sky(rows, bands):
    """'The sky at this moment': the Moon's phase and light, the planets retrograde, the Moon's next contact or
    void of course, and when she leaves her constellation band."""
    by = {r['body']: r for r in rows}
    e = (by['Moon']['ecl_lon'] - by['Sun']['ecl_lon']) % 360          # elongation of the Moon from the Sun
    k = int(((e + 22.5) % 360) // 45)
    _, phase, symbol = PHASES[k]
    void, band, t_exit = moon_void(rows, bands)
    return dict(phase=phase, symbol=symbol, lit=round(50 * (1 - math.cos(math.radians(e)))),
                waxing=e < 180, elongation=e,
                retrograde=[p for p in ll.PLANETS if p not in ('Sun', 'Moon') and by[p]['speed'] < 0],
                void=void, band=band, exit_days=t_exit, next=None if void else moon_next(rows, bands))


def build(R, rows, bands, ph, rules_csv=None):
    rules = pd.read_csv(rules_csv or os.path.join(HERE, 'data', 'forecast_rules.csv'), encoding='utf-8')
    rules = rules[rules['enabled'].astype(str).str.lower().isin(['true', '1', 'yes'])].set_index('rule_id')
    out = {'strength': [], 'weakness': []}

    def fire(rid, **kw):
        if rid in rules.index:
            r = rules.loc[rid]
            plain = r['plain'] if 'plain' in rules.columns and isinstance(r['plain'], str) and r['plain'].strip() else r['text']
            out[r['kind']].append(dict(id=rid, text=r['text'].format(**kw), plain=plain.format(**kw),
                                       source=r['source'], basis=r['basis']))

    P = {p['planet']: p for p in R['planets']}
    asc, lord = R['asc'], R['lord_of_asc']
    hour, day = ph['hour_ruler'], ph['day_ruler']

    # ---------------- summary paragraph (restates the chart) ----------------
    para = [f"This is a {'diurnal' if R['sun_up'] else 'nocturnal'} figure, on a day of {day} "
            f"in the hour of {hour} (hour {ph['hour_number']} of 24, counted from sunrise)."]
    if asc['has_sign']:
        lp = P[lord]
        para.append(f"{asc['constellation']} rises (read as Lilly's {asc['sign']}, about {asc['sign_deg']:.0f}° on the rescaled scale), "
                    f"so the Lord of the Ascendant is {lord}. {lord} stands in {lp['constellation']} in the {ORD(lp['house'])} house, "
                    f"essentially {lp['condition']}, with {lp['fortitudes']} fortitudes and {lp['debilities']} debilities (net {lp['net']:+d}).")
        para.append(f"Lilly gives the {ORD(lp['house'])} house signification of {ll.house_meaning(lp['house'], 160)}")
    else:
        para.append(f"{asc['constellation']} rises. It has no sign in Lilly, so the Ascendant has no Lord.")
    ranked = sorted(R['planets'], key=lambda p: p['net'], reverse=True)
    para.append(f"The strongest planet is {ranked[0]['planet']} (net {ranked[0]['net']:+d}); "
                f"the weakest is {ranked[-1]['planet']} (net {ranked[-1]['net']:+d}).")
    pof = R['part_of_fortune']
    para.append(f"The Part of Fortune falls in {pof['constellation']}, in the {ORD(pof['house'])} house.")

    # ---------------- rules ----------------
    if ph.get('fallback'):
        fire('polar')
    if not asc['has_sign']:
        fire('asc_ophiuchus')
    else:
        ok, why = radical(hour, lord, asc['sign'])
        fire('radical' if ok else 'not_radical', hour=hour, lord=lord, why=why)
        d = asc['sign_deg']
        if d < 3:
            fire('asc_early', deg=d, sign=asc['sign'])
        elif d >= 27:
            fire('asc_late', deg=d, sign=asc['sign'])
        lp = P[lord]
        kw = dict(lord=lord, f=lp['fortitudes'], d=lp['debilities'], n=lp['net'], cond='essentially ' + lp['condition'], house=ORD(lp['house']))
        if lp['net'] >= 5:
            fire('lord_asc_strong', **kw)
        elif lp['net'] <= -5:
            fire('lord_asc_weak', **kw)
        if lp['fortitudes'] == lp['debilities']:
            fire('testimonies_equal', lord=lord, f=lp['fortitudes'])
        if lp['house'] in (1, 4, 7, 10):
            fire('lord_asc_angular', house=lp['house'])
        elif lp['house'] in (3, 6, 9, 12):
            fire('lord_asc_cadent', house=lp['house'])
        if any(k == 'combust' for k, *_ in lp['accidental']):
            sd = abs(((lp['ecl_lon'] - P['Sun']['ecl_lon'] + 180) % 360) - 180)
            fire('lord_asc_combust', lord=lord, d=sd)
    c7 = R['cusp_signs'][6]
    if c7['has_sign']:
        lord7 = ll.BY_SIGN.loc[c7['sign'], 'house_ruler']
        l7 = P[lord7]
        how = []
        if l7['retrograde']:
            how.append('retrograde')
        keys = {k for k, *_ in l7['essential']}
        if 'fall' in keys:
            how.append('in his fall')
        if 'detriment' in keys:
            how.append('in his detriment')
        if l7['sign'] and ll.term_ruler(l7['sign'], l7['sign_deg']) in ('Saturn', 'Mars') and lord7 not in ('Saturn', 'Mars'):
            how.append(f"in the terms of {ll.term_ruler(l7['sign'], l7['sign_deg'])}")
        if how:
            fire('lord_7_afflicted', lord7=lord7, how=_join(how))
    if P['Saturn']['house'] == 1:
        fire('saturn_asc', retro=', and retrograde' if P['Saturn']['retrograde'] else '',
             retro_plain=', and moving backwards (retrograde)' if P['Saturn']['retrograde'] else '')
    if P['Saturn']['house'] == 7:
        fire('saturn_7')
    mo = P['Moon']
    if mo['sign'] == 'Libra' and mo['sign_deg'] >= 15:
        fire('moon_via_combusta', where=f"last half of Libra, {mo['sign_deg']:.0f}° rescaled")
    elif mo['sign'] == 'Scorpio' and mo['sign_deg'] < 15:
        fire('moon_via_combusta', where=f"first half of Scorpio, {mo['sign_deg']:.0f}° rescaled")
    elif mo['sign'] and mo['sign_deg'] >= 27:
        fire('moon_late', sign=mo['sign'], deg=mo['sign_deg'])
    void, band, _ = moon_void(rows, bands)
    if void:
        soft = ('; yet "somewhat she performes" in Taurus, Cancer, Sagittarius or Pisces, as here'
                if mo['sign'] in ('Taurus', 'Cancer', 'Sagittarius', 'Pisces') else '')
        fire('moon_void', sign=band, soft=soft,
             soft_plain=(' (Lilly softens this when the Moon is in Taurus, Cancer, Sagittarius or Pisces, as she is now)'
                         if soft else ''))
    for a in R['aspects']:
        if 'Moon' in (a['a'], a['b']) and a['applying']:
            other = a['b'] if a['a'] == 'Moon' else a['a']
            if other in BENEFIC and a['aspect'] in ('sextile', 'trine', 'conjunction'):
                fire('moon_apply_benefic', aspect=a['aspect'], planet=other, dev=a['deviation'])
            if other in MALEFIC and a['aspect'] in ('square', 'opposition', 'conjunction'):
                fire('moon_apply_malefic', aspect=a['aspect'], planet=other, dev=a['deviation'])
    for p in R['planets']:
        if any(k == 'cazimi' for k, *_ in p['accidental']):
            fire('cazimi', planet=p['planet'])
        if p['constellation'] == 'Ophiuchus':
            fire('ophiuchus_planet', planet=p['planet'])
    seen = set()
    for p in R['planets']:
        for k, txt, *_ in p['essential']:
            if k.startswith('reception'):
                other = txt.split(' with ')[1].split(' by ')[0]
                pair = tuple(sorted((p['planet'], other)))
                if pair not in seen:
                    seen.add(pair)
                    fire('reception', a=pair[0], b=pair[1], kind='house' if k == 'reception_house' else 'exaltation')
    if pof['house'] in (1, 4, 7, 10):
        fire('fortune_angular', house=pof['house'])
    elif pof['house'] in (3, 6, 9, 12):
        fire('fortune_cadent', house=pof['house'])

    return dict(summary=' '.join(para), strengths=out['strength'], weaknesses=out['weakness'],
                note=("The strengths and weaknesses are Lilly's own rules (Christian Astrology, 1647), chiefly his "
                      "'Considerations before Judgment' (pp.121-123), applied here to the sidereal IAU sky. "
                      "Where the app had to adapt a rule, the line says so. This is traditional symbolism for study "
                      "and reflection; controlled studies have not found astrological charts to be predictive."))


def as_text(fc, header=''):
    lines = [header, '', 'FORECAST', '', fc['summary'], '', 'Strengths:']
    lines += [f"  + {s['text']}  [{s['source']}]" for s in fc['strengths']] or ['  (none)']
    lines += ['', 'Weaknesses:'] + ([f"  - {w['text']}  [{w['source']}]" for w in fc['weaknesses']] or ['  (none)'])
    lines += ['', fc['note']]
    return '\n'.join(lines).strip() + '\n'
