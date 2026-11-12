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


# Light-mode proof (user report: in Light mode the text was hard to read). Streamlit draws its own light theme when a
# visitor picks Light in the app menu, or when the phone is in light mode and .streamlit/config.toml is missing (GitHub
# drag-and-drop drops dot-folders). The app paints its panels dark itself, so its text and buttons must be painted light
# itself too. In dark mode these are the colours Streamlit already uses, so nothing changes there.
# Each selector is one unbroken string: a space between ':is(...)' and ':not(...)' would mean "an element inside".
_LP_SCOPE = ('[data-testid="stMain"], [data-testid="stSidebar"], [data-testid="stDialog"], '
             '[data-testid="stPopoverBody"], [data-testid="stBottomBlockContainer"]')
_LP_TEXT = ', '.join(['p', 'li', 'span', 'label', 'small', 'summary', 'b', 'strong', 'em', 'i', 'td', 'th', 'dt', 'dd',
                      '[data-testid="stMarkdownContainer"]', '[data-testid="stWidgetLabel"]',
                      '[data-testid="stMetricLabel"]', '[data-testid="stMetricLabel"] *'])
_LP_NOT = (':not(:is(h1, h2, h3, h4, h5, h6))'
           ':not(:is(h1, h2, h3, h4, h5, h6) *)'
           ':not([data-testid="stBaseButton-primary"] *)'       # the filled button keeps its own (white) text
           ':not(.lilly-badge):not(.lilly-badge *)'               # grade labels keep their own colours
           ':not(.lilly-table *)'                                 # phone tables: black on parchment
           ':not([data-testid="stMarkdownContainer"] [style*="color"])'     # text the app colours itself
           ':not([data-testid="stMarkdownContainer"] [style*="color"] *)'
           ':not(a):not(a *)'                                     # links keep their colour
           ':not(code):not(code *)'
           ':not([data-testid="stMetricValue"] *)'
           ':not([data-testid="stCaptionContainer"]):not([data-testid="stCaptionContainer"] *)')
LIGHT_PROOF_TEXT_SELECTOR = f'body :is({_LP_SCOPE}) :is({_LP_TEXT}){_LP_NOT}'
_LP_BUTTONS = ', '.join([f'button[data-testid="{t}"]' for t in (
    'stBaseButton-secondary', 'stBaseButton-secondaryFormSubmit', 'stBaseButton-segmented_control',
    'stBaseButton-pills', 'stPopoverButton')]
    # the options of st.segmented_control / st.pills carry kind="..." rather than a data-testid (Streamlit 1.67)
    + ['button[kind="segmented_control"]', 'button[kind="pills"]']
    # Streamlit 1.67 draws them as toggle buttons with data-variant="..." (user report: white boxes in light mode)
    + ['button[data-variant="segmented_control"]', 'button[data-variant="pills"]',
       '[data-testid="stButtonGroup"] button'])
_LP_ACTIVE = ', '.join([f'button[data-testid="{t}"]' for t in ('stBaseButton-segmented_controlActive',
                                                               'stBaseButton-pillsActive')]
                       + ['button[kind="segmented_controlActive"]', 'button[kind="pillsActive"]']
                       # 1.67: the chosen option carries data-selected
                       + ['button[data-variant="segmented_control"][data-selected]',
                          'button[data-variant="pills"][data-selected]',
                          '[data-testid="stButtonGroup"] button[data-selected]',
                          '[data-testid="stButtonGroup"] button[aria-checked="true"]',
                          '[data-testid="stButtonGroup"] button[aria-pressed="true"]'])
# Streamlit's own pop-ups, drawn outside the page (user report: white boxes with white text in light mode). They are
# painted dark too, so that the phone layout's white text, or the light text above, can be read on them.
_LP_OVERLAYS = ', '.join(['.stTooltipContent', '.stTooltipErrorContent']
                         + [f'[data-testid="{t}"]' for t in (
    'stMainMenuPopover', 'stTooltipContent', 'stTooltipErrorContent', 'stToast', 'stDateInputQuickSelectPopover',
    'stDateInputHeaderPickerPopover', 'stDateTimeInputPopoverTime', 'stColorPickerPopover', 'stJsonPathTooltipBody',
    'stDataFrameTooltipContent', 'stDataFrameColumnMenu', 'stDataFrameColumnFormattingMenu',
    'stDataFrameColumnVisibilityMenu', 'stDataFrameStatisticsMenu', 'stDataFrameButtonActionMenu',
    'stTopNavPopoverBody', 'stMenuButtonBody', 'stClearCacheDialog')])


def light_proof_css(p, phone=False):
    txt = '#ffffff' if phone else p['starlight']
    caption = (f'    body :is({_LP_SCOPE}) [data-testid="stCaptionContainer"] :is(p, span, li, b, strong, em, small)'
               f':not([style*="color"]):not([data-testid="stCaptionContainer"] [style*="color"] *):not(a):not(.lilly-badge) {{ color: {p["dust"]} !important; }}\n'
               if not phone else '')
    return (
        '/* light-mode proof: light text and dark buttons whatever theme Streamlit is drawing */\n'
        f'    {LIGHT_PROOF_TEXT_SELECTOR} {{ color: {txt} !important; }}\n'
        + caption +
        f'    :is({_LP_BUTTONS}) {{ background-color: {p["void"]} !important; color: {txt} !important;\n'
        f'        border: 1px solid {p["orbit"]} !important; }}\n'
        f'    :is({_LP_BUTTONS}) :is(p, span, div) {{ color: {txt} !important; }}\n'
        f'    :is({_LP_BUTTONS}):hover {{ border-color: {p["brass"]} !important; }}\n'
        f'    :is({_LP_ACTIVE}) {{ background-color: {rgba(p["primary"], 0.35)} !important; color: #ffffff !important;\n'
        f'        border: 1px solid {p["primary"]} !important; }}\n'
        f'    :is({_LP_ACTIVE}) :is(p, span, div) {{ color: #ffffff !important; }}\n'
        f'    [data-testid="stSidebar"] {{ background-color: {p["panel"]} !important; }}\n'
        f'    [data-testid="stSidebarNav"] a:is(:hover, [aria-current="page"]) {{ background-color: {rgba(p["orbit"], 0.45)} !important; }}\n'
        f'    [data-testid="stSidebarNav"] a :is(span, p) {{ color: {txt} !important; }}\n'
        f'    [data-testid="stDialog"] [role="dialog"], [data-testid="stPopoverBody"] {{\n'
        f'        background-color: {p["panel"]} !important; color: {txt} !important; border: 1px solid {p["orbit"]}; }}\n'
        f'    [data-testid="stDialog"] [role="dialog"] button[aria-label="Close"] {{ color: {txt} !important; }}\n'
        f'    [data-testid="stExpander"] details, [data-testid="stExpander"] summary {{ border-color: {p["orbit"]} !important; }}\n'
        # folding-box headers and the file-upload box: Streamlit paints them white in light mode (user report)
        f'    [data-testid="stExpander"] summary {{ background-color: {p["panel"]} !important; color: {txt} !important; }}\n'
        f'    [data-testid="stExpander"] summary:hover {{ background-color: {rgba(p["orbit"], 0.45)} !important; }}\n'
        f'    [data-testid="stExpander"] summary :is(p, span, div, svg) {{ color: {txt} !important; }}\n'
        f'    [data-testid="stExpander"] details {{ background-color: transparent !important; }}\n'
        f'    [data-testid="stFileUploaderDropzone"] {{ background-color: {p["panel"]} !important;\n'
        f'        border: 1px dashed {p["orbit"]} !important; color: {txt} !important; }}\n'
        f'    [data-testid="stFileUploaderDropzoneInstructions"] :is(span, small, div, p) {{ color: {p["dust"]} !important; }}\n'
        f'    [data-testid="stFileUploader"] :is(svg, small) {{ color: {p["dust"]} !important; }}\n'
        f'    [data-testid="stHeader"] :is(button, a, span, svg) {{ color: {txt} !important; }}\n'
        f'    [data-testid="stTooltipIcon"] svg, [data-testid="stWidgetLabel"] svg {{ color: {p["dust"]} !important; }}\n'
        f'    [data-testid="stCheckbox"] [role="checkbox"], [data-testid="stCheckbox"] span:has(> input) {{\n'
        f'        border-color: {p["dust"]} !important; }}\n'
        f'    :is({_LP_OVERLAYS}), div:has(> :is(.stTooltipContent, .stTooltipErrorContent)) {{\n'
        f'        background-color: {p["panel"]} !important; color: {txt} !important; border-color: {p["orbit"]} !important; }}\n'
        f'    :is({_LP_OVERLAYS}) :is(p, span, li, label, small, b, strong, em, div, button, td, th) {{ color: {txt} !important; }}\n'
        f'    :is({_LP_OVERLAYS}) a {{ color: {p["ion"]} !important; }}\n'
        f'    :is({_LP_OVERLAYS}) :is(button, [role^="menuitem"], [role="option"], li) {{ background-color: transparent !important; }}\n'
        f'    :is({_LP_OVERLAYS}) :is(button, [role^="menuitem"], [role="option"], li):is(:hover, :focus-visible) {{\n'
        f'        background-color: {rgba(p["orbit"], 0.45)} !important; }}\n'
        f'    :is({_LP_OVERLAYS}) :is([aria-checked="true"], [aria-selected="true"], [aria-pressed="true"]) {{\n'
        f'        background-color: {rgba(p["orbit"], 0.7)} !important; }}\n'
        f'    :is({_LP_OVERLAYS}) hr, [data-testid="stMainMenuDivider"] {{ border-color: {p["orbit"]} !important;\n'
        f'        background-color: {p["orbit"]} !important; }}\n'
        # notice boxes (st.info / success / warning / error): Streamlit paints them pale in light mode, where the
        # app's light text vanished (user report). Always a dark tinted panel with light text; dark mode looks the same.
        f'    [data-testid="stAlertContainer"], [data-testid="stAlert"] > div {{ background-color: #16283a !important;\n'
        f'        border: 1px solid {p["orbit"]} !important; color: {txt} !important; }}\n'
        f'    [data-testid="stAlertContainer"] :is(p, span, li, b, strong, em, div, small) {{ color: {txt} !important; }}\n'
        f'    [data-testid="stAlertContainer"] a {{ color: {p["ion"]} !important; }}\n'
        # code boxes (st.code, e.g. the friend card's text code) and inline `code`: Streamlit paints their background
        # near-white (#F7F7F6) in light mode while the text stays light (user report: pale text on white). Always the
        # app's dark code colours, the same as .streamlit/config.toml gives in dark mode.
        f'    body [data-testid="stCode"] pre {{ background-color: {p["band_a"]} !important;\n'
        f'        border: 1px solid {p["orbit"]} !important; color: {p["brass_pale"]} !important; }}\n'
        f'    body [data-testid="stCode"] pre :is(div, code) {{ background-color: transparent !important; }}\n'
        f'    body [data-testid="stCode"] pre :is(div, code, span) {{ color: {p["brass_pale"]} !important;\n'
        f'        -webkit-text-fill-color: {p["brass_pale"]} !important; }}\n'
        f'    body [data-testid="stCode"] button {{ background-color: {p["panel"]} !important; color: {txt} !important;\n'
        f'        border: 1px solid {p["orbit"]} !important; }}\n'
        f'    body [data-testid="stCode"] button svg {{ color: {txt} !important; fill: currentColor; }}\n'
        f'    body [data-testid="stMarkdownContainer"] code:not(pre code) {{ background-color: {p["band_a"]} !important;\n'
        f'        color: {p["brass_pale"]} !important; -webkit-text-fill-color: {p["brass_pale"]} !important; }}\n')


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
    /* Input boxes, dropdown lists and calendars always dark with light text, even when a phone in light mode makes
       Streamlit draw them white (user report: white text on white boxes). In dark mode these are the same colours. */
    [data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"], [data-testid="stNumberInputContainer"],
    [data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"], [data-testid="stDateInputField"],
    [data-testid="stSelectbox"] div:has(> input), [data-testid="stTimeInput"] div:has(> input),
    [data-testid="stMultiSelect"] div:has(> input),
    [data-testid="stSelectbox"] [role="combobox"], [data-testid="stTimeInput"] [role="combobox"] {{
        background-color: {p['panel']} !important; color: {p['starlight']} !important; }}
    [data-testid="stApp"] input, [data-testid="stApp"] textarea, .stApp input, .stApp textarea {{
        background-color: transparent !important; color: {p['starlight']} !important;
        -webkit-text-fill-color: {p['starlight']} !important; caret-color: {p['starlight']} !important; }}
    .stApp input::placeholder, .stApp textarea::placeholder {{ color: {p['dust']}b3 !important;
        -webkit-text-fill-color: {p['dust']}b3 !important; }}
    [data-testid="stSelectboxVirtualDropdown"], [data-testid="stSelectboxVirtualDropdown"] *,
    [data-testid="stMultiSelectDropdown"], [data-testid="stMultiSelectDropdown"] *, [role="listbox"], [role="listbox"] *,
    [data-testid="stDateInputCalendar"], [data-testid="stDateTimeInputCalendar"] {{
        background-color: {p['panel']} !important; color: {p['starlight']} !important; }}
    [role="listbox"] [role="option"]:hover, [role="listbox"] [role="option"][aria-selected="true"],
    [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
    [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {{
        background-color: {p['band_b']} !important; }}
    /* Tablets and phones (touch screens): room at the bottom of the page, the sidebar and the windows, so the last
       lines can be scrolled up clear of the browser's toolbars, the keyboard and Streamlit's buttons (user report);
       a box being typed in is kept well above the bottom edge. Computers with a mouse are unchanged. */
    @media (pointer: coarse) {{
        [data-testid="stMainBlockContainer"], .block-container {{
            padding-bottom: calc(10rem + env(safe-area-inset-bottom)) !important; }}
        [data-testid="stSidebarUserContent"] {{ padding-bottom: calc(9rem + env(safe-area-inset-bottom)) !important; }}
        [data-testid="stDialog"] [role="dialog"] {{ margin-bottom: calc(8rem + env(safe-area-inset-bottom)) !important; }}
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stSidebarContent"],
        [data-testid="stDialog"] {{ scroll-padding-bottom: 40vh; }}
    }}
    /* "What does this mean?": the main button of the Forecast box (user request) */
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
    {light_proof_css(p, phone)}
    {phone_css}
    .lilly-badge {{ padding: 0.08rem 0.5rem; border-radius: 0.6rem; font-weight: 600; white-space: nowrap;
        border: 1px solid {p['orbit']}; margin-right: 0.25rem; }}
    </style>"""
