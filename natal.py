"""Birth charts: personal agreement of an election with a nativity, and the agreement of two nativities.

Sources (see data/natal_rules.csv for each rule, its weight and its basis):
  * Two nativities: Ptolemy, Tetrabiblos IV.7 ("Of friends and enemies"), which Lilly follows in Book III: compare the
    four principal places - Sun, Moon, Ascendant and Part of Fortune - of the two nativities. The same sign, or a
    trine or sextile between them, makes for friendship; a square or opposition for discord; an exchange of places
    (one's Sun where the other's Moon is) strengthens the bond;
    the app counts any harmony between one's Sun and the other's Moon double. For marriage (IV.5), the Sun of one and the Moon of the
    other in harmony is the chief testimony.
  * An election for a person: the moment should agree with the nativity - the fortunes Jupiter and Venus well placed
    to the native's Sun, Moon and Ascendant, the infortunes Saturn and Mars not afflicting them (Lilly, Book III,
    on transits), and the rising sign of the election in good aspect to the native's Ascendant.
The degree orbs that turn these sign-based rules into tests on the real sky are app choices. The page references to
Lilly's Book III are still to be checked against the 1647 text (marked so in natal_rules.csv).

Signs are the IAU zodiac constellations (as everywhere in this app). If the birth time is unknown, the Ascendant and
the Part of Fortune are not used, and the Moon is taken at local noon (it may be up to about 7 degrees out).
"""
import os
import pandas as pd

import sidereal_engine as se
import lilly_layer as ll
import user_profile

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, 'data', 'natal_rules.csv')
PLACES4 = ['Sun', 'Moon', 'Ascendant', 'Part of Fortune']
HARMONY = {0: 'conjunction', 60: 'sextile', 120: 'trine'}
DISCORD = {90: 'square', 180: 'opposition'}


def rules():
    r = pd.read_csv(RULES, encoding='utf-8')
    r = r[r['enabled'].astype(str).str.lower().isin(['true', '1', 'yes'])]
    return r.set_index('rule_id')


def chart_of(birth):
    """Natal positions (ecliptic longitude of date) and the IAU band of each, for a birth dict."""
    u = user_profile.birth_utc(birth)
    t, rows = se.chart((u.year, u.month, u.day, u.hour, u.minute, 0), birth['lat'], birth['lon'], 0.0)
    by = {r['body']: r for r in rows}
    places_ = {k: by[k]['ecl_lon'] for k in ('Sun', 'Moon')}
    if birth['time_known']:
        places_['Ascendant'] = by['Ascendant']['ecl_lon']
        places_['Part of Fortune'] = by['Part of Fortune']['ecl_lon']
    planets = {p: by[p]['ecl_lon'] for p in ll.PLANETS}
    bands = {k: by[k]['band'] for k in list(places_) + ll.PLANETS}
    return dict(t=t, rows=rows, places=places_, planets=planets, bands=bands, time_known=birth['time_known'])


def _aspect(a, b, orb):
    s = ll.sep(a, b)
    for ang, name in {**HARMONY, **DISCORD}.items():
        if abs(s - ang) <= orb:
            return name, abs(s - ang)
    return None, None


# ---------------------------------------------------------------- one person and one moment
def election_items(pos, natal, whose, R=None):
    """Personal points for an election moment. pos: {planet: lon, 'Ascendant': lon} of the moment.
    natal: chart_of(). whose: 'your' or "Anna's", used in the text. Returns a list of (rule_id, text, points, source, kind)."""
    R = R if R is not None else rules()
    out = []

    def add(rid, **kw):
        if rid in R.index:
            r = R.loc[rid]
            out.append((rid, r['text'].format(whose=whose, **kw), float(r['points']), r['source'], r['kind']))

    o_tr = float(R.loc['benefic_to_natal', 'orb']) if 'benefic_to_natal' in R.index else 3.0
    targets = [k for k in ('Sun', 'Moon', 'Ascendant') if k in natal['places']]
    for pl in ('Jupiter', 'Venus'):
        for k in targets:
            asp, dev = _aspect(pos[pl], natal['places'][k], o_tr)
            if asp in HARMONY.values():
                add('benefic_to_natal', planet=pl, asp=asp, point=k, dev=dev)
    for pl in ('Saturn', 'Mars'):
        for k in targets:
            asp, dev = _aspect(pos[pl], natal['places'][k], o_tr)
            if asp in ('conjunction', 'square', 'opposition'):
                add('malefic_to_natal', planet=pl, asp=asp, point=k, dev=dev)
    o_m = float(R.loc['moon_to_natal', 'orb']) if 'moon_to_natal' in R.index else 5.0
    for k in ('Sun', 'Moon'):
        asp, dev = _aspect(pos['Moon'], natal['places'][k], o_m)
        if asp in ('sextile', 'trine'):
            add('moon_to_natal', asp=asp, point=k, dev=dev)
    if 'Ascendant' in natal['places']:
        o_a = float(R.loc['asc_agrees', 'orb']) if 'asc_agrees' in R.index else 10.0
        asp, dev = _aspect(pos['Ascendant'], natal['places']['Ascendant'], o_a)
        if asp in HARMONY.values():
            add('asc_agrees', asp=asp, dev=dev)
        elif asp in DISCORD.values():
            add('asc_disagrees', asp=asp, dev=dev)
    return out


def personalise(results, natal, whose):
    """Add a person's natal points to scan results (copies). Returns new list with score/items updated."""
    R = rules()
    out = []
    for r in results:
        extra = election_items(r['pos'], natal, whose, R)
        rr = dict(r)
        rr['items'] = list(r['items']) + extra
        rr['score'] = round(r['score'] + sum(p for _, _, p, _, k in extra if k != 'avoid'), 1)
        out.append(rr)
    return out


# ---------------------------------------------------------------- two nativities
def synastry(na, nb, name_a, name_b):
    """Ptolemy's comparison of the four places of two nativities. Returns dict(items, harmony, discord, summary)."""
    R = rules()
    orb = float(R.loc['syn_harmony', 'orb']) if 'syn_harmony' in R.index else 8.0
    items = []
    for ka in PLACES4:
        if ka not in na['places']:
            continue
        for kb in PLACES4:
            if kb not in nb['places']:
                continue
            asp, dev = _aspect(na['places'][ka], nb['places'][kb], orb)
            if not asp:
                continue
            same_band = na['bands'].get(ka) == nb['bands'].get(kb)
            exchange = {ka, kb} == {'Sun', 'Moon'}
            rid = 'syn_harmony' if asp in HARMONY.values() else 'syn_discord'
            r = R.loc[rid]
            pts = float(r['points']) * (2 if exchange and rid == 'syn_harmony' else 1)
            note = (' (between the lights: counted double)' if rid == 'syn_harmony' else ' (between the lights)') if exchange else ''
            note += ' (in the same constellation)' if same_band and asp == 'conjunction' else ''
            items.append(dict(a=ka, b=kb, aspect=asp, dev=dev, points=pts, kind='good' if pts > 0 else 'bad',
                              text=f"{name_a}'s {ka} and {name_b}'s {kb}: {asp}, {dev:.1f}° from exact{note}",
                              source=r['source']))
    h = sum(i['points'] for i in items if i['points'] > 0)
    d = -sum(i['points'] for i in items if i['points'] < 0)
    if not items:
        summ = 'The four principal places of the two nativities make no aspect to each other within the orb.'
    elif h > d * 1.5:
        summ = 'The testimonies of agreement are the stronger: by Ptolemy\'s rule this promises a firm friendship.'
    elif d > h * 1.5:
        summ = 'The testimonies of discord are the stronger: by Ptolemy\'s rule the bond needs care.'
    else:
        summ = 'The testimonies of agreement and discord are nearly balanced.'
    missing = [n for n, nn in ((name_a, na), (name_b, nb)) if not nn['time_known']]
    if missing:
        summ += f" ({' and '.join(missing)}: birth time unknown, so the Ascendant and Part of Fortune are left out.)"
    return dict(items=sorted(items, key=lambda i: -abs(i['points'])), harmony=h, discord=d, summary=summ)
