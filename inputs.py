"""Shared sidebar inputs: place search (GeoNames) or manual coordinates, and elevation.
The last place query is remembered across the two pages."""
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st
import places
import user_profile


@st.cache_data(show_spinner=False, max_entries=64, ttl=3600)
def find_places(q):
    return places.search(q, n=12)


def start_timezone():
    """IANA time zone for the moment the Chart page opens at: the home place's (profile), else the device's
    (browser), else London."""
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


def place_picker(prefix):
    st.subheader('Place')
    manual = st.checkbox('Enter coordinates manually', value=st.session_state.get('_manual', False), key=prefix + '_manual')
    st.session_state['_manual'] = manual
    if not manual:
        q0, lat0, lon0, why = default_place()
        q = st.text_input('Search place name', st.session_state.get('_place_q', q0), key=prefix + '_q',
                          placeholder='e.g. Mortlake, Kraków, Praha, New York')
        st.session_state['_place_q'] = q
        hits = find_places(q)
        if not hits:
            st.warning('No match in the gazetteer (places with population ≥ 1000). Try another spelling '
                       'or enter coordinates manually.')
            st.stop()
        start = next((i for i, h in enumerate(hits) if lat0 is not None and q == q0
                      and abs(h['lat'] - lat0) < 1e-3 and abs(h['lon'] - lon0) < 1e-3), 0)
        pick = st.selectbox('Matches', range(len(hits)), index=start, format_func=lambda i: places.label(hits[i]),
                            key=prefix + '_pick')
        hit = hits[pick]
        place, lat, lon, tzname = f"{hit['name']}, {hit['country']}", hit['lat'], hit['lon'], hit['tz']
        st.caption(f'{lat:.4f}°, {lon:.4f}° · time zone {tzname}')
        if q == q0 and why.startswith('tz:'):
            st.caption(f"Starting place guessed from your device's time zone ({why[3:]}). To start from your own town, "
                       "add 'Where you live' in your profile (Edit profile, at the top of the sidebar).")
        elif q == q0 and why == 'home':
            st.caption('Starting place: where you live (your profile).')
    else:
        place = st.text_input('Place label', 'Custom location', key=prefix + '_label')
        lat = st.number_input('Latitude (°N)', -89.0, 89.0, 51.5, 0.0001, format='%.4f', key=prefix + '_lat')
        lon = st.number_input('Longitude (°E)', -180.0, 180.0, 0.0, 0.0001, format='%.4f', key=prefix + '_lon')
        tzname = None
    elev = st.number_input('Elevation (m)', 0.0, 9000.0, 0.0, 10.0, key=prefix + '_elev',
                           help='Not in the gazetteer; affects sunrise (planetary hours) slightly.')
    return place, lat, lon, tzname, elev
