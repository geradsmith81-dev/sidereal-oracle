"""The Astrosophy Birth Chart, as a page of this app (user request).

A sidereal star chart on the 13 IAU zodiac constellations, read through Rudolf Steiner's indications and the
astrosophy of Elisabeth Vreede and Willi Sucher, with the tabs of the Astrosophy Birth Chart app: Birth chart,
Prenatal epoch, Life rhythms, Biography chart, Today's sky, Sources & caveats. The calculations and the wording are
the Astrosophy app's own (the astrosophy folder); the profile, the place search, the phone layout and the colours are
this app's. The chart is geocentric, so there is no elevation box.
"""
from __future__ import annotations

import calendar
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

import device
import theme
import user_profile as UP
from astrosophy import astro_inputs as inputs

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    from astrosophy import astrosophy_engine as E
    E.sky()                     # the app's own JPL file (the ephem folder)
except Exception as e:
    st.error("The NASA JPL planetary data file (de440s.bsp) could not be loaded for the Astrosophy page. Check the "
             "internet connection and reload the page. Details: " + str(e))
    st.stop()
from astrosophy import astrosophy_layer as L
from astrosophy import charts as C
from astrosophy import prenatal as P
from astrosophy import plain_summary as PS
from astrosophy import biography as BIO


def wheel_theme(phone):
    """The Astrosophy wheels in this app's colours (theme.PALETTE has the same colour roles as the Astrosophy app)."""
    p = theme.PALETTE
    wt = dict(fig_bg='none', bg=p['void'], face_alpha=0.82, panel=p['panel'], ring_a=p['band_a'], ring_b=p['band_b'],
              line=p['orbit'], text=p['starlight'], muted=p['dust'], gold=p['brass_pale'], flag=p['rose'],
              spoke=p['dust'], glyph_ring=False)
    if phone:                   # the phone layout: white symbols and labels, as on the other pages
        wt.update(text='#ffffff', muted='#ffffff', glyph_ring=True)
    return wt


def page_css():
    p = theme.PALETTE
    return (f"""<style>
    .astro-tag {{ font-size: 0.78em; color: {p['dust']}; border: 1px solid {p['orbit']}; border-radius: 6px;
        padding: 1px 6px; white-space: nowrap; }}
    .astro-subtitle {{ font-size: 1.12rem; color: {p['starlight']}; margin: -0.4rem 0 0.9rem 0; line-height: 1.45; }}
    .astro-card {{ border: 1px solid {p['orbit']}88; border-radius: 10px; padding: 0.55rem 0.8rem; margin: 0.2rem 0 0.7rem;
        background: {theme.rgba(p['band_a'], 0.6)}; }}
    </style>""")


def voice_note():
    """(The Foul-Mouthed Oracle puts a line in its own voice here.)"""
    return None


MONTHS = list(calendar.month_name)[1:]
PHONE = device.phone()
WT = wheel_theme(PHONE)
SUBTITLE = ("Your birth sky among the real constellations, calculated from NASA JPL planet positions and read through "
            "Rudolf Steiner's indications and the astrosophy of Elisabeth Vreede and Willi Sucher.")

st.markdown(page_css(), unsafe_allow_html=True)


# --------------------------------------------------------------------------- cached work
@st.cache_data(show_spinner=False, max_entries=16, ttl=3600)
def compute(utc_iso: str, lat: float, lon: float, months: int):
    utc = datetime.fromisoformat(utc_iso)
    ch = E.chart(utc, lat, lon)
    ep = ev = tr = cyc = None
    err = ""
    try:
        ep = P.hermetic_epoch(ch, months=months)
        if E.in_range(ep.utc):
            tr = P.prenatal_tracks(ep, ch)
            ev = P.prenatal_events(ep, ch)
            cyc = P.cycle_table(ep, ch)
    except Exception as exc:  # outside ephemeris range, etc.
        if "covers dates" in str(exc) or not E.in_range(utc - timedelta(days=300)):
            err = (f"the epoch lies about nine months before birth, i.e. before {E.sky().earliest:%Y}, where the "
                   "ephemeris file starts. To reach earlier dates, put JPL's larger file de440.bsp "
                   "(1550\u20132650) in the app's ephem folder (see READ ME FIRST).")
        else:
            err = str(exc)
    return ch, ep, tr, ev, cyc, err


@st.cache_data(show_spinner=False, max_entries=8, ttl=600)
def compute_now(lat: float, lon: float, stamp: str):
    return E.chart(datetime.fromisoformat(stamp), lat, lon)


def show(fig, legend=None):
    """A figure on the page; on a phone its key is written underneath instead of inside it."""
    st.pyplot(fig, width="stretch")
    if PHONE and legend:
        st.caption(" ".join(legend))


def tag(a: str) -> str:
    return f"<span class='astro-tag'>{a}</span>"


# --------------------------------------------------------------------------- sidebar and inputs
S = E.sky()
y_min, y_max = S.earliest.year + (1 if S.earliest.month > 1 else 0), S.latest.year
prof = UP.get()
mine_ok = False
with device.input_panel("Birth data: date, time and place", expanded=not UP.has_birth()):
    st.header("Birth data")
    if UP.has_birth():
        if st.session_state.get("chart_for") not in (UP.MINE, UP.OTHER):
            st.session_state["chart_for"] = UP.MINE
        st.radio("Whose chart?", [UP.MINE, UP.OTHER], key="chart_for", horizontal=PHONE)
    b = prof.get("birth")
    if UP.has_birth() and st.session_state.get("chart_for") == UP.MINE:
        local = datetime.combine(datetime.fromisoformat(b["date"]).date(), datetime.strptime(b["time"], "%H:%M").time())
        if local.year < y_min or local.year > y_max:
            st.warning(f"Your saved birth date is outside {y_min}\u2013{y_max}, the range of the ephemeris file in use.")
        else:
            mine_ok = True
        off, lat, lon, place_name = float(b["utc_offset"]), float(b["lat"]), float(b["lon"]), b["place"]
        label_txt = prof["name"] or "My chart"
        sign = "+" if off >= 0 else "\u2212"
        st.markdown(f"<div class='astro-card'><b>{UP.html.escape(label_txt)}</b><br>{UP.html.escape(UP.birth_text(b))}"
                    f"<br><span style='font-size:0.85em'>UTC offset {sign}{abs(off):.2f} h \u00b7 {lat:.3f}\u00b0, "
                    f"{lon:.3f}\u00b0</span></div>", unsafe_allow_html=True)
        st.caption("From your profile. To change it, use Edit profile at the top of the sidebar." +
                   (" The birth time is not known, so noon is used: the Ascendant and the epoch are only rough."
                    if not b.get("time_known", True) else ""))
    if not mine_ok:
        label_txt = st.text_input("Name or label (optional)", "", key="b_label")
        c1, c2, c3 = st.columns([1.1, 1.3, 0.9])
        year = c1.number_input("Year", min_value=y_min, max_value=y_max, value=2000, step=1, key="b_year")
        month = c2.selectbox("Month", MONTHS, index=0, key="b_month")
        m_i = MONTHS.index(month) + 1
        max_day = calendar.monthrange(int(year), m_i)[1]
        if st.session_state.get("day_value", 1) > max_day:
            st.session_state["day_value"] = max_day
        day = c3.number_input("Day", min_value=1, max_value=max_day, step=1, key="day_value")
        c4, c5 = st.columns(2)
        hour = c4.number_input("Hour (0\u201323)", 0, 23, 12, key="b_hour")
        minute = c5.number_input("Minute", 0, 59, 0, key="b_min")
        place_name, lat, lon, tz_name = inputs.place_picker("b")
        st.subheader("Clock time")
        modes = ["Automatic (time-zone rules)", "Local Mean Time of the birthplace", "Type the UTC offset"]
        mode = st.radio("The time above is \u2026", modes if tz_name else modes[1:], index=0, key="b_mode")
        local = datetime(int(year), m_i, int(day), int(hour), int(minute))
        tz_note = ""
        if mode.startswith("Automatic"):
            off, tz_note = inputs.utc_offset(local, tz_name)
            if local.year < 1900:
                tz_note += (" Before about 1900 many places kept their own local mean time; consider "
                            "'Local Mean Time of the birthplace'.")
        elif mode.startswith("Local Mean"):
            off = inputs.lmt_offset(lon)
        else:
            off = st.number_input("UTC offset in hours (e.g. 1 or -5.5)", -14.0, 14.0, 0.0, step=0.25, key="b_off")
        sign = "+" if off >= 0 else "\u2212"
        st.caption(f"UTC offset used: {sign}{abs(off):.2f} h")
        if tz_note.strip():
            st.info(tz_note.strip())
        if not UP.has_birth():
            st.caption("Tip: add your own birth details in your profile (top of the sidebar) and the app opens at "
                       "your chart next time.")

    st.subheader("Options")
    premature = st.toggle("Seven-month (premature) birth", value=False, key="o_premature",
                          help="Uses 8 sidereal months (\u2248218 days) for the Hermetic Rule instead of 10.")
    senses = st.radio("Senses-to-zodiac list", ["1921 sketch (Soesman)", "1913 esoteric lesson"], index=0,
                      key="o_senses")
    senses_key = "1921" if senses.startswith("1921") else "1913"

st.sidebar.caption("Astrosophy Birth Chart: readings from fixed tables of Steiner's, Vreede's and Sucher's "
                   "correspondences, each tagged with its source. Ephemeris: JPL " + S.ephem_name +
                   f" (dates {y_min}\u2013{y_max}).")

utc = (local - timedelta(hours=off)).replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------- the page
def main():
    UP.title("\u2726 Astrosophy Birth Chart", "\u2726 {who} Astrosophy Birth Chart")
    st.markdown(f"<p class='astro-subtitle'>{SUBTITLE}</p>", unsafe_allow_html=True)
    voice_note()
    intro = ("A sidereal star chart on the **IAU constellations** (13 on the ecliptic, including Ophiuchus), read "
             "through Rudolf Steiner's indications and the *astrosophy* that Elisabeth Vreede and Willi Sucher built "
             "on them. The positions are astronomically exact. The interpretations are traditional pictures offered "
             "for reflection: astrology has no support from controlled scientific studies, and Steiner himself "
             "warned against reading fate from a birth chart.")
    if PHONE:
        with st.expander("About this chart"):
            st.markdown(intro)
    else:
        st.markdown(intro)

    if not E.in_range(utc):
        st.error(f"This date is outside the range of the ephemeris ({y_min}\u2013{y_max}).")
        st.stop()

    ch, ep, tr, ev, cyc, err = compute(utc.isoformat(), float(lat), float(lon), 8 if premature else 10)
    who = (label_txt or "").strip() or "Chart"
    st.markdown(f"**{UP._md_escape(who)}** \u2014 {local:%d %B %Y, %H:%M} local ({utc:%H:%M} UTC), {place_name}")

    names = (["Chart", "Epoch", "Rhythms", "Biography", "Today", "Sources"] if PHONE else
             ["Birth chart", "Prenatal epoch", "Life rhythms", "Biography chart", "Today's sky", "Sources & caveats"])
    tab_birth, tab_epoch, tab_life, tab_bio, tab_now, tab_src = st.tabs(names)
    now = datetime.now(timezone.utc)

    # ----------------------------------------------------------------------- birth chart
    with tab_birth:
        # the summary in plain English first and most prominent, as on the Sidereal Oracle's Chart page
        with st.container(border=True):
            st.markdown("#### In short")
            st.markdown(PS.overview(ch, ep, now, mine_ok))
            if st.button("What does this mean?", type="primary", icon=":material/lightbulb:", key="plain_btn",
                         width="stretch", help="The whole chart in everyday words: the planets, the time before "
                                               "birth and where the life stands now, with the working underneath."):
                PS.dialog(ch, ep, ev, now, senses_key, who, place_name, local, mine_ok, name=prof.get("name", ""))
        left, right = (st.container(), st.container()) if PHONE else st.columns([1.05, 1])
        with left:
            fig = C.draw_wheel(ch, title=(f"{who}: geocentric sky" if PHONE else
                                          f"{who}: geocentric sky, IAU zodiac"), theme=WT, compact=PHONE)
            show(fig, C.legend_lines())
            st.download_button("Download wheel (PNG)", C.png_bytes(fig, WT), file_name="birth_wheel.png",
                               mime="image/png", on_click="ignore")
            with st.expander("Heliocentric view (Sucher: complementary to the geocentric)"):
                show(C.draw_wheel(ch, helio=True, theme=WT, compact=PHONE), C.legend_lines(helio=True))
        with right:
            paras = L.reading(ch, senses_key, epoch=ep, events=ev, now_utc=now)
            for ptxt in paras:
                st.markdown(f"**{ptxt['heading']}** {tag(ptxt['attr'])}", unsafe_allow_html=True)
                st.write(ptxt["text"])
        st.subheader("Planets, constellations and Steiner's correspondences")
        pt = L.planet_table(ch, senses_key).drop(columns=["_lon"])
        device.table(pt, phone_cols=["body", "zodiac (IAU)", "Steiner's picture", "notes"])
        st.download_button("Download table (CSV)", pt.to_csv(index=False).encode("utf-8-sig"),
                           file_name="birth_chart.csv", mime="text/csv", on_click="ignore")
        st.caption(f"Ascendant {ch['asc']:.2f}\u00b0 in {E.con_name(ch['asc_zodiac'])}; MC {ch['mc']:.2f}\u00b0 in "
                   f"{E.con_name(ch['mc_zodiac'])}; mean lunar node {ch['node']:.2f}\u00b0 in "
                   f"{E.con_name(ch['node_zodiac'])}. Longitudes are ecliptic of date (the tropical figure).")

    # ----------------------------------------------------------------------- epoch
    with tab_epoch:
        if ep is None:
            st.warning("The epoch could not be computed: " + (err or "unknown reason"))
        else:
            st.markdown(
                f"**Epoch:** {ep.utc:%d %B %Y, %H:%M} UTC \u2014 {ep.gestation_days:.1f} days before birth "
                f"(standard: {ep.months} sidereal months = {ep.months * E.SIDEREAL_MONTH:.1f} days).")
            st.markdown(f"**Case {ep.case} of the Hermetic Rule** {tag('Sucher 1937')}: {ep.case_text}",
                        unsafe_allow_html=True)
            st.write(f"Target: the birth {ep.target} at {ep.target_lon:.2f}\u00b0 "
                     f"({E.con_name(str(E.zodiac_band_at(ep.target_lon, ch['t'])[0]))}). "
                     f"The Moon reached it at the moment shown.")
            st.write(f"Reciprocal check: at the epoch the {ep.residual_angle} lies {ep.residual_deg:.1f}\u00b0 from "
                     "the birth Moon. In the classical rule it should be close to 0\u00b0. Astrologers using this "
                     "rule take a large difference as a sign that the recorded birth time may need correcting. The "
                     "app reports the figure and leaves the time as entered.")
            if not ep.consistent:
                st.warning("The computed gestation length does not follow Sucher's case rule; please report this.")
            if not E.in_range(ep.utc):
                st.warning("The epoch lies before the start of the ephemeris; the prenatal graph is unavailable.")
            a, b_ = (st.container(), st.container()) if PHONE else st.columns(2)
            with a:
                show(C.draw_wheel(ep.chart, title="Sky at the epoch (birthplace)", theme=WT, compact=PHONE),
                     C.legend_lines())
            with b_:
                device.table(L.planet_table(ep.chart, senses_key)[["body", "zodiac (IAU)", "Steiner's picture", "notes"]],
                             phone_cols=["body", "zodiac (IAU)", "Steiner's picture"])
                if cyc is not None:
                    st.markdown("**The Moon's returns to its epoch place** " + tag("Sucher"),
                                unsafe_allow_html=True)
                    device.table(cyc)

    # ----------------------------------------------------------------------- life rhythms
    with tab_life:
        age = L.age_years(utc, now)
        st.markdown("Steiner described human life in seven-year periods under the planetary spheres. In Sucher's "
                    "prenatal graph, each sidereal Moon cycle between the epoch and birth reflects one of these "
                    "seven-year periods: the first cycle reflects ages 0\u20137, the second 7\u201314, and so on.")
        spheres = L.tables().life.copy()
        spheres["age_to"] = spheres["age_to"].where(spheres["age_to"] < 200, None)
        if age >= 0:
            ls = L.life_sphere(age)
            if age < 63:
                st.info(f"Today (age {age:.1f}): {ls['sphere']} period, {ls['member']}.")
            else:
                st.info(f"Today (age {age:.1f}): past the seven planetary periods, which end at 63.")
        if tr is not None:
            figp = C.draw_prenatal(tr, ev, ep, ch, theme=WT, compact=PHONE)
            show(figp)
            st.download_button("Download prenatal graph (PNG)", C.png_bytes(figp, WT), file_name="prenatal_graph.png",
                               mime="image/png", on_click="ignore")
            kinds = st.multiselect("Show events", ["conjunction", "enters", "station", "Moon passes"],
                                   default=["conjunction", "enters", "station"], key="l_kinds")
            top = int(7 * len(tr.attrs["cycle_starts"]))
            lo_hi = st.slider("Ages", 0, top, (0, top), step=7, key="l_ages")
            shown = ev[ev.event.isin(kinds) & ev.age.between(*lo_hi)]
            device.table(shown, phone_cols=["age", "event", "bodies", "zodiac"])
            st.download_button("Download events (CSV)", ev.to_csv(index=False).encode("utf-8-sig"),
                               file_name="prenatal_events.csv", mime="text/csv", on_click="ignore")
        device.table(spheres, phone_cols=["age_from", "age_to", "sphere", "member"])

    # ----------------------------------------------------------------------- biography chart
    with tab_bio:
        BIO.show_tab(ch, ev, now, mine_ok, who, PHONE, WT)

    # ----------------------------------------------------------------------- today
    with tab_now:
        h_name, h_lat, h_lon, h_tz, why = inputs.home_place()
        stamp = now.replace(second=0, microsecond=0).isoformat()
        nc = compute_now(float(h_lat), float(h_lon), stamp)
        local_now = inputs.now_local(h_tz) if h_tz else now.replace(tzinfo=None)
        st.markdown(f"The sky now ({local_now:%d %B %Y, %H:%M} local" + (f", {h_tz}" if h_tz else "") +
                    f"; {now:%H:%M} UTC) as seen from **{h_name}**.")
        if why == "home":
            st.caption("Place: where you live (your profile).")
        else:
            st.caption((f"Place guessed from your device's time zone ({why[3:]}). " if why.startswith("tz:") else "")
                       + "To use your own town, add 'Where you live' in your profile (top of the sidebar).")
        a, b_ = (st.container(), st.container()) if PHONE else st.columns(2)
        with a:
            show(C.draw_wheel(nc, title="Now: geocentric, IAU zodiac", theme=WT, compact=PHONE), C.legend_lines())
        with b_:
            show(C.draw_wheel(nc, helio=True, title="Now: heliocentric", theme=WT, compact=PHONE),
                 C.legend_lines(helio=True))
        device.table(L.planet_table(nc, senses_key).drop(columns=["_lon"]),
                     phone_cols=["body", "zodiac (IAU)", "Steiner's picture", "notes"])

    # ----------------------------------------------------------------------- sources
    with tab_src:
        st.markdown("""
**Who said what.** Each reading carries a tag.
* **Steiner**: a correspondence Steiner gave himself, e.g. the twelve world-views and seven soul moods
  (*Human and Cosmic Thought*, GA 151, 1914), the eurythmy sounds (GA 279) and the twelve senses.
* **Vreede / Sucher**: the *astrosophy* of Elisabeth Vreede and Willi Sucher. The term and the methods are
  theirs, not Steiner's: the Hermetic Rule epoch, the prenatal graph, and the heliocentric view alongside the
  geocentric.
* **app rule**: a choice this app makes where the sources say nothing, e.g. Ophiuchus.

**Astronomy.** Positions come from JPL DE440s through Skyfield and are geocentric apparent; the
heliocentric positions are geometric. Constellations follow the official IAU boundaries (Delporte 1930).
A body's reading uses the zodiac constellation on the ecliptic at its longitude. If the body itself lies in a
neighbouring constellation (e.g. the Moon in Orion, Pluto in Cetus), the app notes this.

**Honesty note.** The calculations show where the bodies really are. The meanings are a spiritual tradition.
Controlled studies have not found that birth charts predict personality or life events.

**Your information.** This page uses the same profile as the rest of the app. On your computer (Start app.bat)
your profile is saved in the app's *profile* folder and
never leaves it. Online, the birth details you type are sent to the server only to calculate the chart and are not
stored there; calculated charts (time and place, no name) are kept in the server's memory for up to an hour so
that pages redraw quickly. Your profile is kept only while the app is open, unless you tick *Remember me on this
device*: then it is kept in this browser on this device, and nowhere else. The notes you write on the *Biography
chart* are kept in exactly the same way (never in a friend card), and *Download my notes* saves them as a file you can keep.

**Plain English.** The summary and the *What does this mean?* window restate these pictures in everyday words.
That wording is the app's own, kept as fixed sentences in the *data* folder (the *plain* columns and
*plain_texts.csv*); no AI chatbot writes it while you use the app.

**Biography chart.** The arrangement of the *Biography chart* tab (years 1–21 down the left, 22–42 round the
bottom, 43–63 up the right, 64–84 down the middle) follows George and Gisela O'Neil's life chart (*The Human
Life*, ed. Florin Lowndes, Mercury Press 1990; the chart © 1990 Florin Lowndes). It is drawn afresh for this app,
and its wording is the app's own (*data/biography_periods.csv*). Steiner's own words for the first three periods –
the world is good (moral), beautiful, true – are from *The Study of Man* (GA 293), lecture 9. The notes you write
there are kept like your profile (see *Your information*).

""")
        st.markdown("**Open questions and the rule the app follows**")
        device.table(L.tables().uncertainty, phone_cols=["question", "rule_the_app_follows"])
        st.markdown("**Sources**")
        device.table(L.tables().sources)
        st.markdown("**Correspondence tables** (editable CSV files in the app's *data* folder)")
        device.table(L.tables().world.reset_index(), phone_cols=["zodiac", "world_view", "meaning_paraphrase"])
        device.table(pd.read_csv(os.path.join(L.DATA, "soul_moods.csv")),
                     phone_cols=["planet", "soul_mood", "meaning_paraphrase"])
        device.table(L.tables().zc.reset_index(),
                     phone_cols=["zodiac", "sense_1921_sketch", "sense_1913_lesson", "eurythmy_consonant"])



main()
