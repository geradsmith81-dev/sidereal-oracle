"""The user's profile (name, picture, birth details) and their friends' cards.

Where it is kept
  * Desktop app (started with "Start app.bat", which sets LILLY_LOCAL_PROFILE=1): in the folder profile/ inside the
    app (profile.json, avatar.png, friends.json), so it is there next time. It never leaves the computer.
  * Online (Streamlit Community Cloud) or any other start: for the current browser session only, unless the visitor
    ticks "Remember me on this device". Then the profile and friends are also kept in that browser's own storage
    (localStorage, on the visitor's phone or computer) and filled in again next time. Nothing is ever written to the
    server's disk, which every visitor shares. "Forget me on this device" deletes the stored copy.

Friend cards
  A friend card is a small JSON file (.lillycard) or a copy-paste text code ("LILLY1:..."), holding a name, the birth
  details and, if the sender chooses, the picture. It is sent person to person (e-mail, message); the app has no
  accounts and no server. Imported cards are validated and the picture is re-encoded before use.
"""
import base64
import calendar
import hashlib
import datetime as dt
import html
import io
import json
import os
import re
import urllib.parse
import uuid
import zlib

import streamlit as st
from PIL import Image, ImageOps

import places

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, 'profile')
LOCAL = os.environ.get('LILLY_LOCAL_PROFILE') == '1'
MAX_NAME = 40
MAX_UPLOAD_MB = 15
MAX_CARD_KB = 1024
AVATAR_PX = 256
KEY, FKEY = 'profile', 'friends'
CARD_FORMAT = 'lilly-friend-card'
CODE_PREFIX = 'LILLY1:'
# the online app: a friend card's QR code opens this address with ?card=LILLY1:... (also from the desktop app,
# so that a friend's phone can open it). Change it here if the app moves.
APP_URL = 'https://sidereal-lilly-chart-8aevvdj4xjfdczxjz7swbt.streamlit.app/'


# ---------------------------------------------------------------- storage
def _read_json(name, default):
    try:
        with open(os.path.join(DIR, name), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(name, obj):
    os.makedirs(DIR, exist_ok=True)
    tmp = os.path.join(DIR, name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(DIR, name))


def _read_disk():
    d = _read_json('profile.json', {})
    av = None
    p = os.path.join(DIR, 'avatar.png')
    if os.path.exists(p):
        with open(p, 'rb') as f:
            av = f.read()
    return dict(name=d.get('name', ''), avatar=av, birth=_valid_birth(d.get('birth')), home=_valid_home(d.get('home')),
                life=_valid_life(_read_json('life_chart.json', {})))


def _write_disk(prof):
    _write_json('profile.json', {'name': prof['name'], 'birth': prof.get('birth'), 'home': prof.get('home')})
    p = os.path.join(DIR, 'avatar.png')
    if prof['avatar']:
        with open(p + '.tmp', 'wb') as f:
            f.write(prof['avatar'])
        os.replace(p + '.tmp', p)
    elif os.path.exists(p):
        os.remove(p)


def get():
    """The current profile: dict(name=str, avatar=PNG bytes or None, birth=dict or None)."""
    if KEY not in st.session_state:
        st.session_state[KEY] = _read_disk() if LOCAL else dict(name='', avatar=None, birth=None)
    st.session_state[KEY].setdefault('birth', None)
    st.session_state[KEY].setdefault('home', None)
    st.session_state[KEY].setdefault('life', {})
    return st.session_state[KEY]


def save(name, avatar, birth, home=None):
    old = get()
    old_home = old.get('home')
    prof = dict(name=clean_name(name), avatar=avatar, birth=_valid_birth(birth), home=_valid_home(home),
                life=old.get('life') or {})          # the Biography chart's notes (Astrosophy page) are kept as they are
    st.session_state[KEY] = prof
    if prof['home'] != old_home:
        _reset_place_search()
    if prof['birth'] and prof['birth'] != old.get('birth'):
        st.session_state['chart_for'] = MINE          # a new or changed birth: the Astrosophy page shows the user's chart
    if LOCAL:
        _write_disk(prof)


def _reset_place_search():
    """Start the place search of every page again from the (new) home place."""
    for k in ['_place_q', 'b_q', 'b_pick'] + [f'{pre}_{w}' for pre in ('c', 'e', 'f') for w in ('q', 'pick', 'elev', 'elev_for', 'elev_src', 'elev_found')]:
        st.session_state.pop(k, None)


def friends():
    if FKEY not in st.session_state:
        raw = _read_json('friends.json', []) if LOCAL else []
        st.session_state[FKEY] = [f for f in (_friend_from_store(x) for x in raw) if f]
    return st.session_state[FKEY]


def _store_friends():
    if LOCAL:
        _write_json('friends.json', [dict(id=f['id'], name=f['name'], birth=f['birth'],
                                          avatar=base64.b64encode(f['avatar']).decode() if f['avatar'] else None)
                                     for f in friends()])


def _friend_from_store(x):
    try:
        av = base64.b64decode(x['avatar']) if x.get('avatar') else None
        b = _valid_birth(x.get('birth'))
        return dict(id=str(x['id']), name=clean_name(x['name']), birth=b, avatar=av) if b else None
    except Exception:
        return None


def add_friend(f):
    """f: dict from parse_card. Replaces an earlier card of the same person (same name and birth)."""
    lst = [x for x in friends() if not (x['name'] == f['name'] and x['birth'] == f['birth'])]
    lst.append(dict(f, id=uuid.uuid4().hex[:12]))
    st.session_state[FKEY] = lst
    _store_friends()


def remove_friend(fid):
    st.session_state[FKEY] = [x for x in friends() if x['id'] != fid]
    _store_friends()


# ---------------------------------------------------------------- the Astrosophy Birth Chart page (astrosophy_page.py)
# "Whose chart?" on that page, and the notes of its Biography chart: {'1'..'84': {aspect key: text}}. The notes are
# kept like the rest of the profile: on the computer in the profile folder (life_chart.json); online only while the
# app is open, unless "Remember me on this device" is ticked. They never go into a friend card.
MINE, OTHER = 'My birth chart', 'Another birth or moment'
LIFE_ASPECTS = (('destiny', 'Destiny & health'), ('interests', 'Interests & studies'), ('people', 'People & family'),
                ('places', 'Places & work'))
MAX_NOTE = 600


def has_birth():
    return bool(get().get('birth'))


def _valid_life(d):
    """Biography-chart notes: {'1'..'84': {aspect key: text}}, empty boxes and years left out."""
    out = {}
    if not isinstance(d, dict):
        return out
    keys = [k for k, _ in LIFE_ASPECTS]
    for y, boxes in list(d.items())[:200]:
        try:
            year = int(y)
        except (TypeError, ValueError):
            continue
        if not (1 <= year <= 84) or not isinstance(boxes, dict):
            continue
        clean = {}
        for k in keys:
            t = boxes.get(k)
            if t is None or (isinstance(t, float) and t != t):
                continue
            t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(t)).strip()[:MAX_NOTE]
            if t:
                clean[k] = t
        if clean:
            out[str(year)] = clean
    return out


def life_notes():
    return get().get('life') or {}


def save_life(notes):
    """Replace all the Biography chart's notes (on the computer: profile/life_chart.json)."""
    get()['life'] = _valid_life(notes)
    if LOCAL:
        _write_json('life_chart.json', get()['life'])


def save_life_year(year, boxes):
    notes = dict(life_notes())
    notes[str(int(year))] = boxes
    save_life(notes)


def life_storage_text():
    if LOCAL:
        return 'Your notes are saved on this computer, in the app\'s "profile" folder, and never leave it.'
    if remembered():
        return 'Your notes are kept in this browser on this device (Remember me is on), and nowhere else.'
    return ('Online, your notes are kept only while the app is open. To keep them, tick "Remember me on this device" '
            'in your profile, or use "Download my notes" and load the file again next time.')


# ---------------------------------------------------------------- "Remember me on this device" (online only)
# The browser's own storage (localStorage) on the visitor's phone or computer holds one JSON text: the profile and the
# friends, pictures as small JPEGs. A tiny component (st.components.v2: JavaScript running in the visitor's browser)
# reads it once per session and writes it whenever the profile or the friends change. The server keeps nothing.
DEVICE_FORMAT = 'sidereal-oracle-device'
DEVICE_MAX_CHARS = 4_000_000          # browsers allow about 5 MB per site
REMEMBER = '_dev_remember'            # True: keep this browser's stored copy up to date
_STORE_JS = """
export default function (component) {
  const { data, setStateValue } = component;
  const KEY = "sidereal-oracle-profile-v1";
  const g = (window.__siderealOracleStore = window.__siderealOracleStore || {});
  const d = data || {};
  let ls = null;
  try { ls = window.localStorage; ls.setItem("__so_test", "1"); ls.removeItem("__so_test"); } catch (e) { ls = null; }
  if (d.op === "load") {
    if (g.loadedFor === d.sid) { return; }
    g.loadedFor = d.sid;
    let v = null;
    try { v = ls ? ls.getItem(KEY) : null; } catch (e) { v = null; }
    setStateValue("stored", JSON.stringify({ sid: d.sid, ok: !!ls, value: v }));
  } else if (d.op === "save" || d.op === "forget") {
    let ok = true;
    if (g.lastNonce !== d.nonce) {
      try { if (d.op === "save") { ls.setItem(KEY, d.payload); } else { ls.removeItem(KEY); } }
      catch (e) { ok = false; }
      g.lastNonce = d.nonce;
      g.lastOk = ok;
    } else {
      ok = g.lastOk;
    }
    setStateValue("saved", JSON.stringify({ nonce: d.nonce, ok: ok }));
  }
}
"""
_store = None
try:
    if not LOCAL:
        _store = st.components.v2.component('sidereal_oracle_device_store', js=_STORE_JS, isolate_styles=False)
except Exception:                     # an older Streamlit without st.components.v2: the feature is simply not offered
    _store = None

_jpeg_cache = {}


def _jpeg_b64(png):
    """Profile picture (PNG bytes) -> small JPEG as base64 text, for the browser's storage."""
    if not png:
        return None
    h = hashlib.sha1(png).hexdigest()
    if h not in _jpeg_cache:
        im = Image.open(io.BytesIO(png)).convert('RGB')
        out = io.BytesIO()
        im.save(out, format='JPEG', quality=85, optimize=True)
        if len(_jpeg_cache) > 200:
            _jpeg_cache.clear()
        _jpeg_cache[h] = base64.b64encode(out.getvalue()).decode()
    return _jpeg_cache[h]


def _picture_from_store(b64):
    try:
        return to_avatar(base64.b64decode(b64)) if b64 else None
    except Exception:
        return None                   # a damaged picture is dropped; the rest is still used


def device_payload():
    """The text kept in the browser: profile (with the home place) and friends."""
    p = get()
    return json.dumps({'format': DEVICE_FORMAT, 'version': 1,
                       'profile': {'name': p['name'], 'birth': p['birth'], 'home': p.get('home'),
                                   'life': p.get('life') or {},
                                   'picture_jpeg_base64': _jpeg_b64(p['avatar'])},
                       'friends': [{'id': f['id'], 'name': f['name'], 'birth': f['birth'],
                                    'picture_jpeg_base64': _jpeg_b64(f['avatar'])} for f in friends()]},
                      ensure_ascii=False, separators=(',', ':'))


def parse_device(text):
    """Text from the browser's storage -> (profile dict, friends list), or None if it is not usable."""
    try:
        if not text or len(text) > DEVICE_MAX_CHARS:
            return None
        d = json.loads(text)
        if not isinstance(d, dict) or d.get('format') != DEVICE_FORMAT:
            return None
        p = d.get('profile') or {}
        prof = dict(name=clean_name(p.get('name')), avatar=_picture_from_store(p.get('picture_jpeg_base64')),
                    birth=_valid_birth(p.get('birth')), home=_valid_home(p.get('home')),
                    life=_valid_life(p.get('life')))
        fl = []
        for x in (d.get('friends') or [])[:200]:
            try:
                b, n = _valid_birth(x.get('birth')), clean_name(x.get('name'))
                if b and n:
                    fid = re.sub(r'[^0-9a-zA-Z]', '', str(x.get('id') or ''))[:24] or uuid.uuid4().hex[:12]
                    fl.append(dict(id=fid, name=n, birth=b, avatar=_picture_from_store(x.get('picture_jpeg_base64'))))
            except Exception:
                continue
        return prof, fl
    except Exception:
        return None


def device_available():
    """True when "Remember me on this device" can be offered (online, and the browser allows storage)."""
    ss = st.session_state
    return _store is not None and bool(ss.get('_dev_loaded')) and bool(ss.get('_dev_ok'))


def remembered():
    return bool(st.session_state.get(REMEMBER))


def set_remember(on):
    """Tick or untick "Remember me on this device". Unticking deletes the browser's stored copy."""
    ss = st.session_state
    if on and not ss.get(REMEMBER):
        ss[REMEMBER] = True
        ss.pop('_dev_sent', None)                        # write the current profile at the next run
    elif not on and ss.get(REMEMBER):
        ss[REMEMBER] = False
        ss['_dev_forget'] = uuid.uuid4().hex[:12]        # delete the stored copy at the next run


def _apply_loaded(prof, fl):
    ss = st.session_state
    cur = get()
    # friends added before the stored copy arrived (e.g. from a scanned QR code) are kept, added to the stored ones
    extra = [f for f in friends() if not any(f['name'] == g['name'] and f['birth'] == g['birth'] for g in fl)]
    ss[FKEY] = fl + extra
    if cur['name'] or cur['avatar'] or cur['birth']:
        return                                           # the visitor already typed a profile: keep that
    ss[KEY] = prof
    if prof.get('birth'):
        ss['chart_for'] = MINE
    if prof.get('home'):
        _reset_place_search()
        if ss.get('c_now_tz') != prof['home'].get('tz'):
            ss.pop('c_time', None)                       # the Chart page opens again at "now" in the home time zone


def device_sync():
    """Run once at the top of every run (online only): read the browser's stored copy once per session, and write
    it again whenever the profile or friends have changed. Mounted inside a hidden container."""
    if _store is None:
        return
    ss = st.session_state
    sid = ss.setdefault('_dev_sid', uuid.uuid4().hex)
    if not ss.get('_dev_loaded'):
        cmd = {'op': 'load', 'sid': sid}
    elif ss.get('_dev_forget'):
        cmd = {'op': 'forget', 'nonce': ss['_dev_forget']}
    elif ss.get(REMEMBER):
        text = device_payload()
        nonce = hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]
        cmd = {'op': 'idle'} if ss.get('_dev_sent') == nonce else {'op': 'save', 'nonce': nonce, 'payload': text}
    else:
        cmd = {'op': 'idle'}
    with st.container(key='sidereal_device_box'):
        st.markdown('<style>.st-key-sidereal_device_box{display:none !important;}</style>', unsafe_allow_html=True)
        try:
            res = _store(key='sidereal_device_store', data=cmd,
                         on_stored_change=lambda: None, on_saved_change=lambda: None)
        except Exception:
            return
    try:
        stored = json.loads(res.get('stored') or 'null') if hasattr(res, 'get') else json.loads(getattr(res, 'stored', None) or 'null')
        saved = json.loads(res.get('saved') or 'null') if hasattr(res, 'get') else json.loads(getattr(res, 'saved', None) or 'null')
    except Exception:
        stored = saved = None
    if not ss.get('_dev_loaded') and isinstance(stored, dict) and stored.get('sid') == sid:
        ss['_dev_loaded'] = True
        ss['_dev_ok'] = bool(stored.get('ok'))
        got = parse_device(stored.get('value'))
        if got:
            ss[REMEMBER] = True
            _apply_loaded(*got)
            ss['_dev_sent'] = hashlib.sha1(device_payload().encode('utf-8')).hexdigest()[:16]
    if isinstance(saved, dict) and saved.get('nonce') == cmd.get('nonce'):
        if cmd['op'] == 'forget':
            ss.pop('_dev_forget', None)
            ss.pop('_dev_sent', None)
        else:
            ss['_dev_sent'] = cmd['nonce']
            ss['_dev_save_failed'] = not saved.get('ok', True)


# ---------------------------------------------------------------- validation and helpers
def clean_name(name):
    """Trim, collapse spaces, drop control characters, at most MAX_NAME characters."""
    name = re.sub(r'[\x00-\x1f\x7f]', '', str(name or ''))
    return re.sub(r'\s+', ' ', name).strip()[:MAX_NAME]


def _valid_birth(b):
    """Return a clean birth dict, or None. Fields: date YYYY-MM-DD, time HH:MM, time_known, place, lat, lon,
    tz (IANA name or None), utc_offset (hours, of the local clock at birth)."""
    if not isinstance(b, dict):
        return None
    try:
        d = dt.date.fromisoformat(str(b['date']))
        t = dt.time.fromisoformat(str(b.get('time') or '12:00'))
        lat, lon, off = float(b['lat']), float(b['lon']), float(b['utc_offset'])
        if not (1850 <= d.year <= 2149 and -90 <= lat <= 90 and -180 <= lon <= 180 and -14 <= off <= 14):
            return None
        tz = b.get('tz')
        tz = str(tz)[:64] if tz else None
        return dict(date=d.isoformat(), time=t.strftime('%H:%M'), time_known=bool(b.get('time_known', True)),
                    place=clean_name(b.get('place', ''))[:MAX_NAME] or f'{lat:.2f}, {lon:.2f}',
                    lat=round(lat, 5), lon=round(lon, 5), tz=tz, utc_offset=off)
    except (KeyError, ValueError, TypeError):
        return None


def _valid_home(h):
    """The place where the user lives (the starting place on the Chart and Auspicious dates pages), or None.
    Fields: name, country, lat, lon, tz, elev (ground, m), src ('town' from the search, 'gps' from the device's
    position). It is kept in the profile only - never in a friend card."""
    if not isinstance(h, dict):
        return None
    try:
        lat, lon = float(h['lat']), float(h['lon'])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        # ground height in metres above sea level (looked up or typed in). None = not known: it is looked up again.
        # Values below places.ELEV_MIN are the -500 m that a bug put into the box (user report), not real heights.
        elev = h.get('elev')
        elev = None if elev is None or float(elev) < places.ELEV_MIN - 1 else \
            round(min(max(float(elev), places.ELEV_MIN), places.ELEV_MAX))
        return dict(name=clean_name(h['name'])[:MAX_NAME], country=clean_name(h.get('country', ''))[:MAX_NAME],
                    lat=round(lat, 5), lon=round(lon, 5), tz=str(h['tz'])[:64] if h.get('tz') else None, elev=elev,
                    src='gps' if h.get('src') == 'gps' else 'town')
    except (KeyError, ValueError, TypeError):
        return None


def birth_utc(b):
    """UTC datetime of a birth dict (noon local if the time is unknown)."""
    local = dt.datetime.combine(dt.date.fromisoformat(b['date']), dt.time.fromisoformat(b['time']))
    return (local - dt.timedelta(hours=b['utc_offset'])).replace(tzinfo=dt.timezone.utc)


def birth_text(b):
    if not b:
        return 'no birth details'
    d = dt.date.fromisoformat(b['date'])
    t = b['time'] if b['time_known'] else 'time unknown'
    return f"born {d:%d %b %Y}, {t}, {b['place']}"


def _md_escape(s):
    """Stop Markdown from formatting a name such as *Star* or [link]."""
    return re.sub(r'([\\`*_{}\[\]<>()#+!|~])', r'\\\1', s)


def possessive(name):
    return f"{name}'" if name.lower().endswith('s') else f"{name}'s"


def personal(base, name_form):
    """base: the title without a name. name_form: the same title with {who} where the possessive goes."""
    n = get()['name']
    return name_form.format(who=possessive(n)) if n else base


def to_avatar(file_bytes):
    """Picture -> square PNG, AVATAR_PX pixels, turned upright from the camera's EXIF."""
    im = Image.open(io.BytesIO(file_bytes))
    im = ImageOps.exif_transpose(im).convert('RGB')
    s = min(im.size)
    left, top = (im.width - s) // 2, (im.height - s) // 2
    im = im.crop((left, top, left + s, top + s)).resize((AVATAR_PX, AVATAR_PX), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format='PNG', optimize=True)
    return out.getvalue()


def img_html(png, size, border='#f2994a'):
    b64 = base64.b64encode(png).decode()
    return (f'<img src="data:image/png;base64,{b64}" width="{size}" height="{size}" alt="profile picture" '
            f'style="border-radius:50%; object-fit:cover; border:2px solid {border}; box-shadow:0 0 14px {border}44;">')


def initials_html(name, size, border='#f2994a'):
    ini = ''.join(w[0] for w in name.split()[:2]).upper() or '✦'
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;border:2px solid {border};'
            f'display:flex;align-items:center;justify-content:center;font-family:Georgia,serif;'
            f'font-size:{size * 0.4:.0f}px;color:#ffffff;background:rgba(242,153,74,0.08);">{html.escape(ini)}</div>')


def person_avatar(p, size=64, border='#f2994a'):
    if p.get('avatar'):
        return img_html(p['avatar'], size, border)
    if p.get('name'):
        return initials_html(p['name'], size, border)
    return ''


def avatar_html(size=64):
    return person_avatar(get(), size)


# ---------------------------------------------------------------- friend cards
def make_card(include_picture=True):
    p = get()
    card = {'format': CARD_FORMAT, 'version': 1, 'name': p['name'], 'birth': p['birth']}
    if include_picture and p['avatar']:
        card['picture_png_base64'] = base64.b64encode(p['avatar']).decode()
    return card


def card_file(include_picture=True):
    return json.dumps(make_card(include_picture), ensure_ascii=False, indent=1).encode('utf-8')


def card_filename():
    """'Gerad Smith' -> 'Gerad_Smith.lillycard' (characters Windows does not allow in file names are dropped)."""
    safe = re.sub(r'[\\/:*?"<>|]+', '', get()['name']).strip().replace(' ', '_')
    return (safe or 'friend_card') + '.lillycard'


def card_code():
    """Short text code without the picture: LILLY1:<base64url(zlib(json))>."""
    raw = json.dumps(make_card(False), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return CODE_PREFIX + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip('=')


def card_link():
    """The address a friend card's QR code opens: the online app with the card's text code."""
    return APP_URL + '?card=' + urllib.parse.quote(card_code(), safe=':')


def card_qr_png():
    """PNG of the QR code for card_link() (name and birth details, no picture)."""
    import qr_code
    return qr_code.png(card_link(), scale=6)


@st.dialog('Add a friend')
def _incoming_dialog(f):
    st.markdown(f'<div style="display:flex;align-items:center;gap:12px;">{person_avatar(f, 48) or ""}'
                f'<div><b>{html.escape(f["name"])}</b><br><span style="color:#c4ccdb;font-size:0.85rem;">'
                f'{html.escape(birth_text(f["birth"]))}</span></div></div>', unsafe_allow_html=True)
    st.write('')
    if any(x['name'] == f['name'] and x['birth'] == f['birth'] for x in friends()):
        st.info(f"{f['name']} is already among your friends.")
        if st.button('Close', width='stretch'):
            st.rerun()
        return
    st.markdown(f"**{html.escape(f['name'])}** shared their friend card with you. Add them to your friends? "
                'You can then compare your charts on the Friends page.')
    a, b = st.columns(2)
    if a.button(f"Add {f['name']}", type='primary', width='stretch', key='qr_add'):
        add_friend(f)
        st.toast(f"{f['name']} added to your friends.")
        st.rerun()
    if b.button('No, thank you', width='stretch', key='qr_no'):
        st.rerun()


def incoming_card():
    """Called from app.py: if the page was opened from a friend card's QR code (?card=...), offer to add it."""
    try:
        code = st.query_params.get('card')
    except Exception:
        return
    if not code:
        return
    try:
        del st.query_params['card']                      # once only; the address bar goes back to the plain address
    except Exception:
        pass
    try:
        f = parse_card(code)
    except ValueError as e:
        st.toast(f'That friend card could not be read. {e}')
        return
    _incoming_dialog(f)


# ---------------------------------------------------------------- reading a pasted LILLY1: code, forgivingly
# Phones and messaging apps change pasted text: they may write the prefix in small letters ("lilly1:", user report),
# break the code into lines, add spaces or invisible characters, turn "-" into a typographic dash, or send it inside
# a sentence or a link (?card=LILLY1%3A...). The code itself is base64url, which never contains those characters,
# so they can be removed safely. If words follow the code, shorter and shorter pieces are tried.
_B64URL = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=')
_DASHES = dict.fromkeys(map(ord, '\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe63\uff0d'), '-')
_INVISIBLE = set('\u200b\u200c\u200d\u2060\ufeff\u00ad')
_PREFIX_RE = re.compile(r'lilly\s*1\s*[:\uff1a]', re.IGNORECASE)


def _code_candidates(text):
    """The possible base64 parts of a LILLY1: code found anywhere in `text`, longest first; [] if there is none."""
    t = str(text)
    if re.search(r'lilly1%3a', t, re.IGNORECASE):
        t = urllib.parse.unquote(t)
    t = t.translate(_DASHES)
    m = _PREFIX_RE.search(t)
    if not m:
        return []
    pieces, cur = [], ''
    for ch in t[m.end():]:
        if ch in _INVISIBLE:
            continue
        if ch.isspace():
            if cur:
                pieces.append(cur)
                cur = ''
            continue
        if ch in _B64URL:
            cur += ch
            continue
        break                                     # the first character that cannot be part of a code ends it
    if cur:
        pieces.append(cur)
    return [''.join(pieces[:k]) for k in range(len(pieces), 0, -1)]


def _decode_code(text):
    """JSON text of the card in a LILLY1: code, or None if `text` holds no code; ValueError if it cannot be read."""
    cands = _code_candidates(text)
    if not cands:
        return None
    for b in cands:
        b = b.rstrip('=')
        try:
            raw = zlib.decompress(base64.urlsafe_b64decode(b + '=' * (-len(b) % 4)), bufsize=65536).decode('utf-8')
            json.loads(raw)
            return raw
        except Exception:
            continue
    raise ValueError('That code could not be read: part of it is missing or was changed on the way. Copy the whole '
                     'code again in one piece (it starts with LILLY1:), or ask your friend for the .lillycard file.')


def parse_card(data):
    """data: bytes of a .lillycard file, or the text code. Returns a friend dict; raises ValueError (plain message)."""
    if isinstance(data, bytes):
        if len(data) > MAX_CARD_KB * 1024:
            raise ValueError('That file is too large to be a friend card.')
        text = data.decode('utf-8', errors='replace').strip()
    else:
        text = str(data).strip()
    if not text.lstrip().startswith('{'):          # not a card file: look for a LILLY1: code (any case, any spacing)
        decoded = _decode_code(text)
        if decoded is not None:
            text = decoded
    try:
        card = json.loads(text)
    except ValueError:
        raise ValueError('That is not a friend card. Ask your friend to send the .lillycard file or the LILLY1: code.')
    if not isinstance(card, dict) or card.get('format') != CARD_FORMAT:
        raise ValueError('That is not a friend card from this app.')
    name = clean_name(card.get('name'))
    birth = _valid_birth(card.get('birth'))
    if not name:
        raise ValueError('The card has no name.')
    if not birth:
        raise ValueError(f'{name}\'s card has no birth details yet. Ask them to add their birth date, time and place '
                         'in their profile and send the card again.')
    av = None
    if card.get('picture_png_base64'):
        try:
            av = to_avatar(base64.b64decode(card['picture_png_base64']))
        except Exception:
            av = None          # a damaged picture is dropped; the rest of the card is still used
    return dict(name=name, birth=birth, avatar=av)


# ---------------------------------------------------------------- "Use my location" for where you live (user request)
# Afterglow's rules: the device is asked for its position (GPS on a phone, Wi-Fi position on a computer) - once by
# itself per visit when no home place is set yet, and whenever "Use my location" is pressed. The town and time zone
# come from the nearest gazetteer place, the ground height from open elevation data at the exact position
# (places.lookup_elevation); the device's own altitude is shown but not used (it is height above the GPS ellipsoid,
# which can differ from sea-level height by tens of metres). The position, rounded to about 10 m, is kept only in the
# profile (on this device) and never goes into a friend card.
GPS = 'pf_gps'
_LOC_JS = r"""
function locate(S, auto) {
  if (!('geolocation' in navigator)) {
    S.status.textContent = 'This browser cannot share its location. Type your town or city instead.';
    return;
  }
  S.status.textContent = auto ? 'Finding your location... (allow location if your browser asks)'
                              : 'Asking your device for its position...';
  navigator.geolocation.getCurrentPosition((p) => {
    const c = p.coords;
    S.status.textContent = `Found you (within ${Math.round(c.accuracy)} m).`;
    S.send('pick', { lat: c.latitude, lon: c.longitude, acc: c.accuracy, alt: c.altitude,
                     alt_acc: c.altitudeAccuracy, src: 'gps', ts: Date.now() });
  }, (err) => {
    let why;
    if (err.code === 1) {
      why = (window.top !== window.self)
        ? 'The page frame blocked location. Open the app full-screen (not inside another page), then press "Use my location".'
        : 'Location permission was refused. Allow location for this site in the browser settings, then press "Use my location".';
    } else if (err.code === 3) {
      why = 'The device took too long to find you. Try again, or type your town or city.';
    } else {
      why = 'Your position is not available right now. Press "Use my location" to try again, or type your town or city.';
    }
    S.status.textContent = why;
  }, { enableHighAccuracy: true, timeout: 25000, maximumAge: 0 });
}

function autoLocate(S) {
  if (S.autoTried) return;
  S.autoTried = true;
  try {
    if (sessionStorage.getItem('lilly-home-auto-located')) return;
    sessionStorage.setItem('lilly-home-auto-located', '1');
  } catch (e) { /* storage blocked: still try once for this page */ }
  const go = () => locate(S, true);
  if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: 'geolocation' }).then((st) => {
      if (st.state === 'denied') {
        S.status.textContent = 'Location is blocked for this site in the browser settings. Type your town or city.';
      } else go();
    }).catch(go);
  } else go();
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const d = data || {};
  let S = parentElement.__lillyLocate;
  if (!S || !S.root.isConnected) {
    const root = document.createElement('div');
    root.className = 'lilly-loc';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'lilly-loc-btn';
    btn.textContent = '\u{1F4CD} Use my location';
    const status = document.createElement('div');
    status.className = 'lilly-loc-status';
    root.appendChild(btn);
    root.appendChild(status);
    parentElement.appendChild(root);
    S = { root, btn, status, autoTried: false };
    btn.addEventListener('click', () => locate(S, false));
    parentElement.__lillyLocate = S;
  }
  S.send = setTriggerValue;
  if (d.auto) autoLocate(S);
}
"""
_LOC_CSS = """
.lilly-loc-btn { width: 100%; min-height: 2.6rem; border-radius: 0.5rem; background-color: #0b111c !important;
  color: #f7f1ea !important; border: 1px solid #4f6789 !important; font: inherit; cursor: pointer; padding: 0.4rem 0.8rem; }
.lilly-loc-btn:hover { border-color: #f2994a !important; }
.lilly-loc-status { color: #c4ccdb !important; font-size: 0.85rem; margin-top: 0.35rem; min-height: 0.2rem; }
"""
_locator = None
try:
    _locator = st.components.v2.component('lilly_home_locator', js=_LOC_JS, css=_LOC_CSS, isolate_styles=False)
except Exception:                     # an older Streamlit without st.components.v2: the button is simply not offered
    _locator = None


def _on_locate():
    v = st.session_state.get('pf_locate')
    p = v.get('pick') if hasattr(v, 'get') else None
    if not isinstance(p, dict):
        return
    try:
        lat, lon = float(p['lat']), float(p['lon'])
    except (KeyError, TypeError, ValueError):
        return
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return
    num = lambda x: float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None
    st.session_state[GPS] = dict(lat=round(lat, 4), lon=round(lon, 4), acc=num(p.get('acc')), alt=num(p.get('alt')))
    st.session_state.pop('pf_home_elev_for', None)


def _start_edit():
    """Fresh state for the profile window each time it is opened (a cancelled edit leaves nothing behind)."""
    for k in (GPS, 'pf_home_elev_for', 'pf_home_elev', 'pf_home_elev_src'):
        st.session_state.pop(k, None)
    h = get().get('home') or {}
    if h.get('src') == 'gps':
        st.session_state[GPS] = dict(lat=h['lat'], lon=h['lon'], acc=None, alt=None, saved=True)


# ---------------------------------------------------------------- the dialog
def _date_inputs(prefix, default):
    y0, m0, d0 = default.year, default.month, default.day
    c1, c2, c3 = st.columns([1.3, 1.4, 1])
    y = c1.number_input('Year', 1850, 2149, y0, 1, key=prefix + '_y')
    m = c2.selectbox('Month', range(1, 13), index=m0 - 1, format_func=lambda k: calendar.month_abbr[k], key=prefix + '_m')
    nd = calendar.monthrange(int(y), int(m))[1]
    d = c3.number_input('Day', 1, nd, min(d0, nd), 1, key=prefix + '_d')
    return dt.date(int(y), int(m), int(d))


@st.dialog('Your profile', width='large')
def edit_dialog():
    p = get()
    b0 = p['birth'] or {}
    st.markdown('**Name and picture**')
    name = st.text_input('Your name', p['name'], max_chars=MAX_NAME, placeholder='e.g. Gerad')
    up = st.file_uploader('Profile picture (JPG, PNG or WEBP)', type=['jpg', 'jpeg', 'png', 'webp'])
    new_av, err = None, None
    if up is not None:
        data = up.getvalue()
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            err = f'That picture is larger than {MAX_UPLOAD_MB} MB. Please choose a smaller one.'
        else:
            try:
                new_av = to_avatar(data)
            except Exception:
                err = 'That file could not be read as a picture. Please try a JPG or PNG.'
    if err:
        st.error(err)
    remove = False
    if p['avatar'] and new_av is None:
        remove = st.checkbox('Remove my current picture', value=False)
    show = new_av if new_av is not None else (None if remove else p['avatar'])
    if show:
        st.markdown(img_html(show, 110), unsafe_allow_html=True)

    st.markdown('**Birth details** (used on the Auspicious dates and Friends pages)')
    has_birth = st.checkbox('Add my birth date, time and place', value=bool(p['birth']), key='pf_has_birth')
    birth = None
    if has_birth:
        bdate = _date_inputs('pf', dt.date.fromisoformat(b0['date']) if b0 else dt.date(1990, 1, 1))
        unknown = st.checkbox('I do not know my birth time', value=not b0.get('time_known', True), key='pf_unknown')
        btime = dt.time(12, 0) if unknown else st.time_input(
            'Birth time (local clock)', dt.time.fromisoformat(b0['time']) if b0 else dt.time(12, 0), step=60, key='pf_time')
        q = st.text_input('Birthplace (type in city name and hit "Save", city will automatically populate after)', b0.get('place', '').split(',')[0] if b0 else '', key='pf_place',
                          placeholder='e.g. London, Mortlake, Kraków')
        hits = places.search(q, n=10) if q else []
        if q and not hits:
            st.warning('No match in the gazetteer (places with at least 1,000 inhabitants). Try a nearby town.')
        if hits:
            same = [k for k, hh in enumerate(hits) if b0 and abs(hh['lat'] - b0['lat']) < 1e-3 and abs(hh['lon'] - b0['lon']) < 1e-3]
            i = st.selectbox('Matches', range(len(hits)), index=same[0] if same else 0,
                             format_func=lambda k: places.label(hits[k]), key='pf_pick')
            h = hits[i]
            local = dt.datetime.combine(bdate, btime)
            off, note = places.utc_offset_hours(h['tz'], local)
            if st.checkbox(f'Override the UTC offset at birth (automatic: {off:+.2f} h)', key='pf_override'):
                off = st.number_input('UTC offset at birth (hours)', -12.0, 14.0, float(off), 0.25, key='pf_off')
            elif note:
                st.caption(note)
            birth = _valid_birth(dict(date=bdate.isoformat(), time=btime.strftime('%H:%M'), time_known=not unknown,
                                      place=f"{h['name']}, {h['country']}", lat=h['lat'], lon=h['lon'], tz=h['tz'],
                                      utc_offset=off))
            st.caption(f"{birth_text(birth)} · {h['lat']:.3f}°, {h['lon']:.3f}° · UTC{off:+.2f}")
        elif b0 and not q:
            birth = p['birth']
    st.markdown('**Where you live** (the starting place on the Chart and Auspicious dates pages)')
    ss = st.session_state
    h0 = p.get('home') or {}
    gps = ss.get(GPS)
    if _locator is not None:
        _locator(data=dict(auto=not h0 and not gps and not ss.get('pf_home')), key='pf_locate',
                 on_pick_change=_on_locate, width='stretch', height='content')
    home, hh = None, None
    if gps:
        near, dkm = places.nearest(gps['lat'], gps['lon'])
        hh = dict(name=near['name'], country=near['country'], lat=gps['lat'], lon=gps['lon'], tz=near['tz'])
        how = ('Saved position' if gps.get('saved') else 'Your position'
               + (f" (within {gps['acc']:.0f} m)" if gps.get('acc') else ''))
        st.caption(f"{how}: {gps['lat']:.4f}°, {gps['lon']:.4f}°, {dkm:.1f} km from {near['name']}, {near['country']} "
                   f"(the town and time zone used).")
        st.button('Type a town or city instead', key='pf_gps_off', icon=':material/search:', width='stretch',
                  on_click=lambda: ss.pop(GPS, None))
    else:
        hq = st.text_input('Your town or city', h0.get('name', ''), key='pf_home',
                           placeholder='e.g. Mortlake, Kraków, Chicago')
        hhits = places.search(hq, n=10) if hq else []
        if hq and not hhits:
            st.warning('No match in the gazetteer (places with at least 1,000 inhabitants). Try a nearby town.')
        if hhits:
            same_h = [k for k, x in enumerate(hhits) if h0 and abs(x['lat'] - h0['lat']) < 1e-3 and abs(x['lon'] - h0['lon']) < 1e-3]
            j = st.selectbox('Matches', range(len(hhits)), index=same_h[0] if same_h else 0,
                             format_func=lambda k: places.label(hhits[k]), key='pf_home_pick')
            hh = hhits[j]
    if hh:
        tol = 2e-4 if gps else 1e-3
        same_place = bool(h0) and abs(hh['lat'] - h0['lat']) < tol and abs(hh['lon'] - h0['lon']) < tol
        # ground height (Afterglow's rules, user request): the saved value for the same place, else looked up at the
        # exact point from open elevation data. Also when the box itself was dropped (Streamlit forgets a widget's
        # value while the window is closed, and the box then came back at its lowest value, -500 m: user report).
        here_h = (round(hh['lat'], 4), round(hh['lon'], 4))
        if ss.get('pf_home_elev_for') != here_h or 'pf_home_elev' not in ss:
            ss['pf_home_elev_for'] = here_h
            saved = h0.get('elev') if same_place else None
            if saved is not None and float(saved) < places.ELEV_MIN - 1:   # the old -500 m bug value: look it up
                saved = None
            if saved is not None:
                v, src = float(saved), 'saved'
            else:
                v, src = places.lookup_elevation(hh['lat'], hh['lon'])
            ss['pf_home_elev'] = float(v or 0.0)
            ss['pf_home_elev_src'] = src or 'none'
        src = ss.get('pf_home_elev_src', 'none')
        h_elev = st.number_input('Ground elevation where you live (metres above sea level)', places.ELEV_MIN,
                                 places.ELEV_MAX, step=1.0, format='%.0f', key='pf_home_elev',
                                 help='Filled in by itself for the exact spot from open elevation data (AWS Terrain '
                                      'Tiles: SRTM, USGS 3DEP, GMTED2010 and others; Open-Meteo over water or when '
                                      'they cannot be reached). Type over it if you know better. The charts are '
                                      f'worked out for your eyes, {places.EYE_HEIGHT_M:g} m above the ground. The '
                                      'Chart, Auspicious dates and Friends pages start at this elevation when the '
                                      'place is where you live. It changes sunrise, and so the planetary hours, '
                                      'slightly.')
        st.caption({'tiles': 'Ground height read for this spot from open elevation data (AWS Terrain Tiles).',
                    'open-meteo': 'Ground height read for this spot from a terrain map (Open-Meteo, Copernicus DEM).',
                    'saved': 'Ground height as saved in your profile.',
                    'none': 'The elevation data could not be reached, so this starts at 0 m. Type it in if you '
                            'know it.'}.get(src, '')
                   + f' Eye level used for the charts: {float(h_elev) + places.EYE_HEIGHT_M:.1f} m.')
        if gps and gps.get('alt') is not None:
            st.caption(f"Your device reported an altitude of {gps['alt']:.0f} m. Phones give height above the GPS "
                       "ellipsoid, which can differ from sea-level height by tens of metres, so the elevation data "
                       "is used unless you type the ground height yourself.")
        home = _valid_home(dict(name=hh['name'], country=hh['country'], lat=hh['lat'], lon=hh['lon'], tz=hh['tz'],
                                elev=h_elev, src='gps' if gps else 'town'))
        st.caption(f"{hh['name']}, {hh['country']} · {hh['lat']:.4f}°, {hh['lon']:.4f}° · ground {home['elev']:.0f} m · "
                   f"time zone {hh['tz']}. Not included in your friend card.")
    remember = None
    if LOCAL:
        st.caption('On this computer your profile is saved in the app\'s "profile" folder and never leaves it.')
    elif device_available():
        remember = st.checkbox('Remember me on this device', value=remembered(), key='pf_remember',
                               help='Keeps your profile and friends in this browser, on this phone, tablet or computer '
                                    'only, so they are here next time you open the app. Nothing is stored on the server.')
        st.caption('Ticked: your profile and friends are kept in this browser on this device, and nowhere else. '
                   'Do not tick it on a shared or borrowed device. Not ticked: they are kept only while the app is open.')
    else:
        st.caption('Online, your profile is kept only while the app is open; nothing is stored on the server.'
                   + (' This browser does not allow the app to remember you (private browsing?).'
                      if _store is not None and st.session_state.get('_dev_loaded') else ''))
    c1, c2 = st.columns(2)
    if c1.button('Save', type='primary', width='stretch', disabled=bool(err)):
        save(name, show, birth if has_birth else None, home)
        if remember is not None:
            set_remember(remember)
        st.rerun()
    if c2.button('Cancel', width='stretch'):
        st.rerun()


def sidebar_card():
    """Picture, name and the Edit button, at the top of the sidebar on every page."""
    p = get()
    with st.sidebar:
        if p['name'] or p['avatar']:
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin:2px 0 6px 0;">{avatar_html(56)}'
                        f'<div><div style="font-family:Georgia,serif;font-size:1.15rem;color:#ffffff;">'
                        f'{html.escape(p["name"]) or "&nbsp;"}</div>'
                        f'<div style="font-size:0.75rem;color:#c4ccdb;">{html.escape(birth_text(p["birth"]))}</div></div></div>',
                        unsafe_allow_html=True)
            label = 'Edit profile'
        else:
            label = 'Add your name and picture'
        if st.button(label, key='profile_btn', icon=':material/account_circle:', width='stretch'):
            _start_edit()
            edit_dialog()
        # one click: the user's friend card file, to send to friends (also on the Friends page, with more choices)
        if p['name'] and p['birth']:
            st.download_button('Download my friend card', card_file(True), file_name=card_filename(),
                               mime='application/json', key='card_dl_sidebar', icon=':material/badge:', width='stretch',
                               on_click='ignore',
                               help='Saves your friend card (.lillycard: your name, birth details and picture) to your '
                                    'Downloads folder. Send it to a friend by e-mail or message; they add it on their '
                                    'Friends page. To leave your picture out, or to copy a text code, use the Friends page.')
        elif p['name'] or p['avatar']:
            st.caption('To make your friend card, add your birth date, time and place: click Edit profile.')
        if not LOCAL and device_available():
            if remembered():
                st.caption(':material/smartphone: Remembered on this device.'
                           + (' **Could not save the latest changes: the browser\'s storage is full.**'
                              if st.session_state.get('_dev_save_failed') else ''))
                if st.button('Forget me on this device', key='forget_btn', icon=':material/delete:', width='stretch',
                             help='Deletes your profile and friends from this browser\'s storage. They stay on the '
                                  'screen until you close the app.'):
                    set_remember(False)
                    st.toast('This device will no longer remember you.')
                    st.rerun()
            elif p['name'] or p['avatar'] or p['birth'] or friends():
                if st.button('Remember me on this device', key='remember_btn', icon=':material/smartphone:',
                             width='stretch',
                             help='Keeps your profile and friends in this browser on this device, so they are here '
                                  'next time. Nothing is stored on the server. Not for shared or borrowed devices.'):
                    set_remember(True)
                    st.toast('This device will remember you.')
                    st.rerun()
        st.divider()


def title(base, name_form):
    """Page title with the user's picture beside it, when there is a profile."""
    text = personal(base, name_form)
    text = _md_escape(text) if get()['name'] else text
    av = avatar_html(64)
    if av:
        a, b = st.columns([0.07, 0.93], vertical_alignment='center')
        a.markdown(av, unsafe_allow_html=True)
        b.title(text)
    else:
        st.title(text)
