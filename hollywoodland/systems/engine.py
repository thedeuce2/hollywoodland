from __future__ import annotations
from datetime import date, timedelta
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from hollywoodland.models.entities import (
    CORE_ATTRIBUTES,
    Actor,
    Agency,
    AuditionCandidate,
    AwardRecord,
    ContractOffer,
    DirectorProducerShowrunner,
    FilmOrSeries,
    InboxMessage,
    LedgerEntry,
    MessageButton,
    RoleSlot,
    ScoutOrConsultant,
    SubmissionRecord,
)
from hollywoodland.systems.db_loader import GameDatabase
from hollywoodland.systems.roster_loader import auto_fill_actor_attributes, load_roster_pack


AGE_RANGES = [
    ("Child (8-12)", 8, 12),
    ("Teen (13-17)", 13, 17),
    ("Late teen-early 20's", 18, 24),
    ("Mid 20's-early 30's", 24, 34),
    ("Mid 30's-early 40's", 34, 44),
    ("Mid 40's-early 50's", 44, 54),
    ("Mid 50's-early 60's", 54, 64),
    ("Mid 60's-early 70's", 64, 74),
    ("Mid 70's-early 80's", 74, 83),
    ("Mid 80's-", 80, 99),
]

GENRES = [
    "Animation",
    "Historical",
    "Musical",
    "Western",
    "Crime/Thriller",
    "Drama",
    "Horror",
    "Sci-fi",
    "Fantasy",
    "Comedy",
    "Action",
    "Adventure",
]


class HollywoodlandEngine:
    """Core daily simulation engine for Hollywoodland."""

    def __init__(
        self,
        player_name: str = "John Doe",
        agency_name: str = "Hollywoodland Talent",
        initial_budget: float = 50000.0,
        seed: Optional[int] = None,
        roster_pack: Optional[str] = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.db = GameDatabase()
        self.active_roster_name: str = "Default (Fictional)"
        self.custom_movie_studios: List[Dict[str, Any]] = []
        self.custom_tv_broadcast: List[Dict[str, Any]] = []
        self.custom_tv_cable: List[Dict[str, Any]] = []
        self.queued_roster_movies: List[Dict[str, Any]] = []
        self.queued_roster_tv: List[Dict[str, Any]] = []
        self._roster_data: Optional[Dict[str, Any]] = load_roster_pack(roster_pack) if roster_pack else None
        start_dt = date(2018, 8, 13)
        if self._roster_data:
            manifest = self._roster_data["manifest"]
            self.active_roster_name = manifest.get("name") or self._roster_data["id"]
            if manifest.get("start_year"):
                try:
                    start_dt = date(int(manifest["start_year"]), 1, 5)
                except Exception:
                    pass
            for st in self._roster_data.get("studios", []):
                kind = (st.get("kind") or "Movie").strip()
                if kind == "Movie":
                    self.custom_movie_studios.append({"Studio": st.get("name", "Studio"), "Type": st.get("tier", "B")})
                elif kind == "Broadcast":
                    self.custom_tv_broadcast.append({"Channel": st.get("name", "Network"), "Type": "Broadcast"})
                else:
                    self.custom_tv_cable.append({"Channel": st.get("name", "Streaming"), "Type": "Cable"})
            for pr in self._roster_data.get("projects", []):
                if (pr.get("series_or_movie") or "Movie") == "TV":
                    self.queued_roster_tv.append(pr)
                else:
                    self.queued_roster_movies.append(pr)
        self.current_date: date = start_dt
        self.next_msg_id: int = 1
        self.next_film_id: int = 1
        self.next_actor_id: int = 1
        self._roster_pack_path: str = self._roster_data["path"] if self._roster_data else ""
        self.upcoming_debut_actors: List[Dict[str, Any]] = []

        self.agencies: Dict[int, Agency] = {}
        self.actors: Dict[int, Actor] = {}
        self.creatives: Dict[int, DirectorProducerShowrunner] = {}
        self.films: Dict[int, FilmOrSeries] = {}
        self.submissions: List[SubmissionRecord] = []
        self.messages: List[InboxMessage] = []
        self.ledger: List[LedgerEntry] = []
        self.awards: List[AwardRecord] = []
        self.scouts: List[ScoutOrConsultant] = []
        self.consultants: List[ScoutOrConsultant] = []
        self.pending_tasks: List[Dict[str, Any]] = []
        self.evergreen_backend_deals: List[Dict[str, Any]] = []
        self.fired_events: set[str] = set()
        self.last_random_event_date: date = start_dt
        self.events_by_id: Dict[str, Dict[str, Any]] = {
            e["id"].replace("\\", "/").lower(): e for e in self.db.events
        }
        self.child_event_ids: set[str] = set()
        for e in self.db.events:
            if e.get("execute", {}).get("time") == "parentTriggers":
                self.child_event_ids.add(e["id"].replace("\\", "/").lower())
            for a in e.get("actions", []):
                if a.get("type") == "triggerEvent":
                    t = (a.get("attrib", {}).get("event") or "").replace("\\", "/").strip().lower()
                    if t:
                        self.child_event_ids.add(t)
                elif a.get("type") == "sendMessage":
                    for b in a.get("buttons", []):
                        t = (b.get("event") or "").replace("\\", "/").strip().lower()
                        if t:
                            self.child_event_ids.add(t)

        self._init_agencies(player_name, agency_name, initial_budget)
        self._init_scouts_and_consultants()
        if self._roster_data and self._roster_data.get("creatives"):
            self._init_creatives_from_roster(self._roster_data["creatives"])
        else:
            self._init_creatives()
        if self._roster_data and self._roster_data.get("actors"):
            self._init_actors_from_roster(self._roster_data["actors"], self._roster_data["path"])
        else:
            self._init_actors(count=280)
        self._init_creative_relationships()
        self._init_projects(movie_count=36, tv_count=18)
        self._update_rankings()
        self._send_welcome_emails()

    @property
    def player_agency(self) -> Agency:
        return self.agencies[0]

    @property
    def date_str(self) -> str:
        return self.current_date.strftime("%Y-%m-%d")

    @property
    def pretty_date(self) -> str:
        return self.current_date.strftime("%d %b %Y")

    def _init_agencies(self, player_name: str, agency_name: str, initial_budget: float) -> None:
        # Agency 0 is the player's agency
        self.agencies[0] = Agency(
            id=0,
            name=agency_name,
            owner_name=player_name,
            ours=True,
            budget=initial_budget,
            reputation="Minor",
            reputation_score=12.0,
            max_actors=30,
            ranking=39,
            knowledge_skill=28,
            personal_skill=28,
            negotiation_skill=28,
            logo_file="cat.png",
        )

        # Load rival AI agencies from AIAgencies table
        agency_id = 1
        rows = self.db.get_rows("AIAgencies")
        seen = set()
        for tier_col, rep_tier, base_rep, max_col in [
            ("Top 5", "Major", 88.0, "Max size"),
            ("Top 6-20", "Medium", 55.0, "Maxi size"),
            ("Bottom", "Minor", 22.0, "Maxim size"),
        ]:
            for r in rows:
                aname = (r.get(tier_col) or "").strip()
                if not aname or aname in seen:
                    continue
                seen.add(aname)
                max_sz = int(float(r.get(max_col) or 50))
                self.agencies[agency_id] = Agency(
                    id=agency_id,
                    name=aname,
                    owner_name=self.db.sample_name(self.rng, self.rng.choice(["Male", "Female"]), "White"),
                    ours=False,
                    budget=500000.0 if rep_tier == "Major" else (180000.0 if rep_tier == "Medium" else 45000.0),
                    reputation=rep_tier,
                    reputation_score=base_rep + self.rng.uniform(-6.0, 6.0),
                    max_actors=max_sz,
                    ranking=agency_id,
                    knowledge_skill=self.rng.randint(45, 92),
                    personal_skill=self.rng.randint(45, 92),
                    negotiation_skill=self.rng.randint(45, 92),
                )
                agency_id += 1

    def _init_scouts_and_consultants(self) -> None:
        self.scouts = [
            ScoutOrConsultant(1, "Arthur Pendelton (VIP Talent Scout)", "Scout", "Well-known", 300, 1, 2, 92, 90, 95, 90),
            ScoutOrConsultant(2, "Brenda Vance (Mid-Tier Scout)", "Scout", "Average", 150, 2, 4, 74, 72, 75, 70),
            ScoutOrConsultant(3, "Chuck 'The Intern' (Bargain Scout)", "Scout", "Unknown", 50, 4, 7, 55, 52, 50, 50),
        ]
        self.consultants = [
            ScoutOrConsultant(1, "Dr. Evelyn Sterling (A-List Script Doctor)", "Consultant", "Well-known", 400, 1, 1, 95, 94, 95, 94),
            ScoutOrConsultant(2, "Marcus Holloway (Story Analyst)", "Consultant", "Average", 200, 1, 2, 76, 75, 78, 74),
            ScoutOrConsultant(3, "lonelyscriptreader99 (Freelance Reader)", "Consultant", "Unknown", 75, 2, 4, 58, 55, 55, 55),
        ]

    def _init_creatives(self) -> None:
        cid = 1
        for kind, count in [("Director", 45), ("Producer", 45), ("Showrunner", 30)]:
            for _ in range(count):
                sex = self.rng.choices(["Male", "Female"], weights=[0.7, 0.3])[0]
                eth = self.rng.choices(
                    ["White", "Black", "Hispanic", "Asian", "Indian", "Arabic"],
                    weights=[65, 12, 10, 7, 3, 3],
                )[0]
                nat = self.rng.choices(
                    ["USA", "England", "Canada", "Australia", "Scotland", "Ireland", "New Zealand"],
                    weights=[68, 12, 8, 5, 3, 2, 2],
                )[0]
                fame = self.rng.choices(
                    ["Unknown", "Average", "Well-known", "Legend"],
                    weights=[25, 45, 22, 8],
                )[0]
                pers, disc = self.rng.choice(self.db.personalities or [("Creative", "I")])
                base_skill = {"Unknown": 42, "Average": 60, "Well-known": 76, "Legend": 90}[fame]
                self.creatives[cid] = DirectorProducerShowrunner(
                    id=cid,
                    name=self.db.sample_name(self.rng, sex, eth),
                    role_kind=kind,
                    sex=sex,
                    age=self.rng.randint(29, 74),
                    nationality=nat,
                    fame=fame,
                    personality=pers,
                    disc=disc,
                    genre_specialty=self.rng.choice(GENRES),
                    knowledge_skill=min(100, max(20, base_skill + self.rng.randint(-12, 12))),
                    personal_skill=min(100, max(20, base_skill + self.rng.randint(-15, 15))),
                    negotiation_skill=min(100, max(20, base_skill + self.rng.randint(-12, 12))),
                    num_movies=self.rng.randint(1, 25) if kind != "Showrunner" else 0,
                    num_series=self.rng.randint(1, 12) if kind == "Showrunner" else 0,
                    total_gross_revenue=self.rng.randint(5, 950) * 1_000_000 if kind != "Showrunner" else 0,
                    highest_review=self.rng.randint(68, 98),
                    lowest_review=self.rng.randint(14, 55),
                )
                cid += 1

    def _init_actors(self, count: int = 280) -> None:
        major_agencies = [a.id for a in self.agencies.values() if not a.ours and a.reputation == "Major"]
        med_agencies = [a.id for a in self.agencies.values() if not a.ours and a.reputation == "Medium"]
        minor_agencies = [a.id for a in self.agencies.values() if not a.ours and a.reputation == "Minor"]

        for aid in range(1, count + 1):
            sex = self.rng.choice(["Male", "Female"])
            eth = self.rng.choices(
                ["White", "Black", "Hispanic", "Asian", "Indian", "Arabic", "Native American"],
                weights=[62, 14, 11, 6, 3, 2, 2],
            )[0]
            nat = self.rng.choices(
                ["USA", "England", "Canada", "Australia", "Scotland", "Ireland", "Wales", "New Zealand"],
                weights=[68, 11, 8, 5, 3, 2, 1, 2],
            )[0]
            age = self.rng.choices(
                [
                    self.rng.randint(8, 12),
                    self.rng.randint(13, 17),
                    self.rng.randint(18, 25),
                    self.rng.randint(26, 36),
                    self.rng.randint(37, 48),
                    self.rng.randint(49, 64),
                    self.rng.randint(65, 82),
                ],
                weights=[4, 8, 22, 30, 19, 12, 5],
            )[0]
            if age <= 12:
                height_cat = self.rng.choice(["Very short", "Short"])
                base_h = self.rng.randint(128, 154)
            elif age <= 17:
                height_cat = self.rng.choices(["Short", "Medium", "Tall"], weights=[35, 50, 15])[0]
                base_h = self.rng.randint(154, 176)
            else:
                height_cat = self.rng.choices(
                    ["Very short", "Short", "Medium", "Tall", "Very tall"],
                    weights=[8, 20, 44, 20, 8],
                )[0]
                base_h = {"Very short": 156, "Short": 165, "Medium": 174, "Tall": 183, "Very tall": 193}[height_cat]
            if sex == "Female":
                base_h -= 9
            height_cm = base_h + self.rng.randint(-3, 3)

            if sex == "Male":
                bodytype = self.rng.choices(
                    ["Slim", "Average", "Athletic", "Muscular", "Chunky", "Overweight"],
                    weights=[16, 32, 24, 14, 8, 6],
                )[0]
                look = self.rng.choices(
                    ["Everyday", "Distinctive", "Clean-Cut", "Rugged"],
                    weights=[34, 22, 22, 22],
                )[0]
            else:
                bodytype = self.rng.choices(
                    ["Slim", "Average", "Curvy", "Athletic", "Muscular", "Overweight"],
                    weights=[26, 30, 20, 14, 4, 6],
                )[0]
                look = self.rng.choices(
                    ["Striking", "Attractive", "Everyday", "Distinctive"],
                    weights=[22, 32, 28, 18],
                )[0]

            pers, disc = self.rng.choice(self.db.personalities or [("Passionate", "I")])

            # Fame distribution: plenty of Unknown/Relatively unknown free agents so the player can sign clients immediately
            fame_tier = self.rng.choices(
                ["Unknown", "Relatively unknown", "Average", "Notable", "A-lister"],
                weights=[35, 28, 19, 11, 7],
            )[0]
            fame_score = {
                "Unknown": self.rng.uniform(1.0, 14.0),
                "Relatively unknown": self.rng.uniform(16.0, 95.0),
                "Average": self.rng.uniform(105.0, 340.0),
                "Notable": self.rng.uniform(360.0, 680.0),
                "A-lister": self.rng.uniform(710.0, 995.0),
            }[fame_tier]

            skill_floor = {
                "Unknown": 28,
                "Relatively unknown": 38,
                "Average": 48,
                "Notable": 60,
                "A-lister": 72,
            }[fame_tier]

            attrs: Dict[str, int] = {}
            known: Dict[str, bool] = {}
            ranges: Dict[str, int] = {}
            youth_scale = min(1.0, 0.56 + max(0, age - 10) * 0.028) if age < 26 else 1.0
            for attr in CORE_ATTRIBUTES:
                peak_v = min(99, max(18, skill_floor + self.rng.randint(-14, 24)))
                v = max(12, min(99, int(round(peak_v * youth_scale))))
                attrs[attr] = v
                # 3 random attributes start partially known, rest require scouting
                known[attr] = self.rng.random() < 0.25
                ranges[attr] = max(5, min(85, v - self.rng.randint(5, 18)))

            avg_curr = sum(attrs.values()) / max(1, len(attrs))
            pot_bonus = self.rng.randint(6, 26) if age < 25 else self.rng.randint(0, 8)
            potential_rating = max(42, min(99, int(round((avg_curr / max(0.55, youth_scale)) + pot_bonus * 0.45))))

            # Assign agency or Free Agent status
            agency_id: Optional[int] = None
            if fame_tier == "A-lister":
                if self.rng.random() < 0.90 and major_agencies:
                    agency_id = self.rng.choice(major_agencies)
            elif fame_tier == "Notable":
                if self.rng.random() < 0.80 and (major_agencies or med_agencies):
                    agency_id = self.rng.choice(major_agencies + med_agencies)
            elif fame_tier == "Average":
                if self.rng.random() < 0.60 and (med_agencies or minor_agencies):
                    agency_id = self.rng.choice(med_agencies + minor_agencies)
            elif fame_tier == "Relatively unknown":
                if self.rng.random() < 0.35 and minor_agencies:
                    agency_id = self.rng.choice(minor_agencies)
            else:
                if self.rng.random() < 0.15 and minor_agencies:
                    agency_id = self.rng.choice(minor_agencies)

            num_spec = self.rng.randint(1, 5)
            spec_skills = self.rng.sample(self.db.special_skills, k=min(num_spec, len(self.db.special_skills))) if self.db.special_skills else ["Standard American accent"]

            p_infos: List[str] = []
            if self.db.personal_infos and self.rng.random() < 0.45:
                p_infos.append(self.rng.choice(self.db.personal_infos))

            quotes = self.db.compute_actor_quotes(self.rng, sex, fame_tier)

            contract = None
            if agency_id is not None:
                exp = self.current_date + timedelta(days=self.rng.randint(45, 360))
                contract = ContractOffer(
                    contract_start=self.date_str,
                    contract_end=exp.strftime("%Y-%m-%d"),
                    commission=10,
                    num_months=12,
                )

            actor = Actor(
                id=aid,
                name=self.db.sample_name(self.rng, sex, eth),
                sex=sex,
                age=age,
                nationality=nat,
                ethnicity=eth,
                birthplace=self.db.sample_birthplace(self.rng, nat),
                height_cm=height_cm,
                height_category=height_cat,
                bodytype=bodytype,
                look=look,
                personality=pers,
                disc=disc,
                fame_score=round(fame_score, 1),
                fame_tier=fame_tier,
                morale_score=float(self.rng.randint(52, 88)),
                condition_score=float(self.rng.randint(68, 98)),
                attributes=attrs,
                known_attributes=known,
                attrib_range_mins=ranges,
                quotes=quotes,
                special_skills=spec_skills,
                personal_info=p_infos,
                agency_id=agency_id,
                contract=contract,
                num_awards=self.rng.randint(1, 4) if fame_tier == "A-lister" else (1 if fame_tier == "Notable" and self.rng.random() < 0.4 else 0),
                portrait_seed=aid * 7919,
                potential_rating=potential_rating,
            )
            self.actors[aid] = actor

    def _init_creatives_from_roster(self, raw_creatives: List[Dict[str, Any]]) -> None:
        cid = 1
        for rec in raw_creatives:
            kind = rec.get("role_kind") or "Director"
            if kind not in ("Director", "Producer", "Showrunner"):
                kind = "Director"
            fame = rec.get("fame") or "Well-known"
            base_skill = {"Unknown": 45, "Average": 62, "Well-known": 78, "Legend": 91}.get(fame, 70)
            pers, disc = self.rng.choice(self.db.personalities or [("Creative", "I")])
            self.creatives[cid] = DirectorProducerShowrunner(
                id=cid,
                name=(rec.get("name") or f"Creative {cid}").strip(),
                role_kind=kind,
                sex=rec.get("sex") if rec.get("sex") in ("Male", "Female") else "Male",
                age=int(rec.get("age") or self.rng.randint(32, 68)),
                nationality=(rec.get("nationality") or "USA").strip(),
                fame=fame,
                personality=rec.get("personality") or pers,
                disc=rec.get("disc") or disc,
                genre_specialty=rec.get("genre_specialty") or self.rng.choice(GENRES),
                knowledge_skill=int(rec.get("knowledge_skill") or min(100, max(25, base_skill + self.rng.randint(-10, 10)))),
                personal_skill=int(rec.get("personal_skill") or min(100, max(25, base_skill + self.rng.randint(-12, 12)))),
                negotiation_skill=int(rec.get("negotiation_skill") or min(100, max(25, base_skill + self.rng.randint(-10, 10)))),
                num_movies=int(rec.get("num_movies") or self.rng.randint(2, 22)),
                num_series=int(rec.get("num_series") or self.rng.randint(0, 8)),
                total_gross_revenue=int(rec.get("total_gross_revenue") or self.rng.randint(15, 900) * 1_000_000),
                highest_review=self.rng.randint(72, 98),
                lowest_review=self.rng.randint(22, 60),
            )
            cid += 1

        # Guarantee at least 8 of each creative kind exist so project generation never runs dry
        for kind in ("Director", "Producer", "Showrunner"):
            existing_k = sum(1 for c in self.creatives.values() if c.role_kind == kind)
            for _ in range(max(0, 8 - existing_k)):
                sex = self.rng.choices(["Male", "Female"], weights=[0.65, 0.35])[0]
                pers, disc = self.rng.choice(self.db.personalities or [("Creative", "I")])
                self.creatives[cid] = DirectorProducerShowrunner(
                    id=cid,
                    name=self.db.sample_name(self.rng, sex, "White"),
                    role_kind=kind,
                    sex=sex,
                    age=self.rng.randint(32, 65),
                    nationality="USA",
                    fame=self.rng.choice(["Average", "Well-known"]),
                    personality=pers,
                    disc=disc,
                    genre_specialty=self.rng.choice(GENRES),
                    knowledge_skill=self.rng.randint(52, 82),
                    personal_skill=self.rng.randint(52, 82),
                    negotiation_skill=self.rng.randint(52, 82),
                )
                cid += 1

    @staticmethod
    def _compute_actor_debut_year(rec: Dict[str, Any]) -> int:
        if rec.get("debut_year"):
            try:
                return int(rec["debut_year"])
            except Exception:
                pass
        bday = (rec.get("birthday") or "").strip()
        if len(bday) >= 4 and bday[:4].isdigit():
            # Allow youth/teen actors to enter the talent pool starting at age 12
            return int(bday[:4]) + 12
        return 0

    def _spawn_actor_from_roster_record(
        self,
        raw: Dict[str, Any],
        pack_path: str,
        is_new_debut: bool = False,
    ) -> Actor:
        major_agencies = [a.id for a in self.agencies.values() if not a.ours and a.reputation == "Major"]
        med_agencies = [a.id for a in self.agencies.values() if not a.ours and a.reputation == "Medium"]
        minor_agencies = [a.id for a in self.agencies.values() if not a.ours and a.reputation == "Minor"]

        rec = auto_fill_actor_attributes(dict(raw), self.rng)
        sex = rec.get("sex") if rec.get("sex") in ("Male", "Female") else "Male"
        potential_rating = max(42, min(99, int(rec.get("potential_rating") or 65)))

        bday = (rec.get("birthday") or "").strip()
        if len(bday) >= 4 and bday[:4].isdigit():
            computed_age = max(8, min(88, self.current_date.year - int(bday[:4])))
        else:
            computed_age = max(8, min(88, int(rec.get("age") or 32)))

        # Young actors start raw and develop toward their real-world Potential ceiling over ages 8-26!
        youth_scale = min(1.0, 0.56 + max(0, computed_age - 10) * 0.028) if computed_age < 26 else 1.0
        raw_attrs = dict(rec.get("attributes") or {})
        attrs = {
            k: max(12, min(99, int(round(raw_attrs.get(k, 50) * youth_scale))))
            for k in CORE_ATTRIBUTES
        }
        known_attrs = {k: False for k in CORE_ATTRIBUTES}
        range_mins = {k: max(1, min(80, attrs.get(k, 50) - self.rng.randint(4, 15))) for k in CORE_ATTRIBUTES}

        if is_new_debut:
            # Newly debuting prospects enter as Unknown Free Agents ready to be discovered & signed!
            fame_tier = "Unknown"
            fame_score = round(self.rng.uniform(6.0, 16.5), 1)
            agency_id: Optional[int] = None
        else:
            fame_tier = rec.get("fame_tier") or "Average"
            fame_score = float(rec.get("fame_score") or 40.0)
            agency_id = None
            if fame_tier == "A-lister" and self.rng.random() < 0.78 and major_agencies:
                agency_id = self.rng.choice(major_agencies)
            elif fame_tier == "Notable" and self.rng.random() < 0.62 and (major_agencies or med_agencies):
                agency_id = self.rng.choice(major_agencies + med_agencies)
            elif fame_tier == "Average" and self.rng.random() < 0.40 and (med_agencies or minor_agencies):
                agency_id = self.rng.choice(med_agencies + minor_agencies)
            elif fame_tier in ("Relatively unknown", "Unknown") and self.rng.random() < 0.15 and minor_agencies:
                agency_id = self.rng.choice(minor_agencies)

        portrait_rel = (rec.get("portrait_file") or "").strip()
        portrait_abs = os.path.join(pack_path, portrait_rel) if portrait_rel else ""
        if portrait_abs and not os.path.isfile(portrait_abs):
            portrait_abs = ""

        aid = self.next_actor_id
        self.next_actor_id += 1
        actor = Actor(
            id=aid,
            name=(rec.get("name") or f"Actor {aid}").strip(),
            sex=sex,
            age=computed_age,
            nationality=(rec.get("nationality") or "USA").strip(),
            ethnicity=(rec.get("ethnicity") or "White").strip(),
            birthplace=(rec.get("birthplace") or "Los Angeles, USA").strip(),
            height_cm=int(rec.get("height_cm") or (180 if sex == "Male" else 166)),
            height_category=rec.get("height_category") or "Medium",
            bodytype=rec.get("bodytype") or "Average",
            look=rec.get("look") or "Average",
            personality=rec.get("personality") or "Charismatic",
            disc=rec.get("disc") or "I",
            fame_score=fame_score,
            fame_tier=fame_tier,
            morale_score=self.rng.uniform(58.0, 86.0),
            condition_score=self.rng.uniform(74.0, 96.0),
            attributes=attrs,
            known_attributes=known_attrs,
            attrib_range_mins=range_mins,
            quotes=self.db.compute_actor_quotes(self.rng, sex, fame_tier),
            special_skills=list(rec.get("special_skills") or []),
            personal_info=list(rec.get("personal_info") or []),
            agency_id=agency_id,
            portrait_seed=aid * 97 + self.rng.randint(1, 999),
            portrait_path=portrait_abs,
            potential_rating=potential_rating,
        )
        self.actors[aid] = actor
        return actor

    def _init_actors_from_roster(self, raw_actors: List[Dict[str, Any]], pack_path: str) -> None:
        self._roster_pack_path = pack_path
        self.upcoming_debut_actors = []
        start_yr = self.current_date.year

        for raw in raw_actors:
            debut_yr = self._compute_actor_debut_year(raw)
            if debut_yr > start_yr:
                entry = dict(raw)
                entry["_debut_year"] = debut_yr
                self.upcoming_debut_actors.append(entry)
            else:
                self._spawn_actor_from_roster_record(raw, pack_path, is_new_debut=False)

        self.upcoming_debut_actors.sort(key=lambda r: (int(r.get("_debut_year", 9999)), (r.get("name") or "")))

    def _apply_annual_progression(self, actor: Actor) -> None:
        """Apply HLM-style annual attribute development (ages 8-27), prime refinement (28-47), and veteran decline (48+)."""
        pot = actor.potential_rating
        age = actor.age
        comm = actor.attributes.get("Commitment", 50)
        intel = actor.attributes.get("Intelligence", 50)
        work_bonus = 1.25 if actor.this_year_all_roles > 0 else 0.85
        dev_factor = (0.75 + ((comm + intel) / 400.0)) * work_bonus

        craft_skills = ("Characterization", "Vocal Expression", "Facial Expression", "Intelligence", "Professionalism")
        phys_skills = ("Physical Expression", "Stamina")

        if age <= 27:
            # Growth phase: climb toward Potential ceiling
            for attr in CORE_ATTRIBUTES:
                cur = actor.attributes.get(attr, 50)
                headroom = pot - cur
                if headroom > 0:
                    step = max(1, int(round(min(6.0, headroom * 0.18 * dev_factor + self.rng.uniform(0.0, 1.5)))))
                    actor.attributes[attr] = min(99, min(pot + 3, cur + step))
        elif age <= 47:
            # Prime phase: subtle craft growth if still below potential and working
            if actor.this_year_all_roles > 0 or self.rng.random() < 0.35:
                for attr in self.rng.sample(list(craft_skills), k=2):
                    cur = actor.attributes.get(attr, 50)
                    if cur < pot:
                        actor.attributes[attr] = min(99, cur + self.rng.randint(1, 2))
        else:
            # Veteran phase: physical & stamina dip, while craft stays sharp
            drop_max = 3 if age >= 62 else 2
            for attr in phys_skills:
                cur = actor.attributes.get(attr, 50)
                actor.attributes[attr] = max(15, cur - self.rng.randint(1, drop_max))
            if age <= 60 and self.rng.random() < 0.30:
                attr = self.rng.choice(["Characterization", "Vocal Expression", "Intelligence"])
                cur = actor.attributes.get(attr, 50)
                if cur < pot:
                    actor.attributes[attr] = min(99, cur + 1)

    def _process_new_year_aging_and_debuts(self) -> None:
        """On Jan 1 each year, age active talent by +1, progress attributes toward Potential, and debut historical prospects."""
        for actor in self.actors.values():
            actor.age = min(95, actor.age + 1)
            self._apply_annual_progression(actor)
            actor.this_year_income = 0
            actor.this_year_all_roles = 0
            actor.this_year_major_roles = 0
        for creative in self.creatives.values():
            creative.age = min(95, creative.age + 1)

        if not self.upcoming_debut_actors:
            return

        cur_yr = self.current_date.year
        debuting: List[Dict[str, Any]] = []
        still_waiting: List[Dict[str, Any]] = []
        for rec in self.upcoming_debut_actors:
            if int(rec.get("_debut_year", 9999)) <= cur_yr:
                debuting.append(rec)
            else:
                still_waiting.append(rec)
        self.upcoming_debut_actors = still_waiting

        if debuting:
            spawned_names: List[str] = []
            for rec in debuting:
                a = self._spawn_actor_from_roster_record(rec, self._roster_pack_path, is_new_debut=True)
                spawned_names.append(f"{a.name} ({a.sex}, {a.age}y)")
            self._update_rankings()
            preview = "\n".join(f" - {n}" for n in spawned_names[:18])
            extra = f"\n...and {len(spawned_names) - 18} more!" if len(spawned_names) > 18 else ""
            self.add_message(
                title=f"Class of {cur_yr}: {len(spawned_names)} New Actors Enter Hollywood!",
                content=(
                    f"A fresh wave of {len(spawned_names)} young actors has entered the "
                    f"Hollywoodland Talent Service as Free Agents for {cur_yr}:\n\n"
                    f"{preview}{extra}\n\n"
                    "Scout and sign promising prospects early before rival agencies lock them up!"
                ),
                category="general",
                severity="Important",
                sender_name="Hollywoodland Talent Wire",
            )

    def _init_creative_relationships(self) -> None:
        all_actors = list(self.actors.values())
        studios = [
            (r.get("Studio") or "").strip()
            for r in self.db.get_rows("MovieNumberofMoviesGenres")
            if (r.get("Studio") or "").strip()
        ] or ["Ocean Pictures", "Galaxy Studios", "Streamline Pictures"]
        for c in self.creatives.values():
            if c.fame in ("Well-known", "Legend") and self.rng.random() < 0.45:
                c.first_look_studio = self.rng.choice(studios)
            sample = self.rng.sample(all_actors, k=min(8, len(all_actors)))
            c.liked_actor_ids = [a.id for a in sample[:4]]
            c.disliked_actor_ids = [a.id for a in sample[4:7]]

    def _init_projects(self, movie_count: int = 36, tv_count: int = 18) -> None:
        for _ in range(movie_count):
            self.generate_project("Movie")
        for _ in range(tv_count):
            self.generate_project("TV")

    def _age_to_bracket(self, age: int) -> str:
        for label, low, high in AGE_RANGES:
            if low <= age <= high:
                return label
        return "Mid 20's-early 30's"

    def _compute_role_desired_fame(
        self,
        series_or_movie: str,
        tier: str,
        budget: int,
        role_type: str,
    ) -> int:
        """Compute studio's target Fame (0-100) for a role based on budget, studio tier, and role billing."""
        if series_or_movie == "Movie":
            if tier == "A":
                if role_type == "Lead":
                    base = self.rng.randint(70, 92) if budget >= 90_000_000 else self.rng.randint(58, 84)
                elif role_type == "Major Support":
                    base = self.rng.randint(46, 72)
                else:
                    base = self.rng.randint(15, 42)
            elif tier == "B":
                if role_type == "Lead":
                    base = self.rng.randint(44, 72)
                elif role_type == "Major Support":
                    base = self.rng.randint(28, 54)
                else:
                    base = self.rng.randint(8, 32)
            else:
                if role_type == "Lead":
                    base = self.rng.randint(16, 46)
                elif role_type == "Major Support":
                    base = self.rng.randint(8, 30)
                else:
                    base = self.rng.randint(0, 20)
        else:
            if role_type == "Series Regular":
                base = self.rng.randint(36, 72) if tier == "Cable" else self.rng.randint(32, 64)
            elif role_type == "Recurring":
                base = self.rng.randint(18, 48)
            else:
                base = self.rng.randint(5, 32)
        return max(0, min(98, base))

    def _compute_role_filming_window(
        self,
        role_type: str,
        film_start: date,
        film_end: date,
    ) -> Tuple[str, str]:
        """Compute realistic per-role shoot window (Guest Stars shoot ~1 week, Recurring ~2-4 weeks, Leads/Regulars full shoot)."""
        if role_type == "Guest Star":
            r_end = min(film_end, film_start + timedelta(days=self.rng.randint(5, 9)))
        elif role_type == "Recurring":
            r_end = min(film_end, film_start + timedelta(days=self.rng.randint(14, 28)))
        elif role_type == "Minor Support":
            r_end = min(film_end, film_start + timedelta(days=self.rng.randint(12, 26)))
        else:
            r_end = film_end
        return film_start.strftime("%Y-%m-%d"), r_end.strftime("%Y-%m-%d")

    def _compute_realistic_schedule(
        self,
        series_or_movie: str,
        tier: str,
        genre: str,
        num_episodes: int = 1,
    ) -> Tuple[date, date, date, date, date, date, date, date]:
        """Compute realistic Hollywood casting, pre-production, principal photography, and post-production dates."""
        sub_days = self.rng.randint(7, 14)
        sub_end = self.current_date + timedelta(days=sub_days)
        aud_start = sub_end + timedelta(days=1)
        aud_end = aud_start + timedelta(days=self.rng.randint(4, 8))
        dec_date = aud_end + timedelta(days=self.rng.randint(2, 4))

        is_vfx_heavy = genre in ("Action", "Sci-fi", "Fantasy", "Animation", "Adventure")

        if series_or_movie == "Movie":
            if tier == "A":
                pre_days = self.rng.randint(40, 70)
                film_duration = self.rng.randint(90, 140) if is_vfx_heavy else self.rng.randint(70, 110)
                post_days = self.rng.randint(250, 365) if is_vfx_heavy else self.rng.randint(190, 290)
            elif tier == "B":
                pre_days = self.rng.randint(28, 50)
                film_duration = self.rng.randint(55, 85) if is_vfx_heavy else self.rng.randint(45, 72)
                post_days = self.rng.randint(170, 255)
            else:
                pre_days = self.rng.randint(18, 35)
                film_duration = self.rng.randint(28, 48)
                post_days = self.rng.randint(100, 165)
        else:
            pre_days = self.rng.randint(21, 45)
            ep_mult = self.rng.randint(7, 9)
            film_duration = max(45, min(200, num_episodes * ep_mult))
            post_days = self.rng.randint(85, 145) if is_vfx_heavy else self.rng.randint(65, 115)

        film_start = dec_date + timedelta(days=pre_days)
        film_end = film_start + timedelta(days=film_duration)
        rel_date = film_end + timedelta(days=post_days)
        run_end = rel_date + timedelta(days=35)
        return sub_end, aud_start, aud_end, dec_date, film_start, film_end, rel_date, run_end

    def _find_creative_id_by_name(self, name: str, role_kind: str) -> int:
        target = (name or "").strip().lower()
        if target:
            for c in self.creatives.values():
                if c.name.lower() == target:
                    return c.id
        pool = [c.id for c in self.creatives.values() if c.role_kind == role_kind]
        return self.rng.choice(pool) if pool else next(iter(self.creatives.keys()))

    def _build_project_from_roster_spec(self, spec: Dict[str, Any]) -> FilmOrSeries:
        fid = self.next_film_id
        self.next_film_id += 1

        series_or_movie = "TV" if spec.get("series_or_movie") == "TV" else "Movie"
        genre = spec.get("genre") if spec.get("genre") in GENRES else self.rng.choice(GENRES)
        title = (spec.get("title") or "").strip() or self.db.generate_title(self.rng, genre=genre, series_or_movie=series_or_movie)
        locations = ["Los Angeles", "New York", "Vancouver", "London", "Atlanta", "Toronto", "Chicago"]
        location = self.rng.choice(locations)

        dir_id = self._find_creative_id_by_name(spec.get("director_name", ""), "Director")
        prod_id = self._find_creative_id_by_name(spec.get("producer_name", ""), "Producer")
        show_id = self._find_creative_id_by_name(spec.get("showrunner_name", ""), "Showrunner") if series_or_movie == "TV" else None

        studio_name = (spec.get("studio") or "").strip()
        if series_or_movie == "Movie":
            raw_budget = int(spec.get("budget") or 0)
            if raw_budget >= 50_000_000:
                tier = "A"
                budget = raw_budget
            elif raw_budget >= 10_000_000:
                tier = "B"
                budget = raw_budget
            elif raw_budget > 0:
                tier = "C"
                budget = raw_budget
            else:
                tier = self.rng.choices(["A", "B", "C"], weights=[30, 38, 32])[0]
                if tier == "A":
                    budget = self.rng.randint(35, 165) * 1_000_000
                elif tier == "B":
                    budget = self.rng.randint(10, 42) * 1_000_000
                else:
                    budget = self.rng.randint(8, 80) * 100_000
            if not studio_name:
                studio_name = self.rng.choice(["Universal Pictures", "Warner Bros. Pictures", "Paramount Pictures", "A24", "Sony Pictures"])
            breakeven = int(budget * 1.8)
            is_pilot = False
            num_episodes = 1
        else:
            num_episodes = max(6, min(24, int(spec.get("num_episodes") or 10)))
            tier = "Broadcast" if studio_name in ("ABC", "NBC", "CBS", "FOX", "The CW") else "Cable"
            if not studio_name:
                studio_name = self.rng.choice(["HBO", "Netflix", "FX", "Apple TV+", "NBC", "ABC"])
            per_ep = self.rng.randint(1_500_000, 6_500_000)
            budget = ((per_ep * num_episodes) // 500_000) * 500_000
            breakeven = budget
            is_pilot = self.rng.random() < 0.4

        era = "1000-1600" if genre == "Historical" and self.rng.random() < 0.5 else (
            "1600-1900" if genre in ("Western", "Historical") else (
                "Future" if genre == "Sci-fi" and self.rng.random() < 0.5 else "1960-2020"
            )
        )

        vote_avg = float(spec.get("vote_average") or 6.6)
        script_rating = max(20, min(97, int(round(vote_avg * 11.2 + self.rng.randint(-8, 8)))))
        max_err = max(5, 38 - int(self.player_agency.knowledge_skill * 0.32))
        player_rating = min(99, max(5, script_rating + self.rng.randint(-max_err, max_err)))

        sub_end, aud_start, aud_end, dec_date, film_start, film_end, rel_date, run_end = self._compute_realistic_schedule(
            series_or_movie, tier, genre, num_episodes
        )

        raw_roles = list(spec.get("roles") or [])
        roles: List[RoleSlot] = []
        if not raw_roles:
            raw_roles = [
                {"role_name": self.db.sample_name(self.rng, "Male", "White"), "role_type": "Lead" if series_or_movie == "Movie" else "Series Regular", "sex": "Male"},
                {"role_name": self.db.sample_name(self.rng, "Female", "White"), "role_type": "Major Support" if series_or_movie == "Movie" else "Series Regular", "sex": "Female"},
                {"role_name": self.db.sample_name(self.rng, "Male", "White"), "role_type": "Minor Support" if series_or_movie == "Movie" else "Recurring", "sex": "Male"},
            ]

        # Enrich scripted TV shows with Recurring (multi-ep arc) + 1-Episode Guest Star roles
        if series_or_movie == "TV":
            raw_roles = raw_roles[:5]
            has_rec = any(r.get("role_type") == "Recurring" for r in raw_roles)
            has_guest = any(r.get("role_type") == "Guest Star" for r in raw_roles)
            if not has_rec:
                rec_sex = self.rng.choice(["Male", "Female"])
                rec_eps = self.rng.randint(3, min(6, num_episodes))
                raw_roles.append({
                    "role_name": f"{self.db.sample_name(self.rng, rec_sex, 'White')} ({rec_eps} eps)",
                    "role_type": "Recurring",
                    "sex": rec_sex,
                })
            if not has_guest or len(raw_roles) < 6:
                g_sex = self.rng.choice(["Male", "Female"])
                g_ep = self.rng.randint(1, num_episodes)
                raw_roles.append({
                    "role_name": f"{self.db.sample_name(self.rng, g_sex, 'White')} (Ep. {g_ep})",
                    "role_type": "Guest Star",
                    "sex": g_sex,
                })

        for r_idx, rspec in enumerate(raw_roles[:7]):
            rtype = rspec.get("role_type") or ("Lead" if r_idx == 0 else "Major Support")
            sex_req = rspec.get("sex") if rspec.get("sex") in ("Male", "Female") else self.rng.choice(["Male", "Female"])
            noun_row = self.rng.choice(self.db.role_nouns) if self.db.role_nouns else {"Role": "Protagonist"}
            noun = (noun_row.get("Role") or "Protagonist").strip()
            adj = self.rng.choice(self.db.role_adjectives) if self.db.role_adjectives else "Charismatic"
            col_tag = self.rng.choice(self.db.collective_tags) if self.db.collective_tags else "KARIZMATIKUS"
            age_weights = (
                [12, 18, 16, 22, 14, 8, 5, 3, 1, 1]
                if genre in ("Animation", "Fantasy", "Adventure")
                else [5, 11, 16, 28, 20, 10, 5, 3, 1, 1]
            )
            age_bracket = self.rng.choices([b[0] for b in AGE_RANGES], weights=age_weights)[0]
            eth_req = "Any" if self.rng.random() < 0.78 else self.rng.choice(["White", "Black", "Hispanic", "Asian"])
            body_req = "Any" if self.rng.random() < 0.65 else (
                self.rng.choice(["Slim", "Average", "Athletic", "Muscular"]) if sex_req == "Male" else self.rng.choice(["Slim", "Average", "Curvy", "Athletic"])
            )
            look_req = "Any" if self.rng.random() < 0.60 else (
                self.rng.choice(["Everyday", "Distinctive", "Clean-Cut", "Rugged"]) if sex_req == "Male" else self.rng.choice(["Striking", "Attractive", "Everyday", "Distinctive"])
            )
            height_req = "Any" if self.rng.random() < 0.75 else self.rng.choice(["Short", "Medium", "Tall"])
            req_skills = [self.rng.choice(self.db.special_skills)] if (self.db.special_skills and self.rng.random() < 0.25) else []
            nudity = "None"
            if (
                age_bracket not in ("Child (8-12)", "Teen (13-17)")
                and genre in ("Drama", "Horror", "Crime/Thriller")
                and tier != "Broadcast"
                and self.rng.random() < 0.14
            ):
                nudity = self.rng.choice(["Partial", "Full"])

            r_fstart, r_fend = self._compute_role_filming_window(rtype, film_start, film_end)
            roles.append(
                RoleSlot(
                    index=r_idx,
                    role_name=(rspec.get("role_name") or f"{adj} {noun}").strip(),
                    noun=noun,
                    adjective=adj,
                    collective_tag=col_tag,
                    role_type=rtype,
                    sex=sex_req,
                    age_range=age_bracket,
                    ethnicity=eth_req,
                    bodytype=body_req,
                    look=look_req,
                    height=height_req,
                    special_skills=req_skills,
                    nudity=nudity,
                    desired_fame=self._compute_role_desired_fame(series_or_movie, tier, budget, rtype),
                    filming_start=r_fstart,
                    filming_end=r_fend,
                )
            )

        film = FilmOrSeries(
            id=fid,
            title=title,
            series_or_movie=series_or_movie,
            studio_or_channel=studio_name,
            studio_tier=tier,
            genre=genre,
            historical_era=era,
            budget=budget,
            breakeven=breakeven,
            filming_location=location,
            director_id=dir_id,
            producer_id=prod_id,
            showrunner_id=show_id,
            script_rating=script_rating,
            player_rating=player_rating,
            submission_end_date=sub_end.strftime("%Y-%m-%d"),
            audition_start_date=aud_start.strftime("%Y-%m-%d"),
            audition_end_date=aud_end.strftime("%Y-%m-%d"),
            final_decision_date=dec_date.strftime("%Y-%m-%d"),
            filming_start_date=film_start.strftime("%Y-%m-%d"),
            filming_end_date=film_end.strftime("%Y-%m-%d"),
            release_date=rel_date.strftime("%Y-%m-%d"),
            run_end_date=run_end.strftime("%Y-%m-%d"),
            is_pilot=is_pilot,
            num_episodes=num_episodes,
            roles=roles,
        )
        self.films[fid] = film
        return film

    def generate_project(self, series_or_movie: str = "Movie") -> FilmOrSeries:
        if series_or_movie == "Movie" and self.queued_roster_movies:
            return self._build_project_from_roster_spec(self.queued_roster_movies.pop(0))
        if series_or_movie == "TV" and self.queued_roster_tv:
            return self._build_project_from_roster_spec(self.queued_roster_tv.pop(0))

        fid = self.next_film_id
        self.next_film_id += 1

        genre = self.rng.choice(GENRES)
        title = self.db.generate_title(
            self.rng,
            genre=genre,
            series_or_movie=series_or_movie,
            existing_titles={f.title for f in self.films.values()},
        )
        locations = [
            (r.get("Location") or "Los Angeles").strip()
            for r in self.db.get_rows("Filminglocations")
            if (r.get("Location") or "").strip()
        ] or ["Los Angeles", "New York", "Vancouver", "London", "Atlanta"]
        location = self.rng.choice(locations)

        directors = [c.id for c in self.creatives.values() if c.role_kind == "Director"]
        producers = [c.id for c in self.creatives.values() if c.role_kind == "Producer"]
        showrunners = [c.id for c in self.creatives.values() if c.role_kind == "Showrunner"]

        dir_id = self.rng.choice(directors)
        prod_id = self.rng.choice(producers)
        show_id = self.rng.choice(showrunners) if series_or_movie == "TV" else None

        if series_or_movie == "Movie":
            studios = self.custom_movie_studios or self.db.get_rows("MovieNumberofMoviesGenres")
            if studios:
                a_studios = [r for r in studios if (r.get("Type") or "").strip() == "A"]
                b_studios = [r for r in studios if (r.get("Type") or "").strip() == "B"]
                c_studios = [r for r in studios if (r.get("Type") or "").strip() not in ("A", "B")]
                tier_roll = self.rng.random()
                if tier_roll < 0.28 and a_studios:
                    st_row = self.rng.choice(a_studios)
                elif tier_roll < 0.60 and b_studios:
                    st_row = self.rng.choice(b_studios)
                elif c_studios:
                    st_row = self.rng.choice(c_studios)
                else:
                    st_row = self.rng.choice(studios)
            else:
                st_row = {"Studio": "Ocean Pictures", "Type": "A"}
            studio_name = (st_row.get("Studio") or "Ocean Pictures").strip()
            tier = (st_row.get("Type") or "B").strip()
            is_tentpole_genre = genre in ("Action", "Sci-fi", "Fantasy", "Animation", "Adventure")
            is_lean_genre = genre in ("Horror", "Drama", "Comedy", "Romance", "Thriller")

            if tier == "A":
                roll = self.rng.random()
                if is_tentpole_genre and roll < 0.35:
                    # Mega-blockbuster tentpole ($140M - $260M)
                    raw = self.rng.randint(140_000_000, 260_000_000)
                    budget = (raw // 5_000_000) * 5_000_000
                elif is_lean_genre and roll < 0.45:
                    # Major studio prestige / mid-budget ($18M - $65M)
                    raw = self.rng.randint(18_000_000, 65_000_000)
                    budget = (raw // 1_000_000) * 1_000_000
                else:
                    # Standard A-studio theatrical slate ($30M - $150M)
                    raw = self.rng.randint(30_000_000, 150_000_000)
                    budget = (raw // 2_500_000) * 2_500_000
            elif tier == "B":
                roll = self.rng.random()
                if roll < 0.25:
                    # Lean genre / specialty feature ($4M - $14M)
                    raw = self.rng.randint(4_000_000, 14_000_000)
                    budget = (raw // 500_000) * 500_000
                elif is_tentpole_genre and roll > 0.72:
                    # Ambitious B-studio swing ($42M - $75M)
                    raw = self.rng.randint(42_000_000, 75_000_000)
                    budget = (raw // 1_000_000) * 1_000_000
                else:
                    # Core mid-budget ($12M - $44M)
                    raw = self.rng.randint(12_000_000, 44_000_000)
                    budget = (raw // 1_000_000) * 1_000_000
            else:
                roll = self.rng.random()
                if roll < 0.30:
                    # Micro-budget indie ($150k - $1.2M)
                    raw = self.rng.randint(150_000, 1_200_000)
                    budget = (raw // 50_000) * 50_000
                elif roll < 0.75:
                    # Festival indie ($1.2M - $5.5M)
                    raw = self.rng.randint(1_200_000, 5_500_000)
                    budget = (raw // 100_000) * 100_000
                else:
                    # Elevated indie ($5.5M - $12M)
                    raw = self.rng.randint(5_500_000, 12_000_000)
                    budget = (raw // 250_000) * 250_000
            breakeven = int(budget * 1.8)
            is_pilot = False
            num_episodes = 1
        else:
            bcast = self.custom_tv_broadcast or self.db.get_rows("TVNumberofSeriesGenresBROADCAST")
            cable = self.custom_tv_cable or self.db.get_rows("TVNumberofSeriesGenresCABLE")
            is_fx_heavy = genre in ("Sci-fi", "Fantasy", "Action", "Historical")
            if self.rng.random() < 0.35 and bcast:
                ch_row = self.rng.choice(bcast)
                tier = "Broadcast"
                num_episodes = self.rng.choice([13, 18, 22, 24])
                per_ep = self.rng.randint(1_200_000, 3_600_000 if is_fx_heavy else 2_600_000)
                budget = ((per_ep * num_episodes) // 500_000) * 500_000
            else:
                ch_row = self.rng.choice(cable) if cable else {"Channel": "HBO Max", "Type": "Cable"}
                tier = "Cable"
                num_episodes = self.rng.choice([6, 8, 10, 12])
                per_ep = self.rng.randint(750_000, 9_500_000 if is_fx_heavy else 5_500_000)
                budget = ((per_ep * num_episodes) // 500_000) * 500_000
            studio_name = (ch_row.get("Channel") or "OBS").strip()
            breakeven = budget
            is_pilot = self.rng.random() < 0.5

        era = "1000-1600" if genre == "Historical" and self.rng.random() < 0.5 else (
            "1600-1900" if genre in ("Western", "Historical") else (
                "Future" if genre == "Sci-fi" and self.rng.random() < 0.5 else "1960-2020"
            )
        )

        # True script rating (1-100) and player's initial estimate
        script_rating = self.rng.randint(22, 96)
        max_err = max(5, 38 - int(self.player_agency.knowledge_skill * 0.32))
        player_rating = min(99, max(5, script_rating + self.rng.randint(-max_err, max_err)))

        # Realistic Hollywood schedule dates
        sub_end, aud_start, aud_end, dec_date, film_start, film_end, rel_date, run_end = self._compute_realistic_schedule(
            series_or_movie, tier, genre, num_episodes
        )

        # Generate 3 to 6 roles
        num_roles = self.rng.randint(3, 6)
        roles: List[RoleSlot] = []
        used_char_names: set[str] = set()
        for r_idx in range(num_roles):
            if series_or_movie == "Movie":
                if r_idx == 0:
                    rtype = "Lead"
                elif r_idx <= 2:
                    rtype = "Major Support"
                else:
                    rtype = "Minor Support"
            else:
                if r_idx <= 2:
                    rtype = "Series Regular"
                elif r_idx == 3:
                    rtype = "Recurring"
                else:
                    rtype = "Guest Star"

            noun_row = self.rng.choice(self.db.role_nouns) if self.db.role_nouns else {"Role": "Detective"}
            noun = (noun_row.get("Role") or "Detective").strip()
            adj = self.rng.choice(self.db.role_adjectives) if self.db.role_adjectives else "Ambivalent"
            col_tag = self.rng.choice(self.db.collective_tags) if self.db.collective_tags else "KARIZMATIKUS"

            sex_req = (noun_row.get("Sex") or "").strip()
            if sex_req not in ("Male", "Female"):
                sex_req = self.rng.choice(["Male", "Female"])

            age_weights = (
                [12, 18, 16, 22, 14, 8, 5, 3, 1, 1]
                if genre in ("Animation", "Fantasy", "Adventure")
                else [5, 11, 16, 28, 20, 10, 5, 3, 1, 1]
            )
            age_bracket = self.rng.choices(
                [b[0] for b in AGE_RANGES],
                weights=age_weights,
            )[0]

            eth_req = "Any" if self.rng.random() < 0.72 else self.rng.choice(["White", "Black", "Hispanic", "Asian"])
            body_req = "Any" if self.rng.random() < 0.65 else (
                self.rng.choice(["Slim", "Average", "Athletic", "Muscular"]) if sex_req == "Male" else self.rng.choice(["Slim", "Average", "Curvy", "Athletic"])
            )
            look_req = "Any" if self.rng.random() < 0.60 else (
                self.rng.choice(["Everyday", "Distinctive", "Clean-Cut", "Rugged"]) if sex_req == "Male" else self.rng.choice(["Striking", "Attractive", "Everyday", "Distinctive"])
            )
            height_req = "Any" if self.rng.random() < 0.75 else self.rng.choice(["Short", "Medium", "Tall"])

            req_skills: List[str] = []
            if self.db.special_skills and self.rng.random() < 0.30:
                req_skills.append(self.rng.choice(self.db.special_skills))

            nudity = "None"
            if (
                age_bracket not in ("Child (8-12)", "Teen (13-17)")
                and genre in ("Drama", "Horror", "Crime/Thriller")
                and tier != "Broadcast"
                and self.rng.random() < 0.18
            ):
                nudity = self.rng.choice(["Partial", "Full"])

            if rtype in ("Lead", "Major Support", "Series Regular", "Recurring"):
                name_eth = eth_req if eth_req != "Any" else self.rng.choices(
                    ["White", "Black", "Hispanic", "Asian"], weights=[60, 16, 14, 10]
                )[0]
                char_name = self.db.sample_name(self.rng, sex_req, name_eth)
                for _ in range(8):
                    if char_name not in used_char_names:
                        break
                    char_name = self.db.sample_name(self.rng, sex_req, name_eth)
                used_char_names.add(char_name)
                display_role_name = (
                    f"{char_name} ({self.rng.randint(3, min(6, max(3, num_episodes)))} eps)"
                    if rtype == "Recurring" else char_name
                )
            elif rtype == "Guest Star":
                display_role_name = f"{adj} {noun} (Ep. {self.rng.randint(1, max(1, num_episodes))})"
            else:
                display_role_name = f"{adj} {noun}"

            r_fstart, r_fend = self._compute_role_filming_window(rtype, film_start, film_end)
            roles.append(
                RoleSlot(
                    index=r_idx,
                    role_name=display_role_name,
                    noun=noun,
                    adjective=adj,
                    collective_tag=col_tag,
                    role_type=rtype,
                    sex=sex_req,
                    ethnicity=eth_req,
                    age_range=age_bracket,
                    look=look_req,
                    bodytype=body_req,
                    height=height_req,
                    special_skills=req_skills,
                    nudity=nudity,
                    desired_fame=self._compute_role_desired_fame(series_or_movie, tier, budget, rtype),
                    casting_type="Open",
                    filming_start=r_fstart,
                    filming_end=r_fend,
                )
            )

        proj = FilmOrSeries(
            id=fid,
            title=title,
            series_or_movie=series_or_movie,
            genre=genre,
            studio_or_channel=studio_name,
            studio_tier=tier,
            budget=budget,
            breakeven=breakeven,
            director_id=dir_id,
            producer_id=prod_id,
            showrunner_id=show_id,
            filming_location=location,
            historical_era=era,
            script_rating=script_rating,
            player_rating=player_rating,
            season=1,
            num_episodes=num_episodes,
            is_pilot=is_pilot,
            status="Casting",
            submission_end_date=sub_end.strftime("%Y-%m-%d"),
            audition_start_date=aud_start.strftime("%Y-%m-%d"),
            audition_end_date=aud_end.strftime("%Y-%m-%d"),
            final_decision_date=dec_date.strftime("%Y-%m-%d"),
            filming_start_date=film_start.strftime("%Y-%m-%d"),
            filming_end_date=film_end.strftime("%Y-%m-%d"),
            release_date=rel_date.strftime("%Y-%m-%d"),
            run_end_date=run_end.strftime("%Y-%m-%d"),
            roles=roles,
        )
        self.films[fid] = proj
        return proj

    def _send_welcome_emails(self) -> None:
        self.add_message(
            title=f"Welcome to {self.player_agency.name}",
            content=(
                f"Your new talent agency, {self.player_agency.name}, is officially open for business in Hollywoodland "
                f"with a starting operating budget of ${self.player_agency.budget:,.0f}.\n\n"
                "Quick Start:\n"
                "- Talent Service: Scout and sign free-agent actors (start with Unknown, Relatively unknown, or Average talent while your agency reputation is Minor; each new signing carries a $500 headshot portfolio fee).\n"
                "- Casting Calls & Role Finder: Browse open Movie and TV castings or use the Role Finder tab to sort open roles by compatibility with each available client.\n"
                "- Finances: Monthly office overhead for a Minor agency is $4,500 (deducted on the 1st of each month). Build a working roster and negotiate strong fees, commissions, and backend points to grow into a Major Hollywood powerhouse."
            ),
            category="general",
            severity="Normal",
            sender_name="Hollywoodland Agency Desk",
        )

    def add_message(
        self,
        title: str,
        content: str,
        category: str = "general",
        severity: str = "Normal",
        sender_name: str = "Hollywoodland Wire",
        portrait_file: str = "",
        canvas_file: str = "",
        related_actor_id: Optional[int] = None,
        related_film_id: Optional[int] = None,
        related_role_index: Optional[int] = None,
        buttons: Optional[List[MessageButton]] = None,
    ) -> InboxMessage:
        btns = buttons or []
        req_resp = any(b.blocker for b in btns)
        msg = InboxMessage(
            id=self.next_msg_id,
            date_str=self.pretty_date,
            title=title,
            content=content,
            category=category,
            severity=severity,
            was_read=False,
            requires_response=req_resp,
            sender_name=sender_name,
            portrait_file=portrait_file,
            canvas_file=canvas_file,
            related_actor_id=related_actor_id,
            related_film_id=related_film_id,
            related_role_index=related_role_index,
            buttons=btns,
        )
        self.next_msg_id += 1
        self.messages.insert(0, msg)
        return msg

    def has_blocking_message(self) -> Optional[InboxMessage]:
        for m in self.messages:
            if m.requires_response:
                return m
        return None

    def record_transaction(
        self,
        description: str,
        amount: int,
        actor_name: str = "",
        project_title: str = "",
        payment_type: str = "General",
    ) -> None:
        self.player_agency.budget += amount
        if amount > 0:
            self.player_agency.stats_income += amount
        self.ledger.insert(
            0,
            LedgerEntry(
                date_str=self.pretty_date,
                description=description,
                amount=amount,
                actor_name=actor_name,
                project_title=project_title,
                payment_type=payment_type,
            ),
        )

    def record_actor_earning(
        self,
        actor: Actor,
        project_title: str,
        role_name: str,
        category: str,
        gross_amount: int,
        agency_cut: int = 0,
        is_backend: bool = False,
    ) -> None:
        """Record an itemized actor earning (upfront fee, backend bonus, gross/net points, TV renewal, or signature fee)."""
        if gross_amount <= 0:
            return
        actor.this_year_income += gross_amount
        actor.career_income += gross_amount
        if is_backend:
            actor.career_backend_income += gross_amount
        else:
            actor.career_upfront_income += gross_amount
        actor.career_agency_commissions += max(0, agency_cut)
        actor.earnings_history.insert(
            0,
            {
                "date": self.date_str,
                "project": project_title,
                "role": role_name,
                "category": category,
                "gross_amount": int(gross_amount),
                "agency_cut": int(max(0, agency_cut)),
                "actor_net": int(max(0, gross_amount - max(0, agency_cut))),
            },
        )

    # -------------------------------------------------------------------------
    # Scouting & Script Consulting
    # -------------------------------------------------------------------------
    def hire_scout(self, actor_id: int, scout_id: int) -> Tuple[bool, str]:
        actor = self.actors.get(actor_id)
        scout = next((s for s in self.scouts if s.id == scout_id), None)
        if not actor or not scout:
            return False, "Invalid actor or scout."
        if all(actor.known_attributes.get(a, False) for a in CORE_ATTRIBUTES):
            return False, f"All attributes for {actor.name} have already been fully scouted."
        if self.player_agency.budget < scout.fee:
            return False, f"Insufficient agency funds (${scout.fee:,} required)."

        self.record_transaction(
            f"Talent scouting fee for {actor.name} ({scout.name})",
            -scout.fee,
            actor_name=actor.name,
            payment_type="Scout/Consultant",
        )
        days = self.rng.randint(scout.report_days_min, scout.report_days_max)
        due = (self.current_date + timedelta(days=days)).strftime("%Y-%m-%d")
        self.pending_tasks.append({"type": "scout", "due": due, "actor_id": actor_id, "scout_tier": scout.tier})
        return True, f"{scout.name} is assessing {actor.name}. Report expected in {days} day(s)."

    def hire_script_consultant(self, film_id: int, consultant_id: int) -> Tuple[bool, str]:
        film = self.films.get(film_id)
        cons = next((c for c in self.consultants if c.id == consultant_id), None)
        if not film or not cons:
            return False, "Invalid project or consultant."
        if film.consultant_rating is not None:
            return False, "You have already hired a consultant to review this script."
        if self.player_agency.budget < cons.fee:
            return False, f"Insufficient agency funds (${cons.fee:,} required)."

        self.record_transaction(
            f"Script doctor review for '{film.title}' ({cons.name})",
            -cons.fee,
            project_title=film.title,
            payment_type="Scout/Consultant",
        )
        days = self.rng.randint(cons.report_days_min, cons.report_days_max)
        due = (self.current_date + timedelta(days=days)).strftime("%Y-%m-%d")
        self.pending_tasks.append({"type": "consultant", "due": due, "film_id": film_id, "tier": cons.tier})
        return True, f"{cons.name} is reviewing '{film.title}'. Verdict expected in {days} day(s)."

    # -------------------------------------------------------------------------
    # Agency <-> Actor Representation Negotiation
    # -------------------------------------------------------------------------
    def check_actor_willing_to_talk(self, actor_id: int) -> Tuple[bool, str]:
        actor = self.actors.get(actor_id)
        if not actor:
            return False, "Actor not found."
        if actor.agency_id == 0:
            return False, f"{actor.name} is already represented by your agency."
        if actor.agency_id is not None:
            ag = self.agencies.get(actor.agency_id)
            aname = ag.name if ag else "another agency"
            return False, f"\"My contract with {aname} hasn't expired yet, don't disturb me!\""

        rep = self.player_agency.reputation
        if actor.fame_tier == "A-lister" and rep != "Major":
            return False, "\"No, thank you. I'll let you know though when I need a small-time agent.\" (Requires Major Agency Reputation)"
        if actor.fame_tier == "Notable" and rep == "Minor":
            return False, "\"Sorry, I only negotiate with Medium or Major talent agencies.\" (Requires Medium+ Agency Reputation)"

        my_clients = [a for a in self.actors.values() if a.agency_id == 0]
        if len(my_clients) >= self.player_agency.max_actors:
            return False, "Your agency roster is at maximum capacity!"
        return True, "Ready to negotiate."

    def get_actor_initial_demands(self, actor_id: int) -> ContractOffer:
        actor = self.actors[actor_id]
        sig_fee = 0
        min_any = 0
        min_major = 0
        min_inc = 0

        if actor.fame_tier == "Average":
            if self.rng.random() < 0.45:
                sig_fee = self.rng.choice([1500, 2500, 4000])
            min_any = 1
        elif actor.fame_tier == "Notable":
            sig_fee = self.rng.choice([5000, 10000, 15000])
            min_any = 2
            min_major = 1
        elif actor.fame_tier == "A-lister":
            sig_fee = self.rng.choice([25000, 50000, 75000])
            min_major = 1
            min_inc = 1_000_000
        elif actor.personality in ("Arrogant", "Materialistic", "Egotistic", "Bossy") and self.rng.random() < 0.35:
            sig_fee = 1000

        return ContractOffer(
            contract_start=self.date_str,
            contract_end=(self.current_date + timedelta(days=365)).strftime("%Y-%m-%d"),
            commission=10,
            num_months=12,
            signature_fee=sig_fee,
            min_any_roles=min_any,
            min_major_roles=min_major,
            min_income=min_inc,
        )

    def evaluate_representation_offer(self, actor_id: int, offer: ContractOffer, demand: ContractOffer) -> Tuple[bool, str, ContractOffer]:
        actor = self.actors[actor_id]
        # Calculate score ratio
        score = 100.0
        # Commission penalty above 10%
        if offer.commission > 10:
            score -= (offer.commission - 10) * 9.5
        elif offer.commission < 10:
            score += (10 - offer.commission) * 5.0

        # Signature fee comparison
        if demand.signature_fee > 0:
            ratio = offer.signature_fee / max(1, demand.signature_fee)
            if ratio < 1.0:
                score -= (1.0 - ratio) * 35.0
            else:
                score += min(15.0, (ratio - 1.0) * 15.0)
        elif offer.signature_fee > 0:
            score += min(20.0, offer.signature_fee / 250.0)

        # Role promises comparison
        if offer.min_any_roles < demand.min_any_roles:
            score -= (demand.min_any_roles - offer.min_any_roles) * 12.0
        if offer.min_major_roles < demand.min_major_roles:
            score -= (demand.min_major_roles - offer.min_major_roles) * 18.0

        # Player negotiation skill bonus
        score += (self.player_agency.negotiation_skill - 25) * 0.35

        if score >= 82.0:
            return self.sign_actor_to_player_agency(actor_id, offer)
        elif score >= 58.0:
            # Counter-offer
            counter = ContractOffer(
                contract_start=offer.contract_start,
                contract_end=offer.contract_end,
                commission=min(offer.commission, 10),
                num_months=offer.num_months,
                signature_fee=int((offer.signature_fee + demand.signature_fee) / 2),
                min_any_roles=demand.min_any_roles,
                min_major_roles=demand.min_major_roles,
                min_income=demand.min_income,
            )
            return False, "\"Some terms are not acceptable for me—here is my counter-offer.\"", counter
        else:
            return False, "\"I think we are just wasting each other's time, so let's cancel the negotiations.\"", demand

    def sign_actor_to_player_agency(self, actor_id: int, offer: ContractOffer) -> Tuple[bool, str, ContractOffer]:
        actor = self.actors[actor_id]
        portfolio_fee = 500
        total_upfront = portfolio_fee + offer.signature_fee
        if self.player_agency.budget < total_upfront:
            return False, f"Insufficient funds! Signing requires ${portfolio_fee:,} photographer portfolio fee + ${offer.signature_fee:,} signature fee.", offer

        offer.contract_start = self.date_str
        offer.contract_end = (self.current_date + timedelta(days=30 * offer.num_months)).strftime("%Y-%m-%d")
        actor.agency_id = 0
        actor.contract = offer
        # Reveal all attributes & potential once signed to player's agency
        for attr in CORE_ATTRIBUTES:
            actor.known_attributes[attr] = True
        actor.potential_known = True

        self.record_transaction(
            f"Photographer portfolio fee for new client {actor.name}",
            -portfolio_fee,
            actor_name=actor.name,
            payment_type="Portfolio",
        )
        if offer.signature_fee > 0:
            self.record_transaction(
                f"Client signature bonus paid to {actor.name}",
                -offer.signature_fee,
                actor_name=actor.name,
                payment_type="Signature Fee",
            )
            self.record_actor_earning(
                actor,
                project_title=self.player_agency.name,
                role_name="Agency Signing Bonus",
                category="Signature Fee",
                gross_amount=offer.signature_fee,
                agency_cut=0,
                is_backend=False,
            )

        self.add_message(
            title=f"{actor.name} joins your agency",
            content=(
                f"\"I'm pleased to team up with a knowledgeable agent like you! Let's conquer Hollywoodland together.\"\n\n"
                f"- Commission Rate: {offer.commission}%\n"
                f"- Contract Duration: {offer.num_months} months (expires {offer.contract_end})\n"
                f"- Photographer Portfolio Fee Paid: ${portfolio_fee:,}"
            ),
            category="general",
            sender_name=actor.name,
            related_actor_id=actor.id,
        )
        return True, f"{actor.name} accepted your offer and joined {self.player_agency.name}!", offer

    # -------------------------------------------------------------------------
    # Casting Submissions & Auditions
    # -------------------------------------------------------------------------
    def is_actor_available_for_submission(self, actor_id: int) -> bool:
        """Returns True only if the player's actor is completely free (not submitted, auditioning, offered, contracted, filming, or training)."""
        actor = self.actors.get(actor_id)
        if not actor or actor.agency_id != 0:
            return False
        if actor.training_type is not None:
            return False
        if actor.schedule_status != "Available":
            return False
        # Also verify no active Submitted / Auditioning / Offered / Cast-and-filming submission exists
        for sub in self.submissions:
            if sub.actor_id == actor_id and sub.status in ("Submitted", "Auditioning", "Offered"):
                return False
        return True

    def get_available_player_clients(self) -> List[Actor]:
        return [a for a in self.actors.values() if self.is_actor_available_for_submission(a.id)]

    def evaluate_role_match_for_actor(self, actor_id: int, film_id: int, role_index: int) -> Dict[str, Any]:
        """Deterministically evaluate how well an actor matches an open role using only visible requirements and actor stats."""
        actor = self.actors[actor_id]
        film = self.films[film_id]
        role = film.roles[role_index]

        # 1. Hard screening / eligibility rules (mirrors submit_actor_to_role)
        reject_reasons: List[str] = []
        if role.sex in ("Male", "Female") and actor.sex != role.sex:
            reject_reasons.append(f"Needs {role.sex}")
        if role.ethnicity != "Any" and actor.ethnicity != role.ethnicity:
            reject_reasons.append(f"Needs {role.ethnicity}")
        if role.nudity != "None" and actor.age < 18:
            reject_reasons.append("Minor (<18) cannot be submitted to nudity role")
        elif role.nudity != "None" and "Won't do nudity" in actor.personal_info:
            reject_reasons.append("Refuses nudity")
        if f"Won't do {film.genre}" in actor.personal_info:
            reject_reasons.append(f"Refuses {film.genre}")
        if (
            role.role_type in ("Lead", "Series Regular")
            and self.player_agency.reputation == "Minor"
            and film.studio_tier == "A"
            and actor.fame_tier in ("Unknown", "Relatively unknown")
        ):
            reject_reasons.append("A-tier Lead fame gate")

        highlights: List[str] = []
        score = 0.0

        # 2. Age bracket fit (max 15)
        actor_bracket = self._age_to_bracket(actor.age)
        if actor_bracket == role.age_range:
            score += 15.0
            highlights.append("Age ✓")
        else:
            age_diff = abs(
                next((i for i, b in enumerate(AGE_RANGES) if b[0] == actor_bracket), 1)
                - next((i for i, b in enumerate(AGE_RANGES) if b[0] == role.age_range), 1)
            )
            if age_diff == 1:
                score += 9.5
                highlights.append("Age ~")
            else:
                score += 2.0
                highlights.append("Age ✗")

        # 3. Look fit (max 13)
        if role.look == "Any":
            score += 13.0
        else:
            look_val = self.db.look_scores.get(role.look, {}).get(actor.look, 500.0)
            score += max(0.0, min(13.0, (look_val / 1000.0) * 13.0))
            if actor.look == role.look:
                highlights.append("Look ✓")
            elif look_val < 400.0:
                highlights.append("Look ✗")

        # 4. Bodytype fit (max 10)
        if role.bodytype == "Any":
            score += 10.0
        else:
            body_val = self.db.body_scores.get(role.bodytype, {}).get(actor.bodytype, 500.0)
            score += max(0.0, min(10.0, (body_val / 1000.0) * 10.0))
            if actor.bodytype == role.bodytype:
                highlights.append("Body ✓")
            elif body_val < 400.0:
                highlights.append("Body ✗")

        # 5. Height fit (max 7)
        if role.height == "Any":
            score += 7.0
        elif actor.height_category == role.height:
            score += 7.0
            highlights.append("Height ✓")
        else:
            score += 2.0
            highlights.append("Height ✗")

        # 6. Acting, Genre & Role Collective Tag attributes (max 25)
        acting_avg = (
            actor.attributes.get("Characterization", 50)
            + actor.attributes.get("Improvisation", 50)
            + actor.attributes.get("Vocal Expression", 50)
            + actor.attributes.get("Physical Expression", 50)
            + actor.attributes.get("Facial Expression", 50)
        ) / 5.0
        genre_attrs = self.db.genre_required_attrs.get(film.genre, ["Characterization", "Facial Expression"])
        genre_avg = sum(actor.attributes.get(ga, 50) for ga in genre_attrs) / max(1, len(genre_attrs))
        tag_attrs = self.db.collective_attr_bonuses.get(role.collective_tag, [])
        tag_avg = (sum(actor.attributes.get(ta, 50) for ta in tag_attrs) / len(tag_attrs)) if tag_attrs else acting_avg

        skill_composite = (acting_avg * 0.45) + (genre_avg * 0.40) + (tag_avg * 0.15)
        score += max(0.0, min(25.0, (skill_composite / 100.0) * 25.0))
        if genre_avg >= 68:
            highlights.append(f"{film.genre} ✓")
        elif genre_avg <= 40:
            highlights.append(f"{film.genre} ✗")

        # 7. Special skills (max 9)
        if not role.special_skills:
            score += 9.0
        else:
            matched_sk = [sk for sk in role.special_skills if sk in actor.special_skills]
            missing_sk = [sk for sk in role.special_skills if sk not in actor.special_skills]
            score += 9.0 * (len(matched_sk) / len(role.special_skills))
            if not missing_sk:
                highlights.append("Skills ✓")
            else:
                highlights.append(f"Missing: {', '.join(missing_sk[:2])}")

        # 8. Desired Fame fit (0-100 scale, max 16)
        fame_val = max(0.0, min(100.0, float(actor.fame_score)))
        desired_f = max(0, min(100, int(getattr(role, "desired_fame", 30))))
        fame_gap = desired_f - fame_val
        if fame_gap <= 0:
            score += 16.0
            if desired_f >= 35:
                highlights.append(f"Fame ✓ ({int(round(fame_val))}/{desired_f})")
        elif fame_gap <= 12:
            score += 11.5
            highlights.append(f"Fame ~ ({int(round(fame_val))}/{desired_f})")
        elif fame_gap <= 28:
            score += 5.5
            highlights.append(f"Fame Low ({int(round(fame_val))}/{desired_f})")
        else:
            score += 0.0
            highlights.append(f"Fame ✗ ({int(round(fame_val))}/{desired_f})")

        # 9. Director affinity (max 5)
        affinity = 2.5
        director = self.creatives.get(film.director_id)
        if director:
            if actor.id in director.liked_actor_ids:
                affinity += 2.5
                highlights.append("Director ♥")
            elif actor.id in director.disliked_actor_ids:
                affinity -= 2.5
                highlights.append("Director ✗")
            elif director.disc == actor.disc:
                affinity += 1.5
                highlights.append("DISC ✓")
        score += max(0.0, min(5.0, affinity))

        match_pct = max(1, min(99, int(round(score))))
        eligible = len(reject_reasons) == 0
        if not eligible:
            fit_label = "Ineligible"
            summary = "Ineligible: " + ", ".join(reject_reasons)
        else:
            if match_pct >= 80:
                fit_label = "Great Fit"
            elif match_pct >= 65:
                fit_label = "Good Fit"
            elif match_pct >= 50:
                fit_label = "Fair Fit"
            else:
                fit_label = "Weak Fit"
            summary = " · ".join(highlights[:5]) if highlights else "Standard match"

        return {
            "film_id": film_id,
            "role_index": role_index,
            "eligible": eligible,
            "already_submitted": actor_id in role.submitted_actor_ids,
            "reject_reasons": reject_reasons,
            "match_pct": match_pct,
            "fit_label": fit_label,
            "summary": summary,
        }

    def find_matching_roles_for_actor(
        self,
        actor_id: int,
        include_ineligible: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return all open, uncast roles across casting projects sorted by match score for actor_id."""
        if actor_id not in self.actors:
            return []
        results: List[Dict[str, Any]] = []
        tier_rank = {"A": 0, "B": 1, "C": 2, "Indie": 3}
        for film in self.films.values():
            if film.status != "Casting":
                continue
            for role in film.roles:
                if role.cast_actor_id is not None or role.offered_actor_id is not None:
                    continue
                res = self.evaluate_role_match_for_actor(actor_id, film.id, role.index)
                if not include_ineligible and not res["eligible"]:
                    continue
                res["film"] = film
                res["role"] = role
                results.append(res)
        results.sort(
            key=lambda r: (
                0 if r["eligible"] else 1,
                -r["match_pct"],
                tier_rank.get(r["film"].studio_tier, 9),
                r["film"].title,
            )
        )
        return results

    def submit_actor_to_role(self, actor_id: int, film_id: int, role_index: int) -> Tuple[bool, str]:
        actor = self.actors.get(actor_id)
        film = self.films.get(film_id)
        if not actor or not film or role_index >= len(film.roles):
            return False, "Invalid actor, project, or role."
        role = film.roles[role_index]

        if actor.agency_id != 0:
            return False, "You can only submit actors represented by your agency."
        if film.status != "Casting":
            return False, f"Submissions for '{film.title}' are already closed."
        if role.cast_actor_id is not None:
            return False, f"The role of '{role.role_name}' has already been cast."
        if actor_id in role.submitted_actor_ids:
            return False, f"{actor.name} has already been submitted for '{role.role_name}'."
        if not self.is_actor_available_for_submission(actor_id):
            return False, f"{actor.name} is already busy ({actor.schedule_status}) and can only be submitted to one role at a time."

        # Screening check (authentic rejection reasons from Cattle Call.exe lines 1286-1292)
        reject_reasons: List[str] = []
        if role.sex in ("Male", "Female") and actor.sex != role.sex:
            reject_reasons.append("wrong sex")
        if role.ethnicity != "Any" and actor.ethnicity != role.ethnicity:
            reject_reasons.append("wrong ethnicity")
        if role.nudity != "None" and actor.age < 18:
            reject_reasons.append("actors under 18 cannot be cast in roles with nudity")
        elif role.nudity != "None" and "Won't do nudity" in actor.personal_info:
            reject_reasons.append("actor refuses roles with nudity")
        if f"Won't do {film.genre}" in actor.personal_info:
            reject_reasons.append(f"actor refuses {film.genre} projects")
        if role.role_type in ("Lead", "Series Regular") and self.player_agency.reputation == "Minor" and film.studio_tier == "A" and actor.fame_tier in ("Unknown", "Relatively unknown"):
            reject_reasons.append("A-tier studio requires a more established star for a Lead role")

        role.submitted_actor_ids.append(actor_id)
        if reject_reasons:
            self.submissions.append(SubmissionRecord(actor_id, film_id, role_index, "Rejected"))
            reason_bullet = "\n".join(f" - {r}" for r in reject_reasons)
            self.add_message(
                title=f"{actor.name}'s submission was rejected.",
                content=(
                    f"The submission of {actor.name} for '{role.role_name}' ({role.role_type}) in '{film.title}' "
                    f"was rejected by {film.studio_or_channel}.\n\nReason(s):\n{reason_bullet}"
                ),
                category="general",
                sender_name=film.studio_or_channel,
                related_actor_id=actor_id,
                related_film_id=film_id,
                related_role_index=role_index,
            )
            return False, f"Submission rejected by {film.studio_or_channel}: {', '.join(reject_reasons)}."

        self.submissions.append(
            SubmissionRecord(actor_id, film_id, role_index, "Submitted", audition_date=film.audition_start_date)
        )
        actor.schedule_status = f"Submitted for '{film.title}' (Auditions: {film.audition_start_date}, Decision: {film.final_decision_date})"
        self.add_message(
            title=f"{actor.name} submitted for '{role.role_name}' in '{film.title}'",
            content=(
                f"{actor.name} was submitted for the {role.role_type} role of '{role.role_name}' in "
                f"{film.studio_or_channel}'s {film.genre} project, '{film.title}'.\n\n"
                f"- Submission Deadline: {film.submission_end_date}\n"
                f"- Audition Period: {film.audition_start_date} to {film.audition_end_date}\n"
                f"- Final Decision Date: {film.final_decision_date}"
            ),
            category="general",
            sender_name=film.studio_or_channel,
            related_actor_id=actor_id,
            related_film_id=film_id,
            related_role_index=role_index,
        )
        return True, f"Submitted {actor.name} for '{role.role_name}' ({role.role_type}) in '{film.title}' (Decision: {film.final_decision_date})!"

    def score_audition_candidate(self, actor: Actor, film: FilmOrSeries, role: RoleSlot) -> AuditionCandidate:
        """Authentic Cattle Call audition scoring matrix + pros/cons bitmask generator."""
        pros: List[str] = []
        cons: List[str] = []
        points = 0.0

        # 1. Age range fit
        actor_bracket = self._age_to_bracket(actor.age)
        if actor_bracket == role.age_range:
            points += 140.0
            pros.append("Fits in the age range perfectly.")
        else:
            age_diff = abs(
                next((i for i, b in enumerate(AGE_RANGES) if b[0] == actor_bracket), 1)
                - next((i for i, b in enumerate(AGE_RANGES) if b[0] == role.age_range), 1)
            )
            if age_diff == 1:
                points += 95.0
            else:
                points += 25.0
                cons.append("Age range is off the mark.")

        # 2. Look fit
        look_val = self.db.look_scores.get(role.look, {}).get(actor.look, 850.0)
        points += look_val * 0.12
        if role.look != "Any" and actor.look == role.look:
            pros.append("Perfect look for the role.")
        elif look_val < 400.0:
            cons.append("Look is off the mark.")

        # 3. Bodytype fit
        body_val = self.db.body_scores.get(role.bodytype, {}).get(actor.bodytype, 850.0)
        points += body_val * 0.10
        if role.bodytype != "Any" and actor.bodytype == role.bodytype:
            pros.append("Perfect bodytype.")
        elif body_val < 400.0:
            cons.append("Bodytype is off the mark.")

        # 4. Height fit
        if role.height == "Any" or actor.height_category == role.height:
            points += 80.0
            if role.height != "Any":
                pros.append("Right height.")
        else:
            points += 35.0
            cons.append("Height is off the mark.")

        # 5. Core acting skills + Genre requirements
        acting_avg = (
            actor.attributes.get("Characterization", 50)
            + actor.attributes.get("Improvisation", 50)
            + actor.attributes.get("Vocal Expression", 50)
            + actor.attributes.get("Physical Expression", 50)
            + actor.attributes.get("Facial Expression", 50)
        ) / 5.0
        points += acting_avg * 2.5
        if acting_avg >= 76:
            pros.append("Outstanding acting skills.")
        elif acting_avg <= 38:
            cons.append("As wooden as Pinocchio.")

        genre_attrs = self.db.genre_required_attrs.get(film.genre, ["Characterization", "Facial Expression"])
        for ga in genre_attrs:
            v = actor.attributes.get(ga, 50)
            points += v * 1.1

        # 6. Role Adjective Collective Tag bonus
        for ba in self.db.collective_attr_bonuses.get(role.collective_tag, []):
            points += actor.attributes.get(ba, 50) * 0.7

        # 7. Charisma, Humor, Voice, Physicality specifics
        charisma = actor.attributes.get("Charisma", 50)
        if charisma >= 78:
            points += 55.0
            pros.append("Very charismatic.")
        elif charisma <= 32:
            points -= 45.0
            cons.append("As charismatic as a door knob.")
        elif charisma <= 45 and role.role_type in ("Lead", "Series Regular"):
            points -= 25.0
            cons.append("Lacks charisma.")

        humor = actor.attributes.get("Humor", 50)
        if film.genre in ("Comedy", "Animation", "Musical"):
            if humor >= 75:
                points += 50.0
                pros.append("Has a great sense of humor.")
            elif humor <= 35:
                points -= 45.0
                cons.append("As funny as a tax inspector.")

        vocal = actor.attributes.get("Vocal Expression", 50)
        if vocal >= 78:
            points += 35.0
            pros.append("Has a brilliant voice.")
        elif vocal <= 32:
            points -= 30.0
            cons.append("Has a voice from hell")

        phys = actor.attributes.get("Physical Expression", 50)
        if phys >= 78:
            points += 35.0
            pros.append("Very agile.")
        elif phys <= 32:
            points -= 30.0
            cons.append("As agile as a dead walrus")

        # 8. Confidence (inhibitions) & Commitment (audition preparation)
        conf = actor.attributes.get("Confidence", 50)
        if conf <= 30:
            points -= 65.0
            cons.append("Paralyzed by inhibitions.")
        elif conf <= 45:
            points -= 30.0
            cons.append("Lacking confidence.")

        comm = actor.attributes.get("Commitment", 50)
        if comm <= 30:
            points -= 70.0
            cons.append("Was obscenely unprepared.")
        elif comm <= 45:
            points -= 35.0
            cons.append("Wasnt fully prepared for the audition.")

        # 9. Special skills match
        for req_sk in role.special_skills:
            if req_sk in actor.special_skills:
                points += 75.0
                pros.append(f"Mastered required skill: {req_sk}.")
            else:
                points -= 55.0
                cons.append(f"Missing required skill: {req_sk}.")

        # 10. Fame (0-100) vs Role Desired Fame & Agency Reputation
        fame_val = max(0.0, min(100.0, float(actor.fame_score)))
        desired_f = max(0, min(100, int(getattr(role, "desired_fame", 30))))
        fame_gap = desired_f - fame_val
        if fame_gap <= 0:
            points += 95.0 + min(35.0, (fame_val - desired_f) * 0.7)
            if desired_f >= 35:
                pros.append(f"Meets studio's Fame target ({int(round(fame_val))}/{desired_f}).")
        elif fame_gap <= 12:
            points += 60.0
        elif fame_gap <= 28:
            points += 15.0
            cons.append(f"Below desired Fame for this role ({int(round(fame_val))}/{desired_f}).")
        else:
            points -= 65.0
            cons.append(f"Not famous enough for studio expectations ({int(round(fame_val))}/{desired_f}).")

        ag = self.agencies.get(actor.agency_id) if actor.agency_id is not None else None
        if ag:
            if ag.reputation == "Major":
                points += 55.0
                pros.append("Represented by a top agency.")
            elif ag.reputation == "Medium":
                points += 30.0
                pros.append("Represented by a well known agency.")
            else:
                points += 10.0
                pros.append("Represented by an agency.")

        # 11. Morale, Condition, and DISC compatibility with Director
        if actor.morale_score <= 25:
            points -= 40.0
            cons.append("Dismal morale.")
        if actor.condition_score <= 30:
            points -= 45.0
            cons.append("Was too exhausted to shine.")

        director = self.creatives.get(film.director_id)
        if director:
            if actor.id in director.liked_actor_ids:
                points += 85.0
                pros.append(f"Personally admired by Director {director.name}!")
            elif actor.id in director.disliked_actor_ids:
                points -= 75.0
                cons.append(f"Disliked by Director {director.name}.")
            elif director.disc == actor.disc:
                points += 40.0
                pros.append("Admired by the decision-makers.")
            elif (director.disc == "D" and actor.disc == "S") or (director.disc == "C" and actor.disc == "I"):
                if self.rng.random() < 0.35:
                    points -= 35.0
                    cons.append("Disliked by the decision-makers.")

        # Small audition day variance
        points += self.rng.uniform(-25.0, 25.0)

        return AuditionCandidate(
            actor_id=actor.id,
            actor_name=actor.name,
            agency_name=ag.name if ag else "Free Agent",
            points=round(max(50.0, points), 1),
            pros=pros or ["Delivered a solid audition reading."],
            cons=cons or ["No major flaws noted by the casting director."],
        )

    # -------------------------------------------------------------------------
    # Studio <-> Actor Role Contract Negotiation
    # -------------------------------------------------------------------------
    def get_initial_role_offer(self, film_id: int, role_index: int, actor_id: int) -> ContractOffer:
        film = self.films[film_id]
        role = film.roles[role_index]
        actor = self.actors[actor_id]
        base_quote = actor.quotes.get(role.role_type, 25000)

        tier_mult = {"A": 1.25, "B": 1.0, "C": 0.65, "Broadcast": 1.1, "Cable": 0.95}.get(film.studio_tier, 1.0)
        fee = max(1500, int((base_quote * tier_mult) // 500) * 500)

        bo_bonus = 0
        bo_thresh = film.breakeven
        net_pts = 0.0
        first_gross = 0.0

        if role.role_type in ("Lead", "Major Support") and film.series_or_movie == "Movie":
            bo_bonus = int(fee * 0.5)
            if actor.fame_tier in ("Notable", "A-lister"):
                net_pts = 2.0 if actor.fame_tier == "Notable" else 5.0
            if actor.fame_tier == "A-lister":
                first_gross = 2.0

        return ContractOffer(
            contract_start=role.filming_start,
            contract_end=role.filming_end,
            commission=actor.contract.commission if actor.contract else 10,
            acting_fee=fee,
            first_dollar_gross=first_gross,
            net_points=net_pts,
            bo_bonus_fee=bo_bonus,
            bo_bonus_threshold=bo_thresh,
            acting_fee_bumps=10 if film.series_or_movie == "TV" else 0,
        )

    def negotiate_role_contract(
        self,
        film_id: int,
        role_index: int,
        actor_id: int,
        proposed: ContractOffer,
        baseline: ContractOffer,
    ) -> Tuple[str, str, ContractOffer]:
        """Returns (status: 'ACCEPTED'|'COUNTER'|'REJECTED', message, offer)."""
        film = self.films[film_id]
        role = film.roles[role_index]
        actor = self.actors[actor_id]

        max_tolerance = 1.18 + (self.player_agency.negotiation_skill / 250.0)
        if actor.fame_tier in ("Notable", "A-lister"):
            max_tolerance += 0.12

        fee_ratio = proposed.acting_fee / max(1, baseline.acting_fee)
        bonus_penalty = (proposed.bo_bonus_fee - baseline.bo_bonus_fee) / max(10000, baseline.acting_fee * 2)
        pts_penalty = (proposed.net_points - baseline.net_points) * 0.05 + (proposed.first_dollar_gross - baseline.first_dollar_gross) * 0.10
        total_ask_ratio = fee_ratio + max(0.0, bonus_penalty) + max(0.0, pts_penalty)

        if total_ask_ratio <= max_tolerance:
            self.finalize_role_contract(film_id, role_index, actor_id, proposed)
            return "ACCEPTED", "\"Okay, these terms are acceptable for us. Let's sign the contract!\"", proposed
        elif total_ask_ratio <= max_tolerance + 0.30:
            counter_fee = int(((baseline.acting_fee * max_tolerance) // 500) * 500)
            counter = ContractOffer(
                contract_start=proposed.contract_start,
                contract_end=proposed.contract_end,
                commission=proposed.commission,
                acting_fee=counter_fee,
                first_dollar_gross=baseline.first_dollar_gross,
                net_points=min(proposed.net_points, baseline.net_points + 1.0),
                bo_bonus_fee=min(proposed.bo_bonus_fee, int(baseline.acting_fee * 0.75)),
                bo_bonus_threshold=baseline.bo_bonus_threshold,
                acting_fee_bumps=baseline.acting_fee_bumps,
            )
            return "COUNTER", "\"Some terms need a little tweaking, here is our counter-offer.\"", counter
        else:
            # Studio walks away and recasts!
            role.offered_actor_id = None
            for cand in role.audition_results:
                if cand.actor_id != actor_id:
                    role.cast_actor_id = cand.actor_id
                    break
            for sub in self.submissions:
                if sub.film_id == film_id and sub.role_index == role_index and sub.actor_id == actor_id:
                    sub.status = "Lost"
            actor.schedule_status = "Available"
            actor.morale_score = max(10.0, actor.morale_score - 15.0)
            self.add_message(
                title=f"{film.studio_or_channel} turns down {actor.name} after negotiations sour",
                content=(
                    f"{film.studio_or_channel} was forced to recast the role of '{role.role_name}' in their upcoming project, "
                    f"'{film.title}', after contract negotiations between the agent of {actor.name} and the producers turned sour."
                ),
                category="general",
                sender_name=film.studio_or_channel,
                related_actor_id=actor_id,
                related_film_id=film_id,
            )
            return "REJECTED", "\"This is number one bullshit! We are wasting each other's time—we're recasting the role.\"", baseline

    def finalize_role_contract(self, film_id: int, role_index: int, actor_id: int, contract: ContractOffer) -> None:
        film = self.films[film_id]
        role = film.roles[role_index]
        actor = self.actors[actor_id]

        role.cast_actor_id = actor_id
        role.offered_actor_id = None
        actor.schedule_status = f"Contracted for '{film.title}'"
        actor.current_project_id = film_id
        actor.current_role_name = role.role_name

        # Clear any blocking offer message for this role
        for m in self.messages:
            if m.related_film_id == film_id and m.related_role_index == role_index and m.requires_response:
                m.requires_response = False

        for sub in self.submissions:
            if sub.film_id == film_id and sub.role_index == role_index and sub.actor_id == actor_id:
                sub.status = "Cast"

        # Pay acting fee & agency commission immediately
        comm_pct = actor.contract.commission if actor.contract else 10
        agency_cut = int(contract.acting_fee * (comm_pct / 100.0))
        self.record_actor_earning(
            actor,
            project_title=film.title,
            role_name=role.role_name,
            category="Acting Fee",
            gross_amount=contract.acting_fee,
            agency_cut=agency_cut,
            is_backend=False,
        )
        actor.this_year_all_roles += 1
        actor.career_roles += 1
        if role.role_type in ("Lead", "Major Support", "Series Regular"):
            actor.this_year_major_roles += 1
            self.player_agency.stats_major_roles += 1
        else:
            self.player_agency.stats_minor_roles += 1

        actor.morale_score = min(100.0, actor.morale_score + 12.0)
        actor.fame_score = min(100.0, actor.fame_score + (4.0 if role.role_type in ("Lead", "Series Regular") else 2.0))
        actor.update_fame_tier()
        actor.quotes = self.db.compute_actor_quotes(self.rng, actor.sex, actor.fame_tier)

        self.record_transaction(
            f"{comm_pct}% Commission: {actor.name} as '{role.role_name}' in '{film.title}' (Fee: ${contract.acting_fee:,})",
            agency_cut,
            actor_name=actor.name,
            project_title=film.title,
            payment_type="Acting Fee",
        )

        # Store backend bonus & points parameters for live weekly theatrical accrual
        if contract.bo_bonus_fee > 0 or contract.net_points > 0 or contract.first_dollar_gross > 0:
            self.pending_tasks.append({
                "type": "backend_check",
                "due": film.run_end_date or film.release_date,
                "film_id": film_id,
                "actor_id": actor_id,
                "role_name": role.role_name,
                "contract": contract,
                "paid_bo_bonus": False,
                "paid_points_total": 0,
            })
        # Register evergreen home-media backend deal (VHS / DVD / Streaming / TV Licensing forever!)
        if film.series_or_movie == "Movie" and (contract.net_points > 0 or contract.first_dollar_gross > 0):
            self.evergreen_backend_deals.append({
                "film_id": film_id,
                "actor_id": actor_id,
                "role_name": role.role_name,
                "contract": contract,
                "paid_home_media_total": 0,
                "unpaid_balance": 0.0,
            })

        self.add_message(
            title=f"{actor.name} signs contract for '{film.title}'",
            content=(
                f"{actor.name} is stepping aboard the upcoming {film.genre} project, '{film.title}', for {film.studio_or_channel}. "
                f"The actor will play the {role.role_type} role of '{role.role_name}'.\n\n"
                f"The studio has paid your client's acting fee of ${contract.acting_fee:,}. "
                f"Your agency's {comm_pct}% commission cut is ${agency_cut:,}.\n"
                f"Any contractual backend bonus, if triggered, will be paid during the theatrical run."
            ),
            category="filming",
            sender_name=film.studio_or_channel,
            related_actor_id=actor_id,
            related_film_id=film_id,
        )

    # -------------------------------------------------------------------------
    # Client Chat: Body Type, Acting School, Special Skills (with DISC Debate)
    # -------------------------------------------------------------------------
    def chat_with_client(self, actor_id: int, topic: str, target_value: str, tactic_disc: str = "") -> Tuple[bool, str]:
        """Persuade client to change bodytype, attend acting course, or learn special skill using DISC debate tactics."""
        actor = self.actors.get(actor_id)
        if not actor or actor.agency_id != 0:
            return False, "Only your own agency clients will chat with you."
        if actor.schedule_status.startswith("Filming"):
            return False, "\"Sorry, I'm on set filming right now and have no time for that!\""
        if actor.training_type is not None:
            return False, f"\"I'm already busy ({actor.schedule_status}) until {actor.training_end_date}!\""

        # Persuasion chance depends on player personal_skill + actor morale + DISC psychological tactic match!
        chance = 42 + int(self.player_agency.personal_skill * 0.45) + int((actor.morale_score - 50) * 0.35)
        if tactic_disc:
            if tactic_disc == actor.disc:
                chance += 32  # Nailed their DISC personality!
            elif (tactic_disc == "D" and actor.disc == "S") or (tactic_disc == "C" and actor.disc == "I"):
                chance -= 22  # Wrong psychological approach
            else:
                chance += 5

        if actor.personality in ("Stubborn", "Arrogant", "Lethargic", "Complacent"):
            chance -= 15
        elif actor.personality in ("Determined", "Passionate", "Energetic", "Responsible"):
            chance += 12

        if self.rng.randint(1, 100) > chance:
            refusals = {
                "bodyType": "\"Thanks, but I'm pleased with my body. I change body for nobody!\" (Hint: Match their DISC personality!)",
                "actingSchool": "\"Oh come on... you want penguins to teach an eagle how to fly?!\" (Hint: Match their DISC personality!)",
                "specialSkills": "\"I'm really not sure about that, chief... maybe next time, okay?\" (Hint: Match their DISC personality!)",
            }
            return False, refusals.get(topic, "\"Sorry, I have no time for that right now.\"")

        duration_days = self.rng.randint(14, 24)
        end_dt = (self.current_date + timedelta(days=duration_days)).strftime("%Y-%m-%d")
        actor.training_type = topic
        actor.training_target = target_value
        actor.training_end_date = end_dt

        if topic == "bodyType":
            actor.schedule_status = f"Changing bodytype to {target_value} (until {end_dt})"
            reply = f"\"Yeah baby, let's work that body! I'll transform to '{target_value}' by {end_dt}.\""
        elif topic == "actingSchool":
            actor.schedule_status = f"Attending {target_value} acting course (until {end_dt})"
            reply = f"\"Awesome. You know my credo: loyalty and royalty! I'll attend the {target_value} course until {end_dt}.\""
        else:
            actor.schedule_status = f"Learning '{target_value}' (until {end_dt})"
            reply = f"\"Hell yeah! Show me the way, chief! I'll master '{target_value}' by {end_dt}.\""

        return True, reply

    # -------------------------------------------------------------------------
    # Daily Simulation Loop
    # -------------------------------------------------------------------------
    def advance_day(self) -> Tuple[bool, str]:
        blocker = self.has_blocking_message()
        if blocker:
            return False, f"You have an important message that requires your response: '{blocker.title}'"

        self.current_date += timedelta(days=1)
        d_str = self.date_str
        msg_start_id = self.next_msg_id
        day_events: List[str] = []

        # 0. Annual Aging & Historical Talent Debuts on Jan 1
        if self.current_date.month == 1 and self.current_date.day == 1:
            self._process_new_year_aging_and_debuts()

        # 1. Monthly Agency Overhead on 1st of month (scales naturally with Agency Tier)
        if self.current_date.day == 1:
            if self.player_agency.reputation == "Major":
                self.player_agency.monthly_overhead = 25000
            elif self.player_agency.reputation == "Medium":
                self.player_agency.monthly_overhead = 12000
            else:
                self.player_agency.monthly_overhead = 4500
            overhead = self.player_agency.monthly_overhead
            self.record_transaction(
                f"Monthly agency office & staff overhead ({self.current_date.strftime('%B %Y')})",
                -overhead,
                payment_type="Overhead",
            )
            self._update_rankings()
            self.add_message(
                title="New 'Top Actors Chart' & Monthly Financial Statement",
                content=(
                    f"Tinsel Town has published its monthly 'Top Actors' rankings.\n\n"
                    f"Monthly agency overhead of ${overhead:,} has been deducted from your account. "
                    f"Current Agency Balance: ${self.player_agency.budget:,.0f}."
                ),
                category="general",
            )
            # Keep project pipeline bustling and varied
            for _ in range(self.rng.randint(8, 12)):
                self.generate_project("Movie")
            for _ in range(self.rng.randint(4, 6)):
                self.generate_project("TV")
            # Monthly home media sales (TV Licensing / VHS / DVD / Streaming) & evergreen backend payouts
            self._step_monthly_home_media_and_evergreen_backend()

        # 2. Weekly Box Office & TV Ratings update (Mondays)
        if self.current_date.weekday() == 0:
            for _ in range(self.rng.randint(2, 3)):
                self.generate_project("Movie")
            self.generate_project("TV")
            # Ensure casting slate never dries up
            open_movies = sum(1 for f in self.films.values() if f.series_or_movie == "Movie" and f.status == "Casting")
            while open_movies < 16:
                self.generate_project("Movie")
                open_movies += 1
            self._step_weekly_theatrical_runs()
            self._try_send_direct_casting_offer()

        # 3. Process Pending Tasks (Scouts, Script Doctors, Backend Bonuses)
        remaining_tasks: List[Dict[str, Any]] = []
        for task in self.pending_tasks:
            if task["due"] <= d_str:
                self._execute_pending_task(task)
            else:
                remaining_tasks.append(task)
        self.pending_tasks = remaining_tasks

        # 4. Process Actor Training Completions & Contract Expirations
        for actor in self.actors.values():
            # Rest recovery when not filming
            if not actor.schedule_status.startswith("Filming"):
                actor.condition_score = min(100.0, actor.condition_score + 1.5)

            if actor.training_type and actor.training_end_date and actor.training_end_date <= d_str:
                self._complete_actor_training(actor)

            if actor.agency_id == 0 and actor.contract and actor.contract.contract_end <= d_str:
                self._handle_contract_expiration(actor)

        # 5. Process Project Lifecycle (Submissions -> Auditions -> Decisions -> Filming -> Release)
        for film in list(self.films.values()):
            self._step_project_lifecycle(film, d_str)

        # 6. CheckAgency Tier Promotion & XML Event Triggers
        self._check_agency_tier_and_events()

        # 7. Annual Awards Season on January 15
        if self.current_date.month == 1 and self.current_date.day == 15:
            self._run_annual_awards()

        new_msgs = [m.title for m in self.messages if m.id >= msg_start_id]
        if new_msgs:
            summary = f"[{self.pretty_date}] " + " | ".join(new_msgs[:3])
            if len(new_msgs) > 3:
                summary += f" (+{len(new_msgs) - 3} more in Messages)"
            return True, summary
        return True, f"Advanced to {self.pretty_date}."

    def _execute_pending_task(self, task: Dict[str, Any]) -> None:
        ttype = task["type"]
        if ttype == "scout":
            actor = self.actors.get(task["actor_id"])
            if not actor:
                return
            tier = task["scout_tier"]
            reveal_count = 12 if tier == "Well-known" else (8 if tier == "Average" else 5)
            hidden_attrs = [a for a in CORE_ATTRIBUTES if not actor.known_attributes.get(a, False)]
            for a in self.rng.sample(hidden_attrs, k=min(len(hidden_attrs), reveal_count)):
                actor.known_attributes[a] = True
            actor.potential_known = True
            self.add_message(
                title=f"The Scouting Agency has finished assessing {actor.name}",
                content=(
                    f"The scouting report for {actor.name} is ready.\n\n"
                    f"- Current Overall: {actor.overall_rating} / 100\n"
                    f"- Projected Potential: {actor.potential_label} ({actor.potential_rating})\n\n"
                    "Open the actor's profile to inspect their uncovered skill ratings."
                ),
                category="general",
                sender_name="Scouting Agency",
                portrait_file="portraits/scout.png",
                related_actor_id=actor.id,
            )
        elif ttype == "consultant":
            film = self.films.get(task["film_id"])
            if not film:
                return
            tier = task["tier"]
            noise = 3 if tier == "Well-known" else (8 if tier == "Average" else 16)
            est = min(99, max(5, film.script_rating + self.rng.randint(-noise, noise)))
            film.consultant_rating = est
            if est < 25:
                verdict = "Verdict - It was probably written by the producer's poodle. Avoid like the bubonic plague!"
            elif est < 45:
                verdict = "Verdict - Revolutionary! Terrific! Sorry, just joking... it's crap."
            elif est < 65:
                verdict = "Verdict - Close, but no cigar. Feast of mediocrity."
            elif est < 82:
                verdict = "Verdict - Solid script. A good director and cast can turn it into a classic."
            else:
                verdict = "Verdict - Magnificent script! Bribe the producers to cast all the clients you have for this masterpiece."
            film.consultant_verdict = verdict
            self.add_message(
                title=f"The script doctor has finished reviewing '{film.title}'",
                content=f"Consultant Script Score: {est}%\n\n{verdict}",
                category="reviews",
                sender_name="Script Consultant",
                portrait_file="portraits/script.png",
                related_film_id=film.id,
            )
        elif ttype == "backend_check":
            self._accrue_backend_for_task(task, is_final=True)

    def _accrue_backend_for_task(self, task: Dict[str, Any], is_final: bool = False) -> None:
        """Constantly accrue backend bonuses and gross/net points week-by-week as box office rolls in."""
        film = self.films.get(task["film_id"])
        actor = self.actors.get(task["actor_id"])
        contract: ContractOffer = task["contract"]
        if not film or not actor or film.box_office_gross <= 0:
            return

        role_name = task.get("role_name") or "Cast"
        comm_pct = actor.contract.commission if actor.contract else 10
        wk_label = f" (Wk {film.box_office_weeks_run})" if film.box_office_weeks_run > 0 and not is_final else ""

        # 1. One-time Box Office Milestone Bonus (triggers immediately once threshold is crossed!)
        if contract.bo_bonus_fee > 0 and not task.get("paid_bo_bonus") and film.box_office_gross >= contract.bo_bonus_threshold:
            task["paid_bo_bonus"] = True
            bonus = int(contract.bo_bonus_fee)
            agency_cut = int(bonus * (comm_pct / 100.0))
            self.record_actor_earning(
                actor,
                project_title=film.title,
                role_name=role_name,
                category="Backend Bonus",
                gross_amount=bonus,
                agency_cut=agency_cut,
                is_backend=True,
            )
            self.record_transaction(
                f"Backend bonus commission ({comm_pct}%) for {actor.name} in '{film.title}'",
                agency_cut,
                actor_name=actor.name,
                project_title=film.title,
                payment_type="Backend Bonus",
            )
            self.add_message(
                title=f"{actor.name}'s Box Office Bonus triggered for '{film.title}'!",
                content=(
                    f"'{film.title}' crossed ${contract.bo_bonus_threshold:,} at the box office "
                    f"(currently ${film.box_office_gross:,}), triggering {actor.name}'s ${bonus:,} backend bonus!\n\n"
                    f"Your {comm_pct}% agency commission is ${agency_cut:,}."
                ),
                category="release",
                sender_name=film.studio_or_channel,
                related_actor_id=actor.id,
                related_film_id=film.id,
            )

        # 2. Live Incremental Gross Points / Net Profit Points (updates every week during the theatrical run!)
        pts_category = ""
        target_pts_total = 0
        if contract.first_dollar_gross > 0:
            pts_category = f"Gross Points{wk_label}"
            target_pts_total = int(film.box_office_gross * (contract.first_dollar_gross / 100.0) * 0.15)
        elif contract.net_points > 0 and film.box_office_gross > film.breakeven:
            pts_category = f"Net Points{wk_label}"
            profit = film.box_office_gross - film.breakeven
            target_pts_total = int(profit * (contract.net_points / 100.0) * 0.15)

        already_paid = int(task.get("paid_points_total") or 0)
        delta_pts = target_pts_total - already_paid
        if delta_pts > 0:
            task["paid_points_total"] = target_pts_total
            agency_cut = int(delta_pts * (comm_pct / 100.0))
            self.record_actor_earning(
                actor,
                project_title=film.title,
                role_name=role_name,
                category=pts_category or "Backend Points",
                gross_amount=delta_pts,
                agency_cut=agency_cut,
                is_backend=True,
            )
            self.record_transaction(
                f"Backend points commission ({comm_pct}%) for {actor.name} in '{film.title}'{wk_label}",
                agency_cut,
                actor_name=actor.name,
                project_title=film.title,
                payment_type="Backend Points",
            )
            if is_final:
                self.add_message(
                    title=f"Final backend points settled for {actor.name} on '{film.title}'",
                    content=(
                        f"'{film.title}' wrapped its theatrical run at ${film.box_office_gross:,}.\n"
                        f"Total backend points earned by {actor.name} across the run: ${target_pts_total:,}."
                    ),
                    category="release",
                    sender_name=film.studio_or_channel,
                    related_actor_id=actor.id,
                    related_film_id=film.id,
                )

    def _complete_actor_training(self, actor: Actor) -> None:
        ttype = actor.training_type
        target = actor.training_target or ""
        actor.training_type = None
        actor.training_target = None
        actor.training_end_date = None
        actor.schedule_status = "Available"

        if ttype == "bodyType":
            actor.bodytype = target
            self.add_message(
                title=f"{actor.name} has managed to switch to new bodytype",
                content=f"After weeks of hard work and suffering, {actor.name} has transformed their body type to '{target}'!",
                category="general",
                sender_name=actor.name,
                related_actor_id=actor.id,
            )
        elif ttype == "actingSchool":
            boosted = []
            for attr in self.rng.sample(CORE_ATTRIBUTES[:5], k=3):
                inc = self.rng.randint(4, 9)
                actor.attributes[attr] = min(100, actor.attributes.get(attr, 50) + inc)
                boosted.append(f" - {attr}: +{inc}")
            self.add_message(
                title=f"{actor.name} has finished acting course",
                content=f"After several weeks, {actor.name} has completed the '{target}' workshop.\n\nSkill improvements:\n" + "\n".join(boosted),
                category="general",
                sender_name=actor.name,
                related_actor_id=actor.id,
            )
        elif ttype == "specialSkills":
            if target and target not in actor.special_skills:
                actor.special_skills.append(target)
            self.add_message(
                title=f"{actor.name} has finished special training",
                content=f"After several weeks of practice, {actor.name} has mastered the special skill '{target}'!",
                category="general",
                sender_name=actor.name,
                related_actor_id=actor.id,
            )

    def _handle_contract_expiration(self, actor: Actor) -> None:
        if actor.morale_score >= 45:
            actor.contract.contract_start = self.date_str
            actor.contract.contract_end = (self.current_date + timedelta(days=365)).strftime("%Y-%m-%d")
            self.add_message(
                title=f"{actor.name} renews representation contract",
                content=f"\"You are the best agent ever! Let's extend our representation agreement for another year until {actor.contract.contract_end}.\"",
                category="general",
                sender_name=actor.name,
                related_actor_id=actor.id,
            )
        else:
            actor.agency_id = None
            actor.contract = None
            self.add_message(
                title=f"{actor.name} leaves your agency",
                content=f"Being unhappy with their career progress, {actor.name} decided to part ways upon the expiry of your representation agreement.",
                category="general",
                sender_name=actor.name,
                related_actor_id=actor.id,
            )

    def _step_project_lifecycle(self, film: FilmOrSeries, d_str: str) -> None:
        # Stage 1: Casting -> Auditioning
        if film.status == "Casting" and d_str >= film.submission_end_date:
            film.status = "Auditioning"
            allowed_tiers = ["Unknown", "Relatively unknown", "Average"]
            if film.studio_tier in ("A", "Broadcast"):
                allowed_tiers = ["Average", "Notable", "A-lister"]
            elif film.studio_tier in ("B", "Cable"):
                allowed_tiers = ["Relatively unknown", "Average", "Notable"]

            for role in film.roles:
                if role.role_type in ("Minor Support", "Guest Star"):
                    role_tiers = ["Unknown", "Relatively unknown", "Average"]
                else:
                    role_tiers = allowed_tiers

                # Add AI competing candidates of matching tier so every role has a realistic 2-4 actor audition pool
                ai_pool = [
                    a for a in self.actors.values()
                    if a.agency_id != 0
                    and a.sex == role.sex
                    and a.fame_tier in role_tiers
                    and a.id not in role.submitted_actor_ids
                    and not a.schedule_status.startswith("Filming")
                ]
                if not ai_pool:
                    ai_pool = [
                        a for a in self.actors.values()
                        if a.agency_id != 0
                        and a.sex == role.sex
                        and a.id not in role.submitted_actor_ids
                    ]
                if ai_pool:
                    comp_count = self.rng.randint(2, 3)
                    for comp in self.rng.sample(ai_pool, k=min(len(ai_pool), comp_count)):
                        role.submitted_actor_ids.append(comp.id)
                role.audition_actor_ids = list(role.submitted_actor_ids)

                for sub in self.submissions:
                    if sub.film_id == film.id and sub.role_index == role.index and sub.status == "Submitted":
                        sub.status = "Auditioning"
                        actor = self.actors.get(sub.actor_id)
                        if actor:
                            actor.schedule_status = f"Auditioning for '{film.title}' (Decision: {film.final_decision_date})"
                            self.add_message(
                                title=f"Audition day: {actor.name} for '{film.title}'",
                                content=(
                                    f"{actor.name} is auditioning for the {role.role_type} role of "
                                    f"'{role.role_name}' in '{film.title}'.\n\n"
                                    f"The producers will announce their final casting decision on {film.final_decision_date}."
                                ),
                                category="general",
                                sender_name=film.studio_or_channel,
                                related_actor_id=actor.id,
                                related_film_id=film.id,
                                related_role_index=role.index,
                            )

        # Stage 2: Auditioning -> Final Decision Date
        elif film.status == "Auditioning" and d_str >= film.final_decision_date:
            film.status = "Filming"
            for role in film.roles:
                candidates: List[AuditionCandidate] = []
                for aid in role.audition_actor_ids:
                    act = self.actors.get(aid)
                    if act:
                        candidates.append(self.score_audition_candidate(act, film, role))
                candidates.sort(key=lambda c: c.points, reverse=True)
                if candidates:
                    candidates[0].won = True
                    role.audition_results = candidates
                    winner_id = candidates[0].actor_id
                    winner = self.actors[winner_id]

                    if winner.agency_id == 0:
                        # Player's actor won the audition! Send blocking contract offer message!
                        role.offered_actor_id = winner_id
                        winner.schedule_status = f"WON AUDITION: '{role.role_name}' in '{film.title}' (Awaiting Contract)"
                        for sub in self.submissions:
                            if sub.film_id == film.id and sub.role_index == role.index and sub.actor_id == winner_id:
                                sub.status = "Offered"
                        self.add_message(
                            title=f"WON AUDITION: {winner.name} landed '{role.role_name}' in '{film.title}'!",
                            content=(
                                f"{winner.name} won the audition for the {role.role_type} role of '{role.role_name}' "
                                f"in {film.studio_or_channel}'s upcoming {film.genre} project, '{film.title}' "
                                f"(Audition Score: {candidates[0].points}).\n\n"
                                f"Click 'Negotiate Role Contract' below to finalize your client's deal with {film.studio_or_channel}, "
                                f"or 'View Audition Report' to inspect the full scorecard."
                            ),
                            category="general",
                            severity="Important",
                            sender_name=film.studio_or_channel,
                            related_actor_id=winner_id,
                            related_film_id=film.id,
                            related_role_index=role.index,
                            buttons=[
                                MessageButton(
                                    title="Negotiate Role Contract",
                                    command=f"ROLE_OFFER:{film.id}:{role.index}:{winner_id}",
                                    blocker=True,
                                ),
                                MessageButton(
                                    title="View Audition Report",
                                    command=f"AUDITION_REPORT:{film.id}:{role.index}",
                                    blocker=False,
                                ),
                            ],
                        )
                    else:
                        role.cast_actor_id = winner_id
                        # Notify player if any of player's actors lost this audition
                        for sub in self.submissions:
                            if sub.film_id == film.id and sub.role_index == role.index and sub.status == "Auditioning":
                                sub.status = "Lost"
                                loser = self.actors.get(sub.actor_id)
                                if loser:
                                    if loser.schedule_status.startswith("Auditioning") or loser.schedule_status.startswith("Submitted"):
                                        loser.schedule_status = "Available"
                                    loser.morale_score = max(10.0, loser.morale_score - 6.0)
                                    loser_cand = next((c for c in candidates if c.actor_id == loser.id), None)
                                    score_line = (
                                        f"Your Client's Score: {loser_cand.points} pts vs. Winner {winner.name}: {candidates[0].points} pts\n"
                                        if loser_cand else ""
                                    )
                                    self.add_message(
                                        title=f"Audition Result: {loser.name} missed out on '{role.role_name}' in '{film.title}'",
                                        content=(
                                            f"{loser.name} was not selected in the audition for the role of '{role.role_name}' in '{film.title}'.\n"
                                            f"The role went to {winner.name} ({candidates[0].agency_name}).\n"
                                            f"{score_line}\n"
                                            f"Click 'View Audition Report' below to see the pros, cons, and scorecard breakdown."
                                        ),
                                        category="general",
                                        sender_name=film.studio_or_channel,
                                        related_actor_id=loser.id,
                                        related_film_id=film.id,
                                        related_role_index=role.index,
                                        buttons=[
                                            MessageButton(
                                                title="View Audition Report",
                                                command=f"AUDITION_REPORT:{film.id}:{role.index}",
                                                blocker=False,
                                            )
                                        ],
                                    )

        # Stage 3: Filming -> Per-role Early Wrap (Guest Stars / Recurring / Minor Support) & Full Project Wrap
        elif film.status == "Filming":
            director = self.creatives.get(film.director_id)
            dir_skill = director.personal_skill if director else 60
            project_wrapped = d_str >= film.filming_end_date
            if project_wrapped:
                film.status = "Post-Production"

            for role in film.roles:
                if not role.cast_actor_id:
                    continue
                act = self.actors.get(role.cast_actor_id)
                if not act or act.current_project_id != film.id:
                    continue
                role_done = project_wrapped or (bool(role.filming_end) and d_str >= role.filming_end)
                if not role_done:
                    continue
                act.schedule_status = "Available"
                act.current_project_id = None
                act.current_role_name = None
                fatigue = self.rng.randint(5, 12) if role.role_type in ("Guest Star", "Recurring") else self.rng.randint(15, 30)
                act.condition_score = max(20.0, act.condition_score - fatigue)
                # Attribute growth from filming
                grown = []
                for attr in self.rng.sample(CORE_ATTRIBUTES[:5], k=2):
                    delta = 2 if dir_skill >= 55 else 1
                    act.attributes[attr] = min(100, act.attributes.get(attr, 50) + delta)
                    grown.append(f" - {attr}: increased (+{delta})")
                if act.agency_id == 0:
                    exp_word = "fantastic" if dir_skill >= 70 else ("so-so" if dir_skill >= 45 else "exhausting")
                    self.add_message(
                        title=f"{act.name} wraps filming '{role.role_name}' on '{film.title}'",
                        content=(
                            f"{act.name} has completed filming their {role.role_type} role ('{role.role_name}') on '{film.title}' "
                            f"in {film.filming_location} and is now Available for new submissions!\n\n"
                            f"Your client says work on set with Director {director.name if director else 'the crew'} was {exp_word} "
                            f"and affected the following attributes:\n" + "\n".join(grown)
                        ),
                        category="filming",
                        sender_name=act.name,
                        related_actor_id=act.id,
                        related_film_id=film.id,
                    )

        # Stage 4: Post-Production -> Release / Premiere & Critic Reviews
        elif film.status == "Post-Production" and d_str >= film.release_date:
            self._evaluate_release_and_reviews(film)

        # Stage 5: TV Pilot / Season Renewal or Cancellation Decision
        elif film.status == "Airing" and film.tv_decision_date and d_str >= film.tv_decision_date:
            self._decide_tv_series_fate(film)

    def _step_weekly_theatrical_runs(self) -> None:
        """Movies build box office gross week by week over a 4-week theatrical run."""
        week_shares = [0.42, 0.27, 0.18, 0.13]
        for film in self.films.values():
            if film.series_or_movie == "Movie" and film.status == "In Theaters":
                wk = film.box_office_weeks_run
                if wk < len(week_shares):
                    add_gross = int(film.box_office_target_gross * week_shares[wk] * self.rng.uniform(0.92, 1.08))
                    film.box_office_gross += add_gross
                    film.box_office_weeks_run += 1
                    # Accrue live weekly backend bonuses & gross/net points as box office rolls in!
                    for task in self.pending_tasks:
                        if task.get("type") == "backend_check" and task.get("film_id") == film.id:
                            self._accrue_backend_for_task(task, is_final=False)
                if film.box_office_weeks_run >= len(week_shares) or self.date_str >= film.run_end_date:
                    film.status = "Released"
                    # Update cast credit gross string & notify player if client starred
                    for r in film.roles:
                        if r.cast_actor_id and r.cast_actor_id in self.actors:
                            a = self.actors[r.cast_actor_id]
                            for cr in a.credits:
                                if cr.get("title") == film.title:
                                    cr["gross_or_rating"] = f"${film.box_office_gross:,}"
                            if a.agency_id == 0:
                                self.add_message(
                                    title=f"'{film.title}' ends box office run (${film.box_office_gross:,})",
                                    content=(
                                        f"After 4 weeks in cinemas, '{film.title}' (starring {a.name}) finished its worldwide theatrical run "
                                        f"with a total box office gross of ${film.box_office_gross:,} (Budget: ${film.budget:,})."
                                    ),
                                    category="release",
                                    sender_name=film.studio_or_channel,
                                    related_actor_id=a.id,
                                    related_film_id=film.id,
                                )

    @staticmethod
    def _get_era_home_media_weights(year: int) -> Dict[str, float]:
        """Historically accurate home-media format weights by calendar year (TV Licensing, VHS, DVD, Streaming)."""
        # TV broadcast / cable licensing exists in all eras
        tv_w = 0.30 if year < 1978 else (0.22 if year < 2000 else 0.14)

        # VHS / Home Video era: 1978 -> 2007
        if year < 1978 or year > 2007:
            vhs_w = 0.0
        elif year <= 1984:
            vhs_w = 0.15 + (year - 1978) * 0.10
        elif year <= 1999:
            vhs_w = 0.85
        else:
            vhs_w = max(0.05, 0.85 - (year - 1999) * 0.11)

        # DVD / Blu-ray era: 1997 -> present (massive 2000-2011 boom, collector tail after 2020)
        if year < 1997:
            dvd_w = 0.0
        elif year <= 2000:
            dvd_w = 0.25 + (year - 1997) * 0.25
        elif year <= 2011:
            dvd_w = 1.25
        elif year <= 2020:
            dvd_w = max(0.18, 1.25 - (year - 2011) * 0.12)
        else:
            dvd_w = 0.12

        # Streaming & Digital VOD era: 2008 -> present
        if year < 2008:
            stream_w = 0.0
        elif year <= 2013:
            stream_w = 0.15 + (year - 2008) * 0.14
        else:
            stream_w = 1.05

        return {"tv": tv_w, "vhs": vhs_w, "dvd": dvd_w, "streaming": stream_w}

    def _step_monthly_home_media_and_evergreen_backend(self) -> None:
        """
        Every month, released movies earn era-appropriate TV Licensing, VHS, DVD/Blu-ray,
        and Streaming/VOD sales with smooth decay and a permanent evergreen floor — paying
        evergreen backend points forever!
        """
        yr = self.current_date.year
        weights = self._get_era_home_media_weights(yr)
        total_market = sum(weights.values())
        if total_market <= 0:
            return

        # Primary format label for ledger entries in this calendar year
        top_fmt_key = max(weights.items(), key=lambda kv: kv[1])[0]
        fmt_labels = {
            "tv": "TV Licensing Backend",
            "vhs": "VHS / Home Video Backend",
            "dvd": "DVD / Blu-ray Backend",
            "streaming": "Streaming / VOD Backend",
        }
        primary_label = fmt_labels.get(top_fmt_key, "Home Media Backend")

        monthly_film_rev: Dict[int, int] = {}
        for film in self.films.values():
            if film.series_or_movie != "Movie" or film.status != "Released":
                continue
            film.months_since_release += 1
            rev_score = film.review_score if film.review_score is not None else 55
            # Classics decay slower and keep a higher permanent evergreen floor
            if rev_score >= 78:
                decay_rate = 0.94
                evergreen_floor = 0.020
            elif rev_score >= 58:
                decay_rate = 0.91
                evergreen_floor = 0.011
            else:
                decay_rate = 0.87
                evergreen_floor = 0.006

            decay_factor = max(evergreen_floor, decay_rate ** film.months_since_release)
            anchor = max(film.box_office_gross, int(film.budget * 0.5))
            if anchor <= 0:
                continue

            # Scale by era total market size (e.g. 2004 DVD boom > 1965 TV-only era!)
            raw_month = anchor * 0.055 * total_market * decay_factor * self.rng.uniform(0.88, 1.12)
            month_rev = max(2500, int(round(raw_month)))

            tv_add = int(round(month_rev * (weights["tv"] / total_market)))
            vhs_add = int(round(month_rev * (weights["vhs"] / total_market)))
            dvd_add = int(round(month_rev * (weights["dvd"] / total_market)))
            str_add = max(0, month_rev - tv_add - vhs_add - dvd_add)

            film.tv_licensing_revenue += tv_add
            film.vhs_revenue += vhs_add
            film.dvd_revenue += dvd_add
            film.streaming_revenue += str_add
            film.home_media_revenue += month_rev
            monthly_film_rev[film.id] = month_rev

        # Accrue & pay evergreen backend points forever
        is_jan = self.current_date.month == 1
        for deal in self.evergreen_backend_deals:
            fid = deal["film_id"]
            month_rev = monthly_film_rev.get(fid, 0)
            if month_rev <= 0:
                continue
            film = self.films.get(fid)
            actor = self.actors.get(deal["actor_id"])
            contract: ContractOffer = deal["contract"]
            if not film or not actor:
                continue

            accrual = 0.0
            if contract.first_dollar_gross > 0:
                accrual = month_rev * (contract.first_dollar_gross / 100.0) * 0.14
            elif contract.net_points > 0 and (film.box_office_gross + film.home_media_revenue) > film.breakeven:
                accrual = month_rev * (contract.net_points / 100.0) * 0.12

            if accrual <= 0:
                continue
            deal["unpaid_balance"] = float(deal.get("unpaid_balance", 0.0)) + accrual

            # Cut a clean residual/backend check once >= $500 accrues (or annually in Jan if >= $25)
            threshold = 25.0 if is_jan else 500.0
            if deal["unpaid_balance"] >= threshold:
                payout = int(deal["unpaid_balance"])
                deal["unpaid_balance"] -= payout
                deal["paid_home_media_total"] = int(deal.get("paid_home_media_total", 0)) + payout

                comm_pct = (actor.contract.commission if actor.contract else 10) if actor.agency_id == 0 else 0
                agency_cut = int(payout * (comm_pct / 100.0)) if comm_pct > 0 else 0
                self.record_actor_earning(
                    actor,
                    project_title=film.title,
                    role_name=deal.get("role_name") or "Cast",
                    category=primary_label,
                    gross_amount=payout,
                    agency_cut=agency_cut,
                    is_backend=True,
                )
                if agency_cut > 0:
                    self.record_transaction(
                        f"{primary_label} ({comm_pct}%): {actor.name} — '{film.title}'",
                        agency_cut,
                        actor_name=actor.name,
                        project_title=film.title,
                        payment_type="Home Media Backend",
                    )

    def _try_send_direct_casting_offer(self) -> None:
        """Studios occasionally send Direct Casting Offers (no audition required!) to your established clients."""
        eligible_clients = [
            a for a in self.actors.values()
            if a.agency_id == 0
            and a.fame_tier in ("Average", "Notable", "A-lister")
            and a.schedule_status == "Available"
        ]
        if not eligible_clients or self.rng.random() > 0.25:
            return
        actor = self.rng.choice(eligible_clients)
        for film in self.films.values():
            if film.status != "Casting":
                continue
            for role in film.roles:
                if role.cast_actor_id is None and role.offered_actor_id is None and role.sex == actor.sex and role.ethnicity in ("Any", actor.ethnicity):
                    role.casting_type = "Direct"
                    role.offered_actor_id = actor.id
                    actor.schedule_status = f"DIRECT OFFER: '{role.role_name}' in '{film.title}'"
                    self.submissions.append(SubmissionRecord(actor.id, film.id, role.index, "Offered"))
                    self.add_message(
                        title=f"DIRECT OFFER: {actor.name} offered '{role.role_name}' in '{film.title}'!",
                        content=(
                            f"{film.studio_or_channel} was so impressed by {actor.name}'s reputation ({actor.fame_tier}) that they skipped auditions "
                            f"and sent a DIRECT CASTING OFFER for the {role.role_type} role of '{role.role_name}' in their upcoming {film.genre} project, '{film.title}'!\n\n"
                            f"Click 'Negotiate Role Contract' below to negotiate their pay and backend points."
                        ),
                        category="general",
                        severity="Important",
                        sender_name=film.studio_or_channel,
                        related_actor_id=actor.id,
                        related_film_id=film.id,
                        related_role_index=role.index,
                        buttons=[
                            MessageButton(
                                title="Negotiate Role Contract",
                                command=f"ROLE_OFFER:{film.id}:{role.index}:{actor.id}",
                                blocker=True,
                            )
                        ],
                    )
                    return

    def _decide_tv_series_fate(self, film: FilmOrSeries) -> None:
        """Evaluates whether a TV Pilot gets a full series order or a running TV show is Renewed / Cancelled."""
        threshold = 2.6 if film.studio_tier == "Broadcast" else 1.8
        renewed = film.tv_average_rating >= threshold

        if renewed:
            was_pilot = film.is_pilot
            film.is_pilot = False
            film.season += 1
            film.status = "Airing"
            film.tv_decision_date = (self.current_date + timedelta(days=90)).strftime("%Y-%m-%d")
            film.tv_average_rating = round(max(0.5, film.tv_average_rating + self.rng.uniform(-0.4, 0.5)), 2)

            for r in film.roles:
                if r.role_type != "Series Regular":
                    continue
                if r.cast_actor_id and r.cast_actor_id in self.actors:
                    act = self.actors[r.cast_actor_id]
                    if act.agency_id == 0:
                        # Pay automatic season renewal fee + acting fee bump!
                        base_q = act.quotes.get(r.role_type, 35000)
                        bumped_fee = int(base_q * (1.0 + 0.15 * (film.season - 1)))
                        comm_pct = act.contract.commission if act.contract else 10
                        cut = int(bumped_fee * (comm_pct / 100.0))
                        self.record_actor_earning(
                            act,
                            project_title=film.title,
                            role_name=f"{r.role_name} (Season {film.season})",
                            category="TV Renewal",
                            gross_amount=bumped_fee,
                            agency_cut=cut,
                            is_backend=False,
                        )
                        act.morale_score = min(100.0, act.morale_score + 12.0)
                        self.record_transaction(
                            f"TV Season {film.season} Renewal ({comm_pct}%): {act.name} in '{film.title}' (Fee: ${bumped_fee:,})",
                            cut,
                            actor_name=act.name,
                            project_title=film.title,
                            payment_type="Acting Fee",
                        )
                        headline = f"'{film.title}' gets full series order!" if was_pilot else f"{film.studio_or_channel} renews '{film.title}' for Season {film.season}!"
                        self.add_message(
                            title=headline,
                            content=(
                                f"Great news! {film.studio_or_channel} confirmed that '{film.title}' has been picked up for Season {film.season} "
                                f"after earning a {film.tv_average_rating} demo rating.\n\n"
                                f"{act.name}'s series option was extended with an Acting Fee Bump to ${bumped_fee:,}. "
                                f"Your agency received ${cut:,} in commission!"
                            ),
                            category="release",
                            sender_name=film.studio_or_channel,
                            related_actor_id=act.id,
                            related_film_id=film.id,
                        )
        else:
            film.status = "Cancelled"
            for r in film.roles:
                if r.role_type != "Series Regular":
                    continue
                if r.cast_actor_id and r.cast_actor_id in self.actors:
                    act = self.actors[r.cast_actor_id]
                    if act.agency_id == 0:
                        act.morale_score = max(10.0, act.morale_score - 12.0)
                        headline = f"{film.studio_or_channel} passes on pilot '{film.title}'" if film.is_pilot else f"'{film.title}' CANCELLED by {film.studio_or_channel}"
                        self.add_message(
                            title=headline,
                            content=(
                                f"{film.studio_or_channel} confirmed that '{film.title}' will not return due to disappointing ratings ({film.tv_average_rating}).\n\n"
                                f"{act.name} is devastated: \"Why did they axe my show? There are shittier series they renewed without flinching!\"\n"
                                f"Your client's TV option has ended and they are available for new projects."
                            ),
                            category="release",
                            sender_name=film.studio_or_channel,
                            related_actor_id=act.id,
                            related_film_id=film.id,
                        )

    def _evaluate_release_and_reviews(self, film: FilmOrSeries) -> None:
        director = self.creatives.get(film.director_id)
        dir_bonus = ((director.knowledge_skill if director else 55) - 50) * 0.35
        cast_skills = []
        cast_fame = 0.0
        for r in film.roles:
            if r.cast_actor_id and r.cast_actor_id in self.actors:
                a = self.actors[r.cast_actor_id]
                avg_s = sum(a.attributes.get(k, 50) for k in CORE_ATTRIBUTES[:5]) / 5.0
                cast_skills.append(avg_s)
                cast_fame += a.fame_score
        cast_avg = (sum(cast_skills) / len(cast_skills)) if cast_skills else 55.0

        raw_score = film.script_rating * 0.55 + cast_avg * 0.35 + dir_bonus + self.rng.uniform(-8, 8)
        review_score = min(99, max(6, int(round(raw_score))))
        film.review_score = review_score

        if review_score >= 78:
            verdict_tag = "is a critics' darling"
            blurb = f"Newly released '{film.title}' is getting stellar reviews ({review_score}% on Box Office Butcher) all around the world!"
        elif review_score >= 52:
            verdict_tag = "receives lukewarm reviews"
            blurb = f"Newly released '{film.title}' is getting mixed-to-decent reviews ({review_score}% on Box Office Butcher)."
        elif review_score >= 30:
            verdict_tag = "is bashed by critics"
            blurb = f"Newly released '{film.title}' is getting poor reviews ({review_score}% on Box Office Butcher)."
        else:
            verdict_tag = "is labelled 'one of the worst ever'"
            blurb = f"'{film.title}' is getting atrocious reviews ({review_score}% on Box Office Butcher) all around the world..."
        film.review_blurb = blurb

        if film.series_or_movie == "Movie":
            mult = (review_score / 50.0) * (1.0 + min(1.5, cast_fame / 800.0)) * self.rng.uniform(0.75, 1.45)
            film.box_office_target_gross = int(film.budget * mult)
            # Opening weekend gross (~35% of total run); remaining weeks build in _step_weekly_theatrical_runs
            film.box_office_gross = int(film.box_office_target_gross * 0.35)
            film.box_office_weeks_run = 1
            film.status = "In Theaters"
        else:
            film.tv_average_rating = round(max(0.3, (review_score / 22.0) + (cast_fame / 600.0) + self.rng.uniform(-0.4, 0.8)), 2)
            film.status = "Airing"
            film.tv_decision_date = (self.current_date + timedelta(days=28)).strftime("%Y-%m-%d")

        # Update every cast actor's credits, review stats, fame, and send message if ours
        for r in film.roles:
            if r.cast_actor_id and r.cast_actor_id in self.actors:
                a = self.actors[r.cast_actor_id]
                a.credits.insert(0, {
                    "year": self.current_date.year,
                    "title": film.title,
                    "type": film.series_or_movie,
                    "genre": film.genre,
                    "role": r.role_name,
                    "role_type": r.role_type,
                    "review": review_score,
                    "gross_or_rating": f"${film.box_office_gross:,}" if film.series_or_movie == "Movie" else f"{film.tv_average_rating} rating",
                })
                if a.this_year_highest_review == 0 or review_score > a.this_year_highest_review:
                    a.this_year_highest_review = review_score
                if a.this_year_lowest_review == 0 or review_score < a.this_year_lowest_review:
                    a.this_year_lowest_review = review_score

                fame_delta = (review_score - 42) * (0.45 if r.role_type in ("Lead", "Series Regular") else 0.22)
                a.fame_score = min(1000.0, max(1.0, round(a.fame_score + fame_delta, 1)))
                a.update_fame_tier()
                a.quotes = self.db.compute_actor_quotes(self.rng, a.sex, a.fame_tier)

                if a.agency_id == 0:
                    if review_score >= 72:
                        a.morale_score = min(100.0, a.morale_score + 15.0)
                        reaction = "\"Man, does it feel frickin' awesome?! Thank you for landing this marvellous role, you are my hero!\""
                    elif review_score >= 45:
                        reaction = "\"The comments about my performance are fairish. Let's say we are making progress!\""
                    else:
                        a.morale_score = max(10.0, a.morale_score - 15.0)
                        reaction = "\"Those nasty words about our project... they are humiliating! Book me better scripts next time!\""

                    perf_str = (
                        f"Box Office Gross: ${film.box_office_gross:,} (Budget: ${film.budget:,})"
                        if film.series_or_movie == "Movie"
                        else f"Premiere 18-49 Demo Rating: {film.tv_average_rating}"
                    )
                    self.add_message(
                        title=f"'{film.title}' {verdict_tag} ({review_score}%)",
                        content=f"{blurb}\n{perf_str}\n\n{a.name} ({r.role_name}):\n{reaction}",
                        category="reviews",
                        sender_name="Box Office Butcher",
                        related_actor_id=a.id,
                        related_film_id=film.id,
                    )

    def _check_agency_tier_and_events(self) -> None:
        # Agency tier promotion
        my_clients = [a for a in self.actors.values() if a.agency_id == 0]
        client_fame_sum = sum(a.fame_score for a in my_clients)
        self.player_agency.reputation_score = round(
            12.0 + len(my_clients) * 2.5 + (client_fame_sum / 35.0) + (self.player_agency.stats_income / 15000.0), 1
        )
        old_rep = self.player_agency.reputation
        if self.player_agency.budget >= 200_000 and self.player_agency.reputation_score >= 45.0:
            if self.player_agency.budget >= 1_000_000 and self.player_agency.reputation_score >= 95.0:
                self.player_agency.reputation = "Major"
            else:
                self.player_agency.reputation = "Medium"
        if self.player_agency.reputation != old_rep:
            self.add_message(
                title=f"Agency Reputation Upgraded to {self.player_agency.reputation.upper()}!",
                content=(
                    f"Congratulations! {self.player_agency.name} is now recognized across Hollywoodland as a "
                    f"**{self.player_agency.reputation}** talent agency!\n\n"
                    f"Higher-tier stars (including Notable and A-list talent) will now take your contract offers seriously."
                ),
                category="general",
                severity="Important",
            )

        # Agency $100k cash reserve milestone
        if self.player_agency.budget > 100_000 and "100kmilestone" not in self.fired_events:
            self.fired_events.add("100kmilestone")
            self.player_agency.knowledge_skill = min(100, self.player_agency.knowledge_skill + 10)
            self.player_agency.personal_skill = min(100, self.player_agency.personal_skill + 10)
            self.add_message(
                title="Agency Milestone: $100,000 Cash Reserve!",
                content=(
                    f"{self.player_agency.name} has crossed $100,000 in operating reserves!\n\n"
                    "Industry insiders are taking notice of your growing momentum. Keep building your roster and "
                    "booking stronger roles to reach Medium agency status ($200,000 budget and 45+ Reputation).\n\n"
                    "(Bonus: Your Manager Knowledge Skill and Personal Skill both increased by +10!)"
                ),
                category="general",
                severity="Important",
                sender_name="Hollywoodland Trade Wire",
            )

        # Trigger authentic root events at a natural pace (at least 18-30 days between random events, ~2.5% daily chance)
        days_since_ev = (self.current_date - self.last_random_event_date).days
        if my_clients and days_since_ev >= 18 and self.rng.random() < 0.03:
            actor = self.rng.choice(my_clients)
            if self._trigger_random_actor_event(actor):
                self.last_random_event_date = self.current_date

    def _check_event_conditions(self, ev: Dict[str, Any], actor: Actor) -> bool:
        attr_map = {
            "characterization": "Characterization",
            "improvisation": "Improvisation",
            "vocalExpression": "Vocal Expression",
            "physicalExpression": "Physical Expression",
            "facialExpression": "Facial Expression",
            "intelligence": "Intelligence",
            "charisma": "Charisma",
            "humor": "Humor",
            "commitment": "Commitment",
            "confidence": "Confidence",
            "professionalism": "Professionalism",
            "stamina": "Stamina",
        }
        for c in ev.get("conditions", []):
            mem = c.get("member", "")
            rel = c.get("relation", "")
            val_str = str(c.get("value", "")).strip()

            if mem == "sex":
                if rel == "equal" and actor.sex.lower() != val_str.lower():
                    return False
            elif mem == "age":
                v = float(val_str or 0)
                if rel == "greater" and not (actor.age > v):
                    return False
                if rel == "less" and not (actor.age < v):
                    return False
            elif mem == "bodytype":
                if rel == "equal" and actor.bodytype.lower() != val_str.lower():
                    return False
                if rel == "notEqual" and actor.bodytype.lower() == val_str.lower():
                    return False
            elif mem == "fameScore":
                v = float(val_str or 0)
                if rel == "greater" and not (actor.fame_score > v):
                    return False
                if rel == "less" and not (actor.fame_score < v):
                    return False
            elif mem == "moraleScore":
                v = float(val_str or 0)
                if rel == "greater" and not (actor.morale_score > v):
                    return False
                if rel == "less" and not (actor.morale_score < v):
                    return False
            elif mem == "conditionScore":
                v = float(val_str or 0)
                if rel == "greater" and not (actor.condition_score > v):
                    return False
                if rel == "less" and not (actor.condition_score < v):
                    return False
            elif mem == "stats.thisyear.income":
                v = float(val_str or 0)
                if rel == "greater" and not (actor.this_year_income > v):
                    return False
                if rel == "less" and not (actor.this_year_income < v):
                    return False
            elif mem == "personalInfo":
                if rel == "contains" and val_str not in actor.personal_info:
                    return False
                if rel == "doesntContain" and val_str in actor.personal_info:
                    return False
            elif mem in attr_map:
                # Original XML attributes are on 0-200 scale; our attributes are 1-100
                v = float(val_str or 0) / 2.0
                act_v = float(actor.attributes.get(attr_map[mem], 50))
                if rel == "greater" and not (act_v > v):
                    return False
                if rel == "less" and not (act_v < v):
                    return False
        return True

    @staticmethod
    def _is_legacy_story_event(ev: Dict[str, Any]) -> bool:
        """Filter out scripted Cattle Call storyline / ex-partner / mafia / dated personal-drama events."""
        eid = ev.get("id", "").replace("\\", "/").lower()
        blocked_prefixes = (
            "awards/",
            "mafia",
            "reputations/",
            "stalker",
            "broke/",
            "outofthecloset/",
            "actorscript/",
            "adultery/",
            "actorfund/",
        )
        blocked_ids = {
            "100kmilestone.evt",
            "busynewrecruits.evt",
            "drought.evt",
            "overheaddeducmessage.evt",
            "scoutingagent.evt",
            "scriptconsultant.evt",
            "submitrules.evt",
            "homophobetweet.evt",
            "christianity_female.evt",
            "christianity_male.evt",
            "scientology_joins.evt",
            "paygapactor.evt",
            "paygapactorblacklisted.evt",
            "beatsuprandomguy.evt",
            "beatsuprandom_myagency.evt",
            "strippertalent.evt",
        }
        if eid in blocked_ids or any(eid.startswith(p) for p in blocked_prefixes):
            return True
        for a in ev.get("actions", []):
            if a.get("type") != "sendMessage":
                continue
            attr = a.get("attrib", {})
            portrait = (attr.get("portraitimagefile") or "").replace("\\", "/").lower()
            if "partner.png" in portrait or "mafia.png" in portrait or "talentescsaj.png" in portrait:
                return True
            blob = f"{attr.get('title', '')} {attr.get('content', '')}".lower()
            if any(w in blob for w in ("cattle call", "luigi", "vaffanculo", "strunz", "bobby ewing", "aloha partner")):
                return True
        return False

    def _trigger_random_actor_event(self, actor: Actor) -> bool:
        # Skip mature/drinking/scandal events for actors under 18
        if actor.age < 18:
            return False
        # Only pick TRUE ROOT events (never parentTriggers, follow-ups, or legacy story events!)
        candidates = [
            e for e in self.db.events
            if e.get("entityType") == "myActors"
            and e["id"].replace("\\", "/").lower() not in self.child_event_ids
            and e["id"] not in self.fired_events
            and not self._is_legacy_story_event(e)
            and any(a.get("type") == "sendMessage" for a in e.get("actions", []))
            and self._check_event_conditions(e, actor)
        ]
        if not candidates:
            return False
        ev = self.rng.choice(candidates)
        self.fired_events.add(ev["id"])
        self.execute_event_by_id(ev["id"], actor.id)
        return True

    def execute_event_by_id(self, event_id: str, actor_id: Optional[int] = None) -> None:
        norm_id = event_id.replace("\\", "/").strip()
        if not norm_id:
            return
        if norm_id.lower() == "#terminatecontract":
            if actor_id and actor_id in self.actors:
                act = self.actors[actor_id]
                act.agency_id = None
                act.contract = None
                act.schedule_status = "Available"
            return

        ev = self.events_by_id.get(norm_id.lower())
        if not ev:
            return
        actor = self.actors.get(actor_id) if actor_id else None

        attr_map = {
            "characterization": "Characterization",
            "improvisation": "Improvisation",
            "vocalExpression": "Vocal Expression",
            "physicalExpression": "Physical Expression",
            "facialExpression": "Facial Expression",
            "intelligence": "Intelligence",
            "charisma": "Charisma",
            "humor": "Humor",
            "commitment": "Commitment",
            "confidence": "Confidence",
            "professionalism": "Professionalism",
            "stamina": "Stamina",
        }

        for act in ev.get("actions", []):
            atype = act.get("type")
            at = act.get("attrib", {})
            if atype in ("modifyParameter1", "modifyParameter2"):
                mem = at.get("memberName", "")
                op = at.get("operation", "+")
                val_str = str(at.get("value", "0")).strip()
                try:
                    val = float(val_str)
                except ValueError:
                    val = 0.0

                if mem == "budget":
                    delta = int(val) if op == "+" else -int(val)
                    self.record_transaction(
                        f"Agency event ({ev['id']})" + (f" — {actor.name}" if actor else ""),
                        delta,
                        actor_name=actor.name if actor else "",
                        payment_type="General",
                    )
                elif mem == "knowledgeSkill":
                    self.player_agency.knowledge_skill = min(100, max(1, self.player_agency.knowledge_skill + (int(val) if op == "+" else -int(val))))
                elif mem == "personalSkill":
                    self.player_agency.personal_skill = min(100, max(1, self.player_agency.personal_skill + (int(val) if op == "+" else -int(val))))
                elif mem == "negotiationSkill":
                    self.player_agency.negotiation_skill = min(100, max(1, self.player_agency.negotiation_skill + (int(val) if op == "+" else -int(val))))
                elif actor is not None:
                    if mem == "moraleScore":
                        actor.morale_score = min(100.0, max(0.0, actor.morale_score + (val if op == "+" else -val)))
                    elif mem == "fameScore":
                        actor.fame_score = min(1000.0, max(1.0, actor.fame_score + (val if op == "+" else -val)))
                        actor.update_fame_tier()
                    elif mem == "conditionScore":
                        actor.condition_score = min(100.0, max(0.0, actor.condition_score + (val if op == "+" else -val)))
                    elif mem == "bodytype" and val_str:
                        actor.bodytype = val_str
                    elif mem == "personalInfo" and val_str:
                        if op == "+" and val_str not in actor.personal_info:
                            actor.personal_info.append(val_str)
                        elif op == "-" and val_str in actor.personal_info:
                            actor.personal_info.remove(val_str)
                    elif mem in attr_map:
                        ak = attr_map[mem]
                        actor.attributes[ak] = min(100, max(5, actor.attributes.get(ak, 50) + (int(val) if op == "+" else -int(val))))

            elif atype == "sendMessage":
                act_name = actor.name if actor else self.player_agency.name
                raw_title = (at.get("title") or "Agency News").replace("%s", act_name)
                title = raw_title if act_name in raw_title else f"{act_name}: {raw_title}"
                content = (at.get("content") or "").replace("\\n", "\n").replace("%s", act_name)
                canvas = (at.get("canvasimagefile") or "").replace("\\", "/")
                sev = at.get("severity") or "Normal"

                msg_btns: List[MessageButton] = []
                for b in act.get("buttons", []):
                    b_title = b.get("title") or "OK"
                    b_evt = (b.get("event") or "").replace("\\", "/").strip()
                    b_block = b.get("blocker") == "1"
                    cmd = f"EVT:{b_evt}:{actor.id if actor else 0}" if b_evt else "CLOSE"
                    msg_btns.append(MessageButton(title=b_title, command=cmd, blocker=b_block))

                self.add_message(
                    title=title,
                    content=content,
                    category="general",
                    severity=sev,
                    sender_name=act_name,
                    canvas_file=canvas,
                    related_actor_id=actor.id if actor else None,
                    buttons=msg_btns,
                )

            elif atype == "triggerEvent":
                child_ev = (at.get("event") or "").replace("\\", "/").strip()
                if child_ev:
                    self.execute_event_by_id(child_ev, actor_id)

    def _run_annual_awards(self) -> None:
        ceremonies = [
            "Thespian League Awards",
            "Silver Sphere Awards",
            "Association Awards",
            "Fan Favorites Awards",
            "Indie Star Awards",
            "Berry Awards",
        ]
        categories = [
            ("Best Actor in a Leading Role", "Male"),
            ("Best Actress in a Leading Role", "Female"),
            ("Best Supporting Actor", "Male"),
            ("Best Supporting Actress", "Female"),
        ]
        year = self.current_date.year - 1
        released_films = [f for f in self.films.values() if f.status == "Released"]
        for cer in ceremonies:
            for cat, sex in categories:
                pool = [a for a in self.actors.values() if a.sex == sex]
                if not pool:
                    continue
                if cer == "Berry Awards":
                    # Razzie parody: picks high-fame low-skill actor
                    winner = max(pool, key=lambda a: a.fame_score - a.attributes.get("Characterization", 50) * 4 + self.rng.uniform(0, 50))
                else:
                    winner = max(pool, key=lambda a: a.fame_score + a.attributes.get("Characterization", 50) * 5 + self.rng.uniform(0, 80))
                winner.num_awards += 1
                ag = self.agencies.get(winner.agency_id) if winner.agency_id is not None else None
                if ag:
                    ag.stats_awards += 1
                proj_title = winner.credits[0]["title"] if winner.credits else (released_films[0].title if released_films else "Hollywoodland Feature")
                self.awards.insert(0, AwardRecord(
                    year=year,
                    ceremony_name=cer,
                    category_name=cat,
                    winner_actor_id=winner.id,
                    winner_actor_name=winner.name,
                    agency_name=ag.name if ag else "Free Agent",
                    project_title=proj_title,
                ))
                if winner.agency_id == 0:
                    self.add_message(
                        title=f"AWARD WINNER: {winner.name} wins at the {cer}!",
                        content=f"Congratulations! Your client {winner.name} won '{cat}' at the {year} {cer} for '{proj_title}'!",
                        category="general",
                        severity="Important",
                        related_actor_id=winner.id,
                    )

    def _update_rankings(self) -> None:
        sorted_actors = sorted(self.actors.values(), key=lambda a: a.fame_score, reverse=True)
        for idx, act in enumerate(sorted_actors, start=1):
            act.actor_ranking = idx

        sorted_agencies = sorted(self.agencies.values(), key=lambda ag: ag.reputation_score, reverse=True)
        for idx, ag in enumerate(sorted_agencies, start=1):
            ag.ranking = idx

    # -------------------------------------------------------------------------
    # Save / Load Game (.json)
    # -------------------------------------------------------------------------
    def save_game(self, filepath: str) -> None:
        state = {
            "current_date": self.date_str,
            "player_agency": {
                "name": self.player_agency.name,
                "owner_name": self.player_agency.owner_name,
                "budget": self.player_agency.budget,
                "reputation": self.player_agency.reputation,
                "reputation_score": self.player_agency.reputation_score,
                "knowledge_skill": self.player_agency.knowledge_skill,
                "personal_skill": self.player_agency.personal_skill,
                "negotiation_skill": self.player_agency.negotiation_skill,
                "stats_income": self.player_agency.stats_income,
                "stats_minor_roles": self.player_agency.stats_minor_roles,
                "stats_major_roles": self.player_agency.stats_major_roles,
                "stats_awards": self.player_agency.stats_awards,
            },
            "my_actor_ids": [a.id for a in self.actors.values() if a.agency_id == 0],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
