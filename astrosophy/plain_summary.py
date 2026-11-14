"""Birth chart: the summary in plain English (after the Sidereal Oracle's "What does this mean?").

  overview(...)  the short summary shown in the 'In short' box at the top of the Birth chart tab;
  show(...)      the window 'Your chart in plain English', opened by the button "What does this mean?":
                 In short; the seven planets in everyday words; before birth (the prenatal epoch); where the life
                 stands now; morning and evening star; what this is and is not. Under each part, 'Show the working'
                 gives the original terms (Steiner's world-views and soul moods, Sucher's rule) and their sources.

All wording is fixed: the 'plain' columns of data/world_views.csv, data/soul_moods.csv and data/life_spheres.csv, and
the sentences in data/plain_texts.csv (with {placeholders} filled in from the chart). Nothing is written by an AI
chatbot while the app runs. The calculations are those of the rest of the app; nothing new is computed here.
"""
import os

import pandas as pd
import streamlit as st

from . import astrosophy_engine as E
from . import astrosophy_layer as L
import device

HERE = os.path.dirname(os.path.abspath(__file__))
GA151 = 'Steiner, Human and Cosmic Thought (GA 151), lecture 3, 22 Jan 1914'


@st.cache_data(show_spinner=False)
def _texts():
    df = pd.read_csv(os.path.join(HERE, 'data', 'plain_texts.csv'), encoding='utf-8-sig')
    return dict(zip(df['key'], df['text']))


def T(key, **kw):
    """A fixed sentence from data/plain_texts.csv, with its {placeholders} filled in."""
    return str(_texts().get(key, '')).format(**kw)


def _plain(series_value):
    return '' if pd.isna(series_value) else str(series_value)


def world_plain(abbr):
    """Everyday words for the world-view of an IAU zodiac band (Ophiuchus: the app's passage reading)."""
    if abbr == 'Oph':
        return T('ophiuchus')
    return _plain(L.tables().world.loc[E.ZODIAC_NAME[abbr]].get('plain'))


def mood_plain(planet):
    return _plain(L.tables().moods.loc[planet].get('plain'))


def _voice(mine):
    """'you' when the chart is the user's own (profile), else neutral words."""
    return (dict(who_obj='you', who_subj='you', are='are') if mine else
            dict(who_obj='the person born at this moment', who_subj='the life', are='is'))


def _event_plain(r):
    b, z = str(r['bodies']), str(r['zodiac'])
    if r['event'] == 'conjunction':
        a, c = [x.strip() for x in b.split('\u2013')]
        return f'{a} and {c} meet in {z}'
    if r['event'] == 'enters':
        a, c = [x.strip() for x in b.split('\u2192')]
        return f'{a} moves into {c}'
    if r['event'] == 'station':
        p = b.split(' turns')[0]
        if 'retrograde' in b:
            return f'{p} seems to stand still in {z}, then moves backwards for a while'
        return f'{p} seems to stand still in {z}, then moves forwards again'
    return b


def overview(ch, ep, now_utc, mine):
    """The short summary (Markdown) for the 'In short' box."""
    sun, moon = E.body(ch, 'Sun'), E.body(ch, 'Moon')
    zn = lambda b: E.con_name(b.zodiac)
    s = (f"At this birth the **Sun** stood in **{zn(sun)}** and the **Moon** in **{zn(moon)}**, and "
         f"**{E.con_name(ch['asc_zodiac'])}** was rising in the east. ")
    s += (f"In Steiner's picture, the Sun's mood, *{mood_plain('Sun')}*, meets *{world_plain(sun.zodiac)}*; "
          f"the Moon's mood, *{mood_plain('Moon')}*, meets *{world_plain(moon.zodiac)}*.")
    if 'Oph' in (sun.zodiac, moon.zodiac):
        s += ' ' + T('ophiuchus_note')
    if ep is not None:
        s += f" The prenatal epoch fell on {ep.utc:%d %B %Y}, {ep.gestation_days:.0f} days before birth."
    age = L.age_years(ch['utc'], now_utc)
    if 0 <= age < 63:
        ls = L.life_sphere(age)
        v = _voice(mine)
        s += (f" Now, at age {int(age)}, {v['who_subj']} {v['are']} in the {ls['sphere']} period "
              f"({ls['age_from']}\u2013{ls['age_to']}).")
    return s + '\n\n' + T('reflection', **_voice(mine))


def _planet_rows(ch, senses):
    rows = []
    for b in ch['bodies']:
        if b.name not in E.CLASSICAL:
            continue
        zr = L.zodiac_reading(b.zodiac, senses)
        mood = L.tables().moods.loc[b.name]
        rows.append(dict(b=b, zodiac=zr['zodiac'], terms=f"{mood.soul_mood} in the sign of {zr['world_view']}"
                         if b.zodiac != 'Oph' else f"{mood.soul_mood} between Dynamism and Monadism",
                         plain=T('pair', mood=mood_plain(b.name), world=world_plain(b.zodiac))))
    return rows


def _working(df, note):
    device.table(df)
    st.caption(note)


def show(ch, ep, ev, now_utc, senses, who, place, local, mine, name=''):
    st.caption(f"{who} \u00b7 {local:%A %d %B %Y, %H:%M} local time \u00b7 {place}"
               + (f" \u00b7 prepared for {name}" if name and not mine else ''))
    st.markdown(T('intro'))

    st.markdown('#### In short')
    st.markdown(overview(ch, ep, now_utc, mine))
    sun = E.body(ch, 'Sun')
    st.caption(T('sidereal_note', tropical=sun.tropical_sign))

    st.markdown('#### The seven planets in everyday words')
    rows = _planet_rows(ch, senses)
    lines = []
    for r in rows:
        b = r['b']
        line = f"- **{E.GLYPH[b.name]} {b.name} in {r['zodiac']}**: {r['plain']}."
        if b.off_zodiac:
            line += ' ' + T('off_zodiac', body=('the ' if b.name in ('Sun', 'Moon') else '') + b.name,
                            true=E.con_name(b.iau_true))
        lines.append(line)
    st.markdown('\n'.join(lines))
    if any(r['b'].zodiac == 'Oph' for r in rows) or ch['asc_zodiac'] == 'Oph':
        st.caption(T('ophiuchus_note'))
    st.markdown(T('rising', rising=E.con_name(ch['asc_zodiac'])))
    with st.expander('Show the working', icon=':material/calculate:'):
        _working(pd.DataFrame([dict(Planet=r['b'].name, Constellation=r['zodiac'], **{"Steiner's terms": r['terms']},
                                    Tropical=r['b'].tropical_sign, Source=GA151) for r in rows]),
                 "Steiner's soul moods (planets) and world-views (zodiac), GA 151. Ophiuchus as a passage is an app "
                 'rule. The rising point as a doorway: Sucher (1937). ' + T('wording'))

    st.markdown('#### Before birth: the prenatal epoch')
    if ep is None:
        st.markdown(T('epoch_none'))
    else:
        st.markdown(T('epoch', date=f'{ep.utc:%d %B %Y}', days=f'{ep.gestation_days:.0f}', target=ep.target)
                    + ' ' + T('epoch_cycles', n=ep.months))
        st.markdown(T('birth_time_check', angle=ep.residual_angle, deg=f'{ep.residual_deg:.0f}'))
        with st.expander('Show the working', icon=':material/calculate:'):
            _working(pd.DataFrame([
                dict(Item='Case of the Hermetic Rule', Value=f'{ep.case}: {ep.case_text}'),
                dict(Item='Epoch (UTC)', Value=f'{ep.utc:%d %b %Y, %H:%M}'),
                dict(Item='Days before birth', Value=f'{ep.gestation_days:.1f} (standard {ep.months} sidereal months '
                                                     f'= {ep.months * E.SIDEREAL_MONTH:.1f})'),
                dict(Item='Target at birth', Value=f'{ep.target}, {ep.target_lon:.2f}\u00b0'),
                dict(Item='Check on the birth time', Value=f'{ep.residual_angle} at the epoch is '
                                                           f'{ep.residual_deg:.1f}\u00b0 from the birth Moon')]),
                     'Sucher, Looking Through the Horoscope of Birth (1937) and Prenatal events (1937). '
                     'The details are on the Prenatal epoch and Life rhythms tabs.')

    st.markdown('#### Where the life stands now' if not mine else '#### Where you stand now')
    v = _voice(mine)
    age = L.age_years(ch['utc'], now_utc)
    if age < 0:
        st.markdown(T('now_future'))
    elif age >= 63:
        st.markdown(T('now_beyond', age=int(age), **v))
    else:
        ls = L.life_sphere(age)
        st.markdown(T('now', age=int(age), sphere=ls['sphere'], a=ls['age_from'], b=ls['age_to'],
                      plain=_plain(ls.get('plain')), **v))
        if ls['sphere'] in ('Mercury', 'Venus'):
            st.caption(T('mercury_venus_note'))
        if ev is not None and len(ev):
            k = int(age // 7)
            win = ev[(ev.age >= 7 * k) & (ev.age < 7 * (k + 1)) & (ev.event != 'Moon passes')]
            if len(win):
                st.markdown(T('now_events', k=k + 1) + '\n' +
                            '\n'.join(f'- at about age {int(r.age)}: {_event_plain(r)}' for _, r in win.iterrows()))
            else:
                st.markdown(T('now_events_none', k=k + 1))
        with st.expander('Show the working', icon=':material/calculate:'):
            _working(pd.DataFrame([dict(Ages=f"{ls['age_from']}\u2013{ls['age_to']}", Planet=ls['sphere'],
                                        Member=ls['member'], Source=ls['source'])]),
                     'Seven-year periods: Steiner, with Vreede (Astronomy and Anthroposophy, letter 8). Matching a '
                     "period with a round of the Moon before birth: Sucher's prenatal graph (Life rhythms tab).")

    st.markdown('#### Morning and evening star')
    vm = [b for b in ch['bodies'] if b.name in ('Venus', 'Mercury')]
    parts = [T('morning' if 'morning' in b.note else 'evening', body=b.name) for b in vm]
    st.markdown(T('morning_evening', list='; '.join(parts)))

    st.markdown('#### What this is, and what it is not')
    st.markdown(T('outer') + ' ' + T('honesty'))
    st.caption(T('wording'))


@st.dialog('Your chart in plain English', width='large')
def dialog(*args, **kw):
    show(*args, **kw)
