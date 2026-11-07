"""
Sidereal chart engine (astronomy layer), extended for the Lilly reading.

Step 1 (astronomy): apparent topocentric positions from NASA JPL DE440s, reduced by
    Skyfield using IAU standards (ICRS frame, IAU 2000A/2006 precession-nutation,
    aberration, light-time, deflection).
Step 2 (zodiac): each body / chart point is assigned to the IAU constellation
    (Delporte 1930 boundaries, Roman 1987 lookup) that contains it. Bodies are placed by
    their *actual* RA/Dec (so a planet off the ecliptic can be in Cetus or Orion), and
    also by the IAU constellation on the ecliptic at their longitude ("ecliptic band"),
    which is the band the Lilly layer reads as the sign.
Additions for Lilly (Christian Astrology, 1647):
    - Regiomontanus house cusps (Lilly erects figures by the Tables of Regiomontanus).
    - daily motion (deg/day), retrograde flag;
    - elongation from the Sun (combustion, Sun-beams, Cazimi, oriental/occidental);
    - fixed stars Regulus, Spica, Algol (Hipparcos J2000 + proper motion);
    - mean lunar node (Dragon's Head / Tail);
    - Part of Fortune = Asc + Moon - Sun, day or night (Lilly pp.143-144);
    - planetary day and hour from local sunrise and sunset (unequal hours).

Valid date range with DE440s: 1849-12-26 to 2150-01-22. If ephem/de440.bsp (JPL, 1550-2650)
is present it is used instead.
"""
import os
from math import atan2, asin, atan, cos, sin, tan, radians, degrees, sqrt
from datetime import timedelta
from skyfield.api import Loader, wgs84, Star
from skyfield import almanac
from skyfield.framelib import ecliptic_frame
from skyfield.positionlib import position_of_radec
from skyfield import nutationlib
from skyfield.api import load_constellation_map, load_constellation_names

HERE = os.path.dirname(os.path.abspath(__file__))
_load = Loader(os.path.join(HERE, 'ephem'))
ts = _load.timescale(builtin=True)
EPH_NAME = 'de440.bsp' if os.path.exists(os.path.join(HERE, 'ephem', 'de440.bsp')) else 'de440s.bsp'
eph = _load(EPH_NAME)   # downloads de440s.bsp from JPL on first start if absent
_const_at = load_constellation_map()
_const_name = dict(load_constellation_names())
EARTH = eph['earth']

BODIES = {
    'Sun': 'sun', 'Moon': 'moon', 'Mercury': 'mercury', 'Venus': 'venus',
    'Mars': 'mars barycenter',  # DE440s has no Mars body centre; offset is centimetres
    'Jupiter': 'jupiter barycenter', 'Saturn': 'saturn barycenter',
    'Uranus': 'uranus barycenter', 'Neptune': 'neptune barycenter',
    'Pluto': 'pluto barycenter',
}
CHALDEAN = ['Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus', 'Mercury', 'Moon']
WEEKDAY_RULER = ['Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Sun']   # Monday..Sunday

# Hipparcos (ESA 1997) J2000 / ICRS: RA h, Dec deg, pm RA* mas/yr, pm Dec mas/yr, parallax mas
STARS = {
    'Regulus': dict(ra=(10, 8, 22.311), dec=(11, 58, 1.95), pmra=-248.73, pmdec=5.59, plx=41.13),
    'Spica': dict(ra=(13, 25, 11.579), dec=(-11, 9, 40.75), pmra=-42.35, pmdec=-30.67, plx=13.06),
    'Algol': dict(ra=(3, 8, 10.132), dec=(40, 57, 20.33), pmra=2.99, pmdec=-1.66, plx=36.27),
}


def _star(d):
    h, m, s = d['ra']
    dd, dm, ds = d['dec']
    sign = -1 if dd < 0 else 1
    return Star(ra_hours=h + m / 60 + s / 3600, dec_degrees=sign * (abs(dd) + dm / 60 + ds / 3600),
                ra_mas_per_year=d['pmra'], dec_mas_per_year=d['pmdec'], parallax_mas=d['plx'])


_STAR_OBJ = {k: _star(v) for k, v in STARS.items()}


def constellation_of(pos):
    abbr = _const_at(pos)
    return abbr, _const_name[abbr]


def _true_obliquity_deg(t):
    mean = nutationlib.mean_obliquity(t.tdb) / 3600.0
    _, deps = nutationlib.iau2000a_radians(t)
    return mean + degrees(deps)


def ecliptic_point_constellation(lon_deg, t):
    """IAU constellation containing the ecliptic-of-date point (lon, lat=0)."""
    eps = radians(_true_obliquity_deg(t))
    lam = radians(lon_deg)
    ra = atan2(sin(lam) * cos(eps), cos(lam)) % (2 * 3.141592653589793)
    dec = degrees(asin(sin(eps) * sin(lam)))
    pos = position_of_radec(degrees(ra) / 15.0, dec, epoch=t)
    return constellation_of(pos)


def ramc_deg(t, lon_deg):
    return (t.gast * 15.0 + lon_deg) % 360.0


def angles(t, lat_deg, lon_deg):
    """Ascendant and Midheaven (ecliptic longitude of date, degrees)."""
    ramc = radians(ramc_deg(t, lon_deg))
    eps = radians(_true_obliquity_deg(t))
    phi = radians(lat_deg)
    asc = degrees(atan2(cos(ramc), -(sin(ramc) * cos(eps) + tan(phi) * sin(eps)))) % 360
    mc = degrees(atan2(sin(ramc), cos(ramc) * cos(eps))) % 360
    return asc, mc


def regiomontanus_cusps(t, lat_deg, lon_deg):
    """Cusps 1..12 (ecliptic longitude of date, deg) by Regiomontanus: the celestial equator is
    divided into twelve 30-degree arcs from the meridian, and each house circle passes through
    the north and south points of the horizon. Pole of the house circle at meridian distance D:
    tan(pole) = tan(lat) * sin(D).  Cusp: lambda = atan2(sin RA, cos RA cos e - tan(pole) sin e)."""
    ramc = ramc_deg(t, lon_deg)
    eps = radians(_true_obliquity_deg(t))
    phi = radians(lat_deg)
    asc, mc = angles(t, lat_deg, lon_deg)
    c = {10: mc, 1: asc}
    for house, D in ((11, 30), (12, 60), (2, 120), (3, 150)):
        ra = radians(ramc + D)
        pole = atan(tan(phi) * sin(radians(D)))
        lam = degrees(atan2(sin(ra), cos(ra) * cos(eps) - tan(pole) * sin(eps))) % 360
        c[house] = lam
    c[4], c[5], c[6] = (c[10] + 180) % 360, (c[11] + 180) % 360, (c[12] + 180) % 360
    c[7], c[8], c[9] = (c[1] + 180) % 360, (c[2] + 180) % 360, (c[3] + 180) % 360
    return [c[i] for i in range(1, 13)]


def house_of(lon, cusps, five_degree_rule=True):
    """House (1..12) of an ecliptic longitude. Lilly p.33: a planet within five degrees of the
    cusp of the next house has its virtue assigned to that house."""
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        width = (b - a) % 360
        off = (lon - a) % 360
        if off < width:
            h = i + 1
            if five_degree_rule and width - off <= 5.0:
                h = h % 12 + 1
            return h
    return 1


def _ecl(app):
    elat, elon, _ = app.frame_latlon(ecliptic_frame)
    return elon.degrees, elat.degrees


def mean_node_deg(t):
    """Mean longitude of the Moon's ascending node, ecliptic of date (Meeus, Astr. Alg. 47.7)."""
    T = (t.tt - 2451545.0) / 36525.0
    om = 125.0445479 - 1934.1362891 * T + 0.0020754 * T * T + T ** 3 / 467441 - T ** 4 / 60616000
    return om % 360


def chart(utc, lat_deg, lon_deg, elev_m=0.0):
    """utc: (Y, M, D, h, m, s). Returns (t, rows). Positions are topocentric apparent."""
    t = ts.utc(*utc)
    t0, t1 = ts.tt_jd(t.tt - 0.5), ts.tt_jd(t.tt + 0.5)
    topo = wgs84.latlon(lat_deg, lon_deg, elevation_m=elev_m)
    observer = EARTH + topo
    rows = []
    for name, key in BODIES.items():
        app = observer.at(t).observe(eph[key]).apparent()
        ra, dec, dist = app.radec(epoch='date')
        elon, elat = _ecl(app)
        alt, az, _ = app.altaz()
        abbr, cname = constellation_of(app)
        l0, _ = _ecl(observer.at(t0).observe(eph[key]).apparent())
        l1, _ = _ecl(observer.at(t1).observe(eph[key]).apparent())
        speed = ((l1 - l0 + 180) % 360) - 180          # deg per day
        rows.append(dict(body=name, ra_h=ra.hours, dec_deg=dec.degrees, ecl_lon=elon, ecl_lat=elat,
                         alt=alt.degrees, az=az.degrees, dist_au=dist.au, speed=speed,
                         retrograde=speed < 0, const=abbr, constellation=cname))
    sun_lon = rows[0]['ecl_lon']
    for r in rows:
        r['elong'] = ((r['ecl_lon'] - sun_lon + 180) % 360) - 180   # + = east of (ahead of) the Sun
        r['sun_dist'] = abs(r['elong'])
    nn = mean_node_deg(t)
    asc, mc = angles(t, lat_deg, lon_deg)
    moon_lon = rows[1]['ecl_lon']
    fortune = (asc + moon_lon - sun_lon) % 360
    for name, lon in (('North Node', nn), ('South Node', (nn + 180) % 360), ('Part of Fortune', fortune),
                      ('Ascendant', asc), ('Midheaven', mc)):
        abbr, cname = ecliptic_point_constellation(lon, t)
        rows.append(dict(body=name, ecl_lon=lon, ecl_lat=0.0, const=abbr, constellation=cname))
    for r in rows:
        r['band_abbr'], r['band'] = ecliptic_point_constellation(r['ecl_lon'], t)
    return t, rows


def fixed_stars(t):
    """Geocentric apparent ecliptic longitude/latitude of date of Regulus, Spica, Algol."""
    out = {}
    for k, s in _STAR_OBJ.items():
        app = EARTH.at(t).observe(s).apparent()
        lon, lat = _ecl(app)
        out[k] = dict(ecl_lon=lon, ecl_lat=lat)
    return out


def ecliptic_constellation_bands(t, step=0.01):
    """Where the ecliptic of date crosses IAU boundaries: list of (start_lon, abbr, name)."""
    bands, prev = [], None
    n = int(360 / step)
    for i in range(n):
        lon = i * step
        abbr, cname = ecliptic_point_constellation(lon, t)
        if abbr != prev:
            bands.append((round(lon, 2), abbr, cname))
            prev = abbr
    return bands


def _rise_set(lat, lon, elev, ta, tb):
    topo = wgs84.latlon(lat, lon, elevation_m=elev)
    horizon = -0.8333 - 0.0293 * sqrt(max(elev, 0.0))
    tr, yr = almanac.find_risings(EARTH + topo, eph['sun'], ta, tb, horizon_degrees=horizon)
    tset, ys = almanac.find_settings(EARTH + topo, eph['sun'], ta, tb, horizon_degrees=horizon)
    rises = [x for x, ok in zip(tr, yr) if ok]
    sets = [x for x, ok in zip(tset, ys) if ok]
    return rises, sets


def planetary_hour(t, lat, lon, elev=0.0):
    """Planetary day and hour (Lilly: the day's planet rules the first hour from sunrise and the
    eighth). Unequal hours: day = sunrise..sunset / 12, night = sunset..next sunrise / 12.
    Returns dict with day_ruler, hour_ruler, hour_number (1-24), weekday, sunrise/sunset times,
    and fallback flag (polar day/night: equal hours from local-mean-time midnight)."""
    ta, tb = ts.tt_jd(t.tt - 1.6), ts.tt_jd(t.tt + 1.6)
    rises, sets = _rise_set(lat, lon, elev, ta, tb)
    prev_r = [r for r in rises if r.tt <= t.tt]
    next_r = [r for r in rises if r.tt > t.tt]
    if prev_r and next_r:
        r0, r1 = prev_r[-1], next_r[0]
        ss = [s for s in sets if r0.tt < s.tt < r1.tt]
        if ss:
            s0 = ss[0]
            lmt = r0.utc_datetime() + timedelta(hours=lon / 15.0)
            wd = lmt.weekday()
            if t.tt < s0.tt:
                n = int((t.tt - r0.tt) / ((s0.tt - r0.tt) / 12))
                hour_no = n + 1
                part = 'day'
            else:
                n = int((t.tt - s0.tt) / ((r1.tt - s0.tt) / 12))
                hour_no = 13 + n
                part = 'night'
            day_ruler = WEEKDAY_RULER[wd]
            hr = CHALDEAN[(CHALDEAN.index(day_ruler) + hour_no - 1) % 7]
            return dict(day_ruler=day_ruler, hour_ruler=hr, hour_number=hour_no, part=part,
                        weekday=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][wd],
                        sunrise=r0.utc_datetime(), sunset=s0.utc_datetime(), next_sunrise=r1.utc_datetime(),
                        fallback=False)
    # polar fallback: equal hours from local mean midnight
    lmt = t.utc_datetime() + timedelta(hours=lon / 15.0)
    wd = lmt.weekday()
    hour_no = lmt.hour + 1
    day_ruler = WEEKDAY_RULER[wd]
    hr = CHALDEAN[(CHALDEAN.index(day_ruler) + hour_no - 1) % 7]
    return dict(day_ruler=day_ruler, hour_ruler=hr, hour_number=hour_no, part='equal hours',
                weekday=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][wd],
                sunrise=None, sunset=None, next_sunrise=None, fallback=True)
