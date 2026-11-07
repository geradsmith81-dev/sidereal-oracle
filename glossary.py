"""Tap-to-explain: short definitions of the terms the app uses, each with the page of Lilly's Christian Astrology
(1647) it comes from and a link to that page of the scanned book (Wellcome Library copy, Internet Archive b30338724).

Page references are the ones the app's data tables already cite. In the scan, printed page N is image N + 35
(checked at pp.57-115), which the Internet Archive viewer numbers n(N + 34).
"""
import inspect
import re

import streamlit as st

SCAN = 'https://archive.org/details/b30338724'
BOOK = "Lilly, *Christian Astrology* (1647)"

# key: (title, plain definition, [pages] or None for an app rule)
TERMS = {
    'ascendant': ('Rising sign (Ascendant)',
                  'The constellation coming up over the eastern horizon at this moment. It begins the 1st house, which '
                  'Lilly says "hath signification of the life of man": it stands for you, or for whoever asks.', [50]),
    'lord_asc': ('Lord of the Ascendant',
                 'The planet that rules the rising sign. It stands for you in the chart: its strength and its place '
                 'describe your part in the matter.', None),
    'hours': ('Planetary day and hour',
              'Each day and each of its 24 unequal hours (12 from sunrise to sunset, 12 from sunset to sunrise) '
              'belongs to one of the seven planets, in a fixed order. The planet of the day rules its first hour.', [61, 65]),
    'radical': ('Radical',
                "Lilly's first test of whether a chart is fit to be judged: the planet of the hour and the Lord of the "
                'Ascendant must agree (be the same planet, share a triplicity, or share a nature).', [121]),
    'considerations': ('Considerations before judgment',
                       "Lilly's list of signs that a chart may not be safe to judge at all: for example the rising sign "
                       'in its first or last degrees, the Moon void of course or on the Via Combusta, or Saturn in the '
                       '1st or 7th house. They are cautions about the reading, not predictions of misfortune.', [121]),
    'fortitudes': ('Fortitudes and debilities',
                   "Lilly's table of points for (fortitudes) and against (debilities) each planet. The net score is "
                   'one minus the other: "subtract the lesser number from the greater, and so judge".', [115, 181]),
    'essential': ('Essential dignity',
                  "A planet's strength from where it stands among the signs: in its own house +5, exaltation +4, "
                  'triplicity +3, terms +2, face +1. The app reads each IAU constellation as the sign of that name, '
                  'rescaled to 30 degrees.', [104, 115]),
    'detriment': ('Detriment', 'A planet in the sign opposite its own house: ill at ease and weakened (-5).', [104, 115]),
    'fall': ('Fall', 'A planet in the sign opposite its exaltation (-4).', [104, 115]),
    'peregrine': ('Peregrine', 'A "wandering" planet, with no essential dignity at all in its degree (-5).', [112, 115]),
    'reception': ('Reception',
                  'Two planets each standing in a sign (or exaltation) of the other: mutual reception, which Lilly '
                  'reads as cooperation between the two.', [112]),
    'angles': ('Angular, succedent and cadent houses',
               'The four angles (1st, 10th, 7th, 4th) are the strongest places in the chart; the succedent houses '
               '(11th, 5th, 2nd, 8th) come next; the cadent ones (9th, 3rd, 12th, 6th) are the weakest. Lilly scores '
               'each house in his table.', [115]),
    'houses': ('Houses',
               'Twelve divisions of the sky, each standing for a part of life: the 7th for partners and love, the 11th '
               'for friends and hopes, the 4th for home and endings, the 10th for work and reputation. The app uses '
               "Regiomontanus houses, as Lilly did.", [50]),
    'five_degree': ('Five-degree rule',
                    'A planet within five degrees before the next house cusp is counted in that next house.', [33]),
    'retrograde': ('Retrograde and direct',
                   'Seen from Earth, a planet sometimes appears to move backwards against the stars (retrograde, -5); '
                   'moving forwards it is direct (+4).', [115]),
    'speed': ('Swift and slow', 'A planet moving faster than its average daily motion is swift (+2); slower, it is '
                                'slow (-2).', [115]),
    'oriental': ('Oriental and occidental',
                 'Rising before the Sun (oriental) or setting after it (occidental). Lilly counts oriental as good for '
                 'Saturn, Jupiter and Mars, and occidental as good for Venus, Mercury and the Moon.', [115]),
    'moon_light': ('Moon increasing or decreasing in light',
                   'From New to Full Moon she is increasing in light (+2); from Full to New, decreasing (-2).', [115]),
    'combust': ('Combust and free from combustion',
                'A planet within 8°30\' of the Sun is combust, lost in its glare and badly weakened (-5). Well clear '
                'of the Sun it is "free from combustion" (+5).', [113, 115]),
    'cazimi': ('Cazimi', 'Within 17 arc-minutes of the Sun\'s centre: "in the heart of the Sun", and strengthened '
                         'instead (+5).', [113, 115]),
    'beams': ('Under the Sun-beams',
              "Within 17° of the Sun but not combust (-4 in Lilly's table; his own worked example does not count it).",
              [113, 115]),
    'aspects': ('Aspects',
                'Set angles between two planets. Sextile (60°) and trine (120°) are friendly; square (90°) and '
                'opposition (180°) are hard (Lilly: "imperfect" and "perfect" enmity); a conjunction (0°) is a meeting.',
                [106]),
    'orbs': ('Orbs and moieties',
             'Each planet has an orb, a reach of influence. Two planets are in aspect when they are within half the '
             'sum of their orbs (their "moieties").', [107]),
    'partile': ('Partile', 'An aspect exact to the degree. Partile contacts with Jupiter or Venus count for a planet; '
                           'with Saturn or Mars, against it.', [115]),
    'applying': ('Applying and separating',
                 'Applying: the faster planet is moving towards the exact aspect. Separating: moving away from it. '
                 'Lilly judges what is to come by applying aspects.', [124]),
    'perfection': ('Perfection and translation of light',
                   'How a matter "comes about" in Lilly: by an applying aspect between the two planets concerned, or '
                   'by a third planet (often the Moon) carrying the light from one to the other.', [124]),
    'void': ('Void of course',
             'The Moon makes no further aspect before she leaves the sign she is in (here: the constellation band). '
             'Lilly says matters then go on with difficulty.', [112]),
    'via_combusta': ('Via Combusta', 'The "burnt road", the second half of Libra and the first half of Scorpio, '
                                     'which Lilly thought unsafe for the Moon.', [121]),
    'fortune': ('Part of Fortune', 'A calculated point (Ascendant + Moon - Sun) standing for wealth and well-being.',
                [143]),
    'fortunes': ('Fortunes and infortunes', 'Jupiter and Venus are the fortunes (helpful); Saturn and Mars the '
                                            'infortunes (difficult).', [106]),
    'stars': ('Regulus, Spica and Algol', 'A planet with the royal star Regulus (+6) or with Spica (+5) is '
                                          'strengthened; with Algol (-5), weakened.', [115]),
    'besieged': ('Besieged', 'A planet between Saturn and Mars (-5).', [115]),
    'nodes': ("Dragon's Head and Tail", "The Moon's nodes: exactly with the North Node (Dragon's Head) +4; with the "
                                        "South Node (Dragon's Tail) -4.", [115]),
    'sidereal': ('Sidereal sky and the IAU constellations',
                 'This app places the planets against the real constellations as the International Astronomical Union '
                 'draws them: 13 on the ecliptic, of unequal widths, rather than twelve equal signs. Each is rescaled to '
                 "30 degrees so that Lilly's tables can be applied (an app rule).", None),
}

# names used inside the dignity tables -> the term that explains them
_ITEM = {'house': 'essential', 'exaltation': 'essential', 'triplicity': 'essential', 'term': 'essential',
         'face': 'essential', 'detriment': 'detriment', 'fall': 'fall', 'peregrine': 'peregrine',
         'reception_house': 'reception', 'reception_exalt': 'reception', 'retrograde': 'retrograde',
         'direct': 'retrograde', 'swift': 'speed', 'slow': 'speed', 'combust': 'combust', 'free_combustion': 'combust',
         'cazimi': 'cazimi', 'under_beams': 'beams', 'besieged': 'besieged', 'moon_increasing': 'moon_light',
         'moon_decreasing': 'moon_light', 'conj_regulus': 'stars', 'conj_spica': 'stars', 'conj_algol': 'stars',
         'partile_conj_north_node': 'nodes', 'partile_conj_south_node': 'nodes'}


def item_term(k):
    if k in _ITEM:
        return _ITEM[k]
    if k.startswith('house_'):
        return 'angles'
    if 'oriental' in k or 'occidental' in k:
        return 'oriental'
    if k.startswith('partile'):
        return 'partile'
    return None


def scan_url(page):
    return f'{SCAN}/page/n{int(page) + 34}/mode/1up'


def page_links(pages):
    return ', '.join(f'[p.{p}]({scan_url(p)})' for p in pages)


def cite_links(source):
    """'Lilly pp.121-123; p.112' -> the same text with each page linked to the scan."""
    s = str(source or '')
    return re.sub(r'\b(pp?\.)\s?(\d{1,3})((?:\s?[-–]\s?\d{1,3})?)',
                  lambda m: f'[{m.group(1)}{m.group(2)}{m.group(3)}]({scan_url(m.group(2))})', s)


def explain_md(key):
    title, text, pages = TERMS[key]
    cite = (f'{BOOK}, ' + page_links(pages) + ' (opens the page of the 1647 book)') if pages else 'An app rule.'
    return f'**{title}**  \n{text}  \n\n<small>{cite}</small>'


_POP_KEY = 'key' in inspect.signature(st.popover).parameters


def chips(keys, where):
    """A row of small buttons; each opens a short explanation of one term. where: a unique prefix for this row."""
    keys = [k for k in dict.fromkeys(keys) if k in TERMS]
    if not keys:
        return
    try:
        row = st.container(horizontal=True, gap='small')
    except TypeError:                     # an older Streamlit: one under another
        row = st.container()
    with row:
        for k in keys:
            kw = dict(key=f'gl_{where}_{k}') if _POP_KEY else {}
            with st.popover(TERMS[k][0], icon=':material/info:', **kw):
                st.markdown(explain_md(k), unsafe_allow_html=True)


def full_list():
    """Every term, for the About page."""
    for k, (title, text, pages) in sorted(TERMS.items(), key=lambda kv: kv[1][0].lower()):
        cite = page_links(pages) if pages else 'app rule'
        st.markdown(f'**{title}**: {text} <small>({cite})</small>', unsafe_allow_html=True)
