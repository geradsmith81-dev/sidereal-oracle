# Sidereal Oracle · William Lilly's reading

A sidereal star chart on the real IAU constellations (13 ecliptic bands at their true widths, NASA JPL DE440s
positions via Skyfield), read through William Lilly's *Christian Astrology* (London, 1647): essential dignities
(p.104), the table of fortitudes and debilities (p.115), Regiomontanus houses, planetary day and hour, Lilly's
orbs (p.107) and his "Considerations before Judgment" (pp.121-123). Every table is a CSV in `data/` with page
citations; adaptations to the unequal IAU bands are listed in `data/uncertainty_log.csv`.

## Look

Colour scheme "Lagoon" (`theme.py`), taken from the background image: Hubble's 28th-anniversary picture of the Lagoon Nebula (heic1808a), credit NASA, ESA, STScI, [CC BY 4.0](https://esahubble.org/images/heic1808a/). The credit is shown in the sidebar on every page
generated in code (`assets/background.jpg`). Text contrast is at least 4.5:1 throughout.

## Two pages

* **Chart**: the chart for one moment, with Lilly's dignities, scores, aspects and Forecast. The button *What does
  this mean? (plain English)* opens a window that restates the Forecast without technical terms and grades the moment
  for the four undertakings of the Auspicious dates page, against every hour of the same week.
* **Auspicious dates**: an elections calendar for Romance (7th house, Venus: a new romance, or good times to connect
  with a partner), Friendship (11th, Jupiter: new connections, or good times with friends), a life transition (4th, the
  Moon) or a project (10th, Mercury). It is framed from Lilly's
  perfection (ch. XXI), strength (p.115) and Considerations before Judgment (pp.121-123). Rules and weights are in
  `data/election_rules.csv`. It exports .ics and .csv.

## Friends

A third page lets two people compare charts without accounts. Each exports a **friend card** (a small `.lillycard`
JSON file, or a `LILLY1:` text code) and sends it person to person. The page compares the two nativities
(Ptolemy, *Tetrabiblos* IV.7: Sun, Moon, Ascendant and Part of Fortune) and finds election times good for both, where
the joint score is the lower of the two personal scores. Rules and weights are in `data/natal_rules.csv`. Imported cards
are validated, and pictures are re-encoded.

## Profile

A profile box in the sidebar takes a name, a picture and birth details, and a home town, and personalises the page titles ("Gerad's auspicious dates"; the home page is "The Sidereal Oracle"). The home town is the starting place of the Chart and Auspicious dates pages; without it, the most populous gazetteer place in the browser's time zone (`st.context.timezone`) is used, and the page says so. The home town is never written into friend cards. The Chart page opens at the present moment in the local time of the home town (else the browser's time zone, else London); its **Now** button resets the date and time to the present in the chosen place's time zone.
In this online version the profile is kept **only in the visitor's browser session**, unless the visitor ticks
**Remember me on this device**: then the profile and friends are also kept in that browser's `localStorage` (pictures as
small JPEGs), via a small `st.components.v2` component, and filled in again on the next visit. **Forget me on this
device** deletes the stored copy. Nothing is written to the server, which all visitors share. The desktop version (started with `Start app.bat`, which sets `LILLY_LOCAL_PROFILE=1`)
saves it in a local `profile/` folder instead.

## Phones and tablets

The app detects phones from the browser's User-Agent and switches to a phone layout (`device.py`): inputs in a
fold-out panel at the top of each page instead of the sidebar, calendars as a day-by-day list followed by a
phone-sized grid, a compact chart wheel, shorter tables (black text on parchment), all other text except headings in white, and a smaller
portrait background
(`assets/background_phone.jpg`). The sidebar switch **Phone layout** overrides the detection. Desktop rendering is
unchanged.

## Simple and Full views, explanations, the sky, QR codes

- **Simple / Full view** (sidebar switch, Chart page): Simple shows the chart, *The sky at this moment* and the forecast
  in plain words; Full adds Lilly's tables of points, the planets in his words, the aspects and the sources. It starts in
  Simple view on a phone and Full view on a computer.
- **Tap-to-explain**: small buttons marked with an "i" open a short definition of a term (`glossary.py`), with the page
  of *Christian Astrology* linked to the scan on the Internet Archive (printed page N = viewer page n(N+34)).
  The About page lists every term.
- **The sky at this moment**: the Moon's phase and light (Lilly's +2/-2), the planets retrograde, the Moon's next
  aspect or *void of course*, and when she leaves her constellation (`forecast.sky`).
- **Show the working**: in the plain-English window, every statement shows Lilly's rule, its page and how it counted;
  every undertaking shows its points and the week's thresholds.
- **Friend card QR code** (Friends page): `qr_code.py`, a dependency-free QR encoder (byte mode, level M), checked
  module-for-module against an independent encoder. The code opens `APP_URL?card=LILLY1:...` (`user_profile.APP_URL`);
  the app then offers to add the friend.
- **Tone**: the plain-English texts (column `plain` of the rule tables) are worded as cautions rather than verdicts;
  Lilly's own words are kept in the `text` column.

## About page

A fourth page explains the app in plain English. It shows Lilly's engraved portrait and the 1647 title page if
`assets/lilly_portrait.jpg` and `assets/lilly_title_page.jpg` are present (from the public-domain Wellcome copy,
archive.org item b30338724). If they are absent, it shows a link to the scan.

## Put it online (no programming)

See **DEPLOY GUIDE.txt** for step-by-step instructions. In short:

1. On github.com create a new repository and choose **Add file → Upload files**.
2. Drag the *contents* of this folder (not the folder itself) into the page, so that `app.py` sits at the top level.
   Make sure the `.streamlit`, `assets`, `data` and `ephem` folders come along.
3. On share.streamlit.io: **Create app → Yup, I have an app**, choose the repository, branch `main`,
   main file `app.py`, and under *Advanced settings* pick **Python 3.12**. Deploy.
4. The first start takes about a minute longer: the app downloads the NASA JPL file `de440s.bsp` (32 MB).

## Credits
Lilly's text: Wellcome Library copy of the 1647 edition (Internet Archive item b30338724, public domain).
Planetary data: NASA JPL DE440s via Skyfield. Places: GeoNames (CC BY 4.0). Time zones: IANA tz database.

This reading is traditional symbolism for study and reflection; controlled studies have not found
astrological charts to be predictive.
