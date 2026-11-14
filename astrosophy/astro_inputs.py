"""Inputs of the Astrosophy Birth Chart page (from the Astrosophy app): the place search (GeoNames) or coordinates typed by hand, the time zone the app opens in, and the
starting place (adapted from the Sidereal Oracle's inputs.py; without its elevation box, because the Astrosophy chart
is geocentric and the ground height never enters it). The last place query is shared with the other pages.
The place search and the profile are the host app's own (places.py, user_profile.py)."""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st
import places
import user_profile


@st.cache_data(show_spinner=False, max_entries=64, ttl=3600)
def find_places(q):
    return places.search(q, n=12)


def start_timezone():
    """IANA time zone of the present moment: the home place's (profile), else the device's (browser), else London."""
    home = user_profile.get().get('home')
    if home and home.get('tz'):
        return home['tz']
    try:
        tz = st.context.timezone
        if tz:
            ZoneInfo(tz)
            return tz
    except Exception:
        pass
    return 'Europe/London'


def now_local(tzkey):
    """The present moment as a local clock time (naive datetime, whole minutes) in an IANA zone or 'UTC+h.hh'."""
    z = dt.timezone(dt.timedelta(hours=float(tzkey[3:]))) if tzkey.startswith('UTC') else ZoneInfo(tzkey)
    return dt.datetime.now(z).replace(second=0, microsecond=0, tzinfo=None)


def default_place():
    """Where the place search starts: (query, lat, lon, why).
    1. the home place in the user's profile;
    2. otherwise the main city of the device's time zone (a guess, said so on the page);
    3. otherwise London."""
    home = user_profile.get().get('home')
    if home:
        return home['name'], home['lat'], home['lon'], 'home'
    try:
        tz = st.context.timezone
    except Exception:
        tz = None
    big = places.largest_in_tz(tz) if tz else None
    if big:
        return big['name'], big['lat'], big['lon'], f'tz:{tz}'
    return 'London', None, None, ''


def home_place():
    """(name, lat, lon, tz, why) of the place for 'Today's sky': where you live (profile), else the main city of the
    device's time zone, else London."""
    home = user_profile.get().get('home')
    if home:
        return f"{home['name']}, {home['country']}".strip(', '), home['lat'], home['lon'], home.get('tz'), 'home'
    try:
        tz = st.context.timezone
    except Exception:
        tz = None
    big = places.largest_in_tz(tz) if tz else None
    if big:
        return f"{big['name']}, {big['country']}", big['lat'], big['lon'], big['tz'], f'tz:{tz}'
    return 'London, United Kingdom', 51.50853, -0.12574, 'Europe/London', ''


def place_picker(prefix, heading='Place'):
    """Place search or coordinates by hand. Returns (place, lat, lon, tzname); tzname is None for coordinates."""
    st.subheader(heading)
    manual = st.toggle('Enter coordinates by hand', value=st.session_state.get(prefix + '_manual_v', False),
                       key=prefix + '_manual')
    st.session_state[prefix + '_manual_v'] = manual
    if not manual:
        q0, lat0, lon0, why = default_place()
        q = st.text_input('Search for a town or city', st.session_state.get('_place_q', q0), key=prefix + '_q',
                          placeholder='e.g. Dornach, Kraków, Praha, New York')
        st.session_state['_place_q'] = q
        hits = find_places(q)
        home0 = user_profile.get().get('home')
        if why == 'home' and q == q0 and home0 and home0.get('src') == 'gps' and home0.get('tz'):
            # where you live was set from the device's position: offer that exact spot first, not the town centre
            hits = [dict(name=home0['name'], country=home0['country'], lat=home0['lat'], lon=home0['lon'],
                         tz=home0['tz'], pop=0, here=True)] + list(hits)
        if not hits:
            st.warning('No match in the gazetteer (places with at least 1,000 inhabitants). Try another spelling, '
                       'or enter coordinates by hand.')
            return 'London (default)', 51.5074, -0.1278, 'Europe/London'
        start = next((i for i, h in enumerate(hits) if lat0 is not None and q == q0
                      and abs(h['lat'] - lat0) < 1e-3 and abs(h['lon'] - lon0) < 1e-3), 0)
        pick = st.selectbox('Choose', range(len(hits)), index=start,
                            format_func=lambda i: (f"Where you live (your position near {hits[i]['name']})"
                                                   if hits[i].get('here') else places.label(hits[i])),
                            key=prefix + '_pick')
        hit = hits[pick]
        place, lat, lon, tzname = f"{hit['name']}, {hit['country']}", hit['lat'], hit['lon'], hit['tz']
        st.caption(f'{lat:.4f}°, {lon:.4f}° · time zone {tzname}')
        if q == q0 and why.startswith('tz:'):
            st.caption(f"Starting place guessed from your device's time zone ({why[3:]}). To start from your own town, "
                       "add 'Where you live' in your profile (at the top of the sidebar).")
        elif q == q0 and why == 'home':
            st.caption('Starting place: where you live (your profile).')
    else:
        lat = st.number_input('Latitude (north +, south \u2212)', -89.9, 89.9, 51.5074, format='%.4f', key=prefix + '_lat')
        lon = st.number_input('Longitude (east +, west \u2212)', -180.0, 180.0, -0.1278, format='%.4f', key=prefix + '_lon')
        place, tzname = f'{lat:.3f}, {lon:.3f}', None
    return place, lat, lon, tzname


def utc_offset(local, tz_name):
    """(offset_hours, note) for a naive local time in an IANA zone, with the note in plain words for the page."""
    off, note = places.utc_offset_hours(tz_name, local)
    if note.startswith('this clock time did not exist'):
        note = 'This local time did not exist (clocks were put forward). The earlier offset is used; please check.'
    elif note.startswith('ambiguous'):
        note = 'This local time occurred twice (clocks were put back). The first occurrence is used; please check.'
    return off, note


def lmt_offset(lon_deg):
    """Local Mean Time offset in hours for a longitude."""
    return float(lon_deg) / 15.0
