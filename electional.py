"""
Elections: finding auspicious moments to begin an undertaking, framed from Lilly's own principles.

Lilly gives no separate treatise on elections. In his epistle to the reader he says that whoever has
studied his book will be "able (ad libitum) to frame his owne Figure of Elections, let the quere be what it
will". This module does that with his rules, each cited in data/election_rules.csv:

  * the house of the matter and its lord (Book I ch. VII), with the Lord of the Ascendant for the person;
  * perfection: the two significators applying by conjunction, sextile, trine, or (only with dignity) square;
    opposition rarely and badly; reception; translation of light by the Moon (ch. XXI, pp.124-126);
  * the strength of the significators and the Moon by the table of fortitudes and debilities (p.115);
  * the natural significator of the matter, with the Moon in good aspect to it (cf. p.65) and its planetary hour;
  * the "Considerations before Judgment" (pp.121-123), applied as cautions that mark a moment 'avoid'.

The weights that combine these into one number are app choices; they are in the CSV and can be edited.
"""
import os
import datetime as dt
import numpy as np
import pandas as pd
from skyfield import almanac
from skyfield.api import wgs84
from skyfield.framelib import ecliptic_frame

import sidereal_engine as se
import lilly_layer as ll
import forecast

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, 'data', 'election_rules.csv')

UNDERTAKINGS = {
    'romance': dict(label='Romance', house=7, natural='Venus',
                    note="Romance can be interpreted as beginning a new romance or finding the optimal times to connect with your current partner.",
                    why="Lilly: the 7th house 'giveth judgement of Marriage ... all manner of Love questions ... Wives, "
                        "Sweet-harts' (p.54). Venus, 'oft entangled in Love-matters' (p.73), is the natural significator."),
    'friendship': dict(label='Friendship', house=11, natural='Jupiter',
                       note="Friendship can be interpreted as finding new connections or finding the optimal times to connect with your current friends.",
                       why="Lilly: the 11th house 'doth naturally represent Friends and Friendship, Hope, Trust, Confidence' "
                           "(p.56). Jupiter 'doth especially rejoyce in this House' (p.56) and is taken as natural significator."),
    'transition': dict(label='Make a life transition (move, new chapter)', house=4, natural='Moon',
                       why="Lilly: the 4th house signifies 'Houses ... the determination or end of any thing ... all ancient "
                           "Dwellings' (pp.52-53). The Moon, 'naturally propense to flit and shift his Habitation' (p.81), is the "
                           "natural significator of change."),
    'project': dict(label='Initiate a project or enterprise', house=10, natural='Mercury',
                    why="Lilly: the 10th house signifies 'the profession or Trade any one useth ... Honour, Preferment' "
                        "(pp.55-56). Mercury, significator of merchants, secretaries and all manner of business, is taken as "
                        "natural significator (app choice; see Sources)."),
}


def load_rules():
    r = pd.read_csv(RULES, encoding='utf-8')
    r = r[r['enabled'].astype(str).str.lower().isin(['true', '1', 'yes'])]
    return r.set_index('rule_id')


# ------------------------------------------------------------------ vectorised astronomy
def _true_obliquity(t):
    from skyfield import nutationlib
    mean = nutationlib.mean_obliquity(t.tdb) / 3600.0
    _, deps = nutationlib.iau2000a_radians(t)
    return mean + np.degrees(deps)


def scan_positions(times_utc, lat, lon, elev=0.0):
    """times_utc: list of aware UTC datetimes. Returns dict of arrays (deg)."""
    ts = se.ts
    t = ts.from_datetimes(times_utc)
    t0, t1 = ts.tt_jd(t.tt - 0.5), ts.tt_jd(t.tt + 0.5)
    obs = se.EARTH + wgs84.latlon(lat, lon, elevation_m=elev)
    out = {}
    for name in ll.PLANETS:
        key = se.BODIES[name]
        app = obs.at(t).observe(se.eph[key]).apparent()
        _, elon, _ = app.frame_latlon(ecliptic_frame)
        l0 = obs.at(t0).observe(se.eph[key]).apparent().frame_latlon(ecliptic_frame)[1].degrees
        l1 = obs.at(t1).observe(se.eph[key]).apparent().frame_latlon(ecliptic_frame)[1].degrees
        out[name] = elon.degrees
        out[name + '_speed'] = ((l1 - l0 + 180) % 360) - 180
        if name == 'Sun':
            out['sun_alt'] = app.altaz()[0].degrees
    # angles and Regiomontanus cusps, vectorised (same formulas as sidereal_engine)
    eps = np.radians(_true_obliquity(t))
    ramc = (t.gast * 15.0 + lon) % 360.0
    phi = np.radians(lat)
    R = np.radians(ramc)
    asc = np.degrees(np.arctan2(np.cos(R), -(np.sin(R) * np.cos(eps) + np.tan(phi) * np.sin(eps)))) % 360
    mc = np.degrees(np.arctan2(np.sin(R), np.cos(R) * np.cos(eps))) % 360
    c = {1: asc, 10: mc}
    for h, D in ((11, 30), (12, 60), (2, 120), (3, 150)):
        ra = np.radians(ramc + D)
        pole = np.arctan(np.tan(phi) * np.sin(np.radians(D)))
        c[h] = np.degrees(np.arctan2(np.sin(ra), np.cos(ra) * np.cos(eps) - np.tan(pole) * np.sin(eps))) % 360
    c[4], c[5], c[6] = (c[10] + 180) % 360, (c[11] + 180) % 360, (c[12] + 180) % 360
    c[7], c[8], c[9] = (c[1] + 180) % 360, (c[2] + 180) % 360, (c[3] + 180) % 360
    out['cusps'] = np.stack([c[i] for i in range(1, 13)], axis=1)
    out['asc'], out['mc'] = asc, mc
    T = (t.tt - 2451545.0) / 36525.0
    out['node'] = (125.0445479 - 1934.1362891 * T + 0.0020754 * T * T) % 360
    return t, out


def sun_events(lat, lon, elev, start_utc, end_utc):
    """Sunrises and sunsets (UTC datetimes) between start-1d and end+1d."""
    ts = se.ts
    ta, tb = ts.from_datetime(start_utc - dt.timedelta(days=1.5)), ts.from_datetime(end_utc + dt.timedelta(days=1.5))
    rises, sets = se._rise_set(lat, lon, elev, ta, tb)
    return [r.utc_datetime() for r in rises], [s.utc_datetime() for s in sets]


def planetary_hour_at(when, rises, sets, lon):
    """Same rule as sidereal_engine.planetary_hour, using pre-computed sunrises/sunsets."""
    prev = [r for r in rises if r <= when]
    nxt = [r for r in rises if r > when]
    if prev and nxt:
        r0, r1 = prev[-1], nxt[0]
        ss = [s for s in sets if r0 < s < r1]
        if ss:
            s0 = ss[0]
            wd = (r0 + dt.timedelta(hours=lon / 15.0)).weekday()
            if when < s0:
                n = int((when - r0) / ((s0 - r0) / 12)) + 1
            else:
                n = 13 + int((when - s0) / ((r1 - s0) / 12))
            day = se.WEEKDAY_RULER[wd]
            return day, se.CHALDEAN[(se.CHALDEAN.index(day) + n - 1) % 7], n, False
    lmt = when + dt.timedelta(hours=lon / 15.0)
    day = se.WEEKDAY_RULER[lmt.weekday()]
    n = lmt.hour + 1
    return day, se.CHALDEAN[(se.CHALDEAN.index(day) + n - 1) % 7], n, True


# ------------------------------------------------------------------ judging one moment
def _rows_at(i, P):
    rows = []
    sun = P['Sun'][i]
    for name in ll.PLANETS:
        lon = float(P[name][i]); e = ((lon - sun + 180) % 360) - 180
        rows.append(dict(body=name, ecl_lon=lon, speed=float(P[name + '_speed'][i]), elong=e, sun_dist=abs(e),
                         alt=float(P['sun_alt'][i]) if name == 'Sun' else 0.0, constellation=''))
    nn = float(P['node'][i])
    asc = float(P['asc'][i])
    rows += [dict(body='North Node', ecl_lon=nn), dict(body='South Node', ecl_lon=(nn + 180) % 360),
             dict(body='Part of Fortune', ecl_lon=(asc + P['Moon'][i] - sun) % 360),
             dict(body='Ascendant', ecl_lon=asc), dict(body='Midheaven', ecl_lon=float(P['mc'][i]))]
    return rows


def _applying(a, b, rows_by, ang):
    ra, rb = rows_by[a], rows_by[b]
    dev = abs(ll.sep(ra['ecl_lon'], rb['ecl_lon']) - ang)
    la = ra['ecl_lon'] + ra['speed'] / 24; lb = rb['ecl_lon'] + rb['speed'] / 24
    return abs(ll.sep(la, lb) - ang) < dev


def judge(rows, bands, cusps, stars, sun_up, kind, hour_ruler, rules, beams_rule='table', R=None):
    """Score one moment for an undertaking. Returns dict(score, avoid, items, plain, R).
    R: the chart already interpreted by lilly_layer (optional; saves time when judging several undertakings)."""
    u = UNDERTAKINGS[kind]
    if R is None:
        R = ll.interpret(rows, bands, cusps, stars, sun_up, beams_rule=beams_rule)
    P = {p['planet']: p for p in R['planets']}
    by = {r['body']: r for r in rows}
    items = []     # (rule_id, text, points, source, kind)
    plains = []    # the same lines in plain English (data/election_rules.csv, column 'plain')

    def add(rid, **kw):
        if rid in rules.index:
            r = rules.loc[rid]
            items.append((rid, r['text'].format(**kw), float(r['points']), r['source'], r['kind']))
            pl = r.get('plain')
            plains.append((pl if isinstance(pl, str) and pl.strip() else r['text']).format(**kw))

    lord1 = R['lord_of_asc']
    cm = R['cusp_signs'][u['house'] - 1]
    lordm = ll.BY_SIGN.loc[cm['sign'], 'house_ruler'] if cm['has_sign'] else None
    nat = u['natural']
    hn = u['house']
    if not lord1:
        add('asc_no_lord', con=R['asc']['constellation'])
    if not lordm:
        add('matter_no_lord', h=ll._ord(hn), con=cm['constellation'])

    # --- cautions (Considerations before Judgment) -> 'avoid'
    if R['asc']['has_sign']:
        d = R['asc']['sign_deg']
        if d < 3:
            add('asc_early', deg=d, sign=R['asc']['sign'])
        elif d >= 27:
            add('asc_late', deg=d, sign=R['asc']['sign'])
    mo = P['Moon']
    if (mo['sign'] == 'Libra' and mo['sign_deg'] >= 15) or (mo['sign'] == 'Scorpio' and mo['sign_deg'] < 15):
        add('moon_via_combusta')
    void, band, _ = forecast.moon_void(rows, bands)
    if void:
        add('moon_void', sign=band)
    if P['Saturn']['house'] == 1:
        add('saturn_asc')
    for who, wp, pl in (('the Lord of the Ascendant', 'The planet that stands for you', lord1),
                        (f'the lord of the {ll._ord(hn)}', 'The planet of the matter', lordm), ('the Moon', 'The Moon', 'Moon')):
        if pl and any(k == 'combust' for k, *_ in P[pl]['accidental']):
            add('significator_combust', who=who, who_plain=wp, planet=pl)

    # --- strength of the significators (p.115), each planet counted once
    seen = []
    for role, rp, pl in (('Lord of the Ascendant', 'The planet that stands for you', lord1),
                         (f'Lord of the {ll._ord(hn)} (the matter)', 'The planet of the matter', lordm),
                         ('Natural significator', 'The natural planet of the matter', nat), ('The Moon', 'The Moon', 'Moon')):
        if pl and pl not in seen and 'strength' in rules.index:
            seen.append(pl)
            n_ = P[pl]['net']
            word = ('strong' if n_ >= 5 else 'fairly strong' if n_ > 0 else 'neither strong nor weak' if n_ == 0
                    else 'fairly weak' if n_ > -5 else 'weak')
            add('strength', role=role, planet=('' if role == 'The Moon' else ' ' + pl), net=n_, pts=n_,
                role_plain=rp, who_paren=('' if role == 'The Moon' else f' ({pl})'), word=word)
            pts = float(rules.loc['strength', 'points']) * P[pl]['net']
            items[-1] = items[-1][:2] + (pts, items[-1][3], 'good' if pts > 0 else 'bad' if pts < 0 else 'info')
    if lordm and P[lordm]['retrograde']:
        add('matter_lord_retro', planet=lordm, h=ll._ord(hn))

    # --- perfection between Lord of the Ascendant and lord of the matter (ch. XXI)
    if lord1 and lordm:
        if lord1 == lordm:
            add('same_lord', planet=lord1, h=ll._ord(hn))
        else:
            a1, am = P[lord1], P[lordm]
            dign = a1['essential_score'] > 0 and am['essential_score'] > 0
            good_houses = a1['house'] not in (6, 8, 12) and am['house'] not in (6, 8, 12)
            for a in R['aspects']:
                if {a['a'], a['b']} == {lord1, lordm} and a['applying']:
                    asp = a['aspect']
                    if asp == 'conjunction':
                        ang = any(x['house'] in (1, 4, 7, 10) for x in (a1, am))
                        cad = all(x['house'] in (3, 6, 9, 12) for x in (a1, am))
                        add('perf_conj_cadent' if cad else 'perf_conj', a=lord1, b=lordm, dev=a['deviation'])
                    elif asp in ('sextile', 'trine'):
                        add('perf_trine_good' if (dign and good_houses) else 'perf_trine_weak', asp=asp, a=lord1, b=lordm,
                            dev=a['deviation'])
                    elif asp == 'square':
                        add('perf_square_dign' if dign and good_houses else 'perf_square_none', a=lord1, b=lordm, dev=a['deviation'])
                    elif asp == 'opposition':
                        add('perf_opposition', a=lord1, b=lordm, dev=a['deviation'])
            # reception
            for k, txt, *_ in a1['essential']:
                if k.startswith('reception') and lordm in txt:
                    add('reception', a=lord1, b=lordm)
            # translation of light by the Moon: separating from one, applying to the other
            if 'Moon' not in (lord1, lordm):
                def moon_aspect(pl):
                    for a in R['aspects']:
                        if {a['a'], a['b']} == {'Moon', pl}:
                            return a
                s1, s2 = moon_aspect(lord1), moon_aspect(lordm)
                if s1 and s2 and (s1['applying'] != s2['applying']):
                    add('translation', a=lord1, b=lordm)

    # --- the Moon and the natural significator (cf. p.65) and the planetary hour
    for a in R['aspects']:
        if 'Moon' in (a['a'], a['b']) and a['applying']:
            other = a['b'] if a['a'] == 'Moon' else a['a']
            if other == nat and a['aspect'] in ('conjunction', 'sextile', 'trine') and nat != 'Moon':
                add('moon_natural', asp=a['aspect'], planet=nat)
            elif other in ('Jupiter', 'Venus') and a['aspect'] in ('conjunction', 'sextile', 'trine'):
                add('moon_benefic', asp=a['aspect'], planet=other)
            elif other in ('Saturn', 'Mars') and a['aspect'] in ('conjunction', 'square', 'opposition'):
                add('moon_malefic', asp=a['aspect'], planet=other)
    if hour_ruler == nat:
        add('hour_natural', planet=nat)
    elif hour_ruler in ('Saturn', 'Mars') and nat not in ('Saturn', 'Mars'):
        add('hour_malefic', planet=hour_ruler)

    avoid = any(k == 'avoid' for *_, k in items)
    score = sum(p for _, _, p, _, k in items if k != 'avoid')
    plain = [(it[0], t, it[2], it[4]) for it, t in zip(items, plains)]     # (rule_id, plain text, points, kind)
    return dict(score=round(score, 1), avoid=avoid, items=items, plain=plain, R=R, lord1=lord1, lordm=lordm)


# ------------------------------------------------------------------ scanning a period
def scan(kind, lat, lon, elev, tzinfo, start_date, days, day_start=7, day_end=22, step_min=30, beams_rule='table',
         progress=None):
    """tzinfo: a zoneinfo.ZoneInfo or datetime.timezone for the local clock."""
    res, bands = scan_many((kind,), lat, lon, elev, tzinfo, start_date, days, day_start, day_end, step_min, beams_rule,
                           progress)
    return res[kind], bands


def scan_many(kinds, lat, lon, elev, tzinfo, start_date, days, day_start=7, day_end=22, step_min=30, beams_rule='table',
              progress=None):
    """Judge several undertakings over the same moments, reading each moment's chart once.
    Returns ({kind: results}, bands)."""
    rules = load_rules()
    locs = []
    for d in range(days):
        day = start_date + dt.timedelta(days=d)
        m = day_start * 60
        while m <= day_end * 60 and m < 24 * 60:      # 'until 24' means until the end of the day (no 24:00 clock time)
            locs.append(dt.datetime.combine(day, dt.time(m // 60, m % 60)).replace(tzinfo=tzinfo))
            m += step_min
    if not locs:
        raise ValueError('The range of hours is empty: choose an end hour later than the start hour.')
    utcs = [x.astimezone(dt.timezone.utc) for x in locs]
    t, P = scan_positions(utcs, lat, lon, elev)
    tmid = se.ts.from_datetime(utcs[len(utcs) // 2])
    bands = se.ecliptic_constellation_bands(tmid, step=0.05)
    if bands[0][1] == bands[-1][1]:
        bands = bands[1:]
    stars = se.fixed_stars(tmid)
    rises, sets = sun_events(lat, lon, elev, utcs[0], utcs[-1])
    out = {k: [] for k in kinds}
    n = len(utcs)
    for i, (lt, ut) in enumerate(zip(locs, utcs)):
        rows = _rows_at(i, P)
        cusps = [float(x) for x in P['cusps'][i]]
        sun_up = P['sun_alt'][i] > -0.8333
        day_r, hour_r, hn, fb = planetary_hour_at(ut, rises, sets, lon)
        R = ll.interpret(rows, bands, cusps, stars, sun_up, beams_rule=beams_rule)
        pos = {**{pl: float(P[pl][i]) for pl in ll.PLANETS}, 'Ascendant': float(P['asc'][i])}
        for kind in kinds:
            j = judge(rows, bands, cusps, stars, sun_up, kind, hour_r, rules, beams_rule, R=R)
            out[kind].append(dict(local=lt.replace(tzinfo=None), utc=ut, date=lt.date(), time=lt.strftime('%H:%M'),
                                  score=j['score'], avoid=j['avoid'], items=j['items'], day_ruler=day_r, hour_ruler=hour_r,
                                  rising=j['R']['asc']['constellation'], lord1=j['lord1'], lordm=j['lordm'],
                                  moon=j['R']['planets'][6]['constellation'], pos=pos))
        if progress and i % 40 == 0:
            progress(i / n)
    return out, bands


def grade(results):
    """Label each moment by its score relative to the others in the period (app rule):
    'avoid' if a caution applies; otherwise 'best' = top 10 %, 'good' = next 25 %, 'fair' = the rest."""
    ok = np.array([r['score'] for r in results if not r['avoid']])
    if len(ok) == 0:
        for r in results:
            r['grade'] = 'avoid'
        return None
    q90, q65 = np.percentile(ok, 90), np.percentile(ok, 65)
    for r in results:
        r['grade'] = 'avoid' if r['avoid'] else 'best' if r['score'] >= q90 else 'good' if r['score'] >= q65 else 'fair'
    return q90, q65


def windows(results, min_grade=('best', 'good')):
    """Merge consecutive moments of the same day with grade in min_grade into windows."""
    wins, cur = [], None
    for r in results:
        if r['grade'] in min_grade:
            if cur and cur['date'] == r['date'] and (r['local'] - cur['end']).total_seconds() <= 3600:
                cur['end'] = r['local']; cur['moments'].append(r)
                if r['score'] > cur['peak']['score']:
                    cur['peak'] = r
            else:
                cur = dict(date=r['date'], start=r['local'], end=r['local'], moments=[r], peak=r)
                wins.append(cur)
        else:
            cur = None
    for w in wins:
        w['grade'] = 'best' if any(m['grade'] == 'best' for m in w['moments']) else 'good'
        w['score'] = w['peak']['score']
    return sorted(wins, key=lambda w: -w['score'])


def ics(wins, label, place, step_min):
    """iCalendar text for the windows (times in UTC)."""
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Sidereal Lilly Chart//Elections//EN', 'CALSCALE:GREGORIAN']
    for k, w in enumerate(wins):
        a = w['moments'][0]['utc']; b = w['moments'][-1]['utc'] + dt.timedelta(minutes=step_min)
        reasons = '; '.join(t for _, t, p, _, kk in w['peak']['items'] if kk == 'good')[:600]
        L += ['BEGIN:VEVENT', f'UID:lilly-election-{a:%Y%m%d%H%M}-{k}@sidereal-lilly', f'DTSTAMP:{now}',
              f'DTSTART:{a:%Y%m%dT%H%M%SZ}', f'DTEND:{b:%Y%m%dT%H%M%SZ}',
              f"SUMMARY:{w['grade'].title()} time: {label}", f'LOCATION:{place}',
              'DESCRIPTION:' + (f"Score {w['score']:+.1f}. " + reasons).replace(',', '\\,').replace(';', '\\;'),
              'END:VEVENT']
    L.append('END:VCALENDAR')

    def fold(line):                      # RFC 5545: lines of at most 75 octets, continued with a space
        out, cur = [], ''
        for ch in line:
            if len((cur + ch).encode('utf-8')) > 74:
                out.append(cur); cur = ' ' + ch
            else:
                cur += ch
        return '\r\n'.join(out + [cur])
    return '\r\n'.join(fold(x) for x in L) + '\r\n'
