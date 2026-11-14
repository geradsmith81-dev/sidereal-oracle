"""
astrosophy_engine.py - the astronomy behind the Astrosophy Star Chart.

* Ephemeris: JPL DE440s through Skyfield (dates 1850-2149). If the larger
  de440.bsp (1550-2650) is put in the ephem folder, it is used instead.
* Positions are geocentric apparent (as in printed ephemerides, the convention
  Sucher worked from), in the true ecliptic and equinox of date.
  Heliocentric positions are geometric, seen from the Sun's centre.
* Constellations: official IAU boundaries (Delporte 1930) via Skyfield's
  constellation map. Each body gets
    - iau_true : the IAU constellation at its real position in the sky, and
    - zodiac   : the IAU constellation on the ecliptic at the body's longitude
                 (13 bands incl. Ophiuchus). Readings use the zodiac band;
                 if the two differ the body is flagged "off the zodiac".
* Angles: Ascendant / MC from apparent sidereal time and true obliquity.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
from skyfield.api import Loader, load_constellation_map, load_constellation_names
from skyfield.framelib import ecliptic_frame, ecliptic_J2000_frame
from skyfield.positionlib import position_of_radec
from skyfield.nutationlib import iau2000b_radians, mean_obliquity

HERE = os.path.dirname(os.path.abspath(__file__))
# inside the Oracle apps this package sits in a sub-folder: the JPL file is the app's own (its ephem folder)
EPHEM_DIR = os.path.join(os.path.dirname(HERE), "ephem")

BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
          "Uranus", "Neptune", "Pluto"]
CLASSICAL = BODIES[:7]
_SEGMENT = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus",
            "Mars": "mars barycenter", "Jupiter": "jupiter barycenter",
            "Saturn": "saturn barycenter", "Uranus": "uranus barycenter",
            "Neptune": "neptune barycenter", "Pluto": "pluto barycenter"}
GLYPH = {"Sun": "\u2609", "Moon": "\u263D", "Mercury": "\u263F", "Venus": "\u2640",
         "Mars": "\u2642", "Jupiter": "\u2643", "Saturn": "\u2644", "Uranus": "\u2645",
         "Neptune": "\u2646", "Pluto": "\u2647", "Earth": "\u2641", "Node": "\u260A"}
ZODIAC_IAU = ["Ari", "Tau", "Gem", "Cnc", "Leo", "Vir", "Lib", "Sco", "Oph", "Sgr", "Cap", "Aqr", "Psc"]
ZODIAC_NAME = {"Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Cnc": "Cancer", "Leo": "Leo",
               "Vir": "Virgo", "Lib": "Libra", "Sco": "Scorpio", "Oph": "Ophiuchus",
               "Sgr": "Sagittarius", "Cap": "Capricorn", "Aqr": "Aquarius", "Psc": "Pisces"}
TROPICAL = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIDEREAL_MONTH = 27.321661  # days


# --------------------------------------------------------------------------- data
class _Sky:
    def __init__(self):
        load = Loader(EPHEM_DIR, verbose=False)
        self.ts = load.timescale(builtin=True)
        full = os.path.join(EPHEM_DIR, "de440.bsp")
        self.ephem_name = "de440.bsp" if os.path.exists(full) else "de440s.bsp"
        self.eph = load(self.ephem_name)
        self.earth, self.sun = self.eph["earth"], self.eph["sun"]
        self.seg = {b: self.eph[s] for b, s in _SEGMENT.items()}
        self.constellation_at = load_constellation_map()
        self.full_names = dict(load_constellation_names())
        if self.ephem_name == "de440.bsp":
            self.earliest, self.latest = datetime(1550, 1, 1, tzinfo=timezone.utc), datetime(2649, 12, 31, tzinfo=timezone.utc)
        else:
            self.earliest, self.latest = datetime(1850, 1, 1, tzinfo=timezone.utc), datetime(2149, 12, 31, tzinfo=timezone.utc)


_SKY = None


def sky() -> _Sky:
    global _SKY
    if _SKY is None:
        _SKY = _Sky()
    return _SKY


def con_name(abbr: str) -> str:
    """'Sco' -> 'Scorpio' for zodiac, otherwise the IAU full name ('Cetus')."""
    return ZODIAC_NAME.get(abbr) or sky().full_names.get(abbr, abbr)


# --------------------------------------------------------------------------- helpers
def to_time(dt_utc: datetime):
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return sky().ts.from_datetime(dt_utc)


def wrap180(x):
    return (np.asarray(x) + 180.0) % 360.0 - 180.0


def true_obliquity_deg(t) -> float:
    """Mean obliquity (arcsec -> deg) plus nutation in obliquity."""
    _d_psi, d_eps = iau2000b_radians(t)
    return mean_obliquity(t.tdb) / 3600.0 + math.degrees(d_eps)


def ecl_lon_lat(position, frame=ecliptic_frame):
    lat, lon, dist = position.frame_latlon(frame)
    return lon.degrees, lat.degrees, dist.au


def zodiac_band_at(lon_deg, t):
    """IAU constellation on the ecliptic (latitude 0) at ecliptic longitude(s)
    of date `lon_deg` at time t.  Vectorised over lon_deg."""
    S = sky()
    lon = np.radians(np.atleast_1d(lon_deg).astype(float))
    v_ecl = np.array([np.cos(lon), np.sin(lon), np.zeros_like(lon)])
    R = ecliptic_frame.rotation_at(t)          # ICRS -> ecliptic of date
    v = R.T @ v_ecl
    ra = (np.degrees(np.arctan2(v[1], v[0])) % 360.0) / 15.0
    dec = np.degrees(np.arcsin(np.clip(v[2], -1, 1)))
    out = S.constellation_at(position_of_radec(ra, dec))
    return np.atleast_1d(out)


def ecliptic_bands(t, step=0.02):
    """List of (abbr, start_lon, end_lon) along the ecliptic of date, start at
    the band containing 0 deg.  Used for the wheel and band look-ups."""
    lons = np.arange(0.0, 360.0, step)
    ab = zodiac_band_at(lons, t)
    bands, start = [], 0.0
    for i in range(1, len(lons)):
        if ab[i] != ab[i - 1]:
            # refine boundary to ~1e-4 deg by bisection
            lo, hi = lons[i - 1], lons[i]
            for _ in range(10):
                mid = 0.5 * (lo + hi)
                if zodiac_band_at(mid, t)[0] == ab[i - 1]:
                    lo = mid
                else:
                    hi = mid
            bands.append([str(ab[i - 1]), start, hi])
            start = hi
    bands.append([str(ab[-1]), start, 360.0])
    if bands[0][0] == bands[-1][0] and len(bands) > 1:  # merge wrap-around band
        first = bands.pop(0)
        bands[-1][2] = 360.0 + first[2]
    return [tuple(b) for b in bands]


def angles(t, lat_deg, lon_deg):
    """Ascendant, MC (ecliptic longitudes of date, degrees) and the local
    apparent sidereal time (deg)."""
    eps = math.radians(true_obliquity_deg(t))
    theta = math.radians((t.gast * 15.0 + lon_deg) % 360.0)
    phi = math.radians(lat_deg)
    mc = math.degrees(math.atan2(math.sin(theta), math.cos(theta) * math.cos(eps))) % 360.0
    asc = math.degrees(math.atan2(math.cos(theta),
                                  -(math.sin(theta) * math.cos(eps) + math.tan(phi) * math.sin(eps)))) % 360.0
    # Above the polar circles the formula can return the western (setting)
    # intersection of ecliptic and horizon.  Keep the eastern one (hour angle < 0).
    l = math.radians(asc)
    ra = math.atan2(math.sin(l) * math.cos(eps), math.cos(l))
    ha = (math.degrees(theta - ra) + 180.0) % 360.0 - 180.0
    if ha > 0:
        asc = (asc + 180.0) % 360.0
    return asc, mc, math.degrees(theta)


def mean_node_lon(t) -> float:
    """Mean ascending node of the Moon (Meeus, Astronomical Algorithms 47.7)."""
    T = (t.tt - 2451545.0) / 36525.0
    return (125.0445479 - 1934.1362891 * T + 0.0020754 * T ** 2 + T ** 3 / 467441.0
            - T ** 4 / 60616000.0) % 360.0


# --------------------------------------------------------------------------- chart
@dataclass
class Body:
    name: str
    lon: float              # geocentric apparent ecliptic longitude of date (= tropical)
    lat: float
    speed: float            # deg/day (negative = retrograde)
    zodiac: str             # IAU zodiac band at this longitude (abbr)
    iau_true: str           # IAU constellation at the true position (abbr)
    helio_lon: float | None = None
    helio_zodiac: str | None = None
    note: str = ""

    @property
    def off_zodiac(self) -> bool:
        return self.iau_true != self.zodiac

    @property
    def retrograde(self) -> bool:
        return self.speed < 0

    @property
    def tropical_sign(self) -> str:
        return TROPICAL[int(self.lon // 30) % 12]


def geo_lon(body: str, t):
    S = sky()
    pos = S.earth.at(t).observe(S.seg[body]).apparent()
    return ecl_lon_lat(pos)


def moon_lon(t):
    """Geocentric apparent ecliptic longitude of date of the Moon (vectorised)."""
    S = sky()
    return S.earth.at(t).observe(S.seg["Moon"]).apparent().frame_latlon(ecliptic_frame)[1].degrees


def moon_lon_j2000(t):
    """Moon longitude on the fixed J2000 ecliptic - for returns among the stars."""
    S = sky()
    return S.earth.at(t).observe(S.seg["Moon"]).apparent().frame_latlon(ecliptic_J2000_frame)[1].degrees


def chart(dt_utc: datetime, lat_deg: float, lon_deg: float, helio: bool = True) -> dict:
    """Full chart for one moment and place."""
    S = sky()
    t = to_time(dt_utc)
    th, tl = S.ts.tt_jd(t.tt + 0.5), S.ts.tt_jd(t.tt - 0.5)
    bodies = []
    for b in BODIES:
        S_pos = S.earth.at(t).observe(S.seg[b]).apparent()
        lon, lat, dist = ecl_lon_lat(S_pos)
        lon_h, _, _ = geo_lon(b, th)
        lon_l, _, _ = geo_lon(b, tl)
        speed = float(wrap180(lon_h - lon_l))
        z = str(zodiac_band_at(lon, t)[0])
        true_c = str(S.constellation_at(S_pos))
        hl = hz = None
        if helio and b not in ("Sun", "Moon"):
            hp = (S.seg[b] - S.sun).at(t)
            hl, _, _ = ecl_lon_lat(hp)
            hz = str(zodiac_band_at(hl, t)[0])
        bodies.append(Body(b, float(lon), float(lat), speed, z, true_c,
                           None if hl is None else float(hl), hz))
    # Earth seen from the Sun (heliocentric) - opposite the geocentric Sun
    sun = bodies[0]
    earth_hl = (sun.lon + 180.0) % 360.0
    node = mean_node_lon(t)
    asc, mc, lst = angles(t, lat_deg, lon_deg)
    moon = bodies[1]
    elong = float((moon.lon - sun.lon) % 360.0)
    # "above the horizon" in the chart sense: longitude in the half from Desc back to Asc
    moon_above = bool(wrap180(asc - moon.lon) > 0)
    # actual topocentric altitude for information
    from skyfield.api import wgs84
    obs = S.earth + wgs84.latlon(lat_deg, lon_deg)
    alt = obs.at(t).observe(S.seg["Moon"]).apparent().altaz()[0].degrees
    for b in bodies:
        if b.name in ("Mercury", "Venus"):
            e = float(wrap180(b.lon - sun.lon))
            b.note = ("evening star" if e > 0 else "morning star") + f" (elongation {abs(e):.1f}\u00b0)"
    return {
        "utc": dt_utc, "lat": lat_deg, "lon": lon_deg, "t": t,
        "bodies": bodies,
        "asc": asc, "mc": mc, "desc": (asc + 180) % 360, "ic": (mc + 180) % 360, "lst_deg": lst,
        "asc_zodiac": str(zodiac_band_at(asc, t)[0]), "mc_zodiac": str(zodiac_band_at(mc, t)[0]),
        "node": node, "node_zodiac": str(zodiac_band_at(node, t)[0]),
        "earth_helio_lon": earth_hl, "earth_helio_zodiac": str(zodiac_band_at(earth_hl, t)[0]),
        "moon_elongation": elong, "moon_waxing": elong < 180.0,
        "moon_phase_name": phase_name(elong),
        "moon_above_horizon": moon_above, "moon_altitude": float(alt),
        "bands": ecliptic_bands(t),
        "ephemeris": S.ephem_name,
    }


def phase_name(elong: float) -> str:
    names = ["New Moon", "Waxing crescent", "First quarter", "Waxing gibbous",
             "Full Moon", "Waning gibbous", "Last quarter", "Waning crescent"]
    return names[int(((elong + 22.5) % 360) // 45)]


def body(chart_: dict, name: str) -> Body:
    return next(b for b in chart_["bodies"] if b.name == name)


def in_range(dt_utc: datetime) -> bool:
    S = sky()
    return S.earliest <= dt_utc <= S.latest
