"""Phone layout: one switch that the pages consult to fit a small, upright screen.

The switch starts ON when the browser says it is a phone (its "User-Agent" text contains Mobile, iPhone,
iPod or Android) and OFF otherwise. It sits in the sidebar ("Phone layout"), so it can be changed by hand.
With it on:
  * the input boxes move from the sidebar (hidden on a phone) into a fold-out panel at the top of the page;
  * the calendars come first as a day-by-day list in large text, and the coloured grid is drawn at phone size;
  * the chart wheel is drawn with larger symbols and its key is written underneath;
  * tables show their most important columns only, in black text on a parchment background;
  * the starfield background is a smaller portrait copy.
Desktop screens are unchanged.
"""
import html

import streamlit as st

KEY = 'phone_layout'
PHONE_WORDS = ('mobi', 'iphone', 'ipod', 'android')


def detected():
    """True when the browser identifies itself as a phone (or an Android tablet)."""
    try:
        ua = (st.context.headers.get('User-Agent') or '').lower()
    except Exception:            # no browser (tests) or an old Streamlit
        ua = ''
    return any(w in ua for w in PHONE_WORDS)


def phone():
    if KEY not in st.session_state:
        st.session_state[KEY] = detected()
    return bool(st.session_state[KEY])


def switch():
    """The sidebar switch. Call once per run, from app.py, before the page runs."""
    phone()
    st.sidebar.toggle('Phone layout', key=KEY,
                      help='Fits the pages to a phone screen: inputs in a panel at the top of the page, calendars as '
                           'lists, larger chart symbols and shorter tables. It switches on by itself on phones.')


VIEW = 'view_full'


def full_view():
    """Simple view (False): the chart, the sky at this moment and the forecast in plain words.
    Full view (True): also Lilly's tables, the planets in his words, the aspects and the sources.
    Starts in Simple view on a phone and in Full view on a computer."""
    if VIEW not in st.session_state:
        st.session_state[VIEW] = not phone()
    return bool(st.session_state[VIEW])


def view_switch():
    """The sidebar switch for Simple / Full view. Call once per run, from app.py."""
    full_view()
    st.sidebar.toggle("Full view (all of Lilly's tables)", key=VIEW,
                      help="Off: Simple view - the chart, the sky at this moment and the forecast in plain words. "
                           "On: also Lilly's tables of points, the planets in his words, the aspects and the sources.")


def input_panel(label, expanded=False):
    """Where a page puts its inputs: the sidebar on a computer, a fold-out panel on a phone."""
    if phone():
        return st.expander(label, expanded=expanded, icon=':material/tune:')
    return st.sidebar


def where_inputs():
    """Words for the instructions: where the inputs are."""
    return 'in the panel above' if phone() else 'in the sidebar'


def _cell(v):
    """How a cell is written in the phone table (numbers as short as the computer table shows them)."""
    if v is None or (isinstance(v, float) and v != v):
        return ''
    if isinstance(v, float):
        return f'{v:g}'
    return str(v)


def _short_link(url):
    """'https://archive.org/details/b30338724' -> 'archive.org'"""
    host = url.split('//', 1)[-1].split('/', 1)[0]
    return host[4:] if host.startswith('www.') else host


def html_table(df):
    """The phone table: black text on parchment, headings included, every cell in full (long text wraps).
    Web addresses become links. Returns HTML for st.markdown(..., unsafe_allow_html=True)."""
    head = ''.join(f'<th>{html.escape("Link" if c == "url" else str(c))}</th>' for c in df.columns)
    rows = []
    for rec in df.itertuples(index=False):
        cells = []
        for v in rec:
            t = _cell(v)
            if t.startswith(('http://', 'https://')):
                cells.append(f'<td><a href="{html.escape(t, quote=True)}" target="_blank">{html.escape(_short_link(t))}</a></td>')
            else:
                cells.append(f'<td>{html.escape(t)}</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    return (f"<div class='lilly-table-wrap'><table class='lilly-table'><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def table(df, phone_cols=None, **kw):
    """A table. On a computer: Streamlit's interactive table (sortable, scrollable).
    On a phone: only the listed columns (all if phone_cols is None), drawn as a plain table in black text on a
    parchment background (user request), so that the column headings can be black too."""
    if phone():
        if phone_cols:
            df = df[[c for c in phone_cols if c in df.columns]]
        st.markdown(html_table(df), unsafe_allow_html=True)
        return
    st.dataframe(df, hide_index=True, width='stretch', **kw)
