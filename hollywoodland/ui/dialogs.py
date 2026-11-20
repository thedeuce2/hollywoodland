from __future__ import annotations
from typing import Callable, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hollywoodland.models.entities import CORE_ATTRIBUTES, Actor, ContractOffer, DirectorProducerShowrunner, FilmOrSeries, RoleSlot
from hollywoodland.systems.engine import HollywoodlandEngine
from hollywoodland.ui.assets import AssetManager


class CreativeProfileDialog(QDialog):
    """Authentic ProDirShow.ui Bio Card for Directors, Producers, and Showrunners."""

    def __init__(self, engine: HollywoodlandEngine, creative: DirectorProducerShowrunner, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.creative = creative
        self.setWindowTitle(f"{creative.role_kind.upper()} BIO — {creative.name}")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.resize(620, 460)
        self._build_ui()

    def _build_ui(self) -> None:
        c = self.creative
        layout = QVBoxLayout(self)

        card = QFrame()
        card.setObjectName("Card")
        vbox = QVBoxLayout(card)
        vbox.addWidget(QLabel(
            f"<h2 style='color:#f4c552; margin:0;'>{c.name} — {c.role_kind.upper()}</h2>"
            f"<p style='margin:4px 0;'><b>Fame:</b> <span style='color:#38bdf8;'>{c.fame}</span> | "
            f"<b>Age:</b> {c.age} | <b>Sex:</b> {c.sex} | <b>Nationality:</b> {c.nationality}</p>"
            f"<p style='margin:4px 0;'><b>Personality:</b> {c.personality} (<b>DISC Profile: {c.disc}</b>) | "
            f"<b>Specialty Genre:</b> {c.genre_specialty}</p>"
            f"<p style='margin:4px 0;'><b>First-Look / Overall Deal:</b> {c.first_look_studio or 'Independent'}</p>"
            f"<hr>"
            f"<p style='margin:4px 0;'><b>Knowledge Skill:</b> <span style='color:#4ade80;'>{c.knowledge_skill}/100</span> | "
            f"<b>Personal / Man-Management:</b> <span style='color:#4ade80;'>{c.personal_skill}/100</span> | "
            f"<b>Negotiation Skill:</b> <span style='color:#4ade80;'>{c.negotiation_skill}/100</span></p>"
            f"<p style='margin:4px 0;'><b>Career Track Record:</b> {c.num_movies} Movies, {c.num_series} TV Series | "
            f"Total Box Office: <b>${c.total_gross_revenue:,}</b> | Reviews: {c.lowest_review}% – {c.highest_review}%</p>"
        ))

        liked_names = [self.engine.actors[aid].name for aid in c.liked_actor_ids if aid in self.engine.actors]
        disliked_names = [self.engine.actors[aid].name for aid in c.disliked_actor_ids if aid in self.engine.actors]

        rel_lbl = QLabel(
            f"<h3 style='color:#4ade80; margin:8px 0 2px 0;'>Admires Working With (+85 Audition Bonus):</h3>"
            f"<p style='margin:0;'>{', '.join(liked_names) or 'None yet'}</p>"
            f"<h3 style='color:#f87171; margin:8px 0 2px 0;'>Dislikes / Clashes With (-75 Audition Penalty):</h3>"
            f"<p style='margin:0;'>{', '.join(disliked_names) or 'None yet'}</p>"
            f"<p style='color:#94a3b8; margin-top:10px;'><i>Tip: Actors with matching DISC profile (<b>{c.disc}</b>) automatically receive a +40 rapport bonus in auditions!</i></p>"
        )
        rel_lbl.setWordWrap(True)
        vbox.addWidget(rel_lbl)
        layout.addWidget(card, 1)

        close_btn = QPushButton("Close Bio")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


def format_full_role_requirements_html(engine: HollywoodlandEngine, film: FilmOrSeries, role: RoleSlot, actor: Optional[Actor] = None) -> str:
    """Renders every single requirement and scoring factor of a role in a side-by-side 2-column layout so no vertical scrolling is needed."""
    director = engine.creatives.get(film.director_id)
    producer = engine.creatives.get(film.producer_id)
    showrunner = engine.creatives.get(film.showrunner_id) if film.showrunner_id else None

    genre_attrs = engine.db.genre_required_attrs.get(film.genre, ["Characterization", "Facial Expression"])
    archetype_attrs = engine.db.collective_attr_bonuses.get(role.collective_tag, [])
    skills_str = ", ".join(role.special_skills) if role.special_skills else "None required"
    cons_str = f"{film.consultant_rating}% (Script Doctor)" if film.consultant_rating is not None else "Not reviewed yet"

    def _match_badge(req_val: str, act_val: str) -> str:
        if actor is None:
            return f"<b style='color:#e2e8f0;'>{req_val}</b>"
        if req_val in ("Any", "None", "") or req_val == act_val:
            return f"<b style='color:#4ade80;'>{req_val} (Client: {act_val} — MATCH)</b>"
        return f"<b style='color:#f87171;'>{req_val} (Client: {act_val} — MISMATCH)</b>"

    actor_age_bracket = engine._age_to_bracket(actor.age) if actor else ""

    archetype_desc = f"{role.adjective} {role.noun}".strip()
    role_heading = (
        f"ROLE SHEET: {role.role_name} — {role.role_type} "
        f"<span style='color:#94a3b8; font-weight:normal;'>(Character Breakdown: {archetype_desc})</span>"
        if role.role_name != archetype_desc
        else f"ROLE SHEET: {role.role_name} ({role.role_type})"
    )

    desired_f = int(getattr(role, "desired_fame", 30))
    if actor is None:
        fame_badge = f"<b style='color:#f4c552;'>{desired_f} / 100</b>"
    else:
        af = int(round(max(0.0, min(100.0, float(actor.fame_score)))))
        if af >= desired_f:
            fame_badge = f"<b style='color:#4ade80;'>{desired_f}+ (Client: {af} — MATCH)</b>"
        elif desired_f - af <= 12:
            fame_badge = f"<b style='color:#fbbf24;'>{desired_f}+ (Client: {af} — CLOSE)</b>"
        else:
            fame_badge = f"<b style='color:#f87171;'>{desired_f}+ (Client: {af} — LOW)</b>"

    html = (
        f"<h3 style='color:#f4c552; margin:0 0 8px 0;'>{role_heading}</h3>"
        f"<table width='100%' cellspacing='6' cellpadding='4' style='font-size:10.5pt;'>"
        f"<tr>"
        f"  <td width='16%' style='color:#94a3b8;'>Required Sex:</td><td width='34%'>{_match_badge(role.sex, actor.sex if actor else '')}</td>"
        f"  <td width='16%' style='color:#94a3b8;'>Project & Genre:</td><td width='34%'><b>{film.title}</b> ({film.series_or_movie} — {film.genre}, Era: {film.historical_era})</td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Required Ethnicity:</td><td>{_match_badge(role.ethnicity, actor.ethnicity if actor else '')}</td>"
        f"  <td style='color:#94a3b8;'>Studio / Budget:</td><td><b>{film.studio_or_channel}</b> (Tier {film.studio_tier}) | <b>${film.budget:,}</b> (Breakeven: ${film.breakeven:,})</td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Required Age Range:</td><td>{_match_badge(role.age_range, f'{actor_age_bracket} [{actor.age}y]' if actor else '')}</td>"
        f"  <td style='color:#94a3b8;'>Decision Makers:</td><td>Dir: <b>{director.name if director else 'TBA'}</b> (DISC: <b>{director.disc if director else '?'}</b>) | Prod: <b>{producer.name if producer else 'TBA'}</b>"
        + (f" | Show: <b>{showrunner.name}</b>" if showrunner else "") + "</td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Required Look:</td><td>{_match_badge(role.look, actor.look if actor else '')}</td>"
        f"  <td style='color:#94a3b8;'>Script Quality:</td><td><b style='color:#38bdf8;'>~{film.player_rating}% (Your Read)</b> | <b style='color:#fbbf24;'>{cons_str}</b></td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Required Body Type:</td><td>{_match_badge(role.bodytype, actor.bodytype if actor else '')}</td>"
        f"  <td style='color:#94a3b8;'>Genre Skills Tested:</td><td><b style='color:#38bdf8;'>{', '.join(genre_attrs) or 'All Core Acting Skills'}</b></td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Required Height:</td><td>{_match_badge(role.height, f'{actor.height_category} [{actor.height_cm}cm]' if actor else '')}</td>"
        f"  <td style='color:#94a3b8;'>Archetype Bonus:</td><td><b style='color:#c084fc;'>{', '.join(archetype_attrs) or 'General Acting & Charisma'}</b> ({role.collective_tag})</td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Desired Fame (0-100):</td><td>{fame_badge}</td>"
        f"  <td style='color:#94a3b8;'>Special Skills & Nudity:</td><td>Skills: <b style='color:#fbbf24;'>{skills_str}</b> | Nudity: <b>{role.nudity}</b></td>"
        f"</tr>"
        f"<tr>"
        f"  <td style='color:#94a3b8;'>Schedule & Dates:</td><td colspan='3'>Deadline: <b>{film.submission_end_date}</b> | Auditions: <b>{film.audition_start_date}–{film.audition_end_date}</b> | Decision: <b>{film.final_decision_date}</b> | Filming: <b>{role.filming_start}–{role.filming_end}</b> ({film.filming_location})</td>"
        f"</tr>"
        f"</table>"
    )
    return html


class ActorContractDialog(QDialog):
    """Interactive negotiation window for signing a Free Agent to the player's agency."""

    def __init__(self, engine: HollywoodlandEngine, assets: AssetManager, actor: Actor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.assets = assets
        self.actor = actor
        self.demand: ContractOffer = engine.get_actor_initial_demands(actor.id)
        self.signed = False
        self.status_message = ""

        self.setWindowTitle(f"Talent Representation Agreement — {actor.name}")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.resize(620, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        pic = QLabel()
        pic.setPixmap(self.assets.get_actor_portrait(self.actor, 96))
        top.addWidget(pic)

        info_box = QVBoxLayout()
        title_lbl = QLabel(f"<h2 style='color:#f4c552; margin:0;'>{self.actor.name}</h2>")
        sub_lbl = QLabel(
            f"<b>{self.actor.sex}, Age {self.actor.age}</b> | Fame: <b>{self.actor.fame_tier}</b> ({self.actor.fame_score}) | "
            f"Personality: <b>{self.actor.personality}</b>"
        )
        self.speech_lbl = QLabel(
            "<i>\"These are the representation terms I would prefer. Every new client also requires a "
            "$500 professional headshot portfolio.\"</i>"
        )
        self.speech_lbl.setWordWrap(True)
        self.speech_lbl.setStyleSheet("background-color:#1e2433; padding:10px; border-radius:6px; border:1px solid #353f58;")
        info_box.addWidget(title_lbl)
        info_box.addWidget(sub_lbl)
        info_box.addWidget(self.speech_lbl)
        top.addLayout(info_box, 1)
        layout.addLayout(top)

        form_frame = QFrame()
        form_frame.setObjectName("Card")
        form = QFormLayout(form_frame)

        self.months_spin = QSpinBox()
        self.months_spin.setRange(6, 36)
        self.months_spin.setSingleStep(6)
        self.months_spin.setValue(self.demand.num_months)
        self.months_spin.setSuffix(" months")
        form.addRow("Contract Duration:", self.months_spin)

        self.comm_spin = QSpinBox()
        self.comm_spin.setRange(5, 20)
        self.comm_spin.setValue(self.demand.commission)
        self.comm_spin.setSuffix(" %")
        form.addRow("Agency Commission Rate:", self.comm_spin)

        self.sig_spin = QSpinBox()
        self.sig_spin.setRange(0, 250000)
        self.sig_spin.setSingleStep(500)
        self.sig_spin.setValue(self.demand.signature_fee)
        self.sig_spin.setPrefix("$ ")
        form.addRow("Client Signature Bonus:", self.sig_spin)

        self.any_roles_spin = QSpinBox()
        self.any_roles_spin.setRange(0, 10)
        self.any_roles_spin.setValue(self.demand.min_any_roles)
        form.addRow("Min. Guaranteed Roles / Year:", self.any_roles_spin)

        self.major_roles_spin = QSpinBox()
        self.major_roles_spin.setRange(0, 5)
        self.major_roles_spin.setValue(self.demand.min_major_roles)
        form.addRow("Min. Guaranteed Major Roles / Year:", self.major_roles_spin)

        portfolio_lbl = QLabel("<b>$500 USD</b> (Professional Headshot Portfolio)")
        portfolio_lbl.setStyleSheet("color:#38bdf8;")
        form.addRow("Photographer Portfolio Fee:", portfolio_lbl)

        layout.addWidget(form_frame)

        btn_row = QHBoxLayout()
        accept_btn = QPushButton("Accept Actor's Terms Immediately")
        accept_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:9px 14px;")
        accept_btn.clicked.connect(self._on_accept_demands)

        propose_btn = QPushButton("Propose Custom Terms")
        propose_btn.setStyleSheet("background-color:#b45309; color:white; font-weight:bold; padding:9px 14px;")
        propose_btn.clicked.connect(self._on_propose)

        cancel_btn = QPushButton("Walk Away")
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(accept_btn)
        btn_row.addWidget(propose_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _gather_offer(self) -> ContractOffer:
        return ContractOffer(
            num_months=self.months_spin.value(),
            commission=self.comm_spin.value(),
            signature_fee=self.sig_spin.value(),
            min_any_roles=self.any_roles_spin.value(),
            min_major_roles=self.major_roles_spin.value(),
            min_income=self.demand.min_income,
        )

    def _on_accept_demands(self) -> None:
        ok, msg, _ = self.engine.sign_actor_to_player_agency(self.actor.id, self.demand)
        if ok:
            self.signed = True
            self.status_message = msg
            self.accept()
        else:
            self.speech_lbl.setText(f"<b style='color:#f87171;'>{msg}</b>")

    def _on_propose(self) -> None:
        offer = self._gather_offer()
        ok, msg, counter = self.engine.evaluate_representation_offer(self.actor.id, offer, self.demand)
        if ok:
            self.signed = True
            self.status_message = msg
            self.accept()
        else:
            self.speech_lbl.setText(f"<b style='color:#fbbf24;'>{msg}</b>")
            self.demand = counter
            self.comm_spin.setValue(counter.commission)
            self.sig_spin.setValue(counter.signature_fee)
            self.any_roles_spin.setValue(counter.min_any_roles)
            self.major_roles_spin.setValue(counter.min_major_roles)


class RoleContractDialog(QDialog):
    """Studio <-> Actor Role Contract negotiation dialog when a client wins an audition."""

    def __init__(
        self,
        engine: HollywoodlandEngine,
        assets: AssetManager,
        film_id: int,
        role_index: int,
        actor_id: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.assets = assets
        self.film = engine.films[film_id]
        self.role = self.film.roles[role_index]
        self.actor = engine.actors[actor_id]
        self.baseline = engine.get_initial_role_offer(film_id, role_index, actor_id)
        self.current_offer = engine.get_initial_role_offer(film_id, role_index, actor_id)
        self.status_message = ""

        self.setWindowTitle(f"Role Contract Negotiation — {self.actor.name} in '{self.film.title}'")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.resize(640, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(
            f"<h2 style='color:#f4c552; margin:0;'>{self.film.studio_or_channel}: '{self.film.title}' ({self.film.genre})</h2>"
            f"<p style='margin:4px 0;'>Role: <b>{self.role.role_name}</b> ({self.role.role_type}) | "
            f"Client: <b>{self.actor.name}</b> ({self.actor.fame_tier}) | "
            f"Project Budget: <b>${self.film.budget:,}</b> (Breakeven: ${self.film.breakeven:,})</p>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        self.studio_speech = QLabel(
            f"<i>\"{self.actor.name} gave the best audition for '{self.role.role_name}'. "
            f"Here is our standard studio contract offer—let's close the deal!\"</i>"
        )
        self.studio_speech.setWordWrap(True)
        self.studio_speech.setStyleSheet("background-color:#1e2433; padding:10px; border-radius:6px; border:1px solid #353f58;")
        layout.addWidget(self.studio_speech)

        form_frame = QFrame()
        form_frame.setObjectName("Card")
        form = QFormLayout(form_frame)

        self.fee_spin = QSpinBox()
        self.fee_spin.setRange(1000, 35_000_000)
        self.fee_spin.setSingleStep(2500)
        self.fee_spin.setPrefix("$ ")
        self.fee_spin.setValue(self.current_offer.acting_fee)
        form.addRow("Base Acting Fee:", self.fee_spin)

        self.gross_spin = QDoubleSpinBox()
        self.gross_spin.setRange(0.0, 15.0)
        self.gross_spin.setSingleStep(0.5)
        self.gross_spin.setSuffix(" %")
        self.gross_spin.setValue(self.current_offer.first_dollar_gross)
        form.addRow("1st Dollar Gross Points:", self.gross_spin)

        self.net_spin = QDoubleSpinBox()
        self.net_spin.setRange(0.0, 20.0)
        self.net_spin.setSingleStep(0.5)
        self.net_spin.setSuffix(" %")
        self.net_spin.setValue(self.current_offer.net_points)
        form.addRow("Net Profit Points:", self.net_spin)

        self.bonus_spin = QSpinBox()
        self.bonus_spin.setRange(0, 15_000_000)
        self.bonus_spin.setSingleStep(5000)
        self.bonus_spin.setPrefix("$ ")
        self.bonus_spin.setValue(self.current_offer.bo_bonus_fee)
        form.addRow(f"Box Office Bonus (at ${self.film.breakeven:,}):", self.bonus_spin)

        comm_pct = self.actor.contract.commission if self.actor.contract else 10
        self.comm_preview = QLabel()
        self._update_comm_preview()
        self.fee_spin.valueChanged.connect(self._update_comm_preview)
        form.addRow(f"Your Agency Commission ({comm_pct}%):", self.comm_preview)

        layout.addWidget(form_frame)

        btn_row = QHBoxLayout()
        sign_btn = QPushButton("Accept & Sign Studio Offer")
        sign_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:10px 16px;")
        sign_btn.clicked.connect(self._on_accept)

        counter_btn = QPushButton("Demand Higher Terms (Negotiate)")
        counter_btn.setStyleSheet("background-color:#b45309; color:white; font-weight:bold; padding:10px 16px;")
        counter_btn.clicked.connect(self._on_negotiate)

        btn_row.addWidget(sign_btn)
        btn_row.addWidget(counter_btn)
        layout.addLayout(btn_row)

    def _update_comm_preview(self) -> None:
        comm_pct = self.actor.contract.commission if self.actor.contract else 10
        cut = int(self.fee_spin.value() * (comm_pct / 100.0))
        self.comm_preview.setText(f"<b style='color:#4ade80;'>${cut:,} USD paid immediately upon signing</b>")

    def _gather_offer(self) -> ContractOffer:
        return ContractOffer(
            contract_start=self.role.filming_start,
            contract_end=self.role.filming_end,
            commission=self.actor.contract.commission if self.actor.contract else 10,
            acting_fee=self.fee_spin.value(),
            first_dollar_gross=self.gross_spin.value(),
            net_points=self.net_spin.value(),
            bo_bonus_fee=self.bonus_spin.value(),
            bo_bonus_threshold=self.film.breakeven,
        )

    def _on_accept(self) -> None:
        offer = self._gather_offer()
        offer.acting_fee = min(offer.acting_fee, max(self.baseline.acting_fee, self.current_offer.acting_fee))
        self.engine.finalize_role_contract(self.film.id, self.role.index, self.actor.id, offer)
        self.status_message = f"Signed {self.actor.name} as '{self.role.role_name}' in '{self.film.title}'!"
        self.accept()

    def _on_negotiate(self) -> None:
        proposed = self._gather_offer()
        status, msg, reply_offer = self.engine.negotiate_role_contract(
            self.film.id, self.role.index, self.actor.id, proposed, self.baseline
        )
        if status == "ACCEPTED":
            self.status_message = msg
            self.accept()
        elif status == "COUNTER":
            self.current_offer = reply_offer
            self.studio_speech.setText(f"<b style='color:#fbbf24;'>{msg}</b>")
            self.fee_spin.setValue(reply_offer.acting_fee)
            self.gross_spin.setValue(reply_offer.first_dollar_gross)
            self.net_spin.setValue(reply_offer.net_points)
            self.bonus_spin.setValue(reply_offer.bo_bonus_fee)
        else:
            self.status_message = msg
            self.reject()


class AuditionReportDialog(QDialog):
    """Displays the full Audition Scorecard and Pros/Cons for all candidates."""

    def __init__(self, engine: HollywoodlandEngine, film_id: int, role_index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.film = engine.films[film_id]
        self.role = self.film.roles[role_index]

        self.setWindowTitle(f"Audition Report — '{self.role.role_name}' in '{self.film.title}'")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.resize(860, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QLabel(
            f"<h2 style='color:#f4c552; margin:0;'>Audition Report: {self.role.role_name} ({self.role.role_type})</h2>"
            f"<p>Project: <b>{self.film.title}</b> ({self.film.genre}) | Studio/Network: <b>{self.film.studio_or_channel}</b> | "
            f"Sex: <b>{self.role.sex}</b> | Ethnicity: <b>{self.role.ethnicity}</b> | Age: <b>{self.role.age_range}</b> | "
            f"Look: <b>{self.role.look}</b> | Body: <b>{self.role.bodytype}</b> | Height: <b>{self.role.height}</b></p>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        split = QSplitter(Qt.Orientation.Horizontal)

        self.cand_table = QTableWidget(0, 4)
        self.cand_table.setHorizontalHeaderLabels(["Rank", "Actor", "Agency", "Score"])
        self.cand_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.cand_table.horizontalHeader().setStretchLastSection(True)
        self.cand_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cand_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        results = self.role.audition_results
        self.cand_table.setRowCount(len(results))
        for idx, cand in enumerate(results):
            r_item = QTableWidgetItem(f"#{idx + 1}" + (" (WINNER)" if cand.won else ""))
            a_item = QTableWidgetItem(cand.actor_name)
            ag_item = QTableWidgetItem(cand.agency_name)
            s_item = QTableWidgetItem(f"{cand.points:.1f}")
            if cand.won:
                for it in (r_item, a_item, ag_item, s_item):
                    it.setForeground(QColor("#4ade80"))
            self.cand_table.setItem(idx, 0, r_item)
            self.cand_table.setItem(idx, 1, a_item)
            self.cand_table.setItem(idx, 2, ag_item)
            self.cand_table.setItem(idx, 3, s_item)

        self.cand_table.currentCellChanged.connect(self._on_select_candidate)
        split.addWidget(self.cand_table)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        split.addWidget(self.details_text)
        split.setSizes([450, 390])
        layout.addWidget(split, 1)

        if results:
            self.cand_table.selectRow(0)
            self._on_select_candidate(0, 0, -1, -1)

        close_btn = QPushButton("Close Report")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _on_select_candidate(self, row: int, _col: int, _prev_r: int, _prev_c: int) -> None:
        if row < 0 or row >= len(self.role.audition_results):
            return
        cand = self.role.audition_results[row]
        pros_html = "".join(f"<li style='color:#4ade80;'>+ {p}</li>" for p in cand.pros)
        cons_html = "".join(f"<li style='color:#f87171;'>- {c}</li>" for c in cand.cons)
        self.details_text.setHtml(
            f"<h3 style='color:#f4c552;'>{cand.actor_name} ({cand.points:.1f} pts)</h3>"
            f"<p>Agency: <b>{cand.agency_name}</b></p>"
            f"<h4>PROS:</h4><ul>{pros_html}</ul>"
            f"<h4>CONS:</h4><ul>{cons_html}</ul>"
        )


class CastingNoticeDialog(QDialog):
    """Full Casting Notice & Complete Role Sheet screen for a Movie or TV Series."""

    def __init__(
        self,
        engine: HollywoodlandEngine,
        assets: AssetManager,
        film: FilmOrSeries,
        on_refresh: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
        initial_role_index: int = 0,
        preselect_actor_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.assets = assets
        self.film = film
        self.on_refresh = on_refresh
        self.initial_role_index = initial_role_index
        self.preselect_actor_id = preselect_actor_id

        self.setWindowTitle(f"Casting Notice — '{film.title}' ({film.studio_or_channel})")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)
        self.resize(1180, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        director = self.engine.creatives.get(self.film.director_id)
        producer = self.engine.creatives.get(self.film.producer_id)
        cons_str = f"{self.film.consultant_rating}% (Consultant)" if self.film.consultant_rating is not None else "Not reviewed yet"

        info_frame = QFrame()
        info_frame.setObjectName("Card")
        info_layout = QHBoxLayout(info_frame)

        left_html = (
            f"<h2 style='color:#f4c552; margin:0;'>\"{self.film.title}\" — {self.film.series_or_movie} Casting Notice</h2>"
            f"<p style='margin:4px 0;'><b>Studio / Network:</b> {self.film.studio_or_channel} (Tier {self.film.studio_tier}) | "
            f"<b>Genre:</b> {self.film.genre} | <b>Era:</b> {self.film.historical_era} | <b>Budget:</b> ${self.film.budget:,} (Breakeven: ${self.film.breakeven:,})</p>"
            f"<p style='margin:4px 0;'><b>Director:</b> {director.name if director else 'TBA'} ({director.fame if director else ''}, DISC: {director.disc if director else '?'}) | "
            f"<b>Producer:</b> {producer.name if producer else 'TBA'} | <b>Location:</b> {self.film.filming_location}</p>"
            f"<p style='margin:4px 0;'><b>Submission Deadline:</b> {self.film.submission_end_date} | "
            f"<b>Auditions:</b> {self.film.audition_start_date} to {self.film.audition_end_date} | "
            f"<b>Final Decision:</b> {self.film.final_decision_date} | "
            f"<b>Filming:</b> {self.film.filming_start_date} to {self.film.filming_end_date}</p>"
            f"<p style='margin:4px 0; color:#38bdf8;'><b>Script Quality Estimate:</b> ~{self.film.player_rating}% (Your Read) | <b>Script Doctor:</b> {cons_str}</p>"
        )
        if self.film.consultant_verdict:
            left_html += f"<p style='color:#fbbf24; margin:2px 0;'><i>{self.film.consultant_verdict}</i></p>"
        lbl = QLabel(left_html)
        lbl.setWordWrap(True)
        info_layout.addWidget(lbl, 1)

        # Clickable Director / Producer / Showrunner Bio Buttons (ProDirShow.ui)
        bio_box = QVBoxLayout()
        bio_box.addWidget(QLabel("<b>Decision Makers:</b>"))
        if director:
            dbtn = QPushButton(f"Director: {director.name}")
            dbtn.clicked.connect(lambda: CreativeProfileDialog(self.engine, director, self).exec())
            bio_box.addWidget(dbtn)
        if producer:
            pbtn = QPushButton(f"Producer: {producer.name}")
            pbtn.clicked.connect(lambda: CreativeProfileDialog(self.engine, producer, self).exec())
            bio_box.addWidget(pbtn)
        showrunner = self.engine.creatives.get(self.film.showrunner_id) if self.film.showrunner_id else None
        if showrunner:
            sbtn = QPushButton(f"Showrunner: {showrunner.name}")
            sbtn.clicked.connect(lambda: CreativeProfileDialog(self.engine, showrunner, self).exec())
            bio_box.addWidget(sbtn)
        info_layout.addLayout(bio_box)

        # Inline Script Doctor controls (no extra modal popup!)
        doc_box = QVBoxLayout()
        doc_box.addWidget(QLabel("<b>Script Doctor Review:</b>"))
        self.doc_combo = QComboBox()
        for c in self.engine.consultants:
            self.doc_combo.addItem(f"{c.name} (${c.fee:,})", c.id)
        doc_box.addWidget(self.doc_combo)
        cons_btn = QPushButton("Hire Script Doctor")
        cons_btn.setStyleSheet("background-color:#1d4ed8; color:white; font-weight:bold; padding:7px 12px;")
        cons_btn.clicked.connect(self._on_hire_script_doctor)
        doc_box.addWidget(cons_btn)
        info_layout.addLayout(doc_box)
        layout.addWidget(info_frame)

        # Complete 12-Column Roles Table (Fits 100% width with Stretch — zero horizontal scroll!)
        self.roles_table = QTableWidget(len(self.film.roles), 12)
        self.roles_table.setHorizontalHeaderLabels([
            "Role Name", "Role Type", "Desired Fame", "Sex", "Ethnicity", "Age Range",
            "Look", "Body Type", "Height",
            "Special Skills", "Nudity", "Status",
        ])
        self.roles_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.roles_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.roles_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.roles_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._populate_roles_table()
        self.roles_table.currentCellChanged.connect(self._on_role_selected)
        layout.addWidget(self.roles_table, 2)

        # Bottom Full Role Sheet Inspector + Client Submission Bar (Expands dynamically when maximized!)
        bottom_card = QFrame()
        bottom_card.setObjectName("Card")
        bot_hbox = QHBoxLayout(bottom_card)

        self.role_detail_text = QTextEdit()
        self.role_detail_text.setReadOnly(True)
        self.role_detail_text.setMinimumHeight(250)
        bot_hbox.addWidget(self.role_detail_text, 3)

        sub_vbox = QVBoxLayout()
        sub_vbox.addWidget(QLabel("<b>Select Available Client to Submit for Selected Role:</b>"))
        self.client_combo = QComboBox()
        self._populate_available_clients()
        self.client_combo.currentIndexChanged.connect(lambda _: self._on_role_selected(self.roles_table.currentRow(), 0, -1, -1))
        sub_vbox.addWidget(self.client_combo)

        btn_line = QHBoxLayout()
        self.submit_btn = QPushButton("Submit Client to Selected Role")
        self.submit_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:9px 16px;")
        self.submit_btn.clicked.connect(self._on_submit_client)
        btn_line.addWidget(self.submit_btn)

        self.report_btn = QPushButton("View Audition Scorecard")
        self.report_btn.clicked.connect(self._on_view_report)
        btn_line.addWidget(self.report_btn)
        sub_vbox.addLayout(btn_line)

        self.status_banner = QLabel("<span style='color:#94a3b8;'>Click any role above to inspect requirements and submit a client.</span>")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("background-color:#0f172a; padding:8px 10px; border-radius:6px; border:1px solid #334155;")
        sub_vbox.addWidget(self.status_banner)

        prof_btn = QPushButton("View Full Movie / TV Profile & Cast")
        prof_btn.setStyleSheet("background-color:#1a1f2c; color:#f4c552; border:1px solid #3a3019; font-weight:bold; padding:7px 12px;")
        prof_btn.clicked.connect(lambda: ProjectProfileDialog(self.engine, self.assets, self.film, on_refresh=self.on_refresh, parent=self).exec())
        sub_vbox.addWidget(prof_btn)

        close_btn = QPushButton("Close Casting Notice")
        close_btn.clicked.connect(self.accept)
        sub_vbox.addWidget(close_btn)
        sub_vbox.addStretch(1)
        bot_hbox.addLayout(sub_vbox, 1)

        layout.addWidget(bottom_card, 3)

        if self.film.roles:
            start_row = max(0, min(self.initial_role_index, len(self.film.roles) - 1))
            self.roles_table.selectRow(start_row)
            self._on_role_selected(start_row, 0, -1, -1)

    def _populate_roles_table(self) -> None:
        for idx, r in enumerate(self.film.roles):
            status = f"{len(r.submitted_actor_ids)} submitted"
            if r.cast_actor_id and r.cast_actor_id in self.engine.actors:
                status = f"Cast: {self.engine.actors[r.cast_actor_id].name}"
            elif r.offered_actor_id and r.offered_actor_id in self.engine.actors:
                status = f"Offered: {self.engine.actors[r.offered_actor_id].name}"
            skills_str = ", ".join(r.special_skills) if r.special_skills else "None"

            self.roles_table.setItem(idx, 0, QTableWidgetItem(r.role_name))
            self.roles_table.setItem(idx, 1, QTableWidgetItem(r.role_type))
            df_it = QTableWidgetItem(f"{int(getattr(r, 'desired_fame', 30))}+")
            df_it.setForeground(QColor("#f4c552"))
            self.roles_table.setItem(idx, 2, df_it)
            self.roles_table.setItem(idx, 3, QTableWidgetItem(r.sex))
            self.roles_table.setItem(idx, 4, QTableWidgetItem(r.ethnicity))
            self.roles_table.setItem(idx, 5, QTableWidgetItem(r.age_range))
            self.roles_table.setItem(idx, 6, QTableWidgetItem(r.look))
            self.roles_table.setItem(idx, 7, QTableWidgetItem(r.bodytype))
            self.roles_table.setItem(idx, 8, QTableWidgetItem(r.height))
            self.roles_table.setItem(idx, 9, QTableWidgetItem(skills_str))
            self.roles_table.setItem(idx, 10, QTableWidgetItem(r.nudity))
            self.roles_table.setItem(idx, 11, QTableWidgetItem(status))

    def _on_role_selected(self, row: int, _col: int, _pr: int, _pc: int) -> None:
        if row < 0 or row >= len(self.film.roles):
            return
        r = self.film.roles[row]
        sel_actor = None
        if hasattr(self, "client_combo") and self.client_combo.count() > 0:
            aid = int(self.client_combo.currentData())
            sel_actor = self.engine.actors.get(aid)
        self.role_detail_text.setHtml(format_full_role_requirements_html(self.engine, self.film, r, sel_actor))
        self.report_btn.setEnabled(bool(r.audition_results))

    def _populate_available_clients(self) -> None:
        self.client_combo.blockSignals(True)
        self.client_combo.clear()
        avail = self.engine.get_available_player_clients()
        for c in avail:
            self.client_combo.addItem(
                f"{c.name} ({c.sex}, {c.age}y, {c.ethnicity}, {c.look}, {c.bodytype}, {c.height_category})", c.id
            )
        if self.preselect_actor_id is not None:
            idx = self.client_combo.findData(self.preselect_actor_id)
            if idx >= 0:
                self.client_combo.setCurrentIndex(idx)
        self.client_combo.blockSignals(False)
        if hasattr(self, "submit_btn"):
            self.submit_btn.setEnabled(len(avail) > 0)

    def _on_submit_client(self) -> None:
        row = self.roles_table.currentRow()
        if row < 0:
            return
        if self.client_combo.count() == 0:
            self.status_banner.setText("<b style='color:#f87171;'>No available clients right now (all clients are either submitted, auditioning, or filming).</b>")
            return
        actor_id = int(self.client_combo.currentData())
        ok, msg = self.engine.submit_actor_to_role(actor_id, self.film.id, row)
        self._populate_roles_table()
        self._populate_available_clients()
        self.roles_table.selectRow(row)
        self._on_role_selected(row, 0, -1, -1)
        if self.on_refresh:
            self.on_refresh()
        color = "#4ade80" if ok else "#f87171"
        self.status_banner.setText(f"<b style='color:{color};'>{msg}</b>")

    def _on_view_report(self) -> None:
        row = self.roles_table.currentRow()
        if row < 0 or not self.film.roles[row].audition_results:
            self.status_banner.setText("<b style='color:#fbbf24;'>Audition results will be available after the Final Decision Date.</b>")
            return
        dlg = AuditionReportDialog(self.engine, self.film.id, row, self)
        dlg.exec()

    def _on_hire_script_doctor(self) -> None:
        cid = int(self.doc_combo.currentData())
        ok, msg = self.engine.hire_script_consultant(self.film.id, cid)
        if self.on_refresh:
            self.on_refresh()
        color = "#4ade80" if ok else "#f87171"
        self.status_banner.setText(f"<b style='color:{color};'>{msg}</b>")


class ActorProfileDialog(QDialog):
    """Comprehensive Actor Profile, Scouting, Representation Offer, and Client Chat dialog."""

    def __init__(
        self,
        engine: HollywoodlandEngine,
        assets: AssetManager,
        actor: Actor,
        on_refresh: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
        on_find_roles: Optional[Callable[[int], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.assets = assets
        self.actor = actor
        self.on_refresh = on_refresh
        self.on_find_roles = on_find_roles

        self.setWindowTitle(f"Actor Profile — {actor.name} (Rank #{actor.actor_ranking})")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)
        self.resize(900, 650)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        top_card = QFrame()
        top_card.setObjectName("Card")
        top_hbox = QHBoxLayout(top_card)

        pic = QLabel()
        pic.setPixmap(self.assets.get_actor_portrait(self.actor, 128))
        top_hbox.addWidget(pic)

        ag = self.engine.agencies.get(self.actor.agency_id) if self.actor.agency_id is not None else None
        ag_name = f"{ag.name} (YOUR AGENCY)" if (ag and ag.ours) else (ag.name if ag else "Free Agent")

        pot_colors = {
            "Generational": "#f4c552",
            "Elite": "#4ade80",
            "Star": "#38bdf8",
            "Solid": "#cbd5e1",
            "Fringe": "#94a3b8",
        }
        pot_known = self.actor.potential_known or self.actor.agency_id == 0
        pot_col = pot_colors.get(self.actor.potential_label, "#94a3b8") if pot_known else "#64748b"
        ovr_str = f"{self.actor.overall_rating}" if all(self.actor.known_attributes.values()) else f"~{self.actor.overall_rating}"

        bio_html = (
            f"<h2 style='color:#f4c552; margin:0;'>{self.actor.name} — Rank #{self.actor.actor_ranking}</h2>"
            f"<p style='margin:4px 0;'><b>Agency:</b> <span style='color:#38bdf8;'>{ag_name}</span> | "
            f"<b>Overall:</b> <b style='color:#e8eaef;'>{ovr_str}</b> | "
            f"<b>Potential:</b> <b style='color:{pot_col};'>{self.actor.display_potential}</b> | "
            f"<b>Schedule:</b> {self.actor.schedule_status}</p>"
            f"<p style='margin:4px 0;'><b>Sex:</b> {self.actor.sex} | <b>Age:</b> {self.actor.age} ({self.engine._age_to_bracket(self.actor.age)}) | "
            f"<b>Nationality:</b> {self.actor.nationality} ({self.actor.birthplace}) | <b>Ethnicity:</b> {self.actor.ethnicity}</p>"
            f"<p style='margin:4px 0;'><b>Look:</b> {self.actor.look} | <b>Body Type:</b> {self.actor.bodytype} | "
            f"<b>Height:</b> {self.actor.height_cm} cm ({self.actor.height_category})</p>"
            f"<p style='margin:4px 0;'><b>Fame:</b> <b style='color:#f4c552;'>{int(round(max(0.0, min(100.0, self.actor.fame_score))))} / 100</b> | "
            f"<b>Personality:</b> {self.actor.personality} (DISC: {self.actor.disc}) | "
            f"<b>Morale:</b> {self.actor.morale_label} ({self.actor.morale_score:.0f}) | "
            f"<b>Condition:</b> {self.actor.condition_label} ({self.actor.condition_score:.0f})</p>"
        )
        bio_lbl = QLabel(bio_html)
        bio_lbl.setWordWrap(True)
        top_hbox.addWidget(bio_lbl, 1)

        act_vbox = QVBoxLayout()
        scout_btn = QPushButton("Scout Actor (VIP Scout - $300)")
        scout_btn.setStyleSheet("background-color:#1d4ed8; color:white; font-weight:bold; padding:8px;")
        scout_btn.clicked.connect(self._on_scout)
        act_vbox.addWidget(scout_btn)

        if self.actor.agency_id != 0:
            offer_btn = QPushButton("Offer Representation Contract")
            offer_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:8px;")
            offer_btn.clicked.connect(self._on_offer_contract)
            act_vbox.addWidget(offer_btn)
        else:
            if self.on_find_roles is not None:
                is_avail = self.engine.is_actor_available_for_submission(self.actor.id)
                find_roles_btn = QPushButton(
                    "Find Matching Roles (Role Finder)" if is_avail else f"Role Finder Unavailable ({self.actor.schedule_status})"
                )
                find_roles_btn.setStyleSheet("background-color:#0284c7; color:white; font-weight:bold; padding:8px;")
                find_roles_btn.setEnabled(is_avail)
                find_roles_btn.clicked.connect(self._on_find_matching_roles)
                act_vbox.addWidget(find_roles_btn)

            submit_role_btn = QPushButton("Submit to Open Role / Audition")
            submit_role_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:8px;")
            submit_role_btn.clicked.connect(self._on_submit_to_role)
            act_vbox.addWidget(submit_role_btn)

            chat_btn = QPushButton("Chat with Client (Train / Body)")
            chat_btn.setStyleSheet("background-color:#b45309; color:white; font-weight:bold; padding:8px;")
            chat_btn.clicked.connect(self._on_chat)
            act_vbox.addWidget(chat_btn)

        act_vbox.addStretch(1)
        top_hbox.addLayout(act_vbox)
        layout.addWidget(top_card)

        self.profile_status_lbl = QLabel("")
        self.profile_status_lbl.setWordWrap(True)
        self.profile_status_lbl.setStyleSheet("background-color:#0f172a; padding:6px 12px; border-radius:6px; border:1px solid #334155;")
        self.profile_status_lbl.setVisible(False)
        layout.addWidget(self.profile_status_lbl)

        tabs = QTabWidget()

        tab1 = QWidget()
        t1_hbox = QHBoxLayout(tab1)

        attr_frame = QFrame()
        attr_frame.setObjectName("Card")
        attr_grid = QGridLayout(attr_frame)
        attr_grid.setVerticalSpacing(6)
        attr_grid.setHorizontalSpacing(12)
        attr_grid.addWidget(QLabel("<h3 style='color:#f4c552; margin:0 0 4px 0;'>12 Core Attributes (1-100)</h3>"), 0, 0, 1, 2)
        for idx, attr in enumerate(CORE_ATTRIBUTES):
            disp = self.actor.get_display_attribute(attr)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setFormat(disp)
            if "-" in disp:
                parts = [p.strip() for p in disp.split("-") if p.strip().isdigit()]
                mid = int(sum(int(p) for p in parts) / len(parts)) if parts else 50
                bar.setValue(mid)
                chunk_color = "#64748b"
            else:
                val = int(disp) if disp.isdigit() else 50
                bar.setValue(val)
                if val >= 80:
                    chunk_color = "#d4a02c"
                elif val >= 68:
                    chunk_color = "#22c55e"
                elif val >= 52:
                    chunk_color = "#38bdf8"
                elif val >= 38:
                    chunk_color = "#d97706"
                else:
                    chunk_color = "#dc2626"
            bar.setStyleSheet(
                f"QProgressBar {{ background-color:#141823; border:1px solid #262d3f; border-radius:5px; "
                f"text-align:center; color:#ffffff; font-weight:700; min-height:20px; }}"
                f"QProgressBar::chunk {{ background-color:{chunk_color}; border-radius:4px; }}"
            )
            attr_grid.addWidget(QLabel(f"<b>{attr}</b>"), idx + 1, 0)
            attr_grid.addWidget(bar, idx + 1, 1)
        attr_grid.setColumnStretch(1, 1)
        t1_hbox.addWidget(attr_frame, 1)

        quote_frame = QFrame()
        quote_frame.setObjectName("Card")
        q_vbox = QVBoxLayout(quote_frame)
        q_vbox.addWidget(QLabel("<h3 style='color:#f4c552;'>Role Fee Quotes & Contract</h3>"))
        for rtype, qval in self.actor.quotes.items():
            q_vbox.addWidget(QLabel(f"<b>{rtype}:</b> ${qval:,} USD"))
        if self.actor.contract:
            c = self.actor.contract
            q_vbox.addWidget(QLabel(
                f"<p style='color:#38bdf8;'><b>Active Agency Contract:</b> {c.commission}% commission | "
                f"Expires {c.contract_end} | Min Roles: {c.min_any_roles} ({c.min_major_roles} major)</p>"
            ))
        q_vbox.addSpacing(8)
        q_vbox.addWidget(QLabel("<h3 style='color:#f4c552;'>Special Skills & Quirks</h3>"))
        sk_lbl = QLabel("<b>Special Skills:</b> " + (", ".join(self.actor.special_skills) or "None"))
        sk_lbl.setWordWrap(True)
        q_vbox.addWidget(sk_lbl)
        pi_lbl = QLabel("<b>Personal Info:</b> " + (", ".join(self.actor.personal_info) or "None"))
        pi_lbl.setWordWrap(True)
        q_vbox.addWidget(pi_lbl)
        q_vbox.addWidget(QLabel(
            f"<b>This Year Stats:</b> Income ${self.actor.this_year_income:,} | "
            f"Roles: {self.actor.this_year_all_roles} ({self.actor.this_year_major_roles} major) | "
            f"Awards: {self.actor.num_awards}"
        ))
        q_vbox.addStretch(1)
        t1_hbox.addWidget(quote_frame, 1)
        tabs.addTab(tab1, "Attributes, Quotes & Skills")

        tab2 = QWidget()
        t2_vbox = QVBoxLayout(tab2)
        cred_table = QTableWidget(len(self.actor.credits), 6)
        cred_table.setHorizontalHeaderLabels(["Year", "Project Title", "Type", "Role", "Review Score", "Box Office / Rating"])
        cred_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        cred_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cred_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        cred_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cred_table.setCursor(Qt.CursorShape.PointingHandCursor)
        for idx, cr in enumerate(self.actor.credits):
            t_it = QTableWidgetItem(str(cr.get("title", "")))
            cred_table.setItem(idx, 0, QTableWidgetItem(str(cr.get("year", ""))))
            cred_table.setItem(idx, 1, t_it)
            cred_table.setItem(idx, 2, QTableWidgetItem(str(cr.get("type", ""))))
            cred_table.setItem(idx, 3, QTableWidgetItem(f"{cr.get('role', '')} ({cr.get('role_type', '')})"))
            cred_table.setItem(idx, 4, QTableWidgetItem(f"{cr.get('review', 0)}%"))
            cred_table.setItem(idx, 5, QTableWidgetItem(str(cr.get("gross_or_rating", ""))))
        cred_table.cellClicked.connect(lambda r, _c: self._on_credit_clicked(cred_table, r))
        t2_vbox.addWidget(cred_table)
        tabs.addTab(tab2, f"Credits & Filmography ({len(self.actor.credits)})")

        # Tab 3: Live Actor Earnings, Backend Bonuses & Points Ledger
        tab3 = QWidget()
        t3_vbox = QVBoxLayout(tab3)
        t3_vbox.setSpacing(8)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        for label, val_str, sub_str, col in [
            ("CAREER EARNINGS", f"${self.actor.career_income:,}", f"This Year: ${self.actor.this_year_income:,}", "#f4c552"),
            ("UPFRONT FEES", f"${self.actor.career_upfront_income:,}", f"{self.actor.career_roles} career roles booked", "#4ade80"),
            ("BACKEND & POINTS", f"${self.actor.career_backend_income:,}", "Bonuses + Gross/Net Points", "#38bdf8"),
            ("AGENCY COMMISSIONS", f"${self.actor.career_agency_commissions:,}", f"Net to Actor: ${max(0, self.actor.career_income - self.actor.career_agency_commissions):,}", "#e8eaef"),
        ]:
            kcard = QFrame()
            kcard.setObjectName("KpiCard")
            kvb = QVBoxLayout(kcard)
            kvb.setContentsMargins(12, 8, 12, 8)
            kvb.setSpacing(2)
            kvb.addWidget(QLabel(f"<span style='color:#8f99ad; font-size:8pt; font-weight:700;'>{label}</span>"))
            kvb.addWidget(QLabel(f"<span style='color:{col}; font-size:14pt; font-weight:800;'>{val_str}</span>"))
            kvb.addWidget(QLabel(f"<span style='color:#8f99ad; font-size:8.5pt;'>{sub_str}</span>"))
            kpi_row.addWidget(kcard, 1)
        t3_vbox.addLayout(kpi_row)

        # Active Theatrical + Evergreen Home-Media Backend Deals for this actor
        active_deals = [
            t for t in self.engine.pending_tasks
            if t.get("type") == "backend_check" and t.get("actor_id") == self.actor.id
        ]
        evergreen_deals = [
            d for d in getattr(self.engine, "evergreen_backend_deals", [])
            if d.get("actor_id") == self.actor.id
        ]
        # Combine uniquely by film_id so a film shows both theatrical & evergreen home-media totals
        deals_by_film: dict[int, dict] = {}
        for t in active_deals:
            deals_by_film[t["film_id"]] = {"task": t, "evergreen": None, "contract": t["contract"]}
        for d in evergreen_deals:
            if d["film_id"] in deals_by_film:
                deals_by_film[d["film_id"]]["evergreen"] = d
            else:
                deals_by_film[d["film_id"]] = {"task": None, "evergreen": d, "contract": d["contract"]}

        if deals_by_film:
            t3_vbox.addWidget(QLabel("<b style='color:#38bdf8;'>Active & Evergreen Backend Deals (Theatrical + VHS / DVD / Streaming):</b>"))
            deals_tbl = QTableWidget(len(deals_by_film), 6)
            deals_tbl.setHorizontalHeaderLabels([
                "Project", "Status", "Box Office + Home Media", "Breakeven / Target", "Backend Terms", "Backend Paid",
            ])
            deals_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            deals_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            deals_tbl.setMaximumHeight(140)
            for idx, (fid, bundle) in enumerate(deals_by_film.items()):
                flm = self.engine.films.get(fid)
                con = bundle["contract"]
                t = bundle["task"]
                ev = bundle["evergreen"]
                if not flm:
                    continue
                terms = []
                if con.bo_bonus_fee > 0:
                    terms.append(f"${con.bo_bonus_fee:,} Bonus")
                if con.first_dollar_gross > 0:
                    terms.append(f"{con.first_dollar_gross}% Gross")
                if con.net_points > 0:
                    terms.append(f"{con.net_points}% Net")
                paid_so_far = 0
                if t:
                    paid_so_far += int(t.get("paid_points_total") or 0) + (int(con.bo_bonus_fee) if t.get("paid_bo_bonus") else 0)
                if ev:
                    paid_so_far += int(ev.get("paid_home_media_total") or 0)
                rev_str = f"${flm.box_office_gross:,}" + (f" + ${flm.home_media_revenue:,} HM" if flm.home_media_revenue > 0 else "")
                deals_tbl.setItem(idx, 0, QTableWidgetItem(flm.title))
                deals_tbl.setItem(idx, 1, QTableWidgetItem("Evergreen Catalog" if flm.status == "Released" else flm.status))
                deals_tbl.setItem(idx, 2, QTableWidgetItem(rev_str))
                deals_tbl.setItem(idx, 3, QTableWidgetItem(f"${con.bo_bonus_threshold:,}"))
                deals_tbl.setItem(idx, 4, QTableWidgetItem(" + ".join(terms)))
                p_it = QTableWidgetItem(f"${paid_so_far:,}")
                p_it.setForeground(QColor("#4ade80" if paid_so_far > 0 else "#94a3b8"))
                deals_tbl.setItem(idx, 5, p_it)
            t3_vbox.addWidget(deals_tbl)

        t3_vbox.addWidget(QLabel("<b style='color:#f4c552;'>Itemized Earnings Ledger (Upfront, Backend Bonuses, Points & Renewals):</b>"))
        earn_tbl = QTableWidget(len(self.actor.earnings_history), 7)
        earn_tbl.setHorizontalHeaderLabels([
            "Date", "Project", "Role", "Category", "Actor Gross", "Agency Cut", "Actor Net",
        ])
        earn_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        earn_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for idx, e in enumerate(self.actor.earnings_history):
            cat = str(e.get("category", ""))
            is_be = any(w in cat.lower() for w in ("backend", "points", "bonus"))
            c_it = QTableWidgetItem(cat)
            c_it.setForeground(QColor("#38bdf8" if is_be else "#4ade80"))
            g_it = QTableWidgetItem(f"${int(e.get('gross_amount', 0)):,}")
            g_it.setForeground(QColor("#f4c552"))
            earn_tbl.setItem(idx, 0, QTableWidgetItem(str(e.get("date", ""))))
            earn_tbl.setItem(idx, 1, QTableWidgetItem(str(e.get("project", ""))))
            earn_tbl.setItem(idx, 2, QTableWidgetItem(str(e.get("role", ""))))
            earn_tbl.setItem(idx, 3, c_it)
            earn_tbl.setItem(idx, 4, g_it)
            earn_tbl.setItem(idx, 5, QTableWidgetItem(f"${int(e.get('agency_cut', 0)):,}"))
            earn_tbl.setItem(idx, 6, QTableWidgetItem(f"${int(e.get('actor_net', 0)):,}"))
        t3_vbox.addWidget(earn_tbl, 1)
        tabs.addTab(tab3, f"Earnings & Backend (${self.actor.career_income:,})")

        layout.addWidget(tabs, 1)

        close_btn = QPushButton("Close Actor Profile")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _show_profile_status(self, msg: str, ok: bool = True) -> None:
        color = "#4ade80" if ok else "#f87171"
        self.profile_status_lbl.setText(f"<b style='color:{color};'>{msg}</b>")
        self.profile_status_lbl.setVisible(True)

    def _on_credit_clicked(self, table: QTableWidget, row: int) -> None:
        it = table.item(row, 1)
        if not it:
            return
        title = it.text().strip()
        film = next((f for f in self.engine.films.values() if f.title == title), None)
        if not film:
            self._show_profile_status(f"Project '{title}' is an archival credit with no active project page.", False)
            return
        dlg = ProjectProfileDialog(self.engine, self.assets, film, on_refresh=self.on_refresh, parent=self, on_find_roles=self.on_find_roles)
        dlg.exec()
        if self.on_refresh:
            self.on_refresh()

    def _on_scout(self) -> None:
        ok, msg = self.engine.hire_scout(self.actor.id, 1)
        if self.on_refresh:
            self.on_refresh()
        self._show_profile_status(msg, ok)

    def _on_offer_contract(self) -> None:
        willing, reason = self.engine.check_actor_willing_to_talk(self.actor.id)
        if not willing:
            self._show_profile_status(reason, False)
            return
        dlg = ActorContractDialog(self.engine, self.assets, self.actor, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.signed:
            if self.on_refresh:
                self.on_refresh()
            self.accept()

    def _on_find_matching_roles(self) -> None:
        if self.on_find_roles is not None:
            cb = self.on_find_roles
            aid = self.actor.id
            self.accept()
            cb(aid)

    def _on_chat(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Client Discussion & DISC Persuasion — {self.actor.name}")
        dlg.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        dlg.resize(620, 440)
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel(
            f"<h3 style='color:#f4c552; margin:0;'>Discussion with {self.actor.name}</h3>"
            f"<p style='margin:2px 0;'>Personality: <b>{self.actor.personality}</b> | "
            f"DISC Profile: <b style='color:#38bdf8;'>{self.actor.disc}</b> | Morale: <b>{self.actor.morale_label}</b></p>"
            f"<p style='color:#94a3b8; margin:2px 0;'><i>\"{self.actor.name}: Alright boss, what's on your mind? Convince me why I should do this.\"</i></p>"
        ))

        topic_combo = QComboBox()
        topic_combo.addItem("1. Let's work on your body type to land more roles!", "bodyType")
        topic_combo.addItem("2. Attending an acting course would sharpen your skills.", "actingSchool")
        topic_combo.addItem("3. Learning a new special skill will help at auditions.", "specialSkills")
        vbox.addWidget(topic_combo)

        target_combo = QComboBox()

        def _populate_targets() -> None:
            target_combo.clear()
            t = topic_combo.currentData()
            if t == "bodyType":
                opts = ["Slim", "Average", "Athletic", "Muscular", "Chunky", "Overweight"] if self.actor.sex == "Male" else ["Slim", "Average", "Curvy", "Athletic", "Muscular", "Overweight"]
                for o in opts:
                    if o != self.actor.bodytype:
                        target_combo.addItem(o, o)
            elif t == "actingSchool":
                for o in ["Method Acting Intensive", "Improv & Comedy Workshop", "Voice & Stage Presence", "Physical Stunt & Movement Lab"]:
                    target_combo.addItem(o, o)
            else:
                for sk in self.engine.db.special_skills:
                    if sk not in self.actor.special_skills:
                        target_combo.addItem(sk, sk)

        topic_combo.currentIndexChanged.connect(_populate_targets)
        _populate_targets()
        vbox.addWidget(QLabel("<b>Specific Recommendation:</b>"))
        vbox.addWidget(target_combo)

        vbox.addWidget(QLabel("<b>Choose Your Persuasion Approach (Match their DISC Personality for +32% Success!):</b>"))
        tactic_combo = QComboBox()
        tactic_combo.addItem("[D - Direct & Results] \"Do this and we'll dominate the A-list and crush the competition.\"", "D")
        tactic_combo.addItem("[I - Warm & Flattering] \"You're already magnetic—this will make fans and directors adore you!\"", "I")
        tactic_combo.addItem("[S - Steady & Reassuring] \"Take it step by step—I'll support you the whole way for long-term stability.\"", "S")
        tactic_combo.addItem("[C - Logical & Data-Driven] \"Statistically, casting notices with this trait pay 40% more.\"", "C")
        vbox.addWidget(tactic_combo)

        reply_lbl = QLabel("")
        reply_lbl.setWordWrap(True)
        reply_lbl.setStyleSheet("background-color:#1e2433; padding:10px; border-radius:6px;")
        vbox.addWidget(reply_lbl)

        ask_btn = QPushButton("Deliver Argument & Persuade Client")
        ask_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:9px;")

        def _persuade() -> None:
            ok, reply = self.engine.chat_with_client(
                self.actor.id,
                str(topic_combo.currentData()),
                str(target_combo.currentData()),
                tactic_disc=str(tactic_combo.currentData()),
            )
            color = "#4ade80" if ok else "#f87171"
            reply_lbl.setText(f"<b style='color:{color};'>{reply}</b>")
            if self.on_refresh:
                self.on_refresh()

        ask_btn.clicked.connect(_persuade)
        vbox.addWidget(ask_btn)
        dlg.exec()

    def _on_submit_to_role(self) -> None:
        dlg = SubmitActorToRoleDialog(self.engine, self.actor, on_refresh=self.on_refresh, parent=self)
        dlg.exec()


class SubmitActorToRoleDialog(QDialog):
    """Dedicated dialog to browse all matching open Movie & TV roles for a specific client with full 14-column requirements & live comparison."""

    def __init__(
        self,
        engine: HollywoodlandEngine,
        actor: Actor,
        on_refresh: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.actor = actor
        self.on_refresh = on_refresh
        self.role_entries: list[tuple[FilmOrSeries, RoleSlot]] = []

        self.setWindowTitle(f"Submit {actor.name} for Auditions — Complete Role Requirements")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)
        self.resize(1280, 740)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QLabel(
            f"<h2 style='color:#f4c552; margin:0;'>Submit {self.actor.name} for Open Casting Calls</h2>"
            f"<p style='margin:4px 0;'>Client Profile: <b>{self.actor.sex}, Age {self.actor.age} ({self.engine._age_to_bracket(self.actor.age)})</b> | "
            f"Ethnicity: <b>{self.actor.ethnicity}</b> | Fame: <b>{self.actor.fame_tier}</b> | Look: <b>{self.actor.look}</b> | "
            f"Body Type: <b>{self.actor.bodytype}</b> | Height: <b>{self.actor.height_category} ({self.actor.height_cm}cm)</b> | "
            f"Special Skills: <b>{', '.join(self.actor.special_skills) or 'None'}</b></p>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Clean 11-column table fitting 100% width with Stretch (zero horizontal scrolling!)
        cols = [
            "Project Title", "Genre", "Studio", "Role Name", "Role Type",
            "Ethnicity", "Age Range", "Look / Body / Height",
            "Special Skills", "Deadline", "Fit / Status",
        ]
        self.roles_table = QTableWidget(0, len(cols))
        self.roles_table.setHorizontalHeaderLabels(cols)
        self.roles_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.roles_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.roles_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.roles_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.roles_table.currentCellChanged.connect(self._on_role_selected)
        self.roles_table.cellDoubleClicked.connect(lambda _r, _c: self._on_submit())
        layout.addWidget(self.roles_table, 2)

        # Complete Role Requirement & Client Comparison Inspector at the bottom (Expands when maximized!)
        self.detail_box = QTextEdit()
        self.detail_box.setReadOnly(True)
        self.detail_box.setMinimumHeight(240)
        layout.addWidget(self.detail_box, 2)

        self.status_banner = QLabel("<span style='color:#94a3b8;'>Select any role above to compare every requirement against your client.</span>")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("background-color:#0f172a; padding:8px 12px; border-radius:6px; border:1px solid #334155;")
        layout.addWidget(self.status_banner)

        btn_row = QHBoxLayout()
        submit_btn = QPushButton(f"Submit {self.actor.name} to Selected Role")
        submit_btn.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:10px 18px;")
        submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(submit_btn)

        open_notice_btn = QPushButton("Open Full Project Casting Notice")
        open_notice_btn.setStyleSheet("background-color:#1d4ed8; color:white; font-weight:bold; padding:10px 16px;")
        open_notice_btn.clicked.connect(self._on_open_project)
        btn_row.addWidget(open_notice_btn)

        btn_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._populate()

    def _populate(self) -> None:
        prev_row = max(0, self.roles_table.currentRow())
        self.role_entries.clear()
        for f in self.engine.films.values():
            if f.status != "Casting":
                continue
            for r in f.roles:
                if r.cast_actor_id is not None:
                    continue
                if r.sex in ("Male", "Female") and r.sex != self.actor.sex:
                    continue
                self.role_entries.append((f, r))

        self.roles_table.setUpdatesEnabled(False)
        self.roles_table.setRowCount(len(self.role_entries))
        for idx, (f, r) in enumerate(self.role_entries):
            already = self.actor.id in r.submitted_actor_ids
            eth_ok = r.ethnicity in ("Any", self.actor.ethnicity)
            fit_str = "SUBMITTED" if already else ("Eligible Match" if eth_ok else f"Needs {r.ethnicity}")
            skills_str = ", ".join(r.special_skills) if r.special_skills else "None"

            self.roles_table.setItem(idx, 0, QTableWidgetItem(f"{f.title} ({f.series_or_movie})"))
            self.roles_table.setItem(idx, 1, QTableWidgetItem(f.genre))
            self.roles_table.setItem(idx, 2, QTableWidgetItem(f"{f.studio_or_channel} ({f.studio_tier})"))
            self.roles_table.setItem(idx, 3, QTableWidgetItem(r.role_name))
            self.roles_table.setItem(idx, 4, QTableWidgetItem(r.role_type))
            self.roles_table.setItem(idx, 5, QTableWidgetItem(r.ethnicity))
            self.roles_table.setItem(idx, 6, QTableWidgetItem(r.age_range))
            self.roles_table.setItem(idx, 7, QTableWidgetItem(f"{r.look} | {r.bodytype} | {r.height}"))
            self.roles_table.setItem(idx, 8, QTableWidgetItem(skills_str))
            self.roles_table.setItem(idx, 9, QTableWidgetItem(f.submission_end_date))
            st_it = QTableWidgetItem(fit_str)
            if already:
                st_it.setForeground(QColor("#38bdf8"))
            elif eth_ok:
                st_it.setForeground(QColor("#4ade80"))
            else:
                st_it.setForeground(QColor("#f87171"))
            self.roles_table.setItem(idx, 10, st_it)

        self.roles_table.setUpdatesEnabled(True)

        if self.role_entries:
            sel = min(prev_row, len(self.role_entries) - 1)
            self.roles_table.selectRow(sel)
            self._on_role_selected(sel, 0, -1, -1)

    def _on_role_selected(self, row: int, _col: int, _pr: int, _pc: int) -> None:
        if row < 0 or row >= len(self.role_entries):
            return
        film, role = self.role_entries[row]
        self.detail_box.setHtml(format_full_role_requirements_html(self.engine, film, role, self.actor))

    def _on_submit(self) -> None:
        row = self.roles_table.currentRow()
        if row < 0 or row >= len(self.role_entries):
            return
        film, role = self.role_entries[row]
        ok, msg = self.engine.submit_actor_to_role(self.actor.id, film.id, role.index)
        self._populate()
        if self.on_refresh:
            self.on_refresh()
        color = "#4ade80" if ok else "#f87171"
        self.status_banner.setText(f"<b style='color:{color};'>{msg}</b>")

    def _on_open_project(self) -> None:
        row = self.roles_table.currentRow()
        if row < 0 or row >= len(self.role_entries):
            return
        film, _ = self.role_entries[row]
        dlg = CastingNoticeDialog(self.engine, AssetManager(), film, on_refresh=self.on_refresh, parent=self)
        dlg.exec()
        self._populate()


class ProjectProfileDialog(QDialog):
    """IMDb-style Movie / TV Series Profile showing full financials, reception, crew, and clickable cast."""

    def __init__(
        self,
        engine: HollywoodlandEngine,
        assets: AssetManager,
        film: FilmOrSeries,
        on_refresh: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
        on_find_roles: Optional[Callable[[int], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.assets = assets
        self.film = film
        self.on_refresh = on_refresh
        self.on_find_roles = on_find_roles

        kind_str = "Movie Profile" if film.series_or_movie == "Movie" else "TV Series Profile"
        self.setWindowTitle(f"{kind_str} — '{film.title}'")
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.setSizeGripEnabled(True)
        self.resize(1080, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        f = self.film
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        director = self.engine.creatives.get(f.director_id)
        producer = self.engine.creatives.get(f.producer_id)
        showrunner = self.engine.creatives.get(f.showrunner_id) if f.showrunner_id else None

        # Top Executive Header Card
        hdr_card = QFrame()
        hdr_card.setObjectName("Card")
        hdr_hbox = QHBoxLayout(hdr_card)

        status_colors = {
            "Casting": "#38bdf8",
            "Auditioning": "#fbbf24",
            "Filming": "#f4c552",
            "Post-Production": "#c084fc",
            "In Theaters": "#4ade80",
            "Released": "#4ade80",
            "Airing": "#4ade80",
            "Cancelled": "#f87171",
        }
        st_col = status_colors.get(f.status, "#e8eaef")

        if f.series_or_movie == "Movie":
            if f.status in ("In Theaters", "Released"):
                total_rev = f.box_office_gross + f.home_media_revenue
                gross_col = "#4ade80" if total_rev >= f.breakeven else "#f87171"
                hm_parts = []
                if f.tv_licensing_revenue > 0:
                    hm_parts.append(f"TV Licensing: ${f.tv_licensing_revenue:,}")
                if f.vhs_revenue > 0:
                    hm_parts.append(f"VHS: ${f.vhs_revenue:,}")
                if f.dvd_revenue > 0:
                    hm_parts.append(f"DVD/Blu-ray: ${f.dvd_revenue:,}")
                if f.streaming_revenue > 0:
                    hm_parts.append(f"Streaming/VOD: ${f.streaming_revenue:,}")
                hm_line = (
                    f"<br><b>Home Media & Catalog:</b> <b style='color:#38bdf8;'>${f.home_media_revenue:,}</b> "
                    f"<span style='color:#94a3b8;'>({' · '.join(hm_parts)})</span>"
                    if f.home_media_revenue > 0 else ""
                )
                perf_line = (
                    f"<b>Worldwide Box Office:</b> <b style='color:{gross_col};'>${f.box_office_gross:,}</b> "
                    f"(Budget: ${f.budget:,} | Breakeven: ${f.breakeven:,}) | "
                    f"<b>Critic Review:</b> <b style='color:#f4c552;'>{f.review_score or 0}%</b>{hm_line}"
                )
            else:
                perf_line = (
                    f"<b>Production Budget:</b> <b>${f.budget:,}</b> (Breakeven: ${f.breakeven:,}) | "
                    f"<b>Script Estimate:</b> ~{f.player_rating}%"
                    + (f" | <b>Script Doctor:</b> {f.consultant_rating}%" if f.consultant_rating is not None else "")
                )
        else:
            fmt = f"Pilot ({f.num_episodes} eps)" if f.is_pilot else f"Season {f.season} ({f.num_episodes} eps)"
            rat_str = f"{f.tv_average_rating:.2f}" if f.tv_average_rating > 0 else "Upcoming"
            rev_str = f"{f.review_score}%" if f.review_score is not None else "Pending"
            perf_line = (
                f"<b>Format:</b> {fmt} | <b>Budget:</b> ${f.budget:,} | "
                f"<b>18-49 Demo Rating:</b> <b style='color:#4ade80;'>{rat_str}</b> | "
                f"<b>Critic Review:</b> <b style='color:#f4c552;'>{rev_str}</b>"
            )

        info_html = (
            f"<h2 style='color:#f4c552; margin:0;'>\"{f.title}\" "
            f"<span style='font-size:11pt; color:{st_col};'>[{f.status.upper()}]</span></h2>"
            f"<p style='margin:5px 0;'><b>Studio / Network:</b> {f.studio_or_channel} (Tier {f.studio_tier}) | "
            f"<b>Genre:</b> {f.genre} | <b>Era:</b> {f.historical_era} | <b>Location:</b> {f.filming_location}</p>"
            f"<p style='margin:5px 0;'>{perf_line}</p>"
            f"<p style='margin:5px 0; color:#94a3b8;'><b>Filming:</b> {f.filming_start_date} to {f.filming_end_date} | "
            f"<b>Release / Premiere:</b> {f.release_date}</p>"
        )
        info_lbl = QLabel(info_html)
        info_lbl.setWordWrap(True)
        hdr_hbox.addWidget(info_lbl, 1)

        # Right side: Clickable Crew Bios + Open Casting Notice shortcut
        crew_vbox = QVBoxLayout()
        crew_vbox.setSpacing(6)
        if director:
            dbtn = QPushButton(f"Director: {director.name}")
            dbtn.clicked.connect(lambda: CreativeProfileDialog(self.engine, director, self).exec())
            crew_vbox.addWidget(dbtn)
        if producer:
            pbtn = QPushButton(f"Producer: {producer.name}")
            pbtn.clicked.connect(lambda: CreativeProfileDialog(self.engine, producer, self).exec())
            crew_vbox.addWidget(pbtn)
        if showrunner:
            sbtn = QPushButton(f"Showrunner: {showrunner.name}")
            sbtn.clicked.connect(lambda: CreativeProfileDialog(self.engine, showrunner, self).exec())
            crew_vbox.addWidget(sbtn)

        if f.status in ("Casting", "Auditioning"):
            cast_btn = QPushButton("Open Casting Notice / Submit")
            cast_btn.setStyleSheet("background-color:#d4a02c; color:#090b10; font-weight:900; padding:8px 14px;")
            cast_btn.clicked.connect(self._on_open_casting_notice)
            crew_vbox.addWidget(cast_btn)
        crew_vbox.addStretch(1)
        hdr_hbox.addLayout(crew_vbox)
        layout.addWidget(hdr_card)

        # Full Cast & Roles Table (Single-click any cast actor to open Actor Profile!)
        cast_hdr = QLabel(
            "<h3 style='color:#f4c552; margin:0;'>Full Cast & Characters "
            "<span style='font-size:9.5pt; color:#94a3b8; font-weight:normal;'>— Click any cast actor row to open their Actor Profile</span></h3>"
        )
        layout.addWidget(cast_hdr)

        self.cast_table = QTableWidget(len(f.roles), 8)
        self.cast_table.setHorizontalHeaderLabels([
            "Character / Role", "Billing", "Actor (Click to Open)", "Agency",
            "Age", "Fame (0-100)", "Desired Fame", "Status",
        ])
        self.cast_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cast_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cast_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.cast_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cast_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cast_table.cellClicked.connect(self._on_cast_row_clicked)
        self._populate_cast_table()
        layout.addWidget(self.cast_table, 1)

        # Footer Bar
        bot_row = QHBoxLayout()
        self.scorecard_btn = QPushButton("View Selected Role Audition Scorecard")
        self.scorecard_btn.clicked.connect(self._on_view_scorecard)
        bot_row.addWidget(self.scorecard_btn)

        bot_row.addStretch(1)
        close_btn = QPushButton("Close Profile")
        close_btn.clicked.connect(self.accept)
        bot_row.addWidget(close_btn)
        layout.addLayout(bot_row)

    def _populate_cast_table(self) -> None:
        self.cast_table.setRowCount(len(self.film.roles))
        for idx, r in enumerate(self.film.roles):
            actor = None
            status_str = f"Open ({len(r.submitted_actor_ids)} submitted)"
            if r.cast_actor_id and r.cast_actor_id in self.engine.actors:
                actor = self.engine.actors[r.cast_actor_id]
                status_str = "Cast"
            elif r.offered_actor_id and r.offered_actor_id in self.engine.actors:
                actor = self.engine.actors[r.offered_actor_id]
                status_str = "Offered"

            role_it = QTableWidgetItem(r.role_name)
            role_it.setData(Qt.ItemDataRole.UserRole, actor.id if actor else None)
            self.cast_table.setItem(idx, 0, role_it)
            self.cast_table.setItem(idx, 1, QTableWidgetItem(r.role_type))

            if actor:
                ag = self.engine.agencies.get(actor.agency_id) if actor.agency_id is not None else None
                ag_name = f"{ag.name} (YOU)" if (ag and ag.ours) else (ag.name if ag else "Free Agent")
                act_it = QTableWidgetItem(actor.name)
                act_it.setForeground(QColor("#f4c552" if actor.agency_id == 0 else "#38bdf8"))
                self.cast_table.setItem(idx, 2, act_it)
                self.cast_table.setItem(idx, 3, QTableWidgetItem(ag_name))
                self.cast_table.setItem(idx, 4, QTableWidgetItem(str(actor.age)))
                self.cast_table.setItem(idx, 5, QTableWidgetItem(str(int(round(max(0.0, min(100.0, actor.fame_score)))))))
            else:
                open_it = QTableWidgetItem("Uncast — Open Role")
                open_it.setForeground(QColor("#94a3b8"))
                self.cast_table.setItem(idx, 2, open_it)
                self.cast_table.setItem(idx, 3, QTableWidgetItem("—"))
                self.cast_table.setItem(idx, 4, QTableWidgetItem(r.age_range))
                self.cast_table.setItem(idx, 5, QTableWidgetItem("—"))

            df_it = QTableWidgetItem(f"{int(getattr(r, 'desired_fame', 30))}+")
            df_it.setForeground(QColor("#f4c552"))
            self.cast_table.setItem(idx, 6, df_it)
            self.cast_table.setItem(idx, 7, QTableWidgetItem(status_str))

    def _on_cast_row_clicked(self, row: int, _col: int) -> None:
        it = self.cast_table.item(row, 0)
        if not it:
            return
        aid = it.data(Qt.ItemDataRole.UserRole)
        if aid is not None and aid in self.engine.actors:
            dlg = ActorProfileDialog(
                self.engine,
                self.assets,
                self.engine.actors[aid],
                on_refresh=self.on_refresh,
                parent=self,
                on_find_roles=self.on_find_roles,
            )
            dlg.exec()
            self._populate_cast_table()
            if self.on_refresh:
                self.on_refresh()

    def _on_view_scorecard(self) -> None:
        row = self.cast_table.currentRow()
        if row < 0 or row >= len(self.film.roles):
            return
        role = self.film.roles[row]
        if role.audition_results:
            AuditionReportDialog(self.engine, self.film.id, role.index, self).exec()

    def _on_open_casting_notice(self) -> None:
        dlg = CastingNoticeDialog(self.engine, self.assets, self.film, on_refresh=self.on_refresh, parent=self)
        dlg.exec()
        self._populate_cast_table()
        if self.on_refresh:
            self.on_refresh()
