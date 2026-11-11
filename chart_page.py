"""Page 1: the sidereal chart read through William Lilly's Christian Astrology (1647)."""
import calendar
import datetime as dt
import os
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use('Agg')

import sidereal_engine as se
import lilly_layer as ll
import chart_wheel as cw
import places
import inputs
import user_profile
import forecast
import glossary
import plain_forecast
import theme
import device

HERE = os.path.dirname(os.path.abspath(__file__))
ORD = ll._ord


@st.cache_data(show_spinner='Computing the chart ...', max_entries=16, ttl=3600)
def run(utc, lat, lon, elev, beams_rule, orb_col):
    t, rows = se.chart(utc, lat, lon, elev)
    bands = se.ecliptic_constellation_bands(t, step=0.05)
    if bands[0][1] == bands[-1][1]:
        bands = bands[1:]
    cusps = se.regiomontanus_cusps(t, lat, lon)
    stars = se.fixed_stars(t)
    sun_up = [r for r in rows if r['body'] == 'Sun'][0]['alt'] > -0.8333
    R = ll.interpret(rows, bands, cusps, stars, sun_up, beams_rule=beams_rule, orb_col=orb_col)
    ph = se.planetary_hour(t, lat, lon, elev)
    fc = forecast.build(R, rows, bands, ph)
    asc, mc = se.angles(t, lat, lon)
    return rows, bands, cusps, R, ph, fc, asc, mc, stars


user_profile.title('The Sidereal Oracle', 'The Sidereal Oracle')      # home page title (user request)
# subtitle under the title (user's wording)
st.markdown('<p class="lilly-subtitle" style="font-size:1.12rem; line-height:1.45; margin:-0.4rem 0 0.9rem 0; '
            'color:#f7f1ea;">Horoscope readings of the real sky for any moment and place. Powerfully calculated using NASA JPL planet movements, the actual constellation positions, and William Lilly\'s original 1647 work.</p>', unsafe_allow_html=True)
PHONE = device.phone()
FULL = device.full_view()          # Simple view: the chart, the sky and the forecast; Full view: also Lilly's tables

# Forecast rules -> the terms that explain them (the "i" buttons under the Forecast)
RULE_TERMS = {'radical': ['radical'], 'not_radical': ['radical', 'hours'], 'asc_early': ['considerations', 'ascendant'],
              'asc_late': ['considerations', 'ascendant'], 'asc_ophiuchus': ['sidereal'], 'moon_void': ['void'],
              'moon_via_combusta': ['via_combusta'], 'moon_late': ['considerations'], 'saturn_asc': ['considerations'],
              'saturn_7': ['considerations', 'houses'], 'lord_asc_combust': ['combust', 'lord_asc'],
              'lord_7_afflicted': ['considerations', 'retrograde'], 'testimonies_equal': ['fortitudes'],
              'lord_asc_strong': ['lord_asc', 'fortitudes'], 'lord_asc_weak': ['lord_asc', 'fortitudes'],
              'lord_asc_angular': ['angles'], 'lord_asc_cadent': ['angles'], 'moon_apply_benefic': ['applying', 'fortunes'],
              'moon_apply_malefic': ['applying', 'fortunes'], 'cazimi': ['cazimi'], 'reception': ['reception'],
              'fortune_angular': ['fortune', 'angles'], 'fortune_cadent': ['fortune', 'angles'],
              'ophiuchus_planet': ['sidereal'], 'polar': ['hours']}


def _span(days):
    h = days * 24
    return 'under an hour' if h < 1 else f'about {h:.0f} h' if h < 36 else f'about {days:.1f} days'


def sky_card(rows, bands, local):
    """The sky at this moment: the Moon's phase and light, retrograde planets, the Moon's next contact or void of
    course, and when she leaves her constellation."""
    s = forecast.sky(rows, bands)
    leave = local + dt.timedelta(days=s['exit_days'])
    with st.container(border=True):
        st.markdown('**The sky at this moment**')
        st.markdown(f"{s['symbol']} **{s['phase']}**, {s['lit']}% lit: the Moon is "
                    f"{'increasing' if s['waxing'] else 'decreasing'} in light ({'+2' if s['waxing'] else '-2'} for her in "
                    "Lilly's table).")
        st.markdown('**Retrograde:** ' + (', '.join(s['retrograde']) if s['retrograde'] else 'no planet') + '.')
        if s['void']:
            st.markdown(f"**The Moon is void of course** until she leaves {s['band']} ({_span(s['exit_days'])}, "
                        f"{leave:%a %H:%M} local). Lilly: a time when things begun go on with difficulty.")
        else:
            p, asp, days = s['next']
            st.markdown(f"**The Moon's next contact:** {asp} with {p}, in {_span(days)}. She leaves {s['band']} in "
                        f"{_span(s['exit_days'])} ({leave:%a %H:%M} local).")
        glossary.chips(['moon_light', 'retrograde', 'void', 'aspects'], 'sky')

def set_now(tzkey):
    """Put the present moment (local clock time in tzkey) into the date and time boxes."""
    n = inputs.now_local(tzkey)
    st.session_state['c_year'] = min(max(n.year, 1850), 2149)
    st.session_state['c_month'] = n.month
    st.session_state['day_value'] = n.day
    st.session_state['c_time'] = dt.time(n.hour, n.minute)
    st.session_state['c_now_tz'] = tzkey


if 'c_time' not in st.session_state:              # the page opens at the present moment (user request)
    set_now(inputs.start_timezone())

# ---------------- inputs (same as the first app; a fold-out panel at the top on a phone) ----------------
with device.input_panel('Chart input: date, time and place'):
    if not PHONE:
        st.header('Chart input')
    dh, nb = st.columns([2.2, 1], vertical_alignment='bottom')
    dh.markdown('**Date**')
    if nb.button('Now', key='c_now', icon=':material/schedule:', width='stretch',
                 help='Set the date and time to the present moment, in the local time of the chosen place.'):
        set_now(st.session_state.get('c_last_tz') or inputs.start_timezone())
    yc, mc_, dc = st.columns([1.3, 1.4, 1])
    year = yc.number_input('Year', min_value=1850, max_value=2149, step=1, key='c_year',
                           help='Type any year from 1850 to 2149 (range of the NASA JPL DE440s data).')
    month = mc_.selectbox('Month', range(1, 13), format_func=lambda m: calendar.month_abbr[m], key='c_month')
    ndays = calendar.monthrange(int(year), int(month))[1]
    if st.session_state.get('day_value', 1) > ndays:          # e.g. 31 Jan -> Feb keeps the last day
        st.session_state['day_value'] = ndays
    day = dc.number_input('Day', min_value=1, max_value=ndays, step=1, key='day_value')
    d = dt.date(int(year), int(month), int(day))
    tm = st.time_input('Local clock time (24-hour clock)', step=60, key='c_time')
    st.caption(f"The page opens at the present moment (local time, {st.session_state.get('c_now_tz', '')}). "
               'Press Now to return to the present.')
    place, lat, lon, tzname, elev = inputs.place_picker('c')
    local_naive = dt.datetime.combine(d, tm)
    override = False
    if tzname:
        auto_off, tz_note = places.utc_offset_hours(tzname, local_naive)
        override = st.checkbox(f'Override UTC offset (automatic: {auto_off:+.2f} h)', value=False)
        tz = st.number_input('UTC offset (hours)', -12.0, 14.0, float(auto_off), 0.25) if override else auto_off
        if tz_note:
            st.info(tz_note)
    else:
        tz = st.number_input('UTC offset of that clock (hours)', -12.0, 14.0, 0.0, 0.25)
    st.session_state['c_last_tz'] = tzname if (tzname and not override) else f'UTC{tz:+.2f}'   # for the Now button
    st.subheader('Options (Lilly)')
    beams = st.radio('Sun-beams rule', ['As in Lilly\'s table (p.113, p.115)', 'As in Lilly\'s worked example (pp.178-180)'],
                     index=0, help='Lilly\'s table counts a planet within 17° of the Sun as "under the Sun-beams" (-4). '
                                   'In his own worked example he does not apply this, and counts only combustion (8°30\').')
    orbs = st.radio('Orbs of the planets (p.107)', ['Lilly\'s own (Saturn 10, Jupiter 12 ...)', '"According to others" (Saturn 9, Jupiter 9 ...)'],
                    index=0)
    st.caption('Valid dates 1850–2149 (JPL DE440s). Place data: GeoNames (CC BY 4.0); time zones: IANA tz database. '
               'Text: W. Lilly, Christian Astrology (1647), Wellcome Library copy (public domain).')

beams_rule = 'table' if beams.startswith('As in Lilly\'s table') else 'example'
orb_col = 'orb_lilly' if orbs.startswith('Lilly') else 'orb_others'
local = dt.datetime.combine(d, tm)
utc_dt = local - dt.timedelta(hours=tz)
utc = (utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour, utc_dt.minute, 0)
rows, bands, cusps, R, ph, fc, asc, mc, stars = run(utc, lat, lon, elev, beams_rule, orb_col)
P = {p['planet']: p for p in R['planets']}

# ---------------- header ----------------
st.caption(f'{place} · {local:%d %b %Y %H:%M} local (UTC{tz:+.2f}) = {utc_dt:%Y-%m-%d %H:%M} UTC · '
           'positions: NASA JPL DE440s via Skyfield (IAU standards) · houses: Regiomontanus, as Lilly · '
           'signs: the real IAU constellations on the ecliptic (13, at their true widths)')

left, right = st.columns([1.15, 1])
with left:
    fig = cw.draw_wheel(rows, bands, f'{place}, {local:%d %b %Y %H:%M}', asc, mc, cusps=cusps,
                        scores={p['planet']: p['net'] for p in R['planets']}, aspects=R['aspects'],
                        theme=theme.WHEEL_THEME_PHONE if PHONE else theme.WHEEL_THEME, compact=PHONE)
    st.pyplot(fig, width='stretch')
    if PHONE:
        st.caption('  \n'.join(cw.legend_lines(theme.WHEEL_THEME_PHONE)))

with right:
    st.subheader(f"Day of {ph['day_ruler']}, hour of {ph['hour_ruler']}")
    if ph['sunrise']:
        sr = ph['sunrise'] + dt.timedelta(hours=tz); ss = ph['sunset'] + dt.timedelta(hours=tz)
        st.caption(f"{ph['weekday']} planetary day, from local sunrise {sr:%H:%M} (sunset {ss:%H:%M}, local clock). "
                   f"This is hour {ph['hour_number']} of 24, in unequal hours. Lilly: the day's planet rules the first hour and the eighth.")
    else:
        st.caption('No sunrise or sunset here today (polar). Equal hours from local mean midnight are used.')
    c1, c2, c3 = st.columns(3)
    a_ = R['asc']
    c1.metric('Rising', a_['constellation'], help=glossary.TERMS['ascendant'][1])
    c2.metric('Lord of the Ascendant', R['lord_of_asc'] or '—', help=glossary.TERMS['lord_asc'][1])
    if R['lord_of_asc']:
        c3.metric(f"{R['lord_of_asc']}: net score", f"{P[R['lord_of_asc']]['net']:+d}", help=glossary.TERMS['fortitudes'][1])
    sky_card(rows, bands, local)
    if FULL:
      st.write(f"**Figure:** {'diurnal (Sun above the horizon)' if R['sun_up'] else 'nocturnal (Sun below the horizon)'} · "
             f"**Part of Fortune:** {R['part_of_fortune']['constellation']}, {ORD(R['part_of_fortune']['house'])} house")
      st.markdown('**Strength of the planets** (Lilly\'s table, [p.115](' + glossary.scan_url(115) + '))')
      sc = pd.DataFrame([dict(Planet=p['planet'], Constellation=p['constellation'] + (' R' if p['retrograde'] else ''),
                              House=p['house'], Fortitudes=p['fortitudes'], Debilities=p['debilities'], Net=p['net'],
                              Essentially=p['condition']) for p in R['planets']])
      device.table(sc, ['Planet', 'House', 'Net', 'Essentially'])
      found = [glossary.item_term(k) for p in R['planets'] for k, *_ in p['essential'] + p['accidental']]
      glossary.chips(['fortitudes', 'essential'] + [k for k in found if k] + ['angles'], 'table')

st.subheader('Forecast')
with st.container(border=True):
    st.markdown(fc['summary'] if FULL else plain_forecast.overview(fc, R))
    # the plain-English summary first and most prominent (user request), then the Strengths and the Weaknesses;
    # each opens in its own window
    if st.button('What does this mean?', type='primary', icon=':material/lightbulb:', key='plain_btn',
                 width='stretch', help='A summary of the Forecast without the technical terms, with this moment judged '
                                       'for the four undertakings of the Auspicious dates page.'):
        tzkey = tzname if (tzname and not override) else f'UTC{tz:+.2f}'
        plain_forecast.show(fc, R, rows, bands, cusps, stars, ph, lat, lon, elev, tzkey, local, beams_rule, place)
    b0, b1_ = st.columns(2)
    if b0.button(f"Strengths ({len(fc['strengths'])})", icon=':material/thumb_up:', key='strengths_btn', width='stretch',
                 help="Lilly's rules that favour this moment, with his page references."):
        plain_forecast.show_strengths(fc, place, local)
    if b1_.button(f"Weaknesses ({len(fc['weaknesses'])})", icon=':material/report:', key='weaknesses_btn', width='stretch',
                  help="Lilly's rules that count against this moment, with his page references."):
        plain_forecast.show_weaknesses(fc, place, local)
    fired = [x.get('id') for x in fc['strengths'] + fc['weaknesses']]
    glossary.chips([g for rid in fired for g in RULE_TERMS.get(rid, [])], 'fc')
    st.caption(fc['note'])
    st.download_button('Download forecast (.txt)',
                       forecast.as_text(fc, header=(f"Prepared for {user_profile.get()['name']}\n" if user_profile.get()['name'] else '')
                                       + f"{place} · {local:%d %b %Y %H:%M} local (UTC{tz:+.2f})"),
                       file_name=f"forecast_{local:%Y%m%d_%H%M}.txt", mime='text/plain', icon=':material/download:')

if not FULL:
    st.caption("Simple view. Switch on **Full view** in the sidebar for Lilly's tables of points, the planets in his "
               'words, the aspects and the sources.' + (' (On a phone, open the sidebar with the arrow at the top left.)'
                                                         if PHONE else ''))
    st.stop()

st.subheader("The planets in Lilly's words")
st.caption('For each planet: fortitudes, debilities and the net score. Lilly: subtract the lesser number from the '
           f'greater, "and so judge" ([p.181]({glossary.scan_url(181)})).')
_house_told = {}                       # each house's meaning is quoted once on the page; later planets point back
_house_seen = []                       # ... each time in a different wording
_POINTERS = ['its meaning is quoted under {who} above', "Lilly's words for it are given under {who}", 'see {who} above for what it signifies', 'described already, with {who}', 'as told under {who}', 'its signification appears with {who}']
for p in R['planets']:
    head = (f"{cw.GLYPH[p['planet']]} {p['planet']} in {p['constellation']}"
            + (f" (≈ {p['sign']} {p['sign_deg']:.0f}°)" if p['sign'] else '') + f" · {ORD(p['house'])} house · net {p['net']:+d}")
    with st.expander(head):
        text, cite = ll.reading(p['planet'], p['condition'])
        label = 'when ill dignified' if p['condition'] == 'ill dignified' else 'when well dignified'
        st.markdown(f"**Essentially {p['condition']}.** Lilly on {p['planet']} *{label}*:")
        st.markdown(f"> {text}  \n> <small>{cite}</small>", unsafe_allow_html=True)
        if p['true_constellation'] != p['constellation']:
            st.caption(f"Its actual position (RA/Dec) lies in {p['true_constellation']}, off the ecliptic band. "
                       f"It is read by the ecliptic band ({p['constellation']}).")
        if p['house'] in _house_told:
            _n = sum(1 for q_ in _house_seen if q_ == p['house'])
            _house_seen.append(p['house'])
            st.markdown(f"**The {ORD(p['house'])} house**: " + _POINTERS[_n % len(_POINTERS)].format(
                who=_house_told[p['house']]) + '.')
        else:
            _house_told[p['house']] = p['planet']
            st.markdown(f"**The {ORD(p['house'])} house** (Lilly): {ll.house_meaning(p['house'], 400)}")
        e1, e2 = st.columns(2)
        e1.markdown('**Essential dignities**  \n' + '  \n'.join(f"{'+' if v > 0 else ''}{v} {txt} <small>({tag})</small>"
                                                                   for _, txt, v, tag in p['essential']), unsafe_allow_html=True)
        e2.markdown('**Accidental**  \n' + '  \n'.join(f"{'+' if v > 0 else ''}{v} {txt} <small>({tag})</small>"
                                                         for _, txt, v, tag in p['accidental']), unsafe_allow_html=True)
        st.caption(f"{p['planet']}: fortitudes {p['fortitudes']} · debilities {p['debilities']} · net {p['net']:+d}")
        glossary.chips([glossary.item_term(k) for k, *_ in p['essential'] + p['accidental']], 'pl_' + p['planet'])

st.subheader('Aspects (Lilly\'s moieties of orbs, p.107)')
if R['aspects']:
    device.table(pd.DataFrame([dict(Between=f"{a['a']} – {a['b']}", Aspect=a['aspect'], **{'From exact (°)': round(a['deviation'], 2)},
                                    **{'Allowed (°)': a['moiety']}, Partile=a['partile'],
                                    Motion='applying' if a['applying'] else 'separating') for a in R['aspects']]),
                 ['Between', 'Aspect', 'Motion'])
else:
    st.caption('No aspects within the planets\' moieties.')
glossary.chips(['aspects', 'orbs', 'applying', 'partile'], 'asp')

st.subheader('Bodies')
tab = pd.DataFrame([dict(Body=r['body'], **{'Ecl. long. (°)': round(r['ecl_lon'], 2)}, **{'Ecliptic band': r['band']},
                         **{'IAU constellation (RA/Dec)': r['constellation']},
                         **{'Daily motion (°)': round(r['speed'], 3) if 'speed' in r else None},
                         **{'Above horizon': (r['alt'] > 0) if 'alt' in r else None},
                         House=se.house_of(r['ecl_lon'], cusps)) for r in rows])
device.table(tab, ['Body', 'Ecliptic band', 'House'])
if PHONE:
    st.caption('Phone layout shows the main columns of each table. To see them all, switch off "Phone layout" '
               'in the sidebar (open it with the arrow at the top left).')
glossary.chips(['sidereal', 'houses', 'five_degree'], 'bodies')
st.caption('House cusps (Regiomontanus): ' + ' · '.join(f"{i + 1}: {c['constellation']}" for i, c in enumerate(R['cusp_signs'])))

with st.expander('Sources and certainty'):
    st.markdown('Each statement carries a tag: **Lilly** (from *Christian Astrology*, 1647, with page) or **app rule** '
                '(where the app had to adapt Lilly to the sidereal IAU sky). The tables are in the *data* folder as CSV files.')
    device.table(pd.read_csv(os.path.join(HERE, 'data', 'uncertainty_log.csv'), encoding='utf-8'))
    device.table(pd.read_csv(os.path.join(HERE, 'data', 'sources.csv'), encoding='utf-8'))
