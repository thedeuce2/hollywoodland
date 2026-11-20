from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


CORE_ATTRIBUTES = [
    "Characterization",
    "Improvisation",
    "Vocal Expression",
    "Physical Expression",
    "Facial Expression",
    "Intelligence",
    "Charisma",
    "Humor",
    "Commitment",
    "Confidence",
    "Professionalism",
    "Stamina",
]

ROLE_TYPES = [
    "Lead",
    "Major Support",
    "Minor Support",
    "Series Regular",
    "Guest Star",
]


@dataclass
class ContractOffer:
    contract_start: str = "2018-08-13"
    contract_end: str = "2019-08-13"
    commission: int = 10  # percentage (default 10%)
    num_months: int = 12
    signature_fee: int = 0
    min_any_roles: int = 0
    min_major_roles: int = 0
    min_income: int = 0
    # For role contracts (studio <-> actor):
    acting_fee: int = 0
    first_dollar_gross: float = 0.0  # %
    net_points: float = 0.0  # %
    bo_bonus_fee: int = 0
    bo_bonus_threshold: int = 0
    acting_fee_bumps: int = 0


@dataclass
class Actor:
    id: int
    name: str
    sex: str  # "Male" or "Female"
    age: int
    nationality: str
    ethnicity: str
    birthplace: str
    height_cm: int
    height_category: str  # "Very short", "Short", "Medium", "Tall", "Very tall"
    bodytype: str  # "Slim", "Average", "Curvy", "Athletic", "Muscular", "Overweight", "Chunky"
    look: str  # "Striking", "Attractive", "Distinctive", "Everyday", "Clean-Cut", "Rugged"
    personality: str
    disc: str  # "D", "I", "S", "C"
    fame_score: float = 5.0
    fame_tier: str = "Unknown"  # "Unknown", "Relatively unknown", "Average", "Notable", "A-lister"
    actor_ranking: int = 999
    morale_score: float = 65.0
    condition_score: float = 80.0
    attributes: Dict[str, int] = field(default_factory=dict)
    known_attributes: Dict[str, bool] = field(default_factory=dict)
    attrib_range_mins: Dict[str, int] = field(default_factory=dict)
    quotes: Dict[str, int] = field(default_factory=dict)  # Role type -> base fee quote
    special_skills: List[str] = field(default_factory=list)
    personal_info: List[str] = field(default_factory=list)
    happenings: List[str] = field(default_factory=list)
    agency_id: Optional[int] = None  # None = Free Agent, 0 = Player Agency ("ours")
    contract: Optional[ContractOffer] = None
    last_reject_date: Optional[str] = None
    not_available_until: Optional[str] = None
    schedule_status: str = "Available"
    current_project_id: Optional[int] = None
    current_role_name: Optional[str] = None
    training_type: Optional[str] = None  # "bodyType", "actingSchool", "specialSkills"
    training_target: Optional[str] = None
    training_end_date: Optional[str] = None
    num_awards: int = 0
    this_year_income: int = 0
    this_year_major_roles: int = 0
    this_year_all_roles: int = 0
    this_year_lowest_review: int = 0
    this_year_highest_review: int = 0
    career_income: int = 0
    career_upfront_income: int = 0
    career_backend_income: int = 0
    career_agency_commissions: int = 0
    career_roles: int = 0
    credits: List[Dict[str, Any]] = field(default_factory=list)
    earnings_history: List[Dict[str, Any]] = field(default_factory=list)
    portrait_seed: int = 0
    portrait_path: str = ""
    potential_rating: int = 65
    potential_known: bool = False

    @property
    def overall_rating(self) -> int:
        if not self.attributes:
            return 50
        return int(round(sum(self.attributes.values()) / len(self.attributes)))

    @property
    def potential_label(self) -> str:
        if self.potential_rating >= 90:
            return "Generational"
        elif self.potential_rating >= 80:
            return "Elite"
        elif self.potential_rating >= 70:
            return "Star"
        elif self.potential_rating >= 58:
            return "Solid"
        return "Fringe"

    @property
    def display_potential(self) -> str:
        if self.potential_known or self.agency_id == 0:
            return f"{self.potential_label} ({self.potential_rating})"
        return "Unscouted"

    @property
    def morale_label(self) -> str:
        if self.morale_score <= 20:
            return "Depressed"
        elif self.morale_score <= 40:
            return "Upset"
        elif self.morale_score <= 60:
            return "Concerned"
        elif self.morale_score <= 80:
            return "Pleased"
        return "Superb"

    @property
    def condition_label(self) -> str:
        if self.condition_score <= 20:
            return "Very poor"
        elif self.condition_score <= 40:
            return "Poor"
        elif self.condition_score <= 60:
            return "Fair"
        elif self.condition_score <= 80:
            return "Good"
        return "Excellent"

    def update_fame_tier(self) -> None:
        if self.fame_score <= 15:
            self.fame_tier = "Unknown"
        elif self.fame_score <= 100:
            self.fame_tier = "Relatively unknown"
        elif self.fame_score <= 350:
            self.fame_tier = "Average"
        elif self.fame_score <= 700:
            self.fame_tier = "Notable"
        else:
            self.fame_tier = "A-lister"

    def get_display_attribute(self, attr_name: str) -> str:
        val = self.attributes.get(attr_name, 50)
        if self.known_attributes.get(attr_name, False) or self.agency_id == 0:
            return str(val)
        low = self.attrib_range_mins.get(attr_name, max(1, val - 15))
        high = min(100, low + 25)
        return f"{low}-{high}"


@dataclass
class Agency:
    id: int
    name: str
    owner_name: str = "John Doe"
    owner_age: int = 30
    owner_sex: str = "Male"
    owner_nationality: str = "USA"
    ours: bool = False
    budget: float = 25000.0
    reputation: str = "Minor"  # "Minor", "Medium", "Major"
    reputation_score: float = 10.0
    max_actors: int = 30
    ranking: int = 39
    years_in_operation: int = 1
    knowledge_skill: int = 25
    personal_skill: int = 25
    negotiation_skill: int = 25
    logo_file: str = "cat.png"
    stats_income: int = 0
    stats_minor_roles: int = 0
    stats_major_roles: int = 0
    stats_awards: int = 0
    monthly_overhead: int = 4500


@dataclass
class DirectorProducerShowrunner:
    id: int
    name: str
    role_kind: str  # "Director", "Producer", "Showrunner"
    sex: str
    age: int
    nationality: str
    fame: str  # "Unknown", "Average", "Well-known", "Legend"
    personality: str
    disc: str
    genre_specialty: str
    knowledge_skill: int = 50
    personal_skill: int = 50
    negotiation_skill: int = 50
    num_movies: int = 0
    num_series: int = 0
    total_gross_revenue: int = 0
    highest_review: int = 75
    lowest_review: int = 35
    first_look_studio: Optional[str] = None
    liked_actor_ids: List[int] = field(default_factory=list)
    disliked_actor_ids: List[int] = field(default_factory=list)


@dataclass
class AuditionCandidate:
    actor_id: int
    actor_name: str
    agency_name: str
    points: float
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    won: bool = False


@dataclass
class RoleSlot:
    index: int
    role_name: str  # e.g. "Cynical Detective"
    noun: str
    adjective: str
    collective_tag: str
    role_type: str  # "Lead", "Major Support", "Minor Support", "Series Regular", "Guest Star"
    sex: str  # "Male", "Female", "Any"
    ethnicity: str  # "Any" or specific
    age_range: str  # e.g. "Mid 20's-early 30's"
    look: str  # "Any" or specific
    bodytype: str  # "Any" or specific
    height: str  # "Any" or specific
    special_skills: List[str] = field(default_factory=list)
    nudity: str = "None"  # "None", "Partial", "Full"
    desired_fame: int = 30  # 0-100 target Fame expected by studio/casting director
    casting_type: str = "Open"  # "Open" or "Direct"
    filming_start: str = ""
    filming_end: str = ""
    submitted_actor_ids: List[int] = field(default_factory=list)
    audition_actor_ids: List[int] = field(default_factory=list)
    cast_actor_id: Optional[int] = None
    offered_actor_id: Optional[int] = None
    audition_results: List[AuditionCandidate] = field(default_factory=list)


@dataclass
class FilmOrSeries:
    id: int
    title: str
    series_or_movie: str  # "Movie" or "TV"
    genre: str
    studio_or_channel: str
    studio_tier: str  # "A", "B", "C", "Broadcast", "Cable"
    budget: int
    breakeven: int
    director_id: int
    producer_id: int
    showrunner_id: Optional[int]
    filming_location: str
    historical_era: str  # e.g. "1960-2020"
    script_rating: int  # true quality 1-100
    player_rating: int  # player estimated 1-100
    consultant_rating: Optional[int] = None
    consultant_verdict: str = ""
    review_score: Optional[int] = None
    review_blurb: str = ""
    box_office_gross: int = 0
    box_office_weeks_run: int = 0
    box_office_target_gross: int = 0
    home_media_revenue: int = 0
    tv_licensing_revenue: int = 0
    vhs_revenue: int = 0
    dvd_revenue: int = 0
    streaming_revenue: int = 0
    months_since_release: int = 0
    tv_average_rating: float = 0.0
    tv_decision_date: str = ""
    season: int = 1
    num_episodes: int = 10
    is_pilot: bool = False
    status: str = "Casting"  # "Casting", "Auditioning", "Filming", "Post-Production", "In Theaters", "Airing", "Released", "Finished", "Cancelled"
    submission_end_date: str = ""
    audition_start_date: str = ""
    audition_end_date: str = ""
    final_decision_date: str = ""
    filming_start_date: str = ""
    filming_end_date: str = ""
    release_date: str = ""
    run_end_date: str = ""
    roles: List[RoleSlot] = field(default_factory=list)


@dataclass
class SubmissionRecord:
    actor_id: int
    film_id: int
    role_index: int
    status: str  # "Submitted", "Auditioning", "Offered", "Cast", "Rejected", "Lost", "Filming"
    audition_date: str = ""


@dataclass
class MessageButton:
    title: str
    command: str = ""  # e.g. "ROLE_OFFER:film_id:role_idx:actor_id", "EVT:event_path", "EXTEND:actor_id", "CLOSE"
    blocker: bool = False


@dataclass
class InboxMessage:
    id: int
    date_str: str
    title: str
    content: str
    category: str = "general"  # "general", "reviews", "filming", "release", "premiere"
    severity: str = "Normal"  # "Normal", "Important"
    was_read: bool = False
    requires_response: bool = False
    sender_name: str = "Hollywoodland Wire"
    portrait_file: str = ""
    canvas_file: str = ""
    related_actor_id: Optional[int] = None
    related_film_id: Optional[int] = None
    related_role_index: Optional[int] = None
    buttons: List[MessageButton] = field(default_factory=list)


@dataclass
class LedgerEntry:
    date_str: str
    description: str
    amount: int  # positive = income, negative = expense
    actor_name: str = ""
    project_title: str = ""
    payment_type: str = "General"  # "Acting Fee", "Backend Bonus", "Portfolio", "Overhead", "Scout/Consultant", "Signature Fee"


@dataclass
class ScoutOrConsultant:
    id: int
    name: str
    kind: str  # "Scout" or "Consultant"
    tier: str  # "Well-known", "Average", "Unknown"
    fee: int
    report_days_min: int
    report_days_max: int
    discovery: int = 75
    judging: int = 75
    speed: int = 75
    insight: int = 75


@dataclass
class AwardRecord:
    year: int
    ceremony_name: str
    category_name: str
    winner_actor_id: int
    winner_actor_name: str
    agency_name: str
    project_title: str
