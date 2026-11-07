"""
Lilly interpretation layer.

Source: William Lilly, Christian Astrology (London, 1647). Every table it uses is a CSV in data/
with page citations:
  essential_dignities.csv    p.104  houses, exaltations, triplicities, terms, faces, detriment, fall
  fortitudes_debilities.csv  p.115  the points for every fortitude and debility
  orbs_motions.csv           p.107 orbs; planet chapters for mean motions
  planet_natures.csv         Book I ch. VIII-XIIII  nature, manners well / ill dignified, etc.
  house_significations.csv   Book I ch. VII
  sign_natures.csv           Book I ch. XVI
  fixed_stars.csv            p.115
  uncertainty_log.csv        every place where the app has to adapt or choose

APP ADAPTATION (user decision): a body is read by the IAU zodiac constellation on the ecliptic at its
longitude, and that constellation is taken as the sign. Degree-based rules (terms, faces, exaltation
degree) are stretched proportionally across the constellation's true width. Ophiuchus has no
dignities in Lilly; a body there is peregrine.

Every reported item carries a tag: 'Lilly' (sourced) or 'app rule'.
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda f: os.path.join(HERE, 'data', f)
ED = pd.read_csv(D('essential_dignities.csv'), encoding='utf-8').fillna('')
FD = pd.read_csv(D('fortitudes_debilities.csv'), encoding='utf-8').set_index('rule_id')
OM = pd.read_csv(D('orbs_motions.csv'), encoding='utf-8').set_index('planet')
PN = pd.read_csv(D('planet_natures.csv'), encoding='utf-8').fillna('').set_index('planet')
HS = pd.read_csv(D('house_significations.csv'), encoding='utf-8').fillna('').set_index('house')
SN = pd.read_csv(D('sign_natures.csv'), encoding='utf-8').fillna('').set_index('sign')
ST = pd.read_csv(D('fixed_stars.csv'), encoding='utf-8').set_index('star')
BY_IAU = ED.set_index('iau_constellation')
BY_SIGN = ED.set_index('sign')
PLANETS = ['Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus', 'Mercury', 'Moon']
SUPERIOR, INFERIOR = {'Saturn', 'Jupiter', 'Mars'}, {'Venus', 'Mercury'}
ASPECTS = [('conjunction', 0), ('sextile', 60), ('square', 90), ('trine', 120), ('opposition', 180)]
PARTILE_DEG = 1.0            # app rule (uncertainty_log: partile_definition)
COMBUST, BEAMS, CAZIMI = 8.5, 17.0, 17 / 60   # Lilly p.113
STAR_ORB = 5.0


def P(rule):
    return int(FD.loc[rule, 'points'])


def W(rule):
    return FD.loc[rule, 'lilly_wording']


def sep(a, b):
    return abs(((a - b + 180) % 360) - 180)


# ---------------------------------------------------------------- sign placement
def band_of(lon, bands):
    """bands: [(start_lon, abbr, name)] from sidereal_engine.ecliptic_constellation_bands.
    Returns (name, start, width, fraction)."""
    starts = [b[0] for b in bands]
    for i, (s, abbr, name) in enumerate(bands):
        e = starts[(i + 1) % len(bands)]
        w = (e - s) % 360 or 360
        off = (lon - s) % 360
        if off < w:
            return name, s, w, off / w
    return bands[0][2], bands[0][0], 30.0, 0.0


def placement(lon, bands):
    """Sign (= IAU zodiac constellation) and equivalent degree 0-30 (rescaled, app rule)."""
    name, s, w, f = band_of(lon, bands)
    if name in BY_IAU.index:
        sign = BY_IAU.loc[name, 'sign']
        return dict(constellation=name, sign=sign, sign_deg=30.0 * f, band_start=s, band_width=w, has_sign=True)
    return dict(constellation=name, sign=None, sign_deg=None, band_start=s, band_width=w, has_sign=False)


def term_ruler(sign, deg):
    r = BY_SIGN.loc[sign]
    for i in range(1, 6):
        if deg < float(r[f'term{i}_end']):
            return r[f'term{i}']
    return r['term5']


def face_ruler(sign, deg):
    return BY_SIGN.loc[sign, f'face{min(int(deg // 10), 2) + 1}']


# ---------------------------------------------------------------- essential dignity
def essential(planet, pl, is_day, placements):
    """Lilly p.104 / p.115. placements: {planet: placement dict} for mutual reception."""
    items = []
    if not pl['has_sign']:
        items.append(('peregrine', W('peregrine') + f" (in {pl['constellation']}, which has no sign in Lilly)",
                      P('peregrine'), 'app rule'))
        return items
    r = BY_SIGN.loc[pl['sign']]
    deg = pl['sign_deg']
    own = False
    if r['house_ruler'] == planet:
        items.append(('house', 'In his own house', P('house_or_mutual_reception_by_house'), 'Lilly')); own = True
    if r['exaltation'] == planet:
        items.append(('exaltation', 'In his exaltation', P('exaltation_or_reception_by_exaltation'), 'Lilly')); own = True
    trip = r['triplicity_day'] if is_day else r['triplicity_night']
    if trip == planet:
        items.append(('triplicity', f"In his owne Triplicity ({'day' if is_day else 'night'})", P('triplicity'), 'Lilly')); own = True
    if term_ruler(pl['sign'], deg) == planet:
        items.append(('term', 'In his owne Terme (rescaled degree)', P('term'), 'Lilly + app rescaling')); own = True
    if face_ruler(pl['sign'], deg) == planet:
        items.append(('face', 'Decanate or Face (rescaled degree)', P('face'), 'Lilly + app rescaling')); own = True
    # mutual reception (by house, by exaltation)
    mr = False
    for other, opl in placements.items():
        if other == planet or not opl.get('has_sign'):
            continue
        o = BY_SIGN.loc[opl['sign']]
        if r['house_ruler'] == other and o['house_ruler'] == planet and not own:
            items.append(('reception_house', f'In mutual reception with {other} by house', P('house_or_mutual_reception_by_house'), 'Lilly')); mr = True
        if r['exaltation'] == other and o['exaltation'] == planet:
            items.append(('reception_exalt', f'In mutual reception with {other} by exaltation', P('exaltation_or_reception_by_exaltation'), 'Lilly')); mr = True
    if r['detriment'] == planet:
        items.append(('detriment', W('detriment'), P('detriment'), 'Lilly'))
    if r['fall'] == planet:
        items.append(('fall', W('fall'), P('fall'), 'Lilly'))
    if not own and not mr:
        items.append(('peregrine', W('peregrine'), P('peregrine'), 'Lilly'))
    return items


# ---------------------------------------------------------------- accidental
HOUSE_RULE = {1: 'house_1_10', 10: 'house_1_10', 7: 'house_7_4_11', 4: 'house_7_4_11', 11: 'house_7_4_11',
              2: 'house_2_5', 5: 'house_2_5', 9: 'house_9', 3: 'house_3', 12: 'house_12', 8: 'house_8_6', 6: 'house_8_6'}


def accidental(planet, b, house, others, nodes, stars, beams_rule='table'):
    """b: engine row (ecl_lon, speed, elong, sun_dist). others: {planet: ecl_lon}."""
    it = []
    rule = HOUSE_RULE[house]
    it.append((rule, f'In the {_ord(house)} house', P(rule), 'Lilly'))
    if planet not in ('Sun', 'Moon'):
        it.append(('retrograde', W('retrograde'), P('retrograde'), 'Lilly') if b['speed'] < 0
                  else ('direct', 'Direct', P('direct'), 'Lilly'))
    mean = OM.loc[planet, 'mean_motion_arcmin_per_day'] / 60.0
    it.append(('swift', f"Swift in motion ({abs(b['speed']) * 60:.0f}' a day; mean {OM.loc[planet, 'mean_motion_text']})", P('swift'), 'Lilly')
              if abs(b['speed']) > mean else
              ('slow', f"Slow in motion ({abs(b['speed']) * 60:.0f}' a day; mean {OM.loc[planet, 'mean_motion_text']})", P('slow'), 'Lilly'))
    e = b['elong']
    if planet in SUPERIOR:
        it.append(('superior_oriental', 'Orientall of the Sun', P('superior_oriental'), 'Lilly') if e < 0
                  else ('superior_occidental', 'Occidentall of the Sun', P('superior_occidental'), 'Lilly'))
    elif planet in INFERIOR:
        it.append(('inferior_occidental', 'Occidentall of the Sun', P('inferior_occidental'), 'Lilly') if e > 0
                  else ('inferior_oriental', 'Orientall of the Sun', P('inferior_oriental'), 'Lilly'))
    elif planet == 'Moon':
        it.append(('moon_increasing', 'Encreasing in light', P('moon_increasing'), 'Lilly') if e > 0
                  else ('moon_decreasing', 'Decreasing in light', P('moon_decreasing'), 'Lilly'))
    if planet != 'Sun':
        d = b['sun_dist']
        if d <= CAZIMI:
            it.append(('cazimi', 'In the heart of the Sun, or Cazimi', P('cazimi'), 'Lilly'))
        elif d <= COMBUST:
            it.append(('combust', f'Combust of the Sun ({d:.1f}° from him)', P('combust'), 'Lilly'))
        elif d <= BEAMS and beams_rule == 'table':
            it.append(('under_beams', f'Under the Sun Beames ({d:.1f}° from him)', P('under_beams'), 'Lilly'))
        else:
            it.append(('free_combustion', 'Free from Combustion and Sun Beams' if beams_rule == 'table' or d > BEAMS
                       else f'Free from Combustion ({d:.1f}° from the Sun; beams not counted, as in Lilly\'s example)',
                       P('free_combustion'), 'Lilly'))
    lon = b['ecl_lon']

    def partile(other_lon, angle):
        return abs(sep(lon, other_lon) - angle) <= PARTILE_DEG

    def any_partile(names, angle):
        return [n for n in names if n != planet and n in others and partile(others[n], angle)]

    for rid, names, ang, txt in (('partile_conj_jup_ven', ('Jupiter', 'Venus'), 0, 'In partill conjunction with'),
                                 ('partile_trine_jup_ven', ('Jupiter', 'Venus'), 120, 'In partill trine to'),
                                 ('partile_sextile_jup_ven', ('Jupiter', 'Venus'), 60, 'In partill sextile to'),
                                 ('partile_conj_sat_mars', ('Saturn', 'Mars'), 0, 'Partill conjunction with'),
                                 ('partile_opp_sat_mars', ('Saturn', 'Mars'), 180, 'Partill opposition of'),
                                 ('partile_square_sat_mars', ('Saturn', 'Mars'), 90, 'Partill square of')):
        hit = any_partile(names, ang)
        if hit:
            it.append((rid, f"{txt} {' and '.join(hit)} (within {PARTILE_DEG:.0f}°)", P(rid), 'Lilly (partile: app rule)'))
    if partile(nodes['North Node'], 0):
        it.append(('partile_conj_north_node', W('partile_conj_north_node'), P('partile_conj_north_node'), 'Lilly'))
    if partile(nodes['South Node'], 0):
        it.append(('partile_conj_south_node', W('partile_conj_south_node'), P('partile_conj_south_node'), 'Lilly'))
    if planet not in ('Saturn', 'Mars') and 'Saturn' in others and 'Mars' in others:
        s_, m_ = others['Saturn'], others['Mars']
        arc = sep(s_, m_)
        if arc <= 30 and abs(sep(lon, s_) + sep(lon, m_) - arc) < 1e-6:
            it.append(('besieged', W('besieged'), P('besieged'), 'Lilly (definition: app rule)'))
    for star, rid in (('Regulus', 'conj_regulus'), ('Spica', 'conj_spica'), ('Algol', 'conj_algol')):
        d = sep(lon, stars[star]['ecl_lon'])
        if d <= STAR_ORB:
            it.append((rid, f"In conjunction with {ST.loc[star, 'lilly_name']} ({d:.1f}°; within five degrees)", P(rid), 'Lilly'))
    return it


def _ord(n):
    return {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'eighth',
            9: 'ninth', 10: 'tenth', 11: 'eleventh', 12: 'twelfth'}[n]


def score(items):
    f = sum(p for _, _, p, _ in items if p > 0)
    d = -sum(p for _, _, p, _ in items if p < 0)
    return f, d, f - d


# ---------------------------------------------------------------- aspects
def aspects(rows_by, orb_col='orb_lilly'):
    """Aspects among the seven planets with Lilly's moieties: orb = half of each planet's orb (p.107, p.110).
    Applying if the faster planet is moving toward the exact aspect."""
    out = []
    for i, a in enumerate(PLANETS):
        for b_ in PLANETS[i + 1:]:
            ra, rb = rows_by[a], rows_by[b_]
            s = sep(ra['ecl_lon'], rb['ecl_lon'])
            moiety = (OM.loc[a, orb_col] + OM.loc[b_, orb_col]) / 2
            for name, ang in ASPECTS:
                dev = abs(s - ang)
                if dev <= moiety:
                    # applying test: separation change over the next hour
                    la = ra['ecl_lon'] + ra['speed'] / 24; lb = rb['ecl_lon'] + rb['speed'] / 24
                    applying = abs(sep(la, lb) - ang) < dev
                    out.append(dict(a=a, b=b_, aspect=name, angle=ang, deviation=dev, moiety=moiety,
                                    partile=dev <= PARTILE_DEG, applying=applying))
    return out


# ---------------------------------------------------------------- main entry
def interpret(rows, bands, cusps, stars, sun_up, beams_rule='table', orb_col='orb_lilly'):
    """rows: engine chart rows; bands: ecliptic bands; cusps: 12 Regiomontanus cusps;
    stars: engine fixed_stars(); sun_up: True for a day chart."""
    import sidereal_engine as se
    by = {r['body']: r for r in rows}
    pl = {p: placement(by[p]['ecl_lon'], bands) for p in PLANETS}
    nodes = {k: by[k]['ecl_lon'] for k in ('North Node', 'South Node')}
    lons = {p: by[p]['ecl_lon'] for p in PLANETS}
    out = []
    for p in PLANETS:
        b = by[p]
        h = se.house_of(b['ecl_lon'], cusps)
        ess = essential(p, pl[p], sun_up, pl)
        acc = accidental(p, b, h, lons, nodes, stars, beams_rule)
        ef, edb, en = score(ess)
        f, d, n = score(ess + acc)
        cond = 'well dignified' if en > 0 else 'ill dignified' if en < 0 else 'neither well nor ill dignified'
        out.append(dict(planet=p, constellation=pl[p]['constellation'], sign=pl[p]['sign'],
                        sign_deg=pl[p]['sign_deg'], true_constellation=b['constellation'], house=h,
                        essential=ess, accidental=acc, essential_score=en, fortitudes=f, debilities=d, net=n,
                        condition=cond, retrograde=b['speed'] < 0, speed=b['speed'], ecl_lon=b['ecl_lon']))
    asc_pl = placement(by['Ascendant']['ecl_lon'], bands)
    lord = BY_SIGN.loc[asc_pl['sign'], 'house_ruler'] if asc_pl['has_sign'] else None
    mc_pl = placement(by['Midheaven']['ecl_lon'], bands)
    pof = by['Part of Fortune']
    return dict(planets=out, asc=asc_pl, mc=mc_pl, lord_of_asc=lord, sun_up=sun_up,
                part_of_fortune=dict(ecl_lon=pof['ecl_lon'], house=se.house_of(pof['ecl_lon'], cusps),
                                     **placement(pof['ecl_lon'], bands)),
                aspects=aspects(by, orb_col), cusps=cusps,
                cusp_signs=[placement(c, bands) for c in cusps])


def reading(planet, condition):
    """Lilly's own description: 'manners when well dignified' / 'when ill dignified'."""
    r = PN.loc[planet]
    if condition == 'ill dignified':
        return r['manners_ill_dignified'], f"Lilly p.{r['ill_page']}"
    return r['manners_well_dignified'], f"Lilly p.{r['well_page']}"


def house_meaning(n, maxlen=240):
    s = HS.loc[n, 'significations']
    return (s[:maxlen].rsplit(' ', 1)[0] + ' ...') if len(s) > maxlen else s
