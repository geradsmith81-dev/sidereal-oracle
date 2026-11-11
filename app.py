"""Sidereal Oracle: the real sky read through William Lilly's Christian Astrology (1647) - four pages:
  1. Chart: the chart for one moment, with Lilly's dignities, scores and Forecast.
  2. Auspicious dates: an elections calendar for beginning an undertaking.
  3. Friends: share friend cards, compare two nativities, find times good for both.
  4. About: how the app works and what text informs it.

Run:  streamlit run app.py      (or double-click "Start app.bat")
"""
import ast
import importlib
import os
import re
import sys
import streamlit as st
import matplotlib
matplotlib.use('Agg')

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------- keeping the app's own modules up to date ----------------
# After an update (new files pushed to GitHub), a server that is already running can keep an older copy of a
# module in memory while the pages are new; a page then stops with "AttributeError: module ... has no attribute".
# Each run, every module of this app is checked against its file: if a function or setting written in the file is
# missing from the copy in memory, the module is loaded again from the file.
@st.cache_data(show_spinner=False, max_entries=64)
def _names_in_file(path, mtime):
    tree = ast.parse(open(path, encoding='utf-8').read())
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return sorted(names)


def _refresh_stale_modules():
    for name, mod in list(sys.modules.items()):
        path = getattr(mod, '__file__', None)
        if (name == '__main__' or not path or not path.endswith('.py')
                or os.path.dirname(os.path.abspath(path)) != HERE or not os.path.exists(path)):
            continue
        try:
            if any(not hasattr(mod, n) for n in _names_in_file(path, os.path.getmtime(path))):
                importlib.reload(mod)
        except Exception:
            pass                       # leave it; a clear message is shown below if a page still fails


_refresh_stale_modules()

import user_profile

st.set_page_config(page_title='The Sidereal Oracle', layout='wide',
                   # the app icon (an astrolabe): browser tab, the app window's title bar and taskbar button
                   page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'lilly_icon.png'))
try:
    import sidereal_engine  # noqa: F401  (loads, or on first start downloads, the JPL file)
except Exception as e:          # e.g. first start without internet: de440s.bsp cannot be downloaded
    st.error('The NASA JPL planetary data file (de440s.bsp, about 32 MB) could not be loaded or downloaded. '
             'Check the internet connection and reload the page. Details: ' + str(e))
    st.stop()
import theme
import device

st.markdown(theme.css(os.path.join(HERE, 'assets', 'background.jpg'), phone=device.phone()), unsafe_allow_html=True)
# no wording twice on one page (user request): a fresh register of what has been said, every run
for _m in ('glossary', 'plain_forecast'):
    try:
        getattr(importlib.import_module(_m), 'new_page', lambda: None)()
    except Exception:
        pass
# online: "Remember me on this device" - read the profile kept in this browser (once), save it when it changes
getattr(user_profile, 'device_sync', lambda: None)()
# a friend card opened from a QR code (the link carries ?card=LILLY1:...): offer to add it
getattr(user_profile, 'incoming_card', lambda: None)()
pg = st.navigation([st.Page(os.path.join(HERE, 'chart_page.py'), title='Chart', icon=':material/brightness_7:', default=True),
                    st.Page(os.path.join(HERE, 'elections_page.py'), title='Auspicious dates', icon=':material/calendar_month:'),
                    st.Page(os.path.join(HERE, 'friends_page.py'), title='Friends', icon=':material/group:'),
                    st.Page(os.path.join(HERE, 'about_page.py'), title='About', icon=':material/menu_book:')])
user_profile.sidebar_card()
device.switch()
getattr(device, 'view_switch', lambda: None)()
st.sidebar.caption('Free · no ads, trackers or account · readings from fixed rules of Lilly\'s 1647 book, with '
                   'page references · birth details never stored on a server. More on the About page.')
# credit for the background image (required by its CC BY 4.0 licence), on every page
st.sidebar.caption('Background: Hubble\'s image of the Lagoon Nebula (heic1808a). Credit: NASA, ESA, STScI. '
                   '[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)')
try:
    pg.run()
except ModuleNotFoundError as e:
    # a page needs one of the app's own files that is missing (not uploaded with the rest)
    if not (e.name and os.path.exists(os.path.join(HERE, 'app.py')) and not os.path.exists(os.path.join(HERE, e.name + '.py'))
            and e.name in ('glossary', 'qr_code')):
        raise
    st.error(f"**A file of the app is missing:** `{e.name}.py`. Upload all the files from the newest GitHub zip again "
             f"(including `{e.name}.py`), then click **Manage app** (bottom right) > the three dots > **Reboot app**.")
except AttributeError as e:
    # a page needs something that is not in one of the app's files: that file is older than the page
    m = re.match(r"module '(\w+)' has no attribute '(\w+)'", str(e))
    if not (m and os.path.exists(os.path.join(HERE, m.group(1) + '.py'))):
        raise
    mod, attr = m.group(1), m.group(2)
    st.error(f"**The app's files are out of step.** This page needs `{attr}` from the file `{mod}.py`, but the "
             f"copy of `{mod}.py` in use is from an older version of the app.\n\n"
             f"**Online (GitHub and Streamlit):** upload all the files from the newest GitHub zip again (on GitHub, "
             f"open `{mod}.py` and check that it contains `{attr}`). Then, on the app's page, click **Manage app** "
             f"(bottom right) > the three dots > **Reboot app**.\n\n"
             f"**On your computer:** copy all the files from the newest zip into the app folder, choosing "
             f"**Replace**, and start the app again.")
