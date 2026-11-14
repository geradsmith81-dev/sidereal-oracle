"""Page 4: About - how the app works and what text informs it, in plain English."""
import os
import pandas as pd
import streamlit as st

import user_profile
import device
import glossary

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'assets')
SCAN = 'https://archive.org/details/b30338724'

user_profile.title('About this app', 'About {who} app')
st.markdown("**Sidereal Oracle** draws an accurate map of the sky for any moment and place, and reads it the way the English "
            "astrologer **William Lilly** taught in his book ***Christian Astrology*** (London, 1647). This page explains, "
            "in plain words, where every part comes from and what the app adds of its own.")
# the app's promise (from what users of other astrology apps praise and complain about)
st.success("**Free, with no ads, no trackers and no account.** Every reading comes from fixed rules taken from Lilly's 1647 book, each with its page: no AI chatbot writes them, and everyone gets the same reading for the same moment. Your birth details are used only to calculate charts. They are never stored on a server or shared, and are kept on your device only if you tick *Remember me on this device*.", icon=':material/verified_user:')

# ---------------------------------------------------------------- Lilly and his book
st.subheader('William Lilly and his book')
pics = [(f, cap) for f, cap in (('lilly_portrait.jpg', 'William Lilly, engraved portrait from Christian Astrology (1647).'),
                                ('lilly_title_page.jpg', 'Title page of Christian Astrology, London, 1647.'))
        if os.path.exists(os.path.join(ASSETS, f))]
if pics:
    cols = st.columns(len(pics))
    for c, (f, cap) in zip(cols, pics):
        c.image(os.path.join(ASSETS, f), caption=cap + ' Wellcome Collection copy, public domain.', width='stretch')
else:
    with st.container(border=True):
        st.markdown(f"The engraved portrait of Lilly and the title page of the 1647 edition can be seen in the "
                    f"[Wellcome Collection copy on the Internet Archive]({SCAN}) (public domain).")
st.markdown("""
**William Lilly** (1602–1681) was born at Diseworth in Leicestershire, came to London as a young man, and took up
astrology in the 1630s. He became the best-known astrologer in England during the Civil War, publishing a yearly
almanac and many predictions. In 1666, after the Great Fire of London, he was called before a committee of Parliament
because an image in one of his earlier pamphlets seemed to foretell a great fire; he was not blamed.

***Christian Astrology*** (1647) was one of the first full textbooks of astrology written in English rather than Latin, and it is still the best known. It has
three parts:
1. **An Introduction**: the planets, the signs, the twelve houses, and the tables for judging how strong each planet is.
2. **Questions (horary astrology)**: how to answer a question from the chart of the moment it is asked, with Lilly's
   own worked examples.
3. **Nativities**: how to read a birth chart.

The copy used for this app is the **first edition of 1647** held by the Wellcome Library, scanned by the Internet
Archive and marked public domain. Every table in the app was transcribed from Lilly's own pages, and each rule names
the page it comes from.
""")

# ---------------------------------------------------------------- the sky
st.subheader('Step 1 · The real sky')
st.markdown("""
- **Where the planets are.** Positions come from NASA's Jet Propulsion Laboratory (the *DE440* planetary data, the same
  data used to fly spacecraft), calculated with the *Skyfield* program to international (IAU) standards. They are
  worked out for your exact place on Earth. Checked against NASA's own online service, they agree to better than half
  an arcsecond, far finer than the eye can see.
- **Which constellation.** The sky is divided by the official constellation borders agreed by astronomers in 1930.
  Along the path of the Sun there are **thirteen** constellations, not twelve: Ophiuchus, the Serpent-bearer, lies
  between Scorpius and Sagittarius. They are also **unequal**: Virgo is about 44° wide, Scorpius only about 7°.
- **Why this differs from a newspaper horoscope.** Most horoscopes use twelve equal "signs" counted from the spring
  equinox. Because the Earth's axis slowly wobbles, those signs have drifted about a whole sign away from the
  constellations they are named after. This app uses the constellations themselves (a *sidereal* sky).
- **Houses.** The sky is divided into twelve houses by the method Lilly used, called *Regiomontanus*.
""")

# ---------------------------------------------------------------- fitting Lilly to the real sky
st.subheader('Step 2 · Fitting Lilly to the real sky')
st.markdown("""
Lilly worked with twelve equal signs. To read the real constellations with his rules, the app makes three adaptations,
and labels them **app rule** wherever they are used:
- A planet in the constellation Leo is read as being in Lilly's sign of Leo, and so on for each zodiac constellation.
- Some of Lilly's rules depend on degrees within a sign (the "terms" and "faces"). These are stretched in proportion
  to each constellation's real width.
- Ophiuchus has no sign in Lilly's system, so a planet there has no dignity of its own (Lilly calls this "peregrine").
""")

# ---------------------------------------------------------------- the pages
st.subheader('Step 3 · What each page does')
st.markdown("""
**Chart.** The chart wheel for one moment. Each planet gets a score from Lilly's *Table of Fortitudes and Debilities*
(p.115). It gains points for strengths, such as being in its own sign or near the horizon, and loses points for
weaknesses, such as moving backwards or being too close to the Sun. Lilly then subtracts the smaller total from the
larger "and so judge". The **Forecast** box uses Lilly's own *Considerations before Judgment* (pp.121–123), and each
planet is described in Lilly's words, "when well dignified" or "when ill dignified". The button **What does this mean?
(plain English)** opens a window that says the same things without the technical terms. It also judges that moment for
the four undertakings of the Auspicious dates page and compares it with every hour of the same week.

**Auspicious dates.** Searches a stretch of days for good moments to begin something: a romance, a friendship, a life
change or a project. Lilly wrote no separate book on choosing times, but said a student of his book could "frame his
owne Figure of Elections". So the page uses his rules for when a matter is "brought to perfection" (pp.124–126), the
strength of the planets involved, and his cautions, such as a "void of course" Moon. With your birth details it also
checks how each moment suits *your* birth chart.

**Astrosophy Birth Chart.** A second way of reading a birth chart, from the Astrosophy Birth Chart app: the real
sky among the 13 IAU zodiac constellations (Ophiuchus included), read through Rudolf Steiner's indications and the
*astrosophy* of Elisabeth Vreede and Willi Sucher. Its tabs give the birth chart (with a plain-English summary), the
prenatal epoch after Sucher's Hermetic Rule, the life rhythms in seven-year periods, a Biography chart for your own notes
year by year, today's sky, and the sources. Each reading carries a tag saying whose idea it is: Steiner's, Vreede's or
Sucher's, or a rule of the app. It uses your profile's birth details and the same NASA JPL file as the other pages.

**Friends.** You and a friend exchange *friend cards* (small files you send each other yourselves). The page compares
your two birth charts by the rule of the ancient astronomer **Ptolemy**, which Lilly draws on. It looks at the Sun,
Moon, Ascendant and Part of Fortune in both charts. It then finds times good for both of you: a moment counts only as
well as it does for whichever of you it suits less.

**On a phone.** The app switches to a *phone layout* by itself: the date, time and place boxes are in a fold-out
panel at the top of the page, calendars come first as a day-by-day list, the chart wheel has larger symbols, and
tables show their main columns in black on a light parchment background, and all other text except the headings is white. The switch **Phone layout** in the sidebar turns it on or off by hand.
""")

# ---------------------------------------------------------------- checks and honesty
st.subheader('How the app was checked')
st.markdown("""
- **Positions:** compared with NASA JPL's Horizons service at dates from 1900 to 2149: agreement to better than
  0.4 arcseconds, and every constellation the same.
- **Lilly's own example:** Lilly scores every planet in a chart he cast on 16 July 1634 (*If the Querent shall be Rich
  or Poore*, pp.177–180). Recomputed with NASA's data, the app finds the same planetary day and hour he printed and the
  same Part of Fortune. For five of the seven planets it gets exactly his strength totals. For the other two, Lilly left
  out a point that his own table calls for.
- **What is Lilly and what is not:** every reading carries a tag. **Lilly** means it comes from his text, with the
  page. **App rule** means the app had to make a choice. Examples are the stretched degrees, the point weights on the
  calendar pages, and the orbs used to compare two charts. The full list is under *Sources and certainty* on each page.
- **Still to be checked:** the page references for the friends comparison (Ptolemy, *Tetrabiblos* IV.7, and the place
  where Lilly uses it in Book III) are marked "citation to be checked" until they have been verified against the texts.
""")
st.info("**A plain word about astrology.** This app shows how a 17th-century astrologer would read the sky. It is offered "
        "for study, history and reflection. Controlled scientific studies have not found that astrological charts or "
        "chosen times predict personality or events, so please don't base important decisions on it.")

# ---------------------------------------------------------------- your data
st.subheader('Your information')
st.markdown("Your name, picture, birth details and friends are " +
            ("saved only on this computer, in the app's **profile** folder, and none of it is sent anywhere."
             if user_profile.LOCAL else
             "kept only while the app is open, unless you tick **Remember me on this device** in your profile: "
             "then they are also kept in this browser's own storage on your phone or computer, and nowhere else. "
             "**Forget me on this device** (in the sidebar) deletes that copy. Nothing is saved on the server.") +
            " A friend card holds your name, birth details and (if you choose) picture: send it only to people you want "
            "to have them. **Use my location** (in your profile) asks your phone or computer for its position only when "
            "you press it, or once by itself while no home place is set; the position, rounded to about 10 m, is kept "
            "in your profile only and never goes into a friend card. To fill in the elevation, the app sends only the "
            "coordinates of the place (never your name or birth details) to the open elevation data on Amazon's "
            "servers (AWS Terrain Tiles) and, over water or when those cannot be reached, to the free Open-Meteo "
            "elevation service.")

# ---------------------------------------------------------------- glossary
st.subheader('Words used in the app')
st.markdown("Short explanations of Lilly's terms. Each page number opens that page of the 1647 book (the Wellcome "
            "Library copy on the Internet Archive). The same explanations open from the small buttons marked "
            "\u24d8 on the Chart page.")
with st.expander('Show all the words', icon=':material/menu_book:'):
    glossary.full_list()

# ---------------------------------------------------------------- credits
st.subheader('Sources and credits')
src = pd.read_csv(os.path.join(HERE, 'data', 'sources.csv'), encoding='utf-8')
device.table(src, column_config={'url': st.column_config.LinkColumn('Link')})
st.caption("Lilly's text: Wellcome Collection copy of the 1647 edition, Internet Archive item b30338724, public domain. "
           "Planet data: NASA JPL DE440s via Skyfield. Places: GeoNames (CC BY 4.0). Elevation: Terrain Tiles on the AWS Registry of Open Data (Mapzen/Tilezen: SRTM, USGS 3DEP/NED, GMTED2010, ETOPO1 and national models), checked with the Open-Meteo Elevation API (CC BY 4.0), from the Copernicus "
           "DEM GLO-90 (© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under "
           "COPERNICUS by the European Union and ESA). Time zones: IANA tz database. "
           "Background: Hubble's image of the Lagoon Nebula (heic1808a), credit NASA, ESA, STScI, CC BY 4.0; "
           "the colours of the app were taken from it.")
