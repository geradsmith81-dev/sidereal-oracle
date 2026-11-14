"""
astrosophy_layer.py - turns a chart into astrosophical reading material.

Every sentence carries an attribution tag:
  Steiner  - a correspondence Steiner himself gave (GA number in data/*.csv)
  Sucher   - from Willi Sucher's astrosophy (Hermetic Rule, prenatal graph)
  Vreede   - from Elisabeth Vreede
  app rule - a choice made by this app where the sources are silent
The texts are paraphrases kept in editable CSV files under data/.

The readings are prompts for reflection on Steiner's and Sucher's pictures.
Steiner himself said his "world-view constellations" of the soul need not
coincide with the outer birth horoscope (GA 151, lecture 4).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd

from . import astrosophy_engine as E
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def _csv(name):
    return pd.read_csv(os.path.join(DATA, name), encoding="utf-8")


class Tables:
    def __init__(self):
        self.world = _csv("world_views.csv").set_index("zodiac")
        moods = _csv("soul_moods.csv")
        self.moods = moods[moods.kind == "mood"].set_index("planet")
        self.tones = moods[moods.kind == "tone"]
        self.zc = _csv("zodiac_correspondences.csv").set_index("zodiac")
        self.pc = _csv("planet_correspondences.csv").set_index("planet")
        self.life = _csv("life_spheres.csv")
        self.uncertainty = _csv("uncertainty_log.csv")
        self.sources = _csv("sources.csv")


_T = None


def tables() -> Tables:
    global _T
    if _T is None:
        _T = Tables()
    return _T


# --------------------------------------------------------------------------- helpers
def zodiac_reading(abbr: str, senses: str = "1921") -> dict:
    """World-view, sense and sound for an IAU zodiac band (abbr)."""
    T = tables()
    col = "sense_1921_sketch" if senses == "1921" else "sense_1913_lesson"
    if abbr == "Oph":
        return {"zodiac": "Ophiuchus",
                "world_view": "between Dynamism and Monadism",
                "world_meaning": ("Ophiuchus has no world-view of its own in Steiner's circle of twelve. "
                                  "The app reads it as the passage from Dynamism (Scorpio: forces behind the "
                                  "phenomena) to Monadism (Sagittarius: individual centres of being)."),
                "sense": "\u2013", "consonant": "\u2013", "attr": "app rule"}
    name = E.ZODIAC_NAME[abbr]
    w = T.world.loc[name]
    z = T.zc.loc[name]
    return {"zodiac": name, "world_view": w.world_view, "world_meaning": w.meaning_paraphrase,
            "sense": z[col], "consonant": z.eurythmy_consonant, "attr": "Steiner"}


def life_sphere(age: float) -> dict:
    T = tables()
    r = T.life[(T.life.age_from <= age) & (age < T.life.age_to)].iloc[0]
    return r.to_dict()


def age_years(birth_utc: datetime, when_utc: datetime) -> float:
    return (when_utc - birth_utc).total_seconds() / (365.2425 * 86400.0)


# --------------------------------------------------------------------------- main
def planet_table(ch: dict, senses: str = "1921") -> pd.DataFrame:
    T = tables()
    rows = []
    for b in ch["bodies"]:
        zr = zodiac_reading(b.zodiac, senses)
        mood = T.moods.loc[b.name] if b.name in T.moods.index else None
        pc = T.pc.loc[b.name] if b.name in T.pc.index else None
        if mood is not None and b.zodiac != "Oph":
            phrase = f"{mood.soul_mood} in the sign of {zr['world_view']}"
        elif mood is not None:
            phrase = f"{mood.soul_mood} between Dynamism and Monadism"
        else:
            phrase = "\u2013"
        flags = []
        if b.off_zodiac:
            flags.append(f"off the zodiac: true IAU constellation {E.con_name(b.iau_true)}")
        if b.retrograde and b.name not in ("Sun", "Moon"):
            flags.append("retrograde (looping)")
        if b.note:
            flags.append(b.note)
        hz = zodiac_reading(b.helio_zodiac, senses)["zodiac"] if b.helio_zodiac else "\u2013"
        rows.append({
            "body": f"{E.GLYPH[b.name]} {b.name}",
            "zodiac (IAU)": zr["zodiac"],
            "deg in band": _deg_in_band(b.lon, b.zodiac, ch["bands"]),
            "tropical": f"{b.lon % 30:4.1f}\u00b0 {b.tropical_sign}",
            "soul mood": mood.soul_mood if mood is not None else "\u2013",
            "world-view": zr["world_view"],
            "Steiner's picture": phrase,
            "sense": zr["sense"],
            "sound": (pc.eurythmy_vowel if pc is not None else "") + (" / " if pc is not None else "") + zr["consonant"],
            "metal": pc.metal if pc is not None else "\u2013",
            "heliocentric": hz,
            "notes": "; ".join(flags),
            "attribution": "Steiner" + (" + app rule" if b.zodiac == "Oph" or b.off_zodiac else "") if mood is not None else "app rule (no mood for this body)",
            "_lon": b.lon,
        })
    return pd.DataFrame(rows)


def _deg_in_band(lon, abbr, bands):
    for ab, s, e in bands:
        if ab == abbr:
            x = lon if s <= lon < e else lon + 360
            return f"{x - s:4.1f}\u00b0 of {e - s:.0f}\u00b0"
    return ""


def reading(ch: dict, senses: str = "1921", epoch=None, events: pd.DataFrame | None = None,
            now_utc: datetime | None = None) -> list:
    """List of {heading, text, attr} paragraphs for the birth chart."""
    T = tables()
    out = []
    add = lambda h, t, a: out.append({"heading": h, "text": t, "attr": a})

    add("How to read this",
        "Steiner described twelve world-views (the 'spiritual zodiac') and seven soul moods (the 'planets' of "
        "the soul). In his picture a mood can stand 'in the sign of' a world-view, e.g. Venus in Aries = "
        "Mysticism in the sign of Idealism. He also warned that these soul constellations need not coincide "
        "with the outer horoscope. The pairs below therefore show which pictures the actual sky offers at this "
        "moment, as material for reflection. They are not a statement about the person.", "Steiner (GA 151)")

    sun, moon = E.body(ch, "Sun"), E.body(ch, "Moon")
    for b in (sun, moon):
        zr = zodiac_reading(b.zodiac, senses)
        mood = T.moods.loc[b.name]
        txt = (f"The {b.name} stands in the IAU constellation {zr['zodiac']} "
               f"(tropical sign {b.tropical_sign}). Steiner's world-view for {zr['zodiac']} is "
               f"{zr['world_view']}: {zr['world_meaning']} The {b.name}'s soul mood is {mood.soul_mood}: "
               f"{mood.meaning_paraphrase}")
        if b.off_zodiac:
            txt += (f" Seen in the actual sky, the {b.name} is just outside the zodiac band, in "
                    f"{E.con_name(b.iau_true)}; the reading uses the zodiac constellation at its longitude.")
        add(f"{b.name}: {mood.soul_mood} in {zr['world_view']}", txt,
            "Steiner" + (" + app rule" if b.zodiac == "Oph" or b.off_zodiac else ""))

    asc_r = zodiac_reading(ch["asc_zodiac"], senses)
    add("Ascendant",
        f"The eastern horizon (Ascendant) rises in {asc_r['zodiac']}. Sucher saw the Ascendant (or the "
        f"Descendant) as the picture of a bridge: the pathway along which the life body enters from the "
        f"Moon sphere into physical existence. The Moon stood on this point at the prenatal epoch.",
        "Sucher (1937)")

    add("Moon phase",
        f"The Moon is {ch['moon_phase_name'].lower()} ({ch['moon_elongation']:.0f}\u00b0 from the Sun), "
        f"{'waxing' if ch['moon_waxing'] else 'waning'}, and {'above' if ch['moon_above_horizon'] else 'below'} "
        f"the horizon. This decides which form of the Hermetic Rule applies.", "Sucher (1937)")

    if epoch is not None:
        ep_moon = E.body(epoch.chart, "Moon")
        add("Prenatal epoch (Hermetic Rule)",
            f"Epoch: {epoch.utc:%d %b %Y, %H:%M} UTC, {epoch.gestation_days:.1f} days before birth "
            f"({epoch.months} sidereal months = {epoch.months * E.SIDEREAL_MONTH:.1f} d). {epoch.case_text} "
            f"At the epoch the Moon stood in {E.con_name(ep_moon.zodiac)}; each of its returns to that place "
            f"opens one seven-year period of the coming life. Check on the birth time: the epoch "
            f"{epoch.residual_angle} is {epoch.residual_deg:.1f}\u00b0 from the birth Moon. A large figure "
            f"means the recorded birth time and the reciprocal form of the rule do not agree.",
            "Sucher (1937)")

    vm = [b for b in ch["bodies"] if b.name in ("Mercury", "Venus")]
    add("Morning and evening star",
        "; ".join(f"{b.name} is {b.note}" for b in vm) + ". Vreede points out that Venus as morning star "
        "and as evening star reveals two different beings, and the same holds for Mercury.", "Vreede")

    outer = [b.name for b in ch["bodies"] if b.name in ("Uranus", "Neptune", "Pluto")]
    add("Outer planets and nodes",
        f"{', '.join(outer)} and the lunar node are drawn on the chart, but Steiner's seven soul moods belong "
        f"to the seven classical planets only, so they receive no reading here.", "app rule")

    if now_utc is not None:
        age = age_years(ch["utc"], now_utc)
        if age >= 0:
            ls = life_sphere(age)
            if age < 63:
                txt = (f"At age {age:.1f} the life stands in the {ls['sphere']} period "
                       f"({ls['age_from']}\u2013{ls['age_to']} years; {ls['member']}).")
            else:
                txt = f"At age {age:.1f} the life is past the seven planetary periods, which end at 63."
            if ls["sphere"] in ("Mercury", "Venus"):
                txt += (" Note Steiner's remark that the names Mercury and Venus were exchanged in older occult "
                        "tradition; the app does not decide which body is meant (see uncertainty log U3).")
            if events is not None and len(events):
                k = int(age // 7)
                win = events[(events.age >= 7 * k) & (events.age < 7 * (k + 1)) & (events.event != "Moon passes")]
                txt += (f" In the prenatal graph this corresponds to lunar cycle {k + 1}, which shows "
                        f"{len(win)} planetary events (see the Life rhythms tab).")
            add("Life rhythm now", txt, "Steiner / Vreede; Sucher (prenatal graph)")
    return out
