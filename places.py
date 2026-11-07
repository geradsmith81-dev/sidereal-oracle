"""Offline place-name search and historical UTC offsets.

Gazetteer: GeoNames cities with population >= 1000 (geonamescache package, ~170k places),
with coordinates and IANA time zone. Offsets come from the IANA tz database (zoneinfo +
tzdata), which records historical changes (e.g. summer time; London plain GMT in 1850).
Before standard time zones (mostly before ~1880-1900) the database gives Local Mean Time
or an early standard; the app shows the offset it used so the user can override it.
Elevation is not in the gazetteer and defaults to 0 m (editable).
"""
import unicodedata
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
