"""
prenatal.py - Sucher's use of the Hermetic Rule (trutina Hermetis) and the
prenatal "seven-year" graph.

Hermetic Rule (W. Sucher, 'Looking Through the Horoscope of Birth', 1937):
  * Moon waxing at birth  -> at the epoch the Moon stood at the birth Ascendant.
  * Moon waning at birth  -> at the epoch the Moon stood at the birth Descendant.
  * The epoch lies about 10 sidereal months (~273 d) before birth; 8 months
    (~218 d) for a seven-month child.  Whether gestation is shorter or longer
    than 273 d follows from where the Moon stands relative to the horizon.
  The app finds the moment, within half a sidereal month of N*27.32 d before
  birth and on the side given by Sucher's case (shorter or longer), at which
  the geocentric Moon reaches the target longitude.

Reciprocal check (classical form of the rule): the Ascendant or Descendant at
the epoch should fall on the birth Moon.  The app reports the residual; it
does NOT alter the birth time.

Prenatal graph (Sucher 1937, 'prenatal events'): each return of the Moon to its
epoch position among the fixed stars opens a new seven-year period of life -
first lunar cycle = ages 0-7, second = 7-14, ...  Inside a cycle the app maps
time linearly onto the seven years.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import astrosophy_engine as E
HALF = E.SIDEREAL_MONTH / 2.0


def _crossings(f, t_start_jd, t_end_jd, target, step=0.125):
    """Times (TT jd) in [start, end] where angle f(t) passes `target` going
    forward (increasing longitude). f is vectorised over a Skyfield Time."""
    ts = E.sky().ts
    grid = np.arange(t_start_jd, t_end_jd + step, step)
    d = E.wrap180(f(ts.tt_jd(grid)) - target)
    out = []
    for i in range(len(grid) - 1):
        if d[i] < 0 <= d[i + 1] and (d[i + 1] - d[i]) < 90:  # forward pass, not the +/-180 wrap
            lo, hi = grid[i], grid[i + 1]
            dlo = d[i]
            for _ in range(40):  # bisection to ~1e-12 d
                mid = 0.5 * (lo + hi)
                dm = float(E.wrap180(f(ts.tt_jd(mid)) - target))
                if dm < 0:
                    lo, dlo = mid, dm
                else:
                    hi = mid
                if hi - lo < 1e-7:
                    break
            out.append(0.5 * (lo + hi))
    return out


@dataclass
class Epoch:
    utc: datetime
    gestation_days: float
    case: int                 # Sucher's case 1-4
    case_text: str
    target: str               # "Ascendant" or "Descendant"
    target_lon: float
    months: int
    chart: dict               # chart at the epoch (birth place)
    residual_deg: float       # |epoch Asc-or-Desc  -  birth Moon|
    residual_angle: str       # which epoch angle is closest to the birth Moon
    expected_shorter: bool    # from Sucher's four cases
    consistent: bool          # computed gestation agrees with the case rule


CASE_TEXT = {
    1: "Moon waxing and above the horizon: epoch Moon at the Ascendant; gestation a little shorter than the full lunar months.",
    2: "Moon waxing and below the horizon: epoch Moon at the Ascendant; gestation a little longer than the full lunar months.",
    3: "Moon waning and above the horizon: epoch Moon at the Descendant; gestation a little longer than the full lunar months.",
    4: "Moon waning and below the horizon: epoch Moon at the Descendant; gestation a little shorter than the full lunar months.",
}


def hermetic_epoch(birth_chart: dict, months: int = 10) -> Epoch:
    bc = birth_chart
    waxing, above = bc["moon_waxing"], bc["moon_above_horizon"]
    case = {(True, True): 1, (True, False): 2, (False, True): 3, (False, False): 4}[(waxing, above)]
    target_name = "Ascendant" if waxing else "Descendant"
    target = bc["asc"] if waxing else bc["desc"]
    t_birth = bc["t"].tt
    centre = t_birth - months * E.SIDEREAL_MONTH
    shorter = case in (1, 4)
    sols = _crossings(E.moon_lon, centre - HALF - 2.0, centre + HALF + 2.0, target)
    if not sols:
        raise RuntimeError("No epoch found in the search window")
    # Sucher's case decides the side of the standard length (shorter: epoch after
    # `centre`; longer: epoch before it).  Normally exactly one solution lies
    # within half a month on that side; near the horizon edge the Moon's
    # changing speed can leave two candidates, and the case rule settles it.
    side = [x for x in sols if (x >= centre) == shorter]
    jd = min(side or sols, key=lambda x: abs(x - centre))
    t_ep = E.sky().ts.tt_jd(jd)
    ep_utc = t_ep.utc_datetime()
    ec = E.chart(ep_utc, bc["lat"], bc["lon"])
    moon_b = E.body(bc, "Moon").lon
    ra = abs(float(E.wrap180(ec["asc"] - moon_b)))
    rd = abs(float(E.wrap180(ec["desc"] - moon_b)))
    resid, which = (ra, "Ascendant") if ra <= rd else (rd, "Descendant")
    gest = t_birth - jd
    consistent = (gest <= months * E.SIDEREAL_MONTH + 1e-6) == shorter
    return Epoch(ep_utc, gest, case, CASE_TEXT[case], target_name, target, months, ec,
                 resid, which, shorter, consistent)


def lunar_cycles(epoch: Epoch, birth_chart: dict) -> list:
    """TT jd of each sidereal return of the Moon to its epoch longitude
    (fixed J2000 ecliptic), from the epoch to birth."""
    ts = E.sky().ts
    t0 = ts.from_datetime(epoch.utc).tt
    t1 = birth_chart["t"].tt
    target = float(E.moon_lon_j2000(ts.tt_jd(t0)))
    rets = _crossings(E.moon_lon_j2000, t0 + 1.0, t1, target)
    return [t0] + rets


def age_of(jd: float, starts: list) -> float:
    """Map a prenatal moment to a life age (years) via the lunar cycles."""
    k = int(np.searchsorted(starts, jd, side="right")) - 1
    k = max(0, k)
    t_start = starts[k]
    length = (starts[k + 1] - t_start) if k + 1 < len(starts) else E.SIDEREAL_MONTH
    return 7.0 * (k + (jd - t_start) / length)


def prenatal_tracks(epoch: Epoch, birth_chart: dict, step=0.25) -> pd.DataFrame:
    """Daily (quarter-day) longitudes and zodiac bands of the bodies during
    gestation, with the equivalent life age."""
    S = E.sky()
    ts = S.ts
    t0 = ts.from_datetime(epoch.utc).tt
    t1 = birth_chart["t"].tt
    grid = np.arange(t0, t1 + 1e-9, step)
    if grid[-1] < t1:
        grid = np.append(grid, t1)
    T = ts.tt_jd(grid)
    starts = lunar_cycles(epoch, birth_chart)
    rows = {"tt": grid, "utc": [x.replace(tzinfo=None) for x in T.utc_datetime()],
            "age": [age_of(j, starts) for j in grid]}
    mid = ts.tt_jd(0.5 * (t0 + t1))
    bands = E.ecliptic_bands(mid)
    for b in E.CLASSICAL:
        lon = S.earth.at(T).observe(S.seg[b]).apparent().frame_latlon(E.ecliptic_frame)[1].degrees
        rows[b] = lon
    df = pd.DataFrame(rows)
    df.attrs["cycle_starts"] = starts
    df.attrs["bands"] = bands
    return df


def _band_of(lon, bands):
    for ab, s, e in bands:
        if s <= lon < e or s <= lon + 360 < e:
            return ab
    return bands[-1][0]


def prenatal_events(epoch: Epoch, birth_chart: dict) -> pd.DataFrame:
    """Events during gestation mapped to life ages:
       Moon conjunct a planet, Sun conjunct a planet, planet changes zodiac
       band, planet stations (turns retrograde / direct)."""
    df = prenatal_tracks(epoch, birth_chart)
    starts, bands = df.attrs["cycle_starts"], df.attrs["bands"]
    ts = E.sky().ts
    ev = []

    def add(i, frac, kind, what, lon):
        jd = df.tt.iloc[i] + frac * (df.tt.iloc[i + 1] - df.tt.iloc[i])
        ev.append({"utc": ts.tt_jd(jd).utc_datetime().replace(tzinfo=None),
                   "age": round(age_of(jd, starts), 2), "event": kind, "bodies": what,
                   "zodiac": E.con_name(_band_of(lon % 360, bands)), "lon": round(lon % 360, 2)})

    planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    pairs = [("Moon", p, "Moon passes") for p in ["Sun"] + planets]
    pairs += [("Sun", p, "conjunction") for p in planets]
    pairs += [(a, b, "conjunction") for i, a in enumerate(planets) for b in planets[i + 1:]]
    for lead, p, kind in pairs:
        if True:
            d = E.wrap180(df[lead].values - df[p].values)
            for i in range(len(d) - 1):
                if abs(d[i + 1] - d[i]) < 90 and ((d[i] < 0 <= d[i + 1]) or (d[i] > 0 >= d[i + 1])):
                    f = d[i] / (d[i] - d[i + 1]) if d[i] != d[i + 1] else 0.0
                    lon = df[p].iloc[i] + f * float(E.wrap180(df[p].iloc[i + 1] - df[p].iloc[i]))
                    add(i, f, kind, f"{lead} \u2013 {p}", lon)
    for p in ["Sun"] + planets:
        z = [_band_of(v % 360, bands) for v in df[p].values]
        for i in range(len(z) - 1):
            if z[i] != z[i + 1]:
                add(i, 0.5, "enters", f"{p} \u2192 {E.con_name(z[i + 1])}", df[p].iloc[i + 1])
    for p in planets:
        sp = E.wrap180(np.diff(df[p].values))
        for i in range(len(sp) - 1):
            if sp[i] > 0 >= sp[i + 1]:
                add(i + 1, 0.0, "station", f"{p} turns retrograde", df[p].iloc[i + 1])
            elif sp[i] < 0 <= sp[i + 1]:
                add(i + 1, 0.0, "station", f"{p} turns direct", df[p].iloc[i + 1])
    out = pd.DataFrame(ev)
    if len(out):
        out = out.sort_values("utc").reset_index(drop=True)
    return out


def cycle_table(epoch: Epoch, birth_chart: dict) -> pd.DataFrame:
    starts = lunar_cycles(epoch, birth_chart)
    ts = E.sky().ts
    rows = []
    for k, jd in enumerate(starts):
        t = ts.tt_jd(jd)
        rows.append({"cycle": k + 1, "starts_utc": t.utc_datetime().replace(tzinfo=None),
                     "life_period": f"{7 * k}\u2013{7 * (k + 1)} years",
                     "moon_zodiac": E.con_name(str(E.zodiac_band_at(E.moon_lon(t), t)[0]))})
    return pd.DataFrame(rows)
