"""Colour theme "Lagoon": built from the Hubble Space Telescope's image of the Lagoon Nebula, which is also the
page background (assets/background.jpg; portrait crop for phones in assets/background_phone.jpg).
Image: "Hubble's 28th birthday picture: The Lagoon Nebula" (heic1808a), credit NASA, ESA, STScI,
Creative Commons Attribution 4.0 (https://esahubble.org/images/heic1808a/). The credit is shown on every page.

The colours were taken from the image (k-means clusters and its most vivid hues): deep slate-blue shadows, the
teal-cyan glow at its core, the rust and flame-orange clouds, a violet-magenta haze and peach highlights.
Text contrast is at least 4.5:1 everywhere, checked over the brightest pixel of the image behind a panel
(25 % dark wash over the image, panels 78 % opaque).

Palette roles (the key names are kept from the first theme so that the rest of the code is unchanged):
  void        #0b111c  page base, wheel face
  panel       #111927  panels and cards
  band_a/b    #172134 / #21304a  alternating constellation bands on the wheel
  orbit       #4f6789  rings, house lines, borders (decoration only, not text)
  starlight   #f7f1ea  body text
  dust        #c4ccdb  secondary text, captions
  brass       #f2994a  flame orange accent (not used for text): planets above the horizon, 'Best', the icon
  brass_pale  #ffcd9c  peach: headings - the only coloured text besides links (other text is white)
  primary     #b5461a  rust: Streamlit's button and slider colour (white button text 5.4:1)
  ion         #6fd0dc  teal: sextile / trine aspect lines, links
  ember       #ec6a4c  red-orange: square / opposition aspect lines
  nebula      #45b3bf  teal-cyan: 'Good' on the elections calendar
  rose        #f094c8  magenta: off-zodiac flag (a body outside the 13 ecliptic constellations)
"""
import base64, os

PALETTE = {'void': '#0b111c', 'panel': '#111927', 'band_a': '#172134', 'band_b': '#21304a', 'orbit': '#4f6789',
           'starlight': '#f7f1ea', 'dust': '#c4ccdb', 'brass': '#f2994a', 'brass_pale': '#ffcd9c', 'primary': '#b5461a',
           'ion': '#6fd0dc', 'ember': '#ec6a4c', 'nebula': '#45b3bf', 'rose': '#f094c8'}
# phone tables: black text on a warm parchment
PARCHMENT = {'cell': '#f6eee4', 'head': '#ead9c6', 'rule': '#d6c2ab'}
OVERLAY_TOP, OVERLAY_MID, OVERLAY_BOTTOM, PANEL_ALPHA = 0.25, 0.50, 0.85, 0.78


def rgba(hex_colour, alpha):
    h = hex_colour.lstrip('#')
    return f'rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})'


WHEEL_THEME = dict(
    fig_bg='none', face=PALETTE['void'], face_alpha=0.85, band_a=PALETTE['band_a'], band_b=PALETTE['band_b'],
    band_edge=PALETTE['void'], band_text=PALETTE['starlight'], ring=PALETTE['orbit'], ink=PALETTE['starlight'],
    grey=PALETTE['dust'], up=PALETTE['brass'], down_face=PALETTE['void'], accent=PALETTE['rose'],
    label_bg=PALETTE['void'], harmony=PALETTE['ion'], tension=PALETTE['ember'], house_line=PALETTE['orbit'],
    harmony_name='teal', tension_name='red-orange', accent_name='Magenta')

# Phone layout: all text except headings is pure white (user request), on the wheel and calendar too.
WHITE = '#ffffff'
WHEEL_THEME_PHONE = dict(WHEEL_THEME, ink=WHITE, grey=WHITE, band_text=WHITE, spoke=PALETTE['dust'], accent_what='circle',
                         glyph_open=WHITE)   # symbol of a planet below the horizon: white inside its coloured ring

# Elections calendar: lightness rises from Avoid to Best, so the order also reads in greyscale.
GRADE_COLOURS = {'avoid': '#1a2232', 'fair': '#3a5276', 'good': PALETTE['nebula'], 'best': PALETTE['brass']}


# Phone layout: all text except headings is white (user request). Built as one selector without line breaks inside
# it: in CSS a space or line break between ":is(...)" and ":not(...)" would mean "an element inside", not "and".
_WHITE_TARGETS = ', '.join([
    'p', 'li', 'span', 'label', 'small', 'summary', 'a', 'code', 'blockquote', 'td', 'th', 'b', 'strong', 'em',
    '[data-testid="stMarkdownContainer"]', '[data-testid="stMarkdownContainer"] *',
    '[data-testid="stCaptionContainer"]', '[data-testid="stCaptionContainer"] *',
    '[data-testid="stMetricValue"]', '[data-testid="stMetricValue"] *', '[data-testid="stMetricLabel"] *',
    '[data-testid="stSidebarNav"] *', '[data-baseweb="select"] *', '[role="option"]', '[role="option"] *',
    '[data-testid="stExpander"] summary *', '[data-testid="stAlert"] *'])
_NOT_WHITE = (':not(.lilly-badge)'                                    # grade labels keep their own colours
              ':not(:is(h1, h2, h3, h4, h5, h6))'                     # headings keep gold
              ':not(:is(h1, h2, h3, h4, h5, h6) *)'
              ':not([data-testid="stBaseButton-primary"] *)'          # the filled button keeps its own (white) text
              ':not(.lilly-table *)')                                 # tables: black on parchment (below)
WHITE_SELECTOR = f'body :is({_WHITE_TARGETS}){_NOT_WHITE}'
PHONE_TEXT_CSS = (
    '/* phone layout: all text white except headings, grade labels and the filled button */\n'
    f'    {WHITE_SELECTOR} {{ color: #ffffff !important; }}\n'
    '    body input, body textarea { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }\n'
    '    body a:not(button *) { text-decoration: underline; }\n'
    '    body .lilly-badge[data-g="avoid"], body .lilly-badge[data-g="fair"] { color: #ffffff !important; }\n'
    '    body :is(h4, h5, h6) { color: BRASS_PALE !important; }\n'
    '    /* phone tables (device.html_table): black text on parchment, headings included */\n'
    '    .lilly-table-wrap { overflow-x: auto; margin: 0.25rem 0 0.9rem; border-radius: 8px; border: 1px solid ORBIT; }\n'
    '    .lilly-table { border-collapse: collapse; width: 100%; margin: 0; font-size: 0.9rem; line-height: 1.35; }\n'
    '    .lilly-table th, .lilly-table td { color: #000000 !important; text-align: left; vertical-align: top;\n'
    '        padding: 0.32rem 0.5rem; border: none; border-bottom: 1px solid P_RULE; }\n'
    '    .lilly-table th { background: P_HEAD !important; font-weight: 700; white-space: nowrap; }\n'
    '    .lilly-table td { background: P_CELL !important; min-width: 3.5rem; }\n'
    '    .lilly-table a { color: #000000 !important; text-decoration: underline; }\n')


def css(bg_path='assets/background.jpg', phone=False):
    """phone=True: use the smaller portrait copy of the background (assets/background_phone.jpg) if present,
    and make all text except headings white."""
    p = PALETTE
    phone_css = (PHONE_TEXT_CSS.replace('BRASS_PALE', p['brass_pale']).replace('ORBIT', p['orbit'])
                 .replace('P_RULE', PARCHMENT['rule']).replace('P_HEAD', PARCHMENT['head']).replace('P_CELL', PARCHMENT['cell'])
                 if phone else '')
    bg = ''
    if phone:
        small = os.path.join(os.path.dirname(bg_path), 'background_phone.jpg')
        bg_path = small if os.path.exists(small) else bg_path
    if os.path.exists(bg_path):
        b64 = base64.b64encode(open(bg_path, 'rb').read()).decode()
        bg = (f"background-image: linear-gradient(180deg, {rgba(p['void'], OVERLAY_TOP)} 0%, {rgba(p['void'], OVERLAY_MID)} 55%, "
              f"{rgba(p['void'], OVERLAY_BOTTOM)} 100%), url('data:image/jpeg;base64,{b64}');"
              "background-size: cover; background-position: center center; background-attachment: fixed;")
    return f"""<style>
    .stApp {{ {bg} }}
    [data-testid="stHeader"] {{ background: transparent; }}
    :root {{ color-scheme: dark; }}          /* the browser's own controls (date picker, scrollbars) drawn dark */
    /* "What does this mean? (plain English)": the main button of the Forecast box (user request) */
    .st-key-plain_btn button {{ min-height: 3.4rem; font-size: 1.12rem; font-weight: 600; letter-spacing: 0.01em;
        box-shadow: 0 0 0 1px {p['brass']}99, 0 0 22px {rgba(p['brass'], 0.45)}; }}
    .st-key-plain_btn button:hover {{ box-shadow: 0 0 0 2px {p['brass']}, 0 0 28px {rgba(p['brass'], 0.6)}; }}
    [data-testid="stSidebar"] > div:first-child {{ background: {rgba(p['panel'], 0.86)}; backdrop-filter: blur(6px);
        border-right: 1px solid {p['orbit']}66; }}
    .block-container {{ background: {rgba(p['panel'], PANEL_ALPHA)}; border-radius: 16px; padding: 2rem 2.2rem 2.5rem;
        margin-top: 1.2rem; backdrop-filter: blur(5px); border: 1px solid {p['orbit']}55; }}
    h1, h2, h3 {{ font-family: Georgia, 'Palatino Linotype', 'Book Antiqua', serif !important;
        color: {p['brass_pale']} !important; letter-spacing: 0.01em; }}
    h1 {{ text-shadow: 0 0 18px {p['brass']}44; }}
    [data-testid="stMetricValue"] {{ color: #ffffff; font-family: Georgia, serif; }}
    [data-testid="stCaptionContainer"], .stCaption {{ color: {p['dust']} !important; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {p['orbit']} !important;
        background: {rgba(p['band_a'], 0.55)}; }}
    blockquote {{ border-left: 3px solid {p['brass']}99 !important; }}
    code {{ color: #ffffff; background: {rgba(p['brass'], 0.12)}; }}
    a {{ color: {p['ion']}; }}
    /* only headings are coloured (user request): Streamlit draws some text in its accent colour - the value
       above a slider handle, the selected or hovered tab, and buttons while hovered or pressed - make it white.
       The filled primary button keeps its own (white) text. */
    [data-testid="stSliderThumbValue"], [data-testid="stSliderThumbValue"] *,
    [data-testid="stTab"], [data-testid="stTab"] * {{ color: #ffffff !important; }}
    button:is(:hover, :active, :focus, :focus-visible):not([data-testid="stBaseButton-primary"]),
    button:is(:hover, :active, :focus, :focus-visible):not([data-testid="stBaseButton-primary"]) * {{ color: #ffffff !important; }}
    [data-testid="stExpander"] summary:hover, [data-testid="stExpander"] summary:hover * {{ color: #ffffff !important; }}
    /* touch screens (phones, tablets): iPhones and iPads ignore a fixed background, so let it scroll */
    @media (hover: none) and (pointer: coarse) {{
        .stApp {{ background-attachment: scroll; }}
    }}
    /* narrow screens (phones held upright): tighter panel, smaller headings */
    @media (max-width: 640px) {{
        .block-container {{ padding: 1.1rem 0.85rem 1.6rem; margin-top: 0.4rem; border-radius: 12px; }}
        h1 {{ font-size: 1.55rem !important; line-height: 1.25 !important; }}
        h2 {{ font-size: 1.3rem !important; }}
        h3 {{ font-size: 1.15rem !important; }}
        h4 {{ font-size: 1.05rem !important; }}
        [data-testid="stMetricValue"] {{ font-size: 1.45rem; }}
        .lilly-day {{ font-size: 1.02rem; }}
    }}
    .lilly-day {{ padding: 0.32rem 0; border-bottom: 1px solid {p['orbit']}44; line-height: 1.9; }}
    .lilly-day b {{ color: #ffffff; margin-right: 0.4rem; }}
    {phone_css}
    .lilly-badge {{ padding: 0.08rem 0.5rem; border-radius: 0.6rem; font-weight: 600; white-space: nowrap;
        border: 1px solid {p['orbit']}; margin-right: 0.25rem; }}
    </style>"""
