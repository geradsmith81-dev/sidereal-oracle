"""Offline place-name search and historical UTC offsets.

Gazetteer: GeoNames cities with population >= 1000 (geonamescache package, ~170k places),
with coordinates and IANA time zone. Offsets come from the IANA tz database (zoneinfo +
tzdata), which records historical changes (e.g. summer time; London plain GMT in 1850).
Before standard time zones (mostly before ~1880-1900) the database gives Local Mean Time
or an early standard; the app shows the offset it used so the user can override it.
Elevation is not in the gazetteer: the ground height is looked up from open elevation data (AWS Terrain Tiles, with
the Open-Meteo Elevation API as a check over water and as a stand-by) when a place is chosen, following the rules of
the Afterglow app; it can always be typed over, and is 0 m when the lookup fails.
"""
import io
import json
import math
import time
import unicodedata
import urllib.request
from functools import lru_cache
import datetime as dt
from zoneinfo import ZoneInfo
import geonamescache

_gc = geonamescache.GeonamesCache(min_city_population=1000)
_COUNTRY = {k: v['name'] for k, v in _gc.get_countries().items()}


def _norm(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(ch for ch in s if not unicodedata.combining(ch)).casefold().strip()


def _build():
    recs = []
    for c in _gc.get_cities().values():
        alts = [a for a in c.get('alternatenames', []) if a and a.isascii()]
        recs.append(dict(name=c['name'], country=_COUNTRY.get(c['countrycode'], c['countrycode']),
                         lat=float(c['latitude']), lon=float(c['longitude']), tz=c['timezone'],
                         pop=int(c['population']), key=_norm(c['name']),
                         alts='|' + '|'.join(sorted({_norm(a) for a in alts})) + '|'))   # packed: saves memory
    return recs


PLACES = _build()


def search(query, n=12):
    """Rank: exact name > exact alternate name > name prefix > alternate prefix > substring;
    ties broken by population."""
    q = _norm(query)
    if len(q) < 2:
        return []
    scored = []
    for r in PLACES:
        k = r['key']
        if k == q:
            s = 0
        elif f'|{q}|' in r['alts']:
            s = 1
        elif k.startswith(q):
            s = 2
        elif f'|{q}' in r['alts']:
            s = 3
        elif len(q) >= 4 and q in k:
            s = 4
        else:
            continue
        scored.append((s, -r['pop'], r))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [r for _, _, r in scored[:n]]


_BIGGEST = {}


def largest_in_tz(tzname):
    """The most populous gazetteer place in an IANA time zone (e.g. 'America/Chicago' -> Chicago), or None.
    Used only to guess a starting place from the device's time zone when no home place is set."""
    if not _BIGGEST:
        for r in PLACES:
            b = _BIGGEST.get(r['tz'])
            if b is None or r['pop'] > b['pop']:
                _BIGGEST[r['tz']] = r
    return _BIGGEST.get(tzname)


def label(r):
    return f"{r['name']}, {r['country']}  ({r['lat']:.3f}°, {r['lon']:.3f}°; pop. {r['pop']:,})"


def utc_offset_hours(tzname, local_naive):
    """Historical UTC offset (hours) for a local clock time in an IANA zone.
    Returns (offset, note). Ambiguous times (clocks going back) use the first occurrence."""
    z = ZoneInfo(tzname)
    aware = local_naive.replace(tzinfo=z, fold=0)
    off = aware.utcoffset().total_seconds() / 3600
    # detect nonexistent local times (clocks going forward): round-trip check
    back = aware.astimezone(dt.timezone.utc).astimezone(z).replace(tzinfo=None)
    if back != local_naive:
        note = 'this clock time did not exist locally (clocks went forward); pre-change offset used'
    elif aware.replace(fold=1).utcoffset() != aware.utcoffset():
        note = 'ambiguous clock time (clocks went back); first occurrence used'
    else:
        note = ''
    return off, note


# ---------------------------------------------------------------- elevation (user request)
# The same rules as the Afterglow app (user request):
#  * the ground height is read from open elevation data at the exact point - the "Terrain Tiles" of the AWS Registry
#    of Open Data (Mapzen/Tilezen, Terrarium PNG encoding: metres = R*256 + G + B/256 - 32768), which merge SRTM,
#    USGS 3DEP/NED (USA, up to 10 m), GMTED2010, ETOPO1 and national models; zoom 13 = about 19 m per pixel at the
#    equator, sampled between the four nearest pixels;
#  * a phone's GPS altitude is never used for it (phones give height above the GPS ellipsoid, which can differ from
#    sea-level height by tens of metres);
#  * the observer's eye is EYE_HEIGHT_M above the ground;
#  * the user can always type over the ground height.
# Terrain Tiles also hold the sea floor, so a point that reads below sea level is checked with the Open-Meteo
# Elevation API (Copernicus DEM GLO-90, which gives 0 m on water): land below sea level (Dead Sea, Death Valley,
# polders) keeps its height, water counts as 0 m. Open-Meteo is also the stand-by when the tiles cannot be had.
# Only the coordinates are sent (to Amazon S3 and Open-Meteo). Results are kept for the session; after a failure
# a service is not asked again for two minutes, so the app never waits on it repeatedly.
TILE_URL = 'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png'
TILE_ZOOM = 13
ELEVATION_URL = 'https://api.open-meteo.com/v1/elevation?latitude={lat:.4f}&longitude={lon:.4f}'
EYE_HEIGHT_M = 1.7               # Afterglow's default eye height above the ground
ELEV_MIN, ELEV_MAX = -450.0, 8850.0   # the Dead Sea shore to the top of Everest (Afterglow's range)
_down_until = {'tiles': 0.0, 'open-meteo': 0.0}


@lru_cache(maxsize=48)
def _tile(z, x, y):
    """Ground heights (metres, 256 x 256 numpy array) of one Terrarium tile."""
    import numpy as np
    from PIL import Image
    with urllib.request.urlopen(TILE_URL.format(z=z, x=x, y=y), timeout=5) as r:
        im = Image.open(io.BytesIO(r.read())).convert('RGB')
    a = np.asarray(im, dtype=np.float32)
    return a[..., 0] * 256.0 + a[..., 1] + a[..., 2] / 256.0 - 32768.0


def _tiles_height(lat, lon, z=TILE_ZOOM):
    n = 2 ** z
    lat = max(min(float(lat), 85.0), -85.0)
    fx = (float(lon) + 180.0) / 360.0 * n
    s = math.sin(math.radians(lat))
    fy = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    t = _tile(z, int(fx) % n, min(max(int(fy), 0), n - 1))
    px, py = (fx - int(fx)) * 256 - 0.5, (fy - int(fy)) * 256 - 0.5
    x0, y0 = math.floor(px), math.floor(py)
    dx, dy = px - x0, py - y0
    c = lambda i, j: float(t[min(max(j, 0), 255), min(max(i, 0), 255)])
    v = ((1 - dx) * (1 - dy) * c(x0, y0) + dx * (1 - dy) * c(x0 + 1, y0)
         + (1 - dx) * dy * c(x0, y0 + 1) + dx * dy * c(x0 + 1, y0 + 1))
    if not math.isfinite(v):
        raise ValueError(v)
    return v


@lru_cache(maxsize=1024)
def _open_meteo_height(lat, lon):
    with urllib.request.urlopen(ELEVATION_URL.format(lat=lat, lon=lon), timeout=4) as r:
        v = float(json.load(r)['elevation'][0])
    if not math.isfinite(v):
        raise ValueError(v)
    return v


def _ask(service, fn, *args):
    if time.time() < _down_until[service]:
        return None
    try:
        return fn(*args)
    except Exception:
        _down_until[service] = time.time() + 120
        return None


@lru_cache(maxsize=1024)
def _lookup(lat, lon):
    tiles = _ask('tiles', _tiles_height, lat, lon)
    if tiles is not None and tiles >= 0:
        return tiles, 'tiles'
    om = _ask('open-meteo', _open_meteo_height, lat, lon)
    if tiles is not None:                       # below sea level on the tiles: land or water?
        if om is None:
            return (tiles if tiles >= ELEV_MIN else 0.0), 'tiles'
        return (tiles if om < 0 else om), ('tiles' if om < 0 else 'open-meteo')
    if om is not None:
        return om, 'open-meteo'
    raise LookupError('no elevation service could be reached')


def lookup_elevation(lat, lon):
    """(ground height in whole metres above sea level, kept within ELEV_MIN..ELEV_MAX, source) for a point, where
    source is 'tiles' (AWS Terrain Tiles) or 'open-meteo'; (None, None) when no elevation service can be reached."""
    try:
        v, src = _lookup(round(float(lat), 5), round(float(lon), 5))
    except Exception:
        return None, None
    return float(round(min(max(v, ELEV_MIN), ELEV_MAX))), src


def elevation(lat, lon):
    """Ground height of a point in whole metres above sea level, or None when it cannot be looked up."""
    return lookup_elevation(lat, lon)[0]


SOURCE_TEXT = {'tiles': 'open elevation data (AWS Terrain Tiles: SRTM, USGS 3DEP, GMTED2010 and others)',
               'open-meteo': 'a terrain map (Open-Meteo, Copernicus DEM, 90 m)'}


# ---------------------------------------------------------------- the town nearest to a position (GPS)
_GRID = None


def nearest(lat, lon):
    """(gazetteer place nearest to a position, distance in km). Used to name the town and time zone of the
    position a device reports ("Use my location")."""
    global _GRID
    import numpy as np
    if _GRID is None:
        _GRID = (np.radians([r['lat'] for r in PLACES]), np.radians([r['lon'] for r in PLACES]))
    la, lo = _GRID
    p, l = math.radians(float(lat)), math.radians(float(lon))
    a = np.sin((la - p) / 2) ** 2 + math.cos(p) * np.cos(la) * np.sin((lo - l) / 2) ** 2
    i = int(np.argmin(a))
    return PLACES[i], float(2 * 6371.0088 * math.asin(min(1.0, math.sqrt(float(a[i])))))
