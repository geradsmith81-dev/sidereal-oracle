"""Shared sidebar inputs: place search (GeoNames) or manual coordinates, and elevation (ground height looked up
from open elevation data, plus the eye height, following the Afterglow app).
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
        home0 = user_profile.get().get('home')
        if why == 'home' and q == q0 and home0 and home0.get('src') == 'gps' and home0.get('tz'):
            # where you live was set from the device's position: offer that exact spot first, not the town centre
            hits = [dict(name=home0['name'], country=home0['country'], lat=home0['lat'], lon=home0['lon'],
                         tz=home0['tz'], pop=0, here=True)] + list(hits)
        if not hits:
            st.warning('No match in the gazetteer (places with population ≥ 1000). Try another spelling '
                       'or enter coordinates manually.')
            st.stop()
        start = next((i for i, h in enumerate(hits) if lat0 is not None and q == q0
                      and abs(h['lat'] - lat0) < 1e-3 and abs(h['lon'] - lon0) < 1e-3), 0)
        pick = st.selectbox('Matches', range(len(hits)), index=start, format_func=lambda i: (f"Where you live (your position near {hits[i]['name']})" if hits[i].get('here')
                                                    else places.label(hits[i])),
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
    # elevation (Afterglow's rules, user request): the ground height of where you live (profile) when this is your
    # home place; otherwise looked up at the place's coordinates from open elevation data (places.lookup_elevation),
    # 0 m if that fails. It starts again whenever another place is chosen, and can always be typed over. The charts
    # are worked out for the eye, places.EYE_HEIGHT_M above the ground.
    home = user_profile.get().get('home')
    at_home = (not manual and bool(home) and abs(lat - home['lat']) < 1e-3 and abs(lon - home['lon']) < 1e-3)
    home_elev = home.get('elev') if at_home else None
    if home_elev is not None and float(home_elev) < places.ELEV_MIN - 1:   # the old -500 m bug value: look it up
        home_elev = None
    here = (round(float(lat), 4), round(float(lon), 4), home_elev)
    # also when the box itself was dropped: Streamlit forgets a widget's value when another page was shown, and the
    # box then came back at its lowest value (-500 m, user report)
    if st.session_state.get(prefix + '_elev_for') != here or prefix + '_elev' not in st.session_state:
        st.session_state[prefix + '_elev_for'] = here
        if home_elev is not None:
            found, src = float(home_elev), 'home'
        else:
            found, src = places.lookup_elevation(lat, lon)
            src = src or 'none'
        st.session_state[prefix + '_elev_src'] = src
        st.session_state[prefix + '_elev_found'] = found or 0.0
        st.session_state[prefix + '_elev'] = float(found or 0.0)
    src = st.session_state.get(prefix + '_elev_src', 'none')
    shown = st.session_state.get(prefix + '_elev_found', 0.0)
    ground = st.number_input('Ground elevation (m above sea level)', places.ELEV_MIN, places.ELEV_MAX, step=1.0,
                             format='%.0f', key=prefix + '_elev',
                             help=({'home': 'Starts at the elevation of where you live (your profile). ',
                                    'none': 'The elevation data could not be reached, so this starts at 0 m. '
                                            'Type it in if you know it. '}.get(src)
                                   or f'Looked up for this spot from {places.SOURCE_TEXT[src]}. '
                                      'Type over it if you know better. ')
                                  + f'The chart is worked out for your eyes, {places.EYE_HEIGHT_M:g} m above the '
                                    'ground. Elevation changes sunrise, and so the planetary hours, slightly.')
    elev = float(ground) + places.EYE_HEIGHT_M
    if src == 'home':
        st.caption(f'Ground {ground:.0f} m' + (': where you live (your profile).' if abs(ground - shown) < 0.5 else
                   ' (typed in).') + f' Eye level {elev:.1f} m.')
    elif src in places.SOURCE_TEXT:
        st.caption((f'Ground {ground:.0f} m, looked up for this spot '
                    f'({"AWS Terrain Tiles" if src == "tiles" else "Open-Meteo"}).' if abs(ground - shown) < 0.5 else
                    f'Ground {ground:.0f} m (typed in; looked up: {shown:.0f} m).')
                   + f' Eye level {elev:.1f} m.')
    return place, lat, lon, tzname, elev
