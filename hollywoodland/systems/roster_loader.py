from __future__ import annotations
import json
import os
import random
from typing import Any, Dict, List, Optional

from hollywoodland.models.entities import CORE_ATTRIBUTES

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ROSTERS_DIR = os.path.join(PROJECT_ROOT, "rosters")


def list_roster_packs(rosters_dir: str = ROSTERS_DIR) -> List[Dict[str, Any]]:
    """Scan rosters/ for optional external Roster Packs (each folder containing manifest.json)."""
    packs: List[Dict[str, Any]] = []
    if not os.path.isdir(rosters_dir):
        return packs
    for entry in sorted(os.listdir(rosters_dir)):
        pack_dir = os.path.join(rosters_dir, entry)
        manifest_path = os.path.join(pack_dir, "manifest.json")
        if os.path.isdir(pack_dir) and os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                manifest["id"] = entry
                manifest["path"] = pack_dir
                packs.append(manifest)
            except Exception:
                continue
    return packs


def load_roster_pack(pack_id_or_path: str, rosters_dir: str = ROSTERS_DIR) -> Optional[Dict[str, Any]]:
    """Load a Roster Pack by folder name (inside rosters/) or absolute directory path."""
    if os.path.isdir(pack_id_or_path) and os.path.isfile(os.path.join(pack_id_or_path, "manifest.json")):
        pack_dir = pack_id_or_path
    else:
        pack_dir = os.path.join(rosters_dir, pack_id_or_path)
    manifest_path = os.path.join(pack_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        return None

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    def _load_json(filename: str) -> List[Dict[str, Any]]:
        p = os.path.join(pack_dir, filename)
        if not os.path.isfile(p):
            return []
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []

    return {
        "id": os.path.basename(pack_dir),
        "path": pack_dir,
        "manifest": manifest,
        "actors": _load_json("actors.json"),
        "creatives": _load_json("creatives.json"),
        "studios": _load_json("studios.json"),
        "projects": _load_json("projects.json"),
    }


def _clamp(val: float, lo: int = 15, hi: int = 99) -> int:
    return max(lo, min(hi, int(round(val))))


def auto_fill_actor_attributes(record: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """
    Fill in (or derive) Hollywoodland gameplay attributes from real-world TMDb metadata
    (popularity, genres, vote_average, credit_count, age, gender) while preserving any
    fields the user already filled in manually.
    """
    pop = float(record.get("tmdb_popularity", 10.0) or 10.0)
    avg_vote = float(record.get("tmdb_avg_vote", 6.5) or 6.5)
    credit_count = int(record.get("tmdb_credit_count", 12) or 12)
    genres = [str(g).strip() for g in (record.get("top_genres") or [])]
    age = int(record.get("age", 34) or 34)
    sex = record.get("sex") if record.get("sex") in ("Male", "Female") else "Male"

    # 1. Fame tier & score derived from TMDb popularity + career volume
    if not record.get("fame_tier"):
        if pop >= 55.0 or (pop >= 38.0 and credit_count >= 35):
            fame_tier = "A-lister"
        elif pop >= 28.0 or (pop >= 20.0 and credit_count >= 25):
            fame_tier = "Notable"
        elif pop >= 15.0:
            fame_tier = "Average"
        elif pop >= 8.0:
            fame_tier = "Relatively unknown"
        else:
            fame_tier = "Unknown"
        record["fame_tier"] = fame_tier
    else:
        fame_tier = record["fame_tier"]

    if not record.get("fame_score"):
        tier_base = {
            "A-lister": (84.0, 99.0),
            "Notable": (65.0, 83.0),
            "Average": (40.0, 64.0),
            "Relatively unknown": (20.0, 39.0),
            "Unknown": (5.0, 19.0),
        }.get(fame_tier, (20.0, 45.0))
        record["fame_score"] = round(rng.uniform(*tier_base), 1)

    # 2. Derive 12 Core Attributes from career quality, genres, popularity & experience
    existing_attrs = dict(record.get("attributes") or {})
    quality_bonus = (avg_vote - 6.0) * 8.0          # e.g. 7.5 avg vote -> +12
    exp_bonus = min(14.0, credit_count * 0.35)      # veteran actors gain craft
    star_bonus = {"A-lister": 14.0, "Notable": 9.0, "Average": 4.0, "Relatively unknown": 0.0, "Unknown": -4.0}.get(fame_tier, 0.0)
    base = 52.0 + quality_bonus + (exp_bonus * 0.5) + (star_bonus * 0.5)

    gset = {g.lower() for g in genres}
    is_drama = bool(gset & {"drama", "history", "historical", "war", "biography"})
    is_comedy = bool(gset & {"comedy", "family", "romance"})
    is_action = bool(gset & {"action", "adventure", "sci-fi", "science fiction", "fantasy", "western"})
    is_voice = bool(gset & {"animation", "music", "musical"})
    is_thriller = bool(gset & {"thriller", "crime", "mystery", "horror"})

    derived = {
        "Characterization": base + (10 if is_drama else 0) + (4 if is_thriller else 0) + rng.randint(-8, 10),
        "Improvisation": base + (12 if is_comedy else 0) + rng.randint(-10, 10),
        "Vocal Expression": base + (14 if is_voice else 0) + (5 if is_drama else 0) + rng.randint(-9, 9),
        "Physical Expression": base + (13 if is_action else 0) - (max(0, age - 55) * 0.4) + rng.randint(-8, 8),
        "Facial Expression": base + (9 if is_drama or is_thriller else 0) + rng.randint(-8, 10),
        "Intelligence": 55.0 + quality_bonus * 0.8 + exp_bonus * 0.4 + rng.randint(-10, 12),
        "Charisma": 50.0 + star_bonus * 1.4 + (6 if is_comedy else 0) + rng.randint(-8, 10),
        "Humor": 48.0 + (18 if is_comedy else -4) + rng.randint(-10, 12),
        "Commitment": 54.0 + quality_bonus * 0.6 + exp_bonus * 0.5 + rng.randint(-10, 10),
        "Confidence": 52.0 + star_bonus * 1.2 + rng.randint(-9, 10),
        "Professionalism": 56.0 + exp_bonus * 0.6 + rng.randint(-12, 12),
        "Stamina": 66.0 + (10 if is_action else 0) - max(0, age - 42) * 0.55 + rng.randint(-8, 8),
    }

    final_attrs: Dict[str, int] = {}
    for k in CORE_ATTRIBUTES:
        if k in existing_attrs and isinstance(existing_attrs[k], (int, float)) and existing_attrs[k] > 0:
            final_attrs[k] = _clamp(existing_attrs[k])
        else:
            final_attrs[k] = _clamp(derived[k])
    record["attributes"] = final_attrs

    # 2b. Potential rating (ceiling 42-99) derived from real-world career acclaim, longevity & star power
    if not record.get("potential_rating"):
        tier_pot = {
            "A-lister": 88.0,
            "Notable": 78.0,
            "Average": 68.0,
            "Relatively unknown": 59.0,
            "Unknown": 51.0,
        }.get(fame_tier, 62.0)
        vote_mod = (avg_vote - 6.3) * 7.5
        longevity_mod = min(7.0, credit_count * 0.08)
        attr_peak = sum(final_attrs.values()) / max(1, len(final_attrs))
        raw_pot = max(attr_peak, tier_pot + vote_mod + longevity_mod + rng.uniform(-3.0, 4.0))
        record["potential_rating"] = _clamp(raw_pot, lo=42, hi=99)

    # 3. Physical defaults if not manually filled (plus remap legacy look strings)
    look_remap = {
        "Beautiful": "Striking",
        "Pretty": "Attractive",
        "Ruggedly handsome": "Rugged",
        "Boyishly handsome": "Clean-Cut",
        "Average": "Everyday",
        "Unconventional": "Distinctive",
    }
    if record.get("look") in look_remap:
        record["look"] = look_remap[record["look"]]
    if not record.get("look"):
        if sex == "Male":
            record["look"] = rng.choices(
                ["Rugged", "Clean-Cut", "Everyday", "Distinctive"],
                weights=[35, 32, 23, 10] if fame_tier in ("A-lister", "Notable") else [22, 25, 38, 15],
            )[0]
        else:
            record["look"] = rng.choices(
                ["Striking", "Attractive", "Everyday", "Distinctive"],
                weights=[42, 35, 15, 8] if fame_tier in ("A-lister", "Notable") else [24, 34, 28, 14],
            )[0]

    if not record.get("bodytype"):
        if sex == "Male":
            record["bodytype"] = rng.choices(
                ["Athletic", "Muscular", "Average", "Slim", "Chunky"],
                weights=[32, 26, 24, 12, 6] if is_action else [24, 12, 36, 18, 10],
            )[0]
        else:
            record["bodytype"] = rng.choices(
                ["Slim", "Athletic", "Curvy", "Average"],
                weights=[36, 26, 20, 18],
            )[0]

    if not record.get("height_cm"):
        record["height_cm"] = rng.randint(172, 191) if sex == "Male" else rng.randint(157, 177)

    if not record.get("height_category"):
        h = int(record["height_cm"])
        if sex == "Male":
            record["height_category"] = "Very short" if h < 166 else ("Short" if h < 174 else ("Medium" if h < 183 else ("Tall" if h < 191 else "Very tall")))
        else:
            record["height_category"] = "Very short" if h < 156 else ("Short" if h < 163 else ("Medium" if h < 171 else ("Tall" if h < 178 else "Very tall")))

    if not record.get("ethnicity"):
        record["ethnicity"] = "White"

    if not record.get("personality") or not record.get("disc"):
        pers_pool = [
            ("Charismatic", "I"), ("Driven", "D"), ("Methodical", "C"),
            ("Easygoing", "S"), ("Ambitious", "D"), ("Witty", "I"),
            ("Perfectionist", "C"), ("Loyal", "S"),
        ]
        p, d = rng.choice(pers_pool)
        record.setdefault("personality", p)
        record.setdefault("disc", d)

    # 4. Special skills from genres
    if not record.get("special_skills"):
        skills: List[str] = []
        if is_action:
            skills.append(rng.choice(["Martial Arts", "Stunts", "Swordplay", "Horse Riding"]))
        if is_voice:
            skills.append(rng.choice(["Singing", "Voice Acting", "Dancing"]))
        if is_comedy:
            skills.append("Stand-up Comedy")
        record["special_skills"] = list(dict.fromkeys(skills))

    return record


def calibrate_roster_fame_tiers(actors: List[Dict[str, Any]], rng: random.Random) -> List[Dict[str, Any]]:
    """
    Assign realistic Hollywood fame tiers across a Roster Pack using relative percentile
    of TMDb popularity + career credit depth + critical rating, then recalculate attributes.
    """
    if not actors:
        return actors

    def _star_index(rec: Dict[str, Any]) -> float:
        pop = float(rec.get("tmdb_popularity", 5.0) or 5.0)
        creds = min(160, int(rec.get("tmdb_credit_count", 10) or 10))
        vote = float(rec.get("tmdb_avg_vote", 6.2) or 6.2)
        return (pop * 1.6) + (creds * 0.45) + (max(0.0, vote - 6.0) * 6.0)

    ranked_indices = sorted(range(len(actors)), key=lambda i: -_star_index(actors[i]))
    n = len(actors)
    for rank_pos, idx in enumerate(ranked_indices):
        pct = rank_pos / max(1, n)
        rec = actors[idx]
        if pct < 0.09:
            rec["fame_tier"] = "A-lister"
            rec["fame_score"] = round(98.5 - (pct / 0.09) * 14.0, 1)
        elif pct < 0.25:
            rec["fame_tier"] = "Notable"
            rec["fame_score"] = round(83.5 - ((pct - 0.09) / 0.16) * 18.0, 1)
        elif pct < 0.50:
            rec["fame_tier"] = "Average"
            rec["fame_score"] = round(64.5 - ((pct - 0.25) / 0.25) * 24.0, 1)
        elif pct < 0.75:
            rec["fame_tier"] = "Relatively unknown"
            rec["fame_score"] = round(39.5 - ((pct - 0.50) / 0.25) * 19.0, 1)
        else:
            rec["fame_tier"] = "Unknown"
            rec["fame_score"] = round(19.5 - ((pct - 0.75) / 0.25) * 14.0, 1)
        # Clear old auto-derived attributes & potential so they refresh with the calibrated tier
        rec["attributes"] = {}
        rec["potential_rating"] = 0
        actors[idx] = auto_fill_actor_attributes(rec, rng)
    return actors
