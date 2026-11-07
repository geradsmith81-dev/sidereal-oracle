"""Page 2: auspicious dates to begin an undertaking (elections), framed from Lilly's principles."""
import calendar
import datetime as dt
import io
import os
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap

import sidereal_engine as se
import lilly_layer as ll
import chart_wheel as cw
import electional as el
import inputs
import user_profile
import natal
import theme
import device

HERE = os.path.dirname(os.path.abspath(__file__))
from calendar_view import PAL, GRADE_COL, GRADE_TXT, compute, heatmap, reasons, day_list


user_profile.title('Auspicious dates · elections after William Lilly', '{who} auspicious dates · elections after William Lilly')
PHONE = device.phone()

# ---------------- inputs (a fold-out panel at the top on a phone, open until the first search) ----------------
with device.input_panel('What to begin, when and where', expanded='e_result' not in st.session_state):
    if not PHONE:
        st.header('What to begin')
    kind = st.radio('Undertaking', list(el.UNDERTAKINGS), format_func=lambda k: el.UNDERTAKINGS[k]['label'], key='e_kind')
    st.markdown('**From date**')
    today = dt.date.today()
    yc, mc_, dc = st.columns([1.3, 1.4, 1])
    year = yc.number_input('Year', 1850, 2149, min(max(today.year, 1850), 2149), 1, key='e_year')
    month = mc_.selectbox('Month', range(1, 13), index=today.month - 1, format_func=lambda m: calendar.month_abbr[m], key='e_month')
    nd = calendar.monthrange(int(year), int(month))[1]
    if st.session_state.get('e_day', today.day) > nd:
        st.session_state['e_day'] = nd
    day = dc.number_input('Day', 1, nd, step=1, key='e_day', value=None if 'e_day' in st.session_state else min(today.day, nd))
    start = dt.date(int(year), int(month), int(day))
    days = st.slider('Number of days', 7, 92, 31, key='e_days')
    h0, h1 = st.slider('Hours of the day to consider', 0, 24, (7, 22), key='e_hours')
    step = st.select_slider('Time step (minutes)', [15, 30, 60], 30, key='e_step')
    place, lat, lon, tzname, elev = inputs.place_picker('e')
    if tzname:
        tzkey = tzname
        st.caption('Clock times follow the local time zone, including summer time changes.')
    else:
        off = st.number_input('UTC offset of the local clock (hours)', -12.0, 14.0, 0.0, 0.25, key='e_off')
        tzkey = f'UTC{off:+.2f}'
    beams = st.radio('Sun-beams rule', ["As in Lilly's table (p.113, p.115)", "As in Lilly's worked example (pp.178-180)"], key='e_beams')
    beams_rule = 'table' if beams.startswith("As in Lilly's table") else 'example'
    my_birth = user_profile.get()['birth']
    use_natal = st.checkbox('Include my birth chart', value=bool(my_birth), disabled=not my_birth, key='e_natal',
                            help='Adds how each moment agrees with your nativity (fortunes and infortunes to your Sun, Moon '
                                 'and Ascendant; the rising sign to your Ascendant). Add your birth details in your profile first.'
                                 if not my_birth else 'Adds how each moment agrees with your nativity.')
    end_ok = start + dt.timedelta(days=days) <= dt.date(2149, 12, 31)
    if h1 <= h0:
        st.warning('Choose an end hour later than the start hour.')
    go = st.button('Find auspicious times', type='primary', width='stretch', disabled=(not end_ok) or h1 <= h0)

U = el.UNDERTAKINGS[kind]
st.caption(f"{U['label']} · {place} · {start:%d %b %Y} for {days} days, {h0:02d}:00–{h1:02d}:00 local, every {step} min")
if U.get('note'):                  # how the undertaking may be read (user's wording), for Romance and Friendship
    st.info(U['note'], icon=':material/favorite:' if kind == 'romance' else ':material/group:')
with st.container(border=True):
    st.markdown(f"**How this undertaking is judged.** {U['why']} The moment is judged for the Lord of the Ascendant "
                f"(the person who begins), the lord of the {ll._ord(U['house'])} house (the matter), {U['natural']} and the Moon.")
    st.caption('Lilly wrote no separate book of elections. In his epistle he says that whoever has studied his book will be '
               '"able (ad libitum) to frame his owne Figure of Elections, let the quere be what it will". This page frames '
               'them from his rules: perfection of the significators (ch. XXI, pp.124-126), their strength (p.115), and his '
               '"Considerations before Judgment" (pp.121-123), which mark a moment Avoid. The weights that add these into '
               'one score are app choices, editable in data/election_rules.csv.')

params = (kind, lat, lon, elev, tzkey, start, days, h0, h1, step, beams_rule)
if go:
    with st.spinner(f'Judging {days * len(range(h0 * 60, min(h1 * 60, 24 * 60 - 1) + 1, step)):,} moments ... (about 20 seconds per month)'):
        st.session_state['e_result'] = (params, compute(*params))
if 'e_result' not in st.session_state:
    st.info(f'Choose the undertaking, the dates and the place {device.where_inputs()}, then press **Find auspicious times**.')
    st.stop()
p_used, (res, bands, q) = st.session_state['e_result']
if p_used != params:
    st.warning('The settings have changed since this calendar was computed. Press **Find auspicious times** to update it.')
kind, lat, lon, elev, tzkey, start, days, h0, h1, step, beams_rule = p_used
U = el.UNDERTAKINGS[kind]
if use_natal and my_birth:
    res = natal.personalise(res, natal.chart_of(my_birth), 'your')
    q = el.grade(res)
    st.caption(f"Personalised with your birth chart ({user_profile.birth_text(my_birth)}).")
W = el.windows(res)

if PHONE:
    st.subheader('Best times, day by day')
    st.markdown(day_list(res, W, start, days, step), unsafe_allow_html=True)
    st.caption('Up to three Best or Good windows per day, in time order. The coloured grid below shows every hour.')
st.subheader('Calendar' if not PHONE else 'Calendar grid')
st.pyplot(heatmap(res, start, days, h0, h1, step, compact=PHONE), width='stretch')
if q:
    st.caption(f"Best = the top 10 % of the moments that pass Lilly's cautions in this period (score ≥ {q[0]:.1f}); "
               f"Good = the next 25 % (score ≥ {q[1]:.1f}); Avoid = a caution from Lilly's Considerations applies. "
               "Grades are relative to the period searched (app rule).")
n_av = sum(r['avoid'] for r in res)
st.caption(f'{len(res):,} moments judged; {n_av:,} ({n_av / len(res):.0%}) marked Avoid.')

st.subheader('Best windows')
if not W:
    st.info('No Good or Best windows in this period. Try more days or a wider range of hours.')
else:
    top = W[:20]
    tab = pd.DataFrame([dict(Date=f"{w['date']:%a %d %b %Y}", From=w['start'].strftime('%H:%M'),
                             To=(w['end'] + dt.timedelta(minutes=step)).strftime('%H:%M'), Grade=GRADE_TXT[w['grade']],
                             Score=w['score'], Rising=w['peak']['rising'],
                             **{'Day / hour': f"{w['peak']['day_ruler']} / {w['peak']['hour_ruler']}"},
                             **{'Main reasons': reasons(w['peak']['items'])}) for w in top])
    device.table(tab, ['Date', 'From', 'To', 'Grade'])

    st.subheader('Look closer at a window')
    pick = st.selectbox('Window', range(len(top)), key='e_window',
                        format_func=lambda i: f"{top[i]['date']:%a %d %b %Y} {top[i]['start']:%H:%M} · {GRADE_TXT[top[i]['grade']]} · score {top[i]['score']:+.1f}")
    w = top[pick]; m = w['peak']
    left, right = st.columns([1, 1.1])
    with left:
        u = m['utc']
        t, rows = se.chart((u.year, u.month, u.day, u.hour, u.minute, 0), lat, lon, elev)
        cusps = se.regiomontanus_cusps(t, lat, lon)
        stars = se.fixed_stars(t)
        sun_up = [r for r in rows if r['body'] == 'Sun'][0]['alt'] > -0.8333
        R = ll.interpret(rows, bands, cusps, stars, sun_up, beams_rule=beams_rule)
        asc, mc = se.angles(t, lat, lon)
        fig = cw.draw_wheel(rows, bands, f"{place}, {m['local']:%d %b %Y %H:%M}", asc, mc, cusps=cusps,
                            scores={p['planet']: p['net'] for p in R['planets']}, aspects=R['aspects'],
                            theme=theme.WHEEL_THEME_PHONE if PHONE else theme.WHEEL_THEME, compact=PHONE)
        st.pyplot(fig, width='stretch')
        if PHONE:
            st.caption('  \n'.join(cw.legend_lines(theme.WHEEL_THEME_PHONE)))
    with right:
        st.markdown(f"**Peak at {m['local']:%H:%M}**: {m['rising']} rising; Lord of the Ascendant **{m['lord1'] or '—'}**, "
                    f"lord of the {ll._ord(U['house'])} **{m['lordm'] or '—'}**; Moon in {m['moon']}; "
                    f"day of {m['day_ruler']}, hour of {m['hour_ruler']}.")
        good = [(p, t, s) for _, t, p, s, k in m['items'] if k == 'good']
        bad = [(p, t, s) for _, t, p, s, k in m['items'] if k == 'bad']
        info = [(p, t, s) for _, t, p, s, k in m['items'] if k == 'info']
        st.markdown('**For the undertaking**  \n' + ('  \n'.join(f"{p:+.1f} {t} <small>({s})</small>" for p, t, s in good) or '—'),
                    unsafe_allow_html=True)
        st.markdown('**Against**  \n' + ('  \n'.join(f"{p:+.1f} {t} <small>({s})</small>" for p, t, s in bad) or '—'),
                    unsafe_allow_html=True)
        if info:
            st.markdown('**Noted**  \n' + '  \n'.join(f"{t} <small>({s})</small>" for p, t, s in info), unsafe_allow_html=True)
        st.caption(f"Score {m['score']:+.1f} = the sum of the points above. To see the full chart for this moment, open the "
                   f"Chart page and enter {m['local']:%d %b %Y, %H:%M}.")

by_day = {}
for r in res:
    by_day.setdefault(r['date'], []).append(r)
drows = []
for dte, rs in sorted(by_day.items()):
    ok = [r for r in rs if not r['avoid']]
    if ok:
        b = max(ok, key=lambda r: r['score'])
        drows.append(dict(Date=f"{dte:%a %d %b}", **{'Best time': b['time']}, Grade=GRADE_TXT[b['grade']], Score=b['score'],
                          **{'Avoid share': f"{1 - len(ok) / len(rs):.0%}"}, Note=reasons(b['items'], n=2)))
    else:
        from collections import Counter
        c = Counter(t.split(':')[0] for r in rs for _, t, _, _, k in r['items'] if k == 'avoid').most_common(1)
        drows.append(dict(Date=f"{dte:%a %d %b}", **{'Best time': '—'}, Grade='Avoid', Score=None, **{'Avoid share': '100%'},
                          Note='All day: ' + (c[0][0] if c else '')))
if not PHONE:                 # on a phone the day-by-day list at the top already covers this
    st.subheader('Day by day')
    st.dataframe(pd.DataFrame(drows), hide_index=True, width='stretch')

c1, c2 = st.columns(2)
c1.download_button('Download best windows (.ics calendar)', el.ics(W[:40], U['label'] + (f" ({user_profile.get()['name']})" if user_profile.get()['name'] else ''), place, step),
                   file_name=f'auspicious_{kind}_{start:%Y%m%d}.ics', mime='text/calendar', width='stretch')
csv = pd.DataFrame([dict(local_time=r['local'].strftime('%Y-%m-%d %H:%M'), utc=r['utc'].strftime('%Y-%m-%d %H:%M'),
                         grade=r['grade'], score=r['score'], rising=r['rising'], lord_of_asc=r['lord1'], lord_of_matter=r['lordm'],
                         moon=r['moon'], day_ruler=r['day_ruler'], hour_ruler=r['hour_ruler'],
                         reasons=' | '.join(f"{p:+.1f} {t}" for _, t, p, _, k in r['items'])) for r in res]).to_csv(index=False)
c2.download_button('Download every moment (.csv)', csv, file_name=f'auspicious_{kind}_{start:%Y%m%d}.csv', mime='text/csv', width='stretch')

with st.expander('Sources and certainty (elections)'):
    st.markdown("Each rule carries its source in Lilly and a **basis**: *sourced* (Lilly's own rule), *sourced in substance* "
                "(Lilly's doctrine, the app's wording), or *app rule*. The point values are app choices. Lilly built his "
                "judgments on the balance of testimonies, not on a fixed formula.")
    device.table(pd.read_csv(os.path.join(HERE, 'data', 'election_rules.csv'), encoding='utf-8'))
    st.caption('This is traditional symbolism, offered for study and reflection; controlled studies have not found '
               'astrological timing to affect outcomes.')
