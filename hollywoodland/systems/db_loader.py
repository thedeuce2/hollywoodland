from __future__ import annotations
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple


STEAM_ASSETS_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\Cattle Call\assets"


class GameDatabase:
    """Loads and indexes all 121 extracted database tables and 278 event scripts."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        self.data_dir = data_dir
        self.db1: Dict[str, Any] = {}
        self.db2: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        p1 = os.path.join(self.data_dir, "attributes1.json")
        p2 = os.path.join(self.data_dir, "attributes2.json")
        pe = os.path.join(self.data_dir, "events.json")
        if os.path.exists(p1):
            with open(p1, "r", encoding="utf-8") as f:
                self.db1 = json.load(f)
        if os.path.exists(p2):
            with open(p2, "r", encoding="utf-8") as f:
                self.db2 = json.load(f)
        if os.path.exists(pe):
            with open(pe, "r", encoding="utf-8") as f:
                self.events = json.load(f)

        # Build fast lookup caches
        self._build_name_pools()
        self._build_title_pools()
        self._build_role_pools()
        self._build_quote_table()
        self._build_audition_tables()

    def get_rows(self, table_name: str) -> List[Dict[str, Any]]:
        if table_name in self.db1:
            return self.db1[table_name].get("rows", [])
        if table_name in self.db2:
            return self.db2[table_name].get("rows", [])
        return []

    def _build_name_pools(self) -> None:
        self.first_names: Dict[Tuple[str, str], List[str]] = {}
        self.last_names: Dict[Tuple[str, str], List[str]] = {}

        male_tables = {
            "White": "M_BLACKWHITENATIVE",
            "Black": "M_BLACKWHITENATIVE",
            "Native American": "M_BLACKWHITENATIVE",
            "Hispanic": "M_HISPANIC",
            "Asian": "M_ASIAN",
            "Indian": "M_INDIAN",
            "Arabic": "M_ARABIC",
        }
        female_tables = {
            "White": "F_WHITE",
            "Black": "F_BLACKNATIVE",
            "Native American": "F_BLACKNATIVE",
            "Hispanic": "F_HISPANIC",
            "Asian": "F_ASIAN",
            "Indian": "F_INDIAN",
            "Arabic": "F_ARABIC",
        }

        for sex, mapping in [("Male", male_tables), ("Female", female_tables)]:
            for eth, tname in mapping.items():
                rows = self.get_rows(tname)
                fnames = []
                lnames = []
                for r in rows:
                    fn = (r.get("FirstNameUSA") or r.get("First Name Canadian") or "").strip()
                    ln = (r.get("SurnameUSA") or r.get("Surname Canadian") or "").strip()
                    if fn:
                        fnames.append(fn)
                    if ln:
                        lnames.append(ln)
                self.first_names[(sex, eth)] = fnames or ["Alex", "Jordan", "Taylor", "Morgan"]
                self.last_names[(sex, eth)] = lnames or ["Smith", "Miller", "Davis", "Wilson"]

        # Birthplaces by nationality
        self.birthplaces: Dict[str, List[str]] = {}
        for r in self.get_rows("Birthplaces"):
            for nat_col, nat_key in [
                ("USA", "USA"),
                ("CANADA", "Canada"),
                ("ENGLAND", "England"),
                ("AUSTRALIA", "Australia"),
                ("SCOTLAND", "Scotland"),
                ("IRELAND", "Ireland"),
                ("WALES", "Wales"),
            ]:
                val = (r.get(nat_col) or "").strip()
                if val:
                    self.birthplaces.setdefault(nat_key, []).append(val)
        self.birthplaces.setdefault("New Zealand", ["Auckland", "Wellington", "Christchurch"])

    def sample_name(self, rng: random.Random, sex: str, ethnicity: str) -> str:
        fns = self.first_names.get((sex, ethnicity)) or self.first_names.get((sex, "White")) or ["Alex"]
        lns = self.last_names.get((sex, ethnicity)) or self.last_names.get((sex, "White")) or ["Smith"]
        return f"{rng.choice(fns)} {rng.choice(lns)}"

    def sample_birthplace(self, rng: random.Random, nationality: str) -> str:
        places = self.birthplaces.get(nationality) or self.birthplaces.get("USA") or ["Los Angeles"]
        return rng.choice(places)

    def _build_title_pools(self) -> None:
        rows = self.get_rows("Movietitlegenerator")
        self.title_rules: List[Tuple[str, float]] = []
        self.title_numbers: List[str] = []
        self.title_nouns_sing: List[str] = []
        self.title_nouns_plur: List[str] = []
        self.title_adjectives: List[str] = []
        self.title_first_names: List[str] = []
        self.title_last_names: List[str] = []

        for r in rows:
            rule = (r.get("Rules") or "").strip()
            weight = float(r.get("Gyakorisag random") or 0.0)
            if rule and weight > 0:
                self.title_rules.append((rule, weight))
            for col, target in [
                ("NUMBER", self.title_numbers),
                ("NOUN SING", self.title_nouns_sing),
                ("NOUN PLUR", self.title_nouns_plur),
                ("ADJECTIVE", self.title_adjectives),
                ("FIRST NAME", self.title_first_names),
                ("LAST NAME", self.title_last_names),
            ]:
                v = (r.get(col) or "").replace("\xa0", " ").strip()
                if v:
                    target.append(v)

    def generate_title(
        self,
        rng: random.Random,
        genre: Optional[str] = None,
        series_or_movie: str = "Movie",
        existing_titles: Optional[set[str]] = None,
    ) -> str:
        """Generate a varied, cinematic Hollywood movie or TV title tailored to genre and medium."""
        used = existing_titles or set()
        for _ in range(12):
            candidate = self._generate_title_once(rng, genre=genre, series_or_movie=series_or_movie)
            if candidate and candidate not in used:
                return candidate
        return candidate

    def _generate_title_once(
        self,
        rng: random.Random,
        genre: Optional[str] = None,
        series_or_movie: str = "Movie",
    ) -> str:
        cities = [
            "Berlin", "Vienna", "Lisbon", "Marseille", "Prague", "Kyoto", "Havana",
            "Chicago", "Boston", "New Orleans", "Venice", "Tangier", "Reykjavik",
            "Zurich", "Naples", "Hong Kong", "Cairo", "Dublin", "Seattle", "Miami",
            "Palermo", "Monte Carlo", "Shanghai", "Istanbul", "Edinburgh", "Montreal",
        ]
        first = lambda: rng.choice(self.title_first_names) if self.title_first_names else "Claire"
        last = lambda: rng.choice(self.title_last_names) if self.title_last_names else "Vance"
        city = lambda: rng.choice(cities)

        # TV-specific prestige & network title patterns (~45% of TV shows)
        if series_or_movie == "TV" and rng.random() < 0.45:
            tv_places = [
                "Harbor", "Westside", "Beacon", "Redwood", "Pinecrest", "Silverlake",
                "Midtown", "Bayside", "Cedar", "Ashford", "Crestview", "Northgate",
                "Blackwater", "Fairview", "Oakridge", "Kingsbridge", "Mercy", "Sutton",
            ]
            tv_suffixes = [
                "Heights", "Station", "General", "Precinct", "Point", "Landing",
                "Park", "Crossing", "Avenue", "Harbor", "Square", "Hills", "Ward",
            ]
            tv_roles = [
                "The Fixer", "The Syndicate", "The Counsellor", "The Night Shift",
                "The Dispatch", "The Bureau", "The Watch", "The Insider",
                "The Heir", "The Partner", "The Ward", "The Verdict",
            ]
            tv_patterns = [
                lambda: f"{rng.choice(tv_places)} {rng.choice(tv_suffixes)}",
                lambda: f"The {last()} Dynasty",
                lambda: f"{last()} & {last()}",
                lambda: f"{city()} PD",
                lambda: f"Station {rng.randint(7, 99)}",
                lambda: f"{rng.choice(tv_places)} Medical",
                lambda: f"{rng.choice(tv_roles)}",
                lambda: f"Inside {rng.choice(tv_places)}",
                lambda: f"House of {last()}",
                lambda: f"The {city()} Files",
            ]
            return rng.choice(tv_patterns)()

        # Genre-specific cinematic title banks (~80% of titles)
        genre_banks: Dict[str, Tuple[List[str], List[str], List[str]]] = {
            "Action": (
                ["Iron", "Cold", "Black", "Red", "Silent", "Final", "Rogue", "Lethal", "Shadow", "Zero", "Broken", "Savage", "Apex", "Crimson", "Ghost"],
                ["Protocol", "Extraction", "Meridian", "Vanguard", "Reckoning", "Vendetta", "Horizon", "Velocity", "Impact", "Line", "Target", "Strike", "Vector", "Fury", "Directive"],
                ["No Mercy in {city}", "Zero Hour: {city}", "{adj} {noun}", "The {adj} {noun}", "{noun}: {city}", "Operation {adj} {noun}", "Deadman's {noun}", "{last}'s {noun}", "Code Name: {adj}", "Last Stand in {city}"],
            ),
            "Crime/Thriller": (
                ["Shattered", "Quiet", "Dark", "Cold", "Hollow", "Glass", "Bitter", "Buried", "Stolen", "Midnight", "Vanishing", "Crooked", "Second", "Unseen", "Pale"],
                ["Alibi", "Ledger", "Witness", "Confession", "Verdict", "Suspect", "Motive", "Ransom", "Evidence", "Syndicate", "Deception", "Shadow", "Informant", "Labyrinth", "Truth"],
                ["The {adj} {noun}", "{adj} {noun}", "The {last} {noun}", "No One Leaves {city}", "A {adj} {noun}", "Before the {noun}", "The {noun} of {city}", "Buried in {city}", "{first}'s {noun}", "Trust No {noun}"],
            ),
            "Sci-fi": (
                ["Orbital", "Neon", "Solar", "Quantum", "Cryo", "Astral", "Synthetic", "Deep", "Zero-G", "Binary", "Chrome", "Helios", "Eclipse", "Parallax", "Hyperion"],
                ["Drift", "Anomaly", "Singularity", "Horizon", "Protocol", "Signal", "Colony", "Genesis", "Continuum", "Vortex", "Archive", "Frontier", "Pulse", "Odyssey", "Vector"],
                ["The {adj} {noun}", "{adj} {noun}", "Project {adj}", "Beyond the {noun}", "Echoes of {adj}", "{noun} {year}", "The {year} {noun}", "Last {noun} to Mars", "Station {adj}", "Children of the {noun}"],
            ),
            "Horror": (
                ["Pale", "Hollow", "Wicked", "Rotting", "Whispering", "Cursed", "Bleak", "Silent", "Forsaken", "Crimson", "Dead", "Ashen", "Sunken", "Blighted", "Weeping"],
                ["Manor", "Candle", "Cellar", "Lullaby", "Harvest", "Mirror", "Chapel", "Orchard", "Shroud", "Coven", "Attic", "Hollow", "Omen", "Bell", "Lantern"],
                ["The {adj} {noun}", "Whispers at {last} {noun}", "Don't Open the {noun}", "The Seventh {noun}", "Night of the {adj} {noun}", "House on {last} Lane", "Beneath the {noun}", "It Lives in the {noun}", "The {noun} Below", "Ash & {noun}"],
            ),
            "Drama": (
                ["Quiet", "Glass", "Winter", "Distant", "Fading", "Golden", "Fragile", "Broken", "Last", "Paper", "Velvet", "Autumn", "Silver", "Still", "Heavy"],
                ["Orchard", "Season", "Harbor", "Promise", "Shore", "Memory", "Bridge", "Letter", "Reckoning", "Silence", "Inheritance", "Portrait", "Elegy", "Morning", "Grace"],
                ["The Weight of {noun}", "Letters from {city}", "A {adj} {noun}", "The {adj} {noun}", "Before the {noun} Falls", "The Last Ferry to {city}", "{noun} in {city}", "All the {adj} Things", "The {last} {noun}", "Where the {noun} Ends"],
            ),
            "Historical": (
                ["Imperial", "Gilded", "Sovereign", "Forgotten", "Crimson", "Iron", "Royal", "Fallen", "Sacred", "Crowned", "Noble", "Distant", "Obsidian", "Silver"],
                ["Crown", "Empire", "Dynasty", "Treaty", "Throne", "Chronicle", "Rebellion", "Banner", "Cathedral", "Voyage", "Siege", "Scepter", "Court", "Decree"],
                ["The {adj} {noun}", "{noun} of Salt", "The {last} {noun}", "Winter of the {noun}", "The {city} {noun}", "Fall of the {adj} {noun}", "A {noun} in {city}", "The King's {noun}", "Shadows of {city}"],
            ),
            "Comedy": (
                ["Accidentally", "Terribly", "Slightly", "Hopelessly", "Awkwardly", "Wildly", "Barely", "Unexpectedly", "Reluctantly", "Completely"],
                ["Famous", "Married", "Broke", "Employed", "Single", "Undercover", "Grounded", "Viral", "Neighbors", "Roommates", "Cousins", "In-Laws", "Tourists", "Runaways"],
                ["{adj} {noun}", "The Worst {noun} Ever", "Two Tickets to {city}", "Sunday in {city}", "How to Lose a {noun}", "Meet the {last}s", "{first}'s Big Mistake", "No Refunds in {city}", "My {adj} Weekend", "The {last} Family Disaster"],
            ),
            "Musical": (
                ["Midnight", "Velvet", "Electric", "Golden", "Starlight", "Neon", "Rhythm", "Silver", "Crimson", "Encore", "Broadway", "Satin"],
                ["Encore", "Overture", "Serenade", "Spotlight", "Cadence", "Harmony", "Rhapsody", "Ballad", "Chorus", "Melody", "Waltz", "Nocturne"],
                ["{adj} {noun}", "The {adj} {noun}", "Curtain Call in {city}", "Notes in {adj} Blue", "One More {noun}", "{noun} on 42nd", "Sing Me to {city}", "The Last {noun}", "{first}'s {noun}"],
            ),
            "Fantasy": (
                ["Cinder", "Clockwork", "Obsidian", "Sunken", "Astral", "Frost", "Ember", "Emerald", "Shadow", "Starlit", "Gilded", "Thorny", "Runic", "Ivory"],
                ["Citadel", "Crown", "Oath", "Blade", "Kingdom", "Labyrinth", "Spire", "Throne", "Grimoire", "Lantern", "Covenant", "Relic", "Warden", "Realm"],
                ["{noun} of {adj}s", "The {adj} {noun}", "The Mapmaker's {noun}", "Blade of the {adj} King", "Songs of the {adj} {noun}", "The {last} {noun}", "Beyond the {adj} Sea", "Heir to the {adj} {noun}", "The Seventh {noun}"],
            ),
            "Adventure": (
                ["Lost", "Hidden", "Golden", "Sunken", "Forbidden", "Wild", "Emerald", "Crimson", "Forgotten", "Secret", "Distant", "Ancient", "Uncharted"],
                ["Expedition", "Compass", "Isles", "Passage", "Treasure", "Frontier", "Canyon", "Horizon", "Voyage", "Relic", "Trail", "Summit", "Archipelago", "Atlas"],
                ["Voyage to the {adj} {noun}", "The {adj} {noun}", "Raiders of the {adj} {noun}", "Across the {adj} {noun}", "The {noun} of {city}", "Search for the {adj} {noun}", "{last}'s {noun}", "Beyond the {adj} {noun}"],
            ),
            "Western": (
                ["Dusty", "Red", "Iron", "Bitter", "Dry", "Lone", "Dead", "Pale", "Sunbaked", "Broken", "Black", "Silver", "Cold", "Blood"],
                ["Mesa", "Creek", "Canyon", "Brimstone", "Gallows", "Trail", "Outlaw", "Spur", "Ranch", "Marshal", "Gulch", "Crossing", "Frontier", "Saddle"],
                ["The Outlaw of {adj} {noun}", "High Noon at {adj} {noun}", "Dust & {noun}", "Six Miles to {adj} {noun}", "The {adj} {noun}", "{last}'s Revenge", "No Law in {adj} {noun}", "Ride to {adj} {noun}", "The Last {noun}"],
            ),
            "Animation": (
                ["Little", "Magic", "Cloud", "Starlight", "Bumble", "Paper", "Whistle", "Sunny", "Pocket", "Clockwork", "Tumble", "Moonbeam", "Spark", "Tiny"],
                ["Kingdom", "Express", "Inventors", "Voyage", "Meadow", "Dragon", "Bakery", "Balloon", "Explorers", "Forest", "Orchestra", "Island", "Comet", "Carousel"],
                ["The {adj} {noun}", "{first} and the {adj} {noun}", "Journey to {adj} {noun}", "The Secret of {adj} {noun}", "{adj} {noun} Express", "Tales from {adj} {noun}", "The Boy Who Built a {noun}", "{first}'s {adj} Adventure"],
            ),
        }

        if genre in genre_banks and rng.random() < 0.82:
            adjs, nouns, templates = genre_banks[genre]
            tpl = rng.choice(templates)
            title = tpl.format(
                adj=rng.choice(adjs),
                noun=rng.choice(nouns),
                city=city(),
                first=first(),
                last=last(),
                year=rng.choice([1984, 1999, 2036, 2049, 2077, 2084, 2099, 2140]),
            )
            return title.replace("  ", " ").strip()

        # Fallback (~18%): upgraded multi-word DB generator
        if not self.title_rules:
            return "Hollywood Dreams"
        multi_rules = [(r, w) for r, w in self.title_rules if "+" in r]
        pool = multi_rules if multi_rules else self.title_rules
        rules = [r[0] for r in pool]
        weights = [r[1] for r in pool]
        pattern = rng.choices(rules, weights=weights, k=1)[0]
        parts = [p.strip() for p in pattern.split("+")]

        def _replace_tokens(token: str) -> str:
            out = token
            replacements = [
                ("NOUN SING", lambda: rng.choice(self.title_nouns_sing) if self.title_nouns_sing else "Story"),
                ("NOUN_SING", lambda: rng.choice(self.title_nouns_sing) if self.title_nouns_sing else "Story"),
                ("NOUN PLUR", lambda: rng.choice(self.title_nouns_plur) if self.title_nouns_plur else "Stories"),
                ("NOUN_PLUR", lambda: rng.choice(self.title_nouns_plur) if self.title_nouns_plur else "Stories"),
                ("ADJECTIVE", lambda: rng.choice(self.title_adjectives) if self.title_adjectives else "Dark"),
                ("FIRST NAME", lambda: first()),
                ("FIRST_NAME", lambda: first()),
                ("LAST NAME", lambda: last()),
                ("LAST_NAME", lambda: last()),
                ("NUMBER", lambda: rng.choice(self.title_numbers) if self.title_numbers else "Seven"),
                ("DATUM", lambda: str(rng.choice([1984, 1999, 2029, 2049, 2099]))),
            ]
            for key, fn in replacements:
                while key in out.upper():
                    idx = out.upper().find(key)
                    out = out[:idx] + fn() + out[idx + len(key):]
            return out

        words = [_replace_tokens(p) for p in parts if p]
        return " ".join(words).replace("  ", " ").strip()

    def _build_role_pools(self) -> None:
        self.role_nouns = self.get_rows("RoleFonevGeneralRules")
        self.role_adjectives = [
            (r.get("Adjective") or "").strip()
            for r in self.get_rows("RoleAdjective_TortenelmiKorok")
            if (r.get("Adjective") or "").strip()
        ]
        # Map collective categories (Gyűjtőnév) to adjectives and attribute bonuses
        self.collective_tags: List[str] = []
        self.collective_attr_bonuses: Dict[str, List[str]] = {}
        for r in self.get_rows("Auditionpontozas_GYUJTOATTRIBONUS"):
            tag = (r.get("Gyűjtőnév") or "").strip()
            if not tag:
                continue
            self.collective_tags.append(tag)
            bonuses = []
            for k, v in r.items():
                if k not in ("ID", "Gyűjtőnév") and v:
                    bonuses.append(k)
            self.collective_attr_bonuses[tag] = bonuses

        self.special_skills: List[str] = [
            (r.get("Skill") or "").strip()
            for r in self.get_rows("SpecialSkillsNEW")
            if (r.get("Skill") or "").strip()
        ]

        self.personalities: List[Tuple[str, str]] = []
        for r in self.get_rows("PersonalityAttribsNEW"):
            p = (r.get("Personality") or "").strip()
            d = (r.get("DISC") or "I").strip()
            if p:
                self.personalities.append((p, d))

        self.personal_infos: List[str] = [
            (r.get("Personal Info") or "").strip()
            for r in self.get_rows("PersonalInfo1024")
            if (r.get("Personal Info") or "").strip()
        ]

    def _build_quote_table(self) -> None:
        self.quotes_by_role: Dict[str, Dict[str, Any]] = {}
        for r in self.get_rows("ActorQUOTES"):
            role = (r.get("Role") or "").strip()
            if role:
                self.quotes_by_role[role] = r

    def compute_actor_quotes(self, rng: random.Random, sex: str, fame_tier: str) -> Dict[str, int]:
        quotes: Dict[str, int] = {}
        for role_type in ["Lead", "Major Support", "Minor Support", "Guest Star", "Series Regular"]:
            row = self.quotes_by_role.get(role_type, {})
            if fame_tier == "A-lister":
                kmin = "A-lister Male Min" if sex == "Male" else "A lister female Min"
                kmax = "A-lister Male Max" if sex == "Male" else "A lister female Max"
            elif fame_tier == "Notable":
                kmin = "Notable Male min" if sex == "Male" else "Notable Female min"
                kmax = "Notable Male max" if sex == "Male" else "Notable Female max"
            elif fame_tier == "Average":
                kmin, kmax = "Average min", "Average max"
            elif fame_tier == "Relatively unknown":
                kmin, kmax = "Relatively Unknown min", "Relatively Unknown max"
            else:
                kmin, kmax = "Unknown min", "Unknown max"

            low = int(float(row.get(kmin) or 10000))
            high = int(float(row.get(kmax) or low * 2))
            val = rng.randint(min(low, high), max(low, high))
            # Round to nearest 500
            quotes[role_type] = max(1500, (val // 500) * 500)
        # Recurring TV arc sits cleanly between Guest Star and Series Regular
        rec_val = int((quotes["Guest Star"] * 0.55) + (quotes["Series Regular"] * 0.45))
        quotes["Recurring"] = max(2500, (rec_val // 500) * 500)
        return quotes

    def _build_audition_tables(self) -> None:
        # Genre -> list of important attributes from Auditionpontozas_GENREREQ
        self.genre_required_attrs: Dict[str, List[str]] = {}
        for r in self.get_rows("Auditionpontozas_GENREREQ"):
            attr_name = (r.get("Field1") or "").strip()
            if not attr_name:
                continue
            for k, v in r.items():
                if k not in ("ID", "Field1") and v == "x":
                    self.genre_required_attrs.setdefault(k, []).append(attr_name)

        # Look compatibility matrix (remapped to clean plain-English Hollywood casting terms)
        look_remap = {
            "Beautiful": "Striking",
            "Pretty": "Attractive",
            "Ruggedly handsome": "Rugged",
            "Boyishly handsome": "Clean-Cut",
            "Average": "Everyday",
            "Unconventional": "Distinctive",
        }
        self.look_scores: Dict[str, Dict[str, float]] = {}
        for r in self.get_rows("Auditionpontozas_KINEZET_MALE_FEMALE"):
            req_raw = (r.get("Required") or "").strip()
            req = look_remap.get(req_raw, req_raw)
            if req:
                self.look_scores[req] = {
                    look_remap.get(k, k): float(v or 0.0)
                    for k, v in r.items()
                    if k not in ("ID", "Required") and isinstance(v, (int, float))
                }

        # Bodytype compatibility matrix
        self.body_scores: Dict[str, Dict[str, float]] = {}
        for r in self.get_rows("Auditionpontozas_BODYTYPE_MALE_FEMALE"):
            req = (r.get("Required") or "").strip()
            if req:
                self.body_scores[req] = {
                    k: float(v or 0.0) for k, v in r.items() if k not in ("ID", "Required") and isinstance(v, (int, float))
                }

        # Height compatibility matrix
        self.height_scores: Dict[str, Dict[str, float]] = {}
        for r in self.get_rows("Auditionpontozas_HEIGHT_MALE_FEMALE"):
            req = (r.get("Required") or "").strip()
            if req:
                self.height_scores[req] = {
                    k.replace("Medium-Height", "Medium").replace("Very Tall", "Very tall"): float(v or 0.0)
                    for k, v in r.items()
                    if k not in ("ID", "Required") and isinstance(v, (int, float))
                }
