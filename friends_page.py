"""Page 3: friends. Share and import friend cards, compare two nativities, and find auspicious times good for both."""
import calendar
import datetime as dt
import html
import os
import pandas as pd
import streamlit as st

import electional as el
import lilly_layer as ll
import natal
import inputs
import places
import user_profile as upf
import device
from calendar_view import GRADE_TXT, compute, heatmap, reasons, day_list

HERE = os.path.dirname(os.path.abspath(__file__))
me = upf.get()
upf.title('Friends · comparing charts', '{who} friends · comparing charts')
st.caption('Share your friend card with someone, add theirs, then compare your birth charts and find times that are good '
           'for both of you. There are no accounts: cards travel only by the e-mail or message you choose to send.')


def person_line(p, size=44):
    return (f'<div style="display:flex;align-items:center;gap:12px;">{upf.person_avatar(p, size)}'
            f'<div><b>{html.escape(p["name"])}</b><br><span style="color:#c4ccdb;font-size:0.85rem;">'
            f'{html.escape(upf.birth_text(p["birth"]))}</span></div></div>')


# ---------------------------------------------------------------- 1. share
st.subheader('1 · Share your friend card')
if not me['name'] or not me['birth']:
    st.info('Your card needs your name and birth details. Click **Add your name and picture** / **Edit profile** at the '
            'top of the sidebar (on a phone, open the sidebar with the arrow at the top left), tick *Add my birth date, '
            'time and place*, and save.')
else:
    with st.container(border=True):
        st.markdown(person_line(me), unsafe_allow_html=True)
        st.write('')
        pic = st.checkbox('Include my picture in the card file', value=True, key='fr_pic')
        q_, a, b = st.columns(3)
        with q_.popover('Show a QR code', icon=':material/qr_code_2:', width='stretch'):
            st.markdown('**Let a friend scan this with their phone camera.** It opens The Sidereal Oracle and offers '
                        'to add you to their friends.')
            try:
                st.image(upf.card_qr_png(), width=280)
            except Exception as e:                    # e.g. qr_code.py not uploaded
                st.warning(f'The QR code could not be made ({e}). Use the card file or the text code instead.')
            st.caption('The QR code holds your name, birth date, birth time and birthplace (not your picture). '
                       'Show it only to people you want to have them.')
        a.download_button('Download my friend card (.lillycard)', upf.card_file(pic),
                          file_name=upf.card_filename(), mime='application/json', width='stretch')
        with b.popover('Or copy a text code', width='stretch'):
            st.caption('Copy this code (button at the right of the box) and paste it into an e-mail or message. '
                       'The code does not include your picture.')
            st.code(upf.card_code(), language=None, wrap_lines=True)
        st.caption('The card holds your name, birth date, birth time and birthplace' + (' and picture' if pic else '')
                   + '. Send it only to people you want to have them.')

# ---------------------------------------------------------------- 2. add
st.subheader('2 · Add a friend')
with st.container(border=True):
    t1, t2, t3 = st.tabs(['Upload a card file', 'Paste a code', 'Optional: enter their data by hand'])
    found, err = None, None
    with t1:
        f = st.file_uploader('Your friend\'s .lillycard file', type=['lillycard', 'json'], key='fr_file')
        if f is not None:
            try:
                found = upf.parse_card(f.getvalue())
            except ValueError as e:
                err = str(e)
    with t2:
        code = st.text_area('Paste the code (it starts with LILLY1:)', key='fr_code', height=90)
        if code.strip() and found is None:
            try:
                found = upf.parse_card(code)
            except ValueError as e:
                err = str(e)
    with t3:
        # for someone without the app (user request): name, birth date, time and place typed in by hand
        st.caption("For someone who doesn't use the app. Their details are kept like a friend card: only add people "
                   'who are happy for you to have them.')
        m_name = st.text_input('Their name', key='mf_name', max_chars=upf.MAX_NAME, placeholder='e.g. Anna')
        m_date = upf._date_inputs('mf', dt.date(1990, 1, 1))
        m_unknown = st.checkbox('Birth time not known (noon is used)', key='mf_unknown')
        m_time = dt.time(12, 0) if m_unknown else st.time_input('Birth time (local clock, 24-hour)', dt.time(12, 0),
                                                                   step=60, key='mf_time')
        m_q = st.text_input('Birthplace', key='mf_place', placeholder='e.g. London, Kraków, Chicago')
        m_hits = places.search(m_q, n=10) if m_q.strip() else []
        manual = None
        if m_q.strip() and not m_hits:
            st.warning('No match in the gazetteer (places with at least 1,000 inhabitants). Try a nearby town.')
        if m_hits:
            mi = st.selectbox('Matches', range(len(m_hits)), format_func=lambda k: places.label(m_hits[k]), key='mf_pick')
            h = m_hits[mi]
            off, note = places.utc_offset_hours(h['tz'], dt.datetime.combine(m_date, m_time))
            if st.checkbox(f'Override the UTC offset at birth (automatic: {off:+.2f} h)', key='mf_override'):
                off = st.number_input('UTC offset at birth (hours)', -12.0, 14.0, float(off), 0.25, key='mf_off')
            elif note:
                st.caption(note)
            m_birth = upf._valid_birth(dict(date=m_date.isoformat(), time=m_time.strftime('%H:%M'),
                                            time_known=not m_unknown, place=f"{h['name']}, {h['country']}",
                                            lat=h['lat'], lon=h['lon'], tz=h['tz'], utc_offset=off))
            n_ = upf.clean_name(m_name)
            if m_birth:
                st.caption(f"{upf.birth_text(m_birth)} · {h['lat']:.3f}°, {h['lon']:.3f}° · UTC{off:+.2f}")
            if not n_:
                st.info('Type their name to add them.')
            elif m_birth:
                manual = dict(name=n_, birth=m_birth, avatar=None)
        if manual and st.button(f"Add {manual['name']} to my friends", type='primary', key='mf_add'):
            upf.add_friend(manual)
            for k in ('mf_name', 'mf_place', 'mf_pick', 'mf_unknown', 'mf_time', 'mf_override', 'mf_off',
                      'mf_y', 'mf_m', 'mf_d'):
                st.session_state.pop(k, None)
            st.toast(f"{manual['name']} added to your friends.")
            st.rerun()
    if err:
        st.error(err)
    if found:
        st.markdown(person_line(found), unsafe_allow_html=True)
        if st.button(f"Add {found['name']} to my friends", type='primary', key='fr_add'):
            upf.add_friend(found)
            for k in ('fr_code',):
                st.session_state.pop(k, None)
            st.success(f"{found['name']} added.")
            st.rerun()

# ---------------------------------------------------------------- 3. list
friends = upf.friends()
st.subheader('3 · Your friends')
if not friends:
    st.caption('No friends added yet.')
for fr in friends:
    c1, c2 = st.columns([0.8, 0.2], vertical_alignment='center')
    c1.markdown(person_line(fr), unsafe_allow_html=True)
    if c2.button('Remove', key='rm_' + fr['id'], width='stretch'):
        upf.remove_friend(fr['id'])
        st.rerun()
st.caption('Saved on this computer in the app\'s "profile" folder.' if upf.LOCAL else
           ('Remembered on this device (with your profile). Keep their card files to add them on other devices.'
            if getattr(upf, 'remembered', lambda: False)() else
            'Online, friends are kept only while the app is open, unless you tick "Remember me on this device" in '
            'your profile. Keep their card files to add them again.'))

# ---------------------------------------------------------------- 4. compare
st.subheader('4 · Compare and combine')
if not (me['birth'] and friends):
    st.info('To compare, you need your own birth details in your profile and at least one friend.')
    st.stop()
fi = st.selectbox('Friend', range(len(friends)), format_func=lambda i: friends[i]['name'], key='fr_pick')
fr = friends[fi]
my_name = me['name'] or 'You'
na, nb = natal.chart_of(me['birth']), natal.chart_of(fr['birth'])

st.markdown(f'#### How your nativities agree')
with st.container(border=True):
    cols = st.columns(2)
    for col, p, n in ((cols[0], me, na), (cols[1], fr, nb)):
        col.markdown(person_line(p), unsafe_allow_html=True)
        with col:
            device.table(pd.DataFrame([dict(Place=k, Constellation=n['bands'][k], **{'Ecl. long. (°)': round(v, 1)})
                                       for k, v in n['places'].items()]))
    syn = natal.synastry(na, nb, my_name, fr['name'])
    st.markdown(f"**{syn['summary']}**  Agreement {syn['harmony']:.0f} · discord {syn['discord']:.0f}.")
    if syn['items']:
        st.markdown('\n'.join(f"- {'+' if i['points'] > 0 else ''}{i['points']:.0f}  {i['text']}" for i in syn['items']))
    st.caption('Rule: Ptolemy, Tetrabiblos IV.7 (on friends and enemies), the source Lilly draws on in Book III '
               '(page reference still to be checked): compare the Sun, Moon, Ascendant and '
               'Part of Fortune of the two nativities; the same sign, trine or sextile make for friendship, square or '
               'opposition for discord, and harmony between one\'s Sun and the other\'s Moon is the strongest bond (counted double). '
               'Orb and points are app choices (data/natal_rules.csv).')

st.markdown('#### Auspicious times for both of you')
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        kind = st.radio('Undertaking', list(el.UNDERTAKINGS), index=1, format_func=lambda k: el.UNDERTAKINGS[k]['label'],
                        key='fr_kind')
        if el.UNDERTAKINGS[kind].get('note'):
            st.info(el.UNDERTAKINGS[kind]['note'], icon=':material/favorite:' if kind == 'romance' else ':material/group:')
        today = dt.date.today()
        y_, m_, d_ = st.columns([1.3, 1.4, 1])
        year = y_.number_input('Year', 1850, 2149, min(max(today.year, 1850), 2149), 1, key='fr_year')
        month = m_.selectbox('Month', range(1, 13), index=today.month - 1, format_func=lambda m: calendar.month_abbr[m], key='fr_month')
        nd = calendar.monthrange(int(year), int(month))[1]
        day = d_.number_input('Day', 1, nd, min(today.day, nd), 1, key='fr_day')
        start = dt.date(int(year), int(month), int(day))
        days = st.slider('Number of days', 7, 92, 31, key='fr_days')
        h0, h1 = st.slider('Hours of the day to consider', 0, 24, (8, 22), key='fr_hours')
        step = st.select_slider('Time step (minutes)', [15, 30, 60], 30, key='fr_step')
    with c2:
        st.caption('Where you will meet or begin:')
        place, lat, lon, tzname, elev = inputs.place_picker('f')
        tzkey = tzname or 'UTC+0.00'
    ok = h1 > h0 and start + dt.timedelta(days=days) <= dt.date(2149, 12, 31)
    go = st.button('Find times good for both', type='primary', disabled=not ok, key='fr_go')

params = (kind, lat, lon, elev, tzkey, start, days, h0, h1, step, 'table', fr['id'])
if go:
    with st.spinner('Judging every moment for both of you ... (about 20 seconds per month)'):
        st.session_state['fr_result'] = (params, compute(*params[:-1]))
if 'fr_result' not in st.session_state or st.session_state['fr_result'][0][-1] != fr['id']:
    st.stop()
p_used, (res, bands, _) = st.session_state['fr_result']
if p_used != params:
    st.warning('The settings have changed since this was computed. Press **Find times good for both** to update it.')
kind, lat, lon, elev, tzkey, start, days, h0, h1, step, _, _ = p_used
U = el.UNDERTAKINGS[kind]
ra = natal.personalise(res, na, 'your')
rb = natal.personalise(res, nb, upf.possessive(fr['name']))
joint = []
for g, a, b in zip(res, ra, rb):
    extra_b = [x for x in b['items'][len(g['items']):]]
    joint.append(dict(a, items=a['items'] + extra_b, score=round(min(a['score'], b['score']), 1),
                      score_a=a['score'], score_b=b['score']))
q = el.grade(joint)
W = el.windows(joint)

st.markdown(f"**{U['label']}**, judged for both: a moment counts only as well as it does for the one of you it suits "
            "less, and it is Avoid if Lilly's cautions apply.")
if device.phone():
    st.markdown(day_list(joint, W, start, days, step), unsafe_allow_html=True)
    st.caption('Up to three Best or Good windows per day, for both of you. The grid below shows every hour.')
st.pyplot(heatmap(joint, start, days, h0, h1, step, compact=device.phone()), width='stretch')
if q:
    st.caption(f'Best = top 10 % of the joint scores in this period (≥ {q[0]:.1f}); Good = next 25 % (≥ {q[1]:.1f}).')
if W:
    device.table(pd.DataFrame([dict(Date=f"{w['date']:%a %d %b %Y}", From=w['start'].strftime('%H:%M'),
                                    To=(w['end'] + dt.timedelta(minutes=step)).strftime('%H:%M'), Grade=GRADE_TXT[w['grade']],
                                    **{'For both': w['score'], f'For {my_name}': w['peak']['score_a'],
                                       f"For {fr['name']}": w['peak']['score_b']},
                                    **{'Main reasons': reasons(w['peak']['items'])}) for w in W[:20]]),
                 ['Date', 'From', 'Grade', 'For both'])
else:
    st.info('No Good or Best windows for both in this period. Try more days or more hours.')

st.markdown('#### Where your readings differ')
ok_ = [j for j in joint if not j['avoid']]
diff = sorted(ok_, key=lambda j: -abs(j['score_a'] - j['score_b']))[:10]
if diff:
    device.table(pd.DataFrame([dict(When=f"{j['local']:%a %d %b %H:%M}", **{f'For {my_name}': j['score_a'],
                                    f"For {fr['name']}": j['score_b']},
                                    **{'Better for': my_name if j['score_a'] > j['score_b'] else fr['name']},
                                    Why='; '.join(t for _, t, _, _, k in j['items'] if 'natal' in t)[:300])
                               for j in diff]), ['When', f'For {my_name}', f"For {fr['name']}", 'Better for'])
    st.caption('These moments pass the cautions but suit one of you clearly more than the other, usually because a '
               'planet is touching one person\'s Sun, Moon or Ascendant.')

st.download_button('Download the times good for both (.ics calendar)',
                   el.ics(W[:40], f"{U['label']} ({my_name} & {fr['name']})", place, step),
                   file_name=f"together_{kind}_{start:%Y%m%d}.ics", mime='text/calendar')
with st.expander('Sources and certainty (birth charts)'):
    device.table(pd.read_csv(os.path.join(HERE, 'data', 'natal_rules.csv'), encoding='utf-8'))
    st.caption('This is traditional symbolism, offered for study and reflection; controlled studies have not found '
               'astrological comparison or timing to predict how relationships or undertakings turn out.')
