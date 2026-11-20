from __future__ import annotations
import os
import sys
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hollywoodland.models.entities import CORE_ATTRIBUTES, Actor, FilmOrSeries, InboxMessage
from hollywoodland.systems.engine import HollywoodlandEngine
from hollywoodland.ui.assets import AssetManager
from hollywoodland.ui.dialogs import (
    ActorContractDialog,
    ActorProfileDialog,
    AuditionReportDialog,
    CastingNoticeDialog,
    ProjectProfileDialog,
    RoleContractDialog,
    SubmitActorToRoleDialog,
)


HOLLYWOODLAND_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #090b10;
    color: #e8eaef;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}
QFrame#TopBar {
    background-color: #0b0d13;
    border-bottom: 1px solid #3d3118;
}
QFrame#SideBar {
    background-color: #0c0f16;
    border-right: 1px solid #202532;
}
QLabel#SideSection {
    color: #8f7c4c;
    font-size: 8pt;
    font-weight: 800;
    letter-spacing: 1.5px;
    padding: 12px 14px 4px 14px;
    background-color: transparent;
}
QFrame#SideBar QPushButton {
    background-color: transparent;
    color: #a6b0c3;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 10px 14px;
    text-align: left;
    font-size: 10pt;
    font-weight: 600;
}
QFrame#SideBar QPushButton:hover {
    background-color: #151924;
    color: #f3f4f6;
}
QFrame#SideBar QPushButton:checked {
    background-color: #191d28;
    color: #f4c552;
    border-left: 3px solid #f4c552;
    font-weight: 700;
}
QFrame#Card {
    background-color: #11151f;
    border: 1px solid #222838;
    border-radius: 10px;
}
QFrame#KpiCard {
    background-color: #11151f;
    border: 1px solid #272d3d;
    border-top: 2px solid #d4a02c;
    border-radius: 10px;
}
QPushButton {
    background-color: #1a1f2c;
    color: #e8eaef;
    border: 1px solid #2e3547;
    border-radius: 7px;
    padding: 7px 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #232a3b;
    border-color: #d4a02c;
}
QPushButton:checked {
    background-color: #241f14;
    color: #f4c552;
    border: 1px solid #f4c552;
}
QPushButton:disabled {
    background-color: #12151d;
    color: #555e70;
    border-color: #1e222e;
}
QTableWidget {
    background-color: #0e1119;
    alternate-background-color: #121621;
    gridline-color: #1c2230;
    border: 1px solid #222838;
    border-radius: 8px;
    selection-background-color: #f4c552;
    selection-color: #090b10;
    outline: none;
}
QTableWidget::item {
    padding: 7px 9px;
}
QTableWidget::item:hover {
    background-color: #1d2230;
    color: #f4c552;
}
QTableWidget::item:selected, QTableWidget::item:selected:active, QTableWidget::item:selected:!active {
    background-color: #f4c552;
    color: #090b10;
    font-weight: 700;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 5px;
}
QListWidget::item:hover {
    background-color: #1a1f2c;
}
QListWidget::item:selected, QListWidget::item:selected:active, QListWidget::item:selected:!active {
    background-color: #f4c552;
    color: #090b10;
    font-weight: 700;
    border-radius: 5px;
}
QHeaderView::section {
    background-color: #151924;
    color: #f4c552;
    padding: 9px 8px;
    border: none;
    border-bottom: 1px solid #2c3244;
    font-weight: 700;
    font-size: 9pt;
    letter-spacing: 0.4px;
}
QLineEdit, QComboBox, QTextEdit, QListWidget, QSpinBox, QDoubleSpinBox {
    background-color: #0e1119;
    color: #e8eaef;
    border: 1px solid #262c3d;
    border-radius: 7px;
    padding: 6px 9px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #d4a02c;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QTabWidget::pane {
    border: 1px solid #222838;
    border-radius: 8px;
    background-color: #10141d;
}
QTabBar::tab {
    background-color: #141823;
    color: #8f99ad;
    padding: 9px 16px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:hover {
    color: #e8eaef;
    background-color: #1b202e;
}
QTabBar::tab:selected {
    background-color: #1c212f;
    color: #f4c552;
    border-bottom: 2px solid #f4c552;
}
QProgressBar {
    background-color: #181d29;
    border: 1px solid #262d3f;
    border-radius: 5px;
    text-align: center;
    color: #f8fafc;
    font-weight: 700;
    font-size: 9pt;
    min-height: 18px;
}
QScrollBar:vertical {
    background: #0c0f16;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #282f42;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #d4a02c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #0c0f16;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #282f42;
    border-radius: 5px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background: #d4a02c;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


class NumericTableItem(QTableWidgetItem):
    def __init__(self, text: str, num_val: float) -> None:
        super().__init__(str(text))
        self.setData(Qt.ItemDataRole.UserRole + 10, float(num_val))

    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            v1 = self.data(Qt.ItemDataRole.UserRole + 10)
            v2 = other.data(Qt.ItemDataRole.UserRole + 10) if other is not None else None
            if v1 is not None and v2 is not None:
                return float(v1) < float(v2)
        except Exception:
            pass
        return False


class HollywoodlandWindow(QMainWindow):
    """Main Desktop GUI for Hollywoodland — Zero Horizontal Scrolling & Single-Click Row Navigation."""

    def __init__(self, engine: HollywoodlandEngine) -> None:
        super().__init__()
        self.engine = engine
        self.assets = AssetManager()
        self.nav_buttons: List[QPushButton] = []

        # View state toggles matching original Cattle Call UI
        self.roster_status_filter: str = "ALL"      # "ALL", "AVAILABLE", "SUBMITTED", "AUDITIONING", "FILMING"
        self.roster_view_mode: str = "GENERAL"      # "GENERAL" or "ATTRIBUTES"
        self.ts_view_mode: str = "GENERAL"          # "GENERAL" or "ATTRIBUTES"

        self.setWindowTitle("HOLLYWOODLAND — Talent Agency & Showbiz Tycoon")
        self.resize(1480, 920)
        self.setStyleSheet(HOLLYWOODLAND_QSS)

        self.logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "hollywoodland_logo.png"
        )
        if os.path.exists(self.logo_path):
            self.setWindowIcon(QIcon(self.logo_path))

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_vbox = QVBoxLayout(central)
        root_vbox.setContentsMargins(0, 0, 0, 0)
        root_vbox.setSpacing(0)

        # 1. Persistent Executive Header
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_hbox = QHBoxLayout(top_bar)
        top_hbox.setContentsMargins(16, 8, 16, 8)
        top_hbox.setSpacing(10)

        brand_lbl = QLabel()
        if os.path.exists(self.logo_path):
            logo_pm = QPixmap(self.logo_path).scaledToHeight(
                54, Qt.TransformationMode.SmoothTransformation
            )
            brand_lbl.setPixmap(logo_pm)
            brand_lbl.setStyleSheet("background-color: transparent; padding: 0 2px;")
        else:
            brand_lbl.setText(
                "<span style='font-size:18pt; font-weight:900; color:#f4c552; letter-spacing:2px;'>HOLLYWOODLAND</span>"
            )
        top_hbox.addWidget(brand_lbl)
        top_hbox.addStretch(1)

        self.agency_badge_lbl = QLabel()
        self.agency_badge_lbl.setStyleSheet(
            "background-color:#141822; color:#f4c552; font-size:10pt; font-weight:700; "
            "padding:6px 12px; border-radius:7px; border:1px solid #3a3019;"
        )
        top_hbox.addWidget(self.agency_badge_lbl)

        self.budget_lbl = QLabel()
        self.budget_lbl.setStyleSheet(
            "background-color:#0e1713; color:#4ade80; font-size:11.5pt; font-weight:800; "
            "padding:6px 13px; border-radius:7px; border:1px solid #1e3a2a;"
        )
        top_hbox.addWidget(self.budget_lbl)

        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet(
            "background-color:#151822; color:#e8eaef; font-size:10.5pt; font-weight:700; "
            "padding:6px 12px; border-radius:7px; border:1px solid #272d3d;"
        )
        top_hbox.addWidget(self.date_lbl)

        self.next_day_btn = QPushButton("NEXT DAY  ›")
        self.next_day_btn.setStyleSheet(
            "background-color:#d4a02c; color:#090b10; font-size:10.5pt; font-weight:900; "
            "padding:8px 16px; border-radius:7px; border:1px solid #f4c552;"
        )
        self.next_day_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_day_btn.clicked.connect(self._on_next_day)
        top_hbox.addWidget(self.next_day_btn)

        self.next_week_btn = QPushButton("+7 DAYS  »")
        self.next_week_btn.setStyleSheet(
            "background-color:#1a1f2c; color:#f4c552; font-size:9.5pt; font-weight:700; "
            "padding:8px 12px; border-radius:7px; border:1px solid #3a3019;"
        )
        self.next_week_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_week_btn.clicked.connect(self._on_next_week)
        top_hbox.addWidget(self.next_week_btn)

        root_vbox.addWidget(top_bar)

        # 2. Main Body: Sleek Left Sidebar + Right Content Area
        body_hbox = QHBoxLayout()
        body_hbox.setContentsMargins(0, 0, 0, 0)
        body_hbox.setSpacing(0)

        side_bar = QFrame()
        side_bar.setObjectName("SideBar")
        side_bar.setFixedWidth(210)
        side_vbox = QVBoxLayout(side_bar)
        side_vbox.setContentsMargins(0, 8, 0, 12)
        side_vbox.setSpacing(2)

        sec_agency = QLabel("AGENCY")
        sec_agency.setObjectName("SideSection")
        side_vbox.addWidget(sec_agency)

        agency_nav = [
            (0, "Inbox"),
            (1, "My Agency"),
            (2, "My Actors"),
            (3, "Casting Calls"),
            (4, "Talent Service"),
        ]
        for idx, label in agency_nav:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked, i=idx: self._switch_page(i))
            side_vbox.addWidget(btn)
            self.nav_buttons.append(btn)

        sec_ind = QLabel("INDUSTRY")
        sec_ind.setObjectName("SideSection")
        side_vbox.addWidget(sec_ind)

        industry_nav = [
            (5, "Box Office"),
            (6, "TV Ratings"),
            (7, "Awards"),
            (8, "Top 100 Actors"),
        ]
        for idx, label in industry_nav:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked, i=idx: self._switch_page(i))
            side_vbox.addWidget(btn)
            self.nav_buttons.append(btn)

        side_vbox.addStretch(1)

        save_wrap = QHBoxLayout()
        save_wrap.setContentsMargins(14, 0, 14, 0)
        save_btn = QPushButton("Save Agency")
        save_btn.setStyleSheet(
            "background-color:#151924; color:#e8eaef; border:1px solid #2e3547; "
            "border-radius:7px; padding:8px 12px; text-align:center; font-weight:700;"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save_game)
        save_wrap.addWidget(save_btn)
        side_vbox.addLayout(save_wrap)

        body_hbox.addWidget(side_bar)

        # Right column: Stacked Content Pages + Bottom Status Toast Bar
        content_vbox = QVBoxLayout()
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_messages_page())       # 0
        self.stack.addWidget(self._build_my_agency_page())      # 1
        self.stack.addWidget(self._build_my_actors_page())      # 2
        self.stack.addWidget(self._build_casting_calls_page())  # 3
        self.stack.addWidget(self._build_talent_service_page()) # 4
        self.stack.addWidget(self._build_box_office_page())     # 5
        self.stack.addWidget(self._build_tv_ratings_page())     # 6
        self.stack.addWidget(self._build_awards_page())         # 7
        self.stack.addWidget(self._build_top_actors_page())     # 8

        content_vbox.addWidget(self.stack, 1)

        # Bottom Status Toast Bar (Ignored horizontal policy prevents long messages from widening the window)
        self.toast_bar = QLabel("Tip: Single-click any Actor or Film in any table to open it immediately!")
        self.toast_bar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.toast_bar.setStyleSheet(
            "background-color:#0b0d13; color:#8f99ad; font-weight:600; padding:7px 18px; border-top:1px solid #202532;"
        )
        content_vbox.addWidget(self.toast_bar)

        body_hbox.addLayout(content_vbox, 1)
        root_vbox.addLayout(body_hbox, 1)
        self._switch_page(0)

    def show_toast(self, message: str, is_error: bool = False) -> None:
        if not hasattr(self, "toast_bar"):
            return
        color = "#f87171" if is_error else "#4ade80"
        self.toast_bar.setText(f"<span style='color:{color};'>{message}</span>")

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)
        self.refresh_all()

    # =========================================================================
    # Page 0: Messages Inbox
    # =========================================================================
    def _build_messages_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("<h3 style='color:#f4c552; margin:0;'>Agency Inbox & Wire</h3>"))
        self.msg_cat_combo = QComboBox()
        for label, key in [
            ("All Messages", "all"),
            ("General & Events", "general"),
            ("Critic Reviews", "reviews"),
            ("Filming Updates", "filming"),
            ("Box Office & Releases", "release"),
        ]:
            self.msg_cat_combo.addItem(label, key)
        self.msg_cat_combo.currentIndexChanged.connect(self._refresh_messages_page)
        filter_row.addWidget(self.msg_cat_combo)
        filter_row.addStretch(1)
        vbox.addLayout(filter_row)

        split = QSplitter(Qt.Orientation.Horizontal)

        self.msg_list = QListWidget()
        self.msg_list.currentRowChanged.connect(self._on_message_selected)
        split.addWidget(self.msg_list)

        right_card = QFrame()
        right_card.setObjectName("Card")
        r_vbox = QVBoxLayout(right_card)

        self.msg_header_lbl = QLabel("Select a message on the left.")
        self.msg_header_lbl.setWordWrap(True)
        self.msg_header_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        r_vbox.addWidget(self.msg_header_lbl)

        self.msg_canvas_lbl = QLabel()
        self.msg_canvas_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_vbox.addWidget(self.msg_canvas_lbl)

        self.msg_body_text = QTextEdit()
        self.msg_body_text.setReadOnly(True)
        r_vbox.addWidget(self.msg_body_text, 1)

        self.msg_btn_row = QVBoxLayout()
        self.msg_btn_row.setSpacing(6)
        r_vbox.addLayout(self.msg_btn_row)

        split.addWidget(right_card)
        split.setSizes([480, 920])
        vbox.addWidget(split, 1)
        return page

    def _refresh_messages_page(self) -> None:
        cat = self.msg_cat_combo.currentData() if hasattr(self, "msg_cat_combo") else "all"
        prev_id = None
        curr_item = self.msg_list.currentItem()
        if curr_item:
            prev_id = curr_item.data(Qt.ItemDataRole.UserRole)

        self.msg_list.blockSignals(True)
        self.msg_list.clear()
        self.filtered_messages: List[InboxMessage] = []
        sel_row = 0

        for m in self.engine.messages:
            if cat != "all" and m.category != cat:
                continue
            idx = len(self.filtered_messages)
            self.filtered_messages.append(m)
            prefix = "[ACTION REQUIRED] " if m.requires_response else ("* " if not m.was_read else "")
            item = QListWidgetItem(f"{prefix}[{m.date_str}] {m.title}")
            item.setData(Qt.ItemDataRole.UserRole, m.id)
            if m.requires_response:
                item.setForeground(QColor("#f87171"))
            elif not m.was_read:
                item.setForeground(QColor("#f4c552"))
            self.msg_list.addItem(item)
            if prev_id == m.id:
                sel_row = idx

        for idx, m in enumerate(self.filtered_messages):
            if m.requires_response:
                sel_row = idx
                break
        else:
            if self.filtered_messages and not self.filtered_messages[0].was_read:
                sel_row = 0

        self.msg_list.blockSignals(False)
        if self.filtered_messages:
            self.msg_list.setCurrentRow(sel_row)
            self._on_message_selected(sel_row)

    def _on_message_selected(self, row: int) -> None:
        while self.msg_btn_row.count():
            child = self.msg_btn_row.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if row < 0 or row >= len(getattr(self, "filtered_messages", [])):
            self.msg_header_lbl.setText("No message selected.")
            self.msg_body_text.clear()
            self.msg_canvas_lbl.clear()
            return

        m = self.filtered_messages[row]
        m.was_read = True
        self._update_nav_badges()

        sev_badge = "<span style='color:#f87171;'>[RESPONSE REQUIRED]</span> " if m.requires_response else ""
        self.msg_header_lbl.setText(
            f"<h2 style='color:#f4c552; margin:0;'>{sev_badge}{m.title}</h2>"
            f"<p style='color:#94a3b8; margin:2px 0;'>From: <b>{m.sender_name}</b> | Date: <b>{m.date_str}</b> | Category: {m.category.title()}</p>"
        )
        self.msg_body_text.setPlainText(m.content)

        if m.canvas_file:
            pm = self.assets.get_texture(m.canvas_file, 480, 180)
            if pm:
                self.msg_canvas_lbl.setPixmap(pm)
                self.msg_canvas_lbl.setVisible(True)
            else:
                self.msg_canvas_lbl.setVisible(False)
        else:
            self.msg_canvas_lbl.setVisible(False)

        for btn_spec in m.buttons:
            b = QPushButton(btn_spec.title)
            b.setStyleSheet("background-color:#15803d; color:white; font-weight:bold; padding:9px 16px; text-align:left;")
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            b.clicked.connect(lambda _c, msg=m, cmd=btn_spec.command: self._execute_message_command(msg, cmd))
            self.msg_btn_row.addWidget(b)

        if m.related_actor_id and m.related_actor_id in self.engine.actors:
            ab = QPushButton(f"Open Actor Profile ({self.engine.actors[m.related_actor_id].name})")
            ab.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            ab.clicked.connect(lambda _c, aid=m.related_actor_id: self._open_actor_profile(aid))
            self.msg_btn_row.addWidget(ab)

        if m.related_film_id and m.related_film_id in self.engine.films:
            fb = QPushButton(f"Open Casting Notice ('{self.engine.films[m.related_film_id].title}')")
            fb.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            fb.clicked.connect(lambda _c, fid=m.related_film_id: self._open_casting_notice(fid))
            self.msg_btn_row.addWidget(fb)

    def _execute_message_command(self, msg: InboxMessage, command: str) -> None:
        if command == "CLOSE":
            msg.requires_response = False
            msg.buttons.clear()
            self.refresh_all()
            return
        if command.startswith("EVT:"):
            parts = command.split(":")
            child_evt = parts[1]
            aid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) > 0 else msg.related_actor_id
            msg.requires_response = False
            msg.buttons.clear()
            self.engine.execute_event_by_id(child_evt, aid)
            self.refresh_all()
            return
        if command.startswith("ROLE_OFFER:"):
            _, fid_s, ridx_s, aid_s = command.split(":")
            dlg = RoleContractDialog(self.engine, self.assets, int(fid_s), int(ridx_s), int(aid_s), self)
            dlg.exec()
            msg.requires_response = False
            self.refresh_all()
            if dlg.status_message:
                self.show_toast(dlg.status_message, False)
        elif command.startswith("AUDITION_REPORT:"):
            _, fid_s, ridx_s = command.split(":")
            dlg = AuditionReportDialog(self.engine, int(fid_s), int(ridx_s), self)
            dlg.exec()

    # =========================================================================
    # Page 1: My Agency Screen (Executive Dashboard + Ledger & Rankings)
    # =========================================================================
    def _make_kpi_card(self, label: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("KpiCard")
        vb = QVBoxLayout(card)
        vb.setContentsMargins(14, 10, 14, 10)
        vb.setSpacing(2)
        title_lbl = QLabel(f"<span style='color:#8f99ad; font-size:8.5pt; font-weight:700; letter-spacing:0.8px;'>{label.upper()}</span>")
        val_lbl = QLabel("--")
        val_lbl.setStyleSheet("font-size:15pt; font-weight:800; color:#f4c552; background:transparent;")
        sub_lbl = QLabel("")
        sub_lbl.setStyleSheet("font-size:8.5pt; color:#8f99ad; background:transparent;")
        vb.addWidget(title_lbl)
        vb.addWidget(val_lbl)
        vb.addWidget(sub_lbl)
        return card, val_lbl, sub_lbl

    def _build_my_agency_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)
        vbox.setSpacing(10)

        # Executive KPI Strip (5 glanceable cards)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        c1, self.kpi_cash_val, self.kpi_cash_sub = self._make_kpi_card("Cash Reserve")
        c2, self.kpi_burn_val, self.kpi_burn_sub = self._make_kpi_card("Monthly Overhead")
        c3, self.kpi_roster_val, self.kpi_roster_sub = self._make_kpi_card("Active Roster")
        c4, self.kpi_pipe_val, self.kpi_pipe_sub = self._make_kpi_card("Active Pipeline")
        c5, self.kpi_rank_val, self.kpi_rank_sub = self._make_kpi_card("Agency Standing")
        for c in (c1, c2, c3, c4, c5):
            kpi_row.addWidget(c, 1)
        vbox.addLayout(kpi_row)

        top_split = QHBoxLayout()
        top_split.setSpacing(10)

        self.agency_summary_card = QFrame()
        self.agency_summary_card.setObjectName("Card")
        ag_vbox = QVBoxLayout(self.agency_summary_card)
        self.agency_info_lbl = QLabel()
        self.agency_info_lbl.setWordWrap(True)
        ag_vbox.addWidget(self.agency_info_lbl)
        top_split.addWidget(self.agency_summary_card, 1)

        self.manager_card = QFrame()
        self.manager_card.setObjectName("Card")
        m_vbox = QVBoxLayout(self.manager_card)
        self.manager_info_lbl = QLabel()
        self.manager_info_lbl.setWordWrap(True)
        m_vbox.addWidget(self.manager_info_lbl)
        top_split.addWidget(self.manager_card, 1)

        vbox.addLayout(top_split)

        tabs = QTabWidget()

        self.ledger_table = QTableWidget(0, 5)
        self.ledger_table.setHorizontalHeaderLabels(["Date", "Category", "Description", "Actor / Project", "Amount (USD)"])
        self.ledger_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ledger_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabs.addTab(self.ledger_table, "Financial Ledger & Commissions")

        self.upcoming_pay_table = QTableWidget(0, 6)
        self.upcoming_pay_table.setHorizontalHeaderLabels([
            "Client", "Project Title", "Current Box Office", "Bonus Threshold (Breakeven)", "Potential Bonus / Points", "Payout Date (Run End)",
        ])
        self.upcoming_pay_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.upcoming_pay_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabs.addTab(self.upcoming_pay_table, "Upcoming Backend Bonuses & Points")

        self.agency_rank_table = QTableWidget(0, 5)
        self.agency_rank_table.setHorizontalHeaderLabels(["Rank", "Agency Name", "Tier", "Reputation Score", "Represented Clients"])
        self.agency_rank_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.agency_rank_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabs.addTab(self.agency_rank_table, "Hollywoodland Agency Rankings (All 39 Agencies)")

        vbox.addWidget(tabs, 1)
        return page

    def _refresh_my_agency_page(self) -> None:
        pa = self.engine.player_agency
        my_clients = [a for a in self.engine.actors.values() if a.agency_id == 0]
        avail_cnt = sum(1 for a in my_clients if self.engine.is_actor_available_for_submission(a.id))
        active_subs = sum(1 for s in self.engine.submissions if s.status in ("Submitted", "Auditioning", "Offered"))
        filming_cnt = sum(1 for a in my_clients if "FILMING" in a.schedule_status.upper() or "CONTRACTED" in a.schedule_status.upper())

        cash_color = "#4ade80" if pa.budget >= 15000 else ("#fbbf24" if pa.budget >= 0 else "#f87171")
        self.kpi_cash_val.setText(f"${pa.budget:,.0f}")
        self.kpi_cash_val.setStyleSheet(f"font-size:15pt; font-weight:800; color:{cash_color}; background:transparent;")
        self.kpi_cash_sub.setText(f"Lifetime Commissions: ${pa.stats_income:,}")

        self.kpi_burn_val.setText(f"${pa.monthly_overhead:,}/mo")
        self.kpi_burn_val.setStyleSheet("font-size:15pt; font-weight:800; color:#e8eaef; background:transparent;")
        runway = int(pa.budget // max(1, pa.monthly_overhead)) if pa.budget > 0 else 0
        self.kpi_burn_sub.setText(f"~{runway} mo runway (billed 1st)")

        self.kpi_roster_val.setText(f"{len(my_clients)} / {pa.max_actors}")
        self.kpi_roster_val.setStyleSheet("font-size:15pt; font-weight:800; color:#f4c552; background:transparent;")
        self.kpi_roster_sub.setText(f"{avail_cnt} available · {filming_cnt} filming")

        self.kpi_pipe_val.setText(f"{active_subs} Active")
        self.kpi_pipe_val.setStyleSheet("font-size:15pt; font-weight:800; color:#38bdf8; background:transparent;")
        self.kpi_pipe_sub.setText(f"{pa.stats_major_roles} Major · {pa.stats_minor_roles} Minor booked")

        self.kpi_rank_val.setText(f"#{pa.ranking} · {pa.reputation}")
        self.kpi_rank_val.setStyleSheet("font-size:15pt; font-weight:800; color:#f4c552; background:transparent;")
        self.kpi_rank_sub.setText(f"Reputation Score: {pa.reputation_score:.1f}")

        self.agency_info_lbl.setText(
            f"<h2 style='color:#f4c552; margin:0;'>{pa.name} (Rank #{pa.ranking} of {len(self.engine.agencies)})</h2>"
            f"<p><b>Agency Reputation Tier:</b> <span style='color:#38bdf8;'>{pa.reputation}</span> (Score: {pa.reputation_score:.1f})<br>"
            f"<b>Current Bank Balance:</b> <span style='color:#4ade80;'>${pa.budget:,.0f} USD</span><br>"
            f"<b>Monthly Office Overhead:</b> ${pa.monthly_overhead:,} USD (next billed on 1st of month)<br>"
            f"<b>Active Client Roster:</b> {len(my_clients)} / {pa.max_actors} actors<br>"
            f"<b>Total Commission Income Earned:</b> ${pa.stats_income:,} USD<br>"
            f"<b>Bookings Landed:</b> {pa.stats_major_roles} Major Roles | {pa.stats_minor_roles} Minor Roles | {pa.stats_awards} Awards</p>"
        )
        self.manager_info_lbl.setText(
            f"<h2 style='color:#f4c552; margin:0;'>Managing Partner: {pa.owner_name}</h2>"
            f"<p><b>Age:</b> {pa.owner_age} | <b>Nationality:</b> {pa.owner_nationality}</p>"
            f"<p><b>Knowledge Skill (Script Reading Accuracy):</b> <span style='color:#4ade80;'>{pa.knowledge_skill} / 100</span><br>"
            f"<b>Personal Skill (Client Persuasion & Morale):</b> <span style='color:#4ade80;'>{pa.personal_skill} / 100</span><br>"
            f"<b>Negotiation Skill (Studio & Actor Deals):</b> <span style='color:#4ade80;'>{pa.negotiation_skill} / 100</span></p>"
            f"<p style='color:#94a3b8;'><i>Tip: Reach $200,000 balance and 45+ Reputation Score to advance to a Medium Agency and unlock Notable stars!</i></p>"
        )

        self.ledger_table.setRowCount(len(self.engine.ledger))
        for idx, entry in enumerate(self.engine.ledger):
            self.ledger_table.setItem(idx, 0, QTableWidgetItem(entry.date_str))
            self.ledger_table.setItem(idx, 1, QTableWidgetItem(entry.payment_type))
            self.ledger_table.setItem(idx, 2, QTableWidgetItem(entry.description))
            ap = " / ".join(x for x in (entry.actor_name, entry.project_title) if x)
            self.ledger_table.setItem(idx, 3, QTableWidgetItem(ap))
            amt_str = f"+${entry.amount:,}" if entry.amount >= 0 else f"-${abs(entry.amount):,}"
            amt_item = NumericTableItem(amt_str, float(entry.amount))
            amt_item.setForeground(QColor("#4ade80" if entry.amount >= 0 else "#f87171"))
            self.ledger_table.setItem(idx, 4, amt_item)

        backend_tasks = [t for t in self.engine.pending_tasks if t.get("type") == "backend_check"]
        self.upcoming_pay_table.setRowCount(len(backend_tasks))
        for idx, t in enumerate(backend_tasks):
            act = self.engine.actors.get(t["actor_id"])
            film = self.engine.films.get(t["film_id"])
            c = t["contract"]
            if not act or not film:
                continue
            self.upcoming_pay_table.setItem(idx, 0, QTableWidgetItem(act.name))
            self.upcoming_pay_table.setItem(idx, 1, QTableWidgetItem(f"{film.title} ({film.status})"))
            bo_it = NumericTableItem(f"${film.box_office_gross:,}", float(film.box_office_gross))
            bo_it.setForeground(QColor("#4ade80" if film.box_office_gross >= c.bo_bonus_threshold else "#fbbf24"))
            self.upcoming_pay_table.setItem(idx, 2, bo_it)
            self.upcoming_pay_table.setItem(idx, 3, NumericTableItem(f"${c.bo_bonus_threshold:,}", float(c.bo_bonus_threshold)))
            pts_parts = []
            if c.bo_bonus_fee > 0:
                pts_parts.append(f"${c.bo_bonus_fee:,} BO Bonus")
            if c.first_dollar_gross > 0:
                pts_parts.append(f"{c.first_dollar_gross}% 1st Dollar Gross")
            if c.net_points > 0:
                pts_parts.append(f"{c.net_points}% Net Points")
            self.upcoming_pay_table.setItem(idx, 4, QTableWidgetItem(" + ".join(pts_parts)))
            self.upcoming_pay_table.setItem(idx, 5, QTableWidgetItem(t["due"]))

        sorted_ag = sorted(self.engine.agencies.values(), key=lambda a: a.ranking)
        self.agency_rank_table.setRowCount(len(sorted_ag))
        for idx, ag in enumerate(sorted_ag):
            c_count = sum(1 for a in self.engine.actors.values() if a.agency_id == ag.id)
            r_it = NumericTableItem(f"#{ag.ranking}", float(ag.ranking))
            n_it = QTableWidgetItem(f"{ag.name} (YOU)" if ag.ours else ag.name)
            t_it = QTableWidgetItem(ag.reputation)
            s_it = NumericTableItem(f"{ag.reputation_score:.1f}", ag.reputation_score)
            c_it = NumericTableItem(f"{c_count} / {ag.max_actors}", float(c_count))
            if ag.ours:
                for it in (r_it, n_it, t_it, s_it, c_it):
                    it.setForeground(QColor("#f4c552"))
            self.agency_rank_table.setItem(idx, 0, r_it)
            self.agency_rank_table.setItem(idx, 1, n_it)
            self.agency_rank_table.setItem(idx, 2, t_it)
            self.agency_rank_table.setItem(idx, 3, s_it)
            self.agency_rank_table.setItem(idx, 4, c_it)

    # =========================================================================
    # Page 2: My Actors (Original Roster.ui Layout — Zero Horizontal Scroll!)
    # =========================================================================
    def _build_my_actors_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)

        # Authentic Roster.ui Top Bar: Status Filter Tabs + General/Attributes View Toggle
        top_card = QFrame()
        top_card.setObjectName("Card")
        top_vbox = QVBoxLayout(top_card)
        top_vbox.setSpacing(6)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b style='color:#f4c552;'>ROSTER VIEW:</b>"))
        self.roster_status_btns: List[QPushButton] = []
        for label, key in [
            ("All Clients", "ALL"),
            ("Available", "AVAILABLE"),
            ("Submitted", "SUBMITTED"),
            ("Auditioning", "AUDITIONING"),
            ("Filming", "FILMING"),
        ]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(key == "ALL")
            b.clicked.connect(lambda _c, k=key: self._set_roster_status_filter(k))
            row1.addWidget(b)
            self.roster_status_btns.append((b, key))
        row1.addStretch(1)
        top_vbox.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("<b style='color:#38bdf8;'>COLUMNS:</b>"))
        self.roster_gen_btn = QPushButton("GENERAL (Bio & Schedule)")
        self.roster_gen_btn.setCheckable(True)
        self.roster_gen_btn.setChecked(True)
        self.roster_gen_btn.clicked.connect(lambda: self._set_roster_view_mode("GENERAL"))
        row2.addWidget(self.roster_gen_btn)

        self.roster_attr_btn = QPushButton("ATTRIBUTES (All 12 Skills)")
        self.roster_attr_btn.setCheckable(True)
        self.roster_attr_btn.clicked.connect(lambda: self._set_roster_view_mode("ATTRIBUTES"))
        row2.addWidget(self.roster_attr_btn)

        tip_lbl = QLabel("<i style='color:#94a3b8;'>Single-click any actor row to open Profile / Submit for Auditions</i>")
        tip_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row2.addWidget(tip_lbl, 1)
        top_vbox.addLayout(row2)
        vbox.addWidget(top_card)

        self.roster_table = QTableWidget(0, 10)
        self.roster_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.roster_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.roster_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.roster_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.roster_table.setSortingEnabled(True)
        self.roster_table.setCursor(Qt.CursorShape.PointingHandCursor)
        # Single-click immediately opens Actor Profile (just like original Cattle Call!)
        self.roster_table.cellClicked.connect(self._on_roster_clicked)
        vbox.addWidget(self.roster_table, 1)
        return page

    def _set_roster_status_filter(self, key: str) -> None:
        self.roster_status_filter = key
        for b, k in self.roster_status_btns:
            b.setChecked(k == key)
        self._refresh_my_actors_page()

    def _set_roster_view_mode(self, mode: str) -> None:
        self.roster_view_mode = mode
        self.roster_gen_btn.setChecked(mode == "GENERAL")
        self.roster_attr_btn.setChecked(mode == "ATTRIBUTES")
        self._refresh_my_actors_page()

    def _refresh_my_actors_page(self, *_args) -> None:
        all_clients = [a for a in self.engine.actors.values() if a.agency_id == 0]
        filtered: List[Actor] = []
        for a in all_clients:
            st = a.schedule_status.upper()
            if self.roster_status_filter == "AVAILABLE" and st != "AVAILABLE":
                continue
            elif self.roster_status_filter == "SUBMITTED" and "SUBMITTED" not in st:
                continue
            elif self.roster_status_filter == "AUDITIONING" and "AUDITION" not in st:
                continue
            elif self.roster_status_filter == "FILMING" and ("FILMING" not in st and "CONTRACTED" not in st):
                continue
            filtered.append(a)

        self.roster_table.setUpdatesEnabled(False)
        self.roster_table.setSortingEnabled(False)
        self.roster_table.clear()

        if self.roster_view_mode == "GENERAL":
            cols = ["Sex", "Name", "Age", "Fame", "OVR", "Potential", "Ethnicity", "Look", "Body Type", "Morale / Condition", "Schedule / Status"]
            self.roster_table.setColumnCount(len(cols))
            self.roster_table.setHorizontalHeaderLabels(cols)
            self.roster_table.setRowCount(len(filtered))
            pot_colors = {"Generational": "#f4c552", "Elite": "#4ade80", "Star": "#38bdf8", "Solid": "#cbd5e1", "Fringe": "#94a3b8"}
            for row, a in enumerate(filtered):
                s_it = QTableWidgetItem(a.sex)
                s_it.setData(Qt.ItemDataRole.UserRole, a.id)
                p_it = NumericTableItem(a.display_potential, float(a.potential_rating))
                p_it.setForeground(QColor(pot_colors.get(a.potential_label, "#94a3b8")))
                self.roster_table.setItem(row, 0, s_it)
                self.roster_table.setItem(row, 1, QTableWidgetItem(a.name))
                self.roster_table.setItem(row, 2, NumericTableItem(str(a.age), float(a.age)))
                f_val = int(round(max(0.0, min(100.0, a.fame_score))))
                self.roster_table.setItem(row, 3, NumericTableItem(str(f_val), float(f_val)))
                self.roster_table.setItem(row, 4, NumericTableItem(str(a.overall_rating), float(a.overall_rating)))
                self.roster_table.setItem(row, 5, p_it)
                self.roster_table.setItem(row, 6, QTableWidgetItem(a.ethnicity))
                self.roster_table.setItem(row, 7, QTableWidgetItem(a.look))
                self.roster_table.setItem(row, 8, QTableWidgetItem(a.bodytype))
                self.roster_table.setItem(row, 9, QTableWidgetItem(f"{a.morale_label} / {a.condition_label}"))
                self.roster_table.setItem(row, 10, QTableWidgetItem(a.schedule_status))
        else:
            cols = ["Sex", "Name", "Age", "Fame", "CHAR.", "IMPR.", "VOC.", "PHYS.", "FAC.", "INTEL.", "CHRSM.", "HUM.", "COMM.", "CONF.", "PROF.", "STAM."]
            self.roster_table.setColumnCount(len(cols))
            self.roster_table.setHorizontalHeaderLabels(cols)
            self.roster_table.setRowCount(len(filtered))
            for row, a in enumerate(filtered):
                s_it = QTableWidgetItem(a.sex)
                s_it.setData(Qt.ItemDataRole.UserRole, a.id)
                self.roster_table.setItem(row, 0, s_it)
                self.roster_table.setItem(row, 1, QTableWidgetItem(a.name))
                self.roster_table.setItem(row, 2, NumericTableItem(str(a.age), float(a.age)))
                f_val = int(round(max(0.0, min(100.0, a.fame_score))))
                self.roster_table.setItem(row, 3, NumericTableItem(str(f_val), float(f_val)))
                for idx, ak in enumerate(CORE_ATTRIBUTES):
                    v = a.attributes.get(ak, 50)
                    self.roster_table.setItem(row, 4 + idx, NumericTableItem(str(v), float(v)))

        self.roster_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.roster_table.setSortingEnabled(True)
        self.roster_table.setUpdatesEnabled(True)

    def _on_roster_clicked(self, row: int, _col: int) -> None:
        it = self.roster_table.item(row, 0)
        if it:
            self._open_actor_profile(int(it.data(Qt.ItemDataRole.UserRole)))

    # =========================================================================
    # Page 3: Casting Calls (Original Casting.ui — Single Click Opens Film!)
    # =========================================================================
    def _build_casting_calls_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)

        casting_hdr = QLabel(
            "<h3 style='color:#f4c552; margin:0;'>Casting Calls — Click any Movie or TV Series below to immediately open its Casting Notice & Roles</h3>"
        )
        casting_hdr.setWordWrap(True)
        casting_hdr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        vbox.addWidget(casting_hdr)

        self.casting_tabs = QTabWidget()
        tabs = self.casting_tabs

        # Tab 1: Open Movie Castings (7 clean columns fitting 100% of screen width)
        self.movie_open_table = QTableWidget(0, 7)
        self.movie_open_table.setHorizontalHeaderLabels([
            "TITLE", "STUDIO", "BUDGET", "GENRE", "DIRECTOR", "SUBMISSION DEADLINE", "FILMING STARTS",
        ])
        self.movie_open_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.movie_open_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.movie_open_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.movie_open_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.movie_open_table.setCursor(Qt.CursorShape.PointingHandCursor)
        # Single-click opens the Casting Notice right away!
        self.movie_open_table.cellClicked.connect(lambda r, _c: self._on_casting_table_clicked(self.movie_open_table, r))
        tabs.addTab(self.movie_open_table, "MOVIES — Open Casting Calls")

        # Tab 2: Open TV Series Castings (7 clean columns fitting 100% of screen width)
        self.tv_open_table = QTableWidget(0, 7)
        self.tv_open_table.setHorizontalHeaderLabels([
            "TITLE", "TV NETWORK", "NO. OF EPISODES", "GENRE", "SHOWRUNNER", "SUBMISSION DEADLINE", "FILMING STARTS",
        ])
        self.tv_open_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tv_open_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tv_open_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tv_open_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tv_open_table.setCursor(Qt.CursorShape.PointingHandCursor)
        # Single-click opens the Casting Notice right away!
        self.tv_open_table.cellClicked.connect(lambda r, _c: self._on_casting_table_clicked(self.tv_open_table, r))
        tabs.addTab(self.tv_open_table, "TELEVISION — Open Series & Pilots")

        # Tab 3: Your Clients' Active Submissions & Auditions (Single-click opens Report or Contract!)
        self.my_subs_table = QTableWidget(0, 7)
        self.my_subs_table.setHorizontalHeaderLabels([
            "CLIENT", "PROJECT TITLE", "STUDIO / NETWORK", "ROLE", "STATUS", "DECISION DATE", "AUDITION SCORE / ACTION (CLICK ROW)",
        ])
        self.my_subs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.my_subs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.my_subs_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.my_subs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.my_subs_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.my_subs_table.cellClicked.connect(self._on_subs_table_clicked)
        tabs.addTab(self.my_subs_table, "MY SUBMITTED & AUDITIONING CLIENTS")

        # Tab 4: Role Finder — Search & Sort Open Roles by Match to Selected Client
        rf_page = QWidget()
        rf_vbox = QVBoxLayout(rf_page)
        rf_vbox.setContentsMargins(8, 8, 8, 8)
        rf_vbox.setSpacing(8)

        rf_bar = QFrame()
        rf_bar.setObjectName("Card")
        rf_bar_vbox = QVBoxLayout(rf_bar)
        rf_bar_vbox.setSpacing(6)

        rf_row1 = QHBoxLayout()
        rf_row1.addWidget(QLabel("<b style='color:#f4c552;'>CLIENT:</b>"))
        self.rf_actor_combo = QComboBox()
        self.rf_actor_combo.setMinimumWidth(220)
        self.rf_actor_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.rf_actor_combo.currentIndexChanged.connect(self._refresh_role_finder_table)
        rf_row1.addWidget(self.rf_actor_combo)

        rf_row1.addWidget(QLabel("<b>Search:</b>"))
        self.rf_search = QLineEdit()
        self.rf_search.setPlaceholderText("Project, role, studio, genre...")
        self.rf_search.textChanged.connect(self._refresh_role_finder_table)
        rf_row1.addWidget(self.rf_search, 1)

        self.rf_hide_ineligible_chk = QCheckBox("Hide Ineligible")
        self.rf_hide_ineligible_chk.setChecked(True)
        self.rf_hide_ineligible_chk.toggled.connect(self._refresh_role_finder_table)
        rf_row1.addWidget(self.rf_hide_ineligible_chk)

        rf_clear_btn = QPushButton("Clear")
        rf_clear_btn.clicked.connect(self._clear_role_finder_filters)
        rf_row1.addWidget(rf_clear_btn)
        rf_bar_vbox.addLayout(rf_row1)

        rf_row2 = QHBoxLayout()
        rf_row2.addWidget(QLabel("<b>Medium:</b>"))
        self.rf_medium_combo = QComboBox()
        self.rf_medium_combo.addItems(["All", "Movie", "TV"])
        self.rf_medium_combo.currentIndexChanged.connect(self._refresh_role_finder_table)
        rf_row2.addWidget(self.rf_medium_combo)

        rf_row2.addWidget(QLabel("<b>Role Type:</b>"))
        self.rf_roletype_combo = QComboBox()
        self.rf_roletype_combo.addItems(["All", "Lead", "Supporting", "Series Regular", "Recurring", "Guest Star", "Featured", "Cameo"])
        self.rf_roletype_combo.currentIndexChanged.connect(self._refresh_role_finder_table)
        rf_row2.addWidget(self.rf_roletype_combo)

        rf_row2.addWidget(QLabel("<b>Genre:</b>"))
        self.rf_genre_combo = QComboBox()
        self.rf_genre_combo.addItem("All")
        self.rf_genre_combo.currentIndexChanged.connect(self._refresh_role_finder_table)
        rf_row2.addWidget(self.rf_genre_combo)
        rf_row2.addStretch(1)
        rf_bar_vbox.addLayout(rf_row2)

        self.rf_summary_lbl = QLabel("<i style='color:#94a3b8;'>Select a client to rank all open roles by compatibility.</i>")
        self.rf_summary_lbl.setWordWrap(True)
        self.rf_summary_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        rf_bar_vbox.addWidget(self.rf_summary_lbl)
        rf_vbox.addWidget(rf_bar)

        self.rf_table = QTableWidget(0, 9)
        self.rf_table.setHorizontalHeaderLabels([
            "MATCH", "PROJECT", "MEDIUM", "STUDIO / TIER", "GENRE",
            "ROLE", "REQUIREMENTS", "DEADLINE", "FIT BREAKDOWN",
        ])
        self.rf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rf_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rf_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.rf_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rf_table.setSortingEnabled(True)
        self.rf_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rf_table.cellClicked.connect(self._on_rf_table_clicked)
        rf_vbox.addWidget(self.rf_table, 1)

        tabs.addTab(rf_page, "ROLE FINDER — Match to Client")

        vbox.addWidget(tabs, 1)
        return page

    def _refresh_casting_calls_page(self) -> None:
        open_movies = [f for f in self.engine.films.values() if f.series_or_movie == "Movie" and f.status in ("Casting", "Auditioning")]
        open_tv = [f for f in self.engine.films.values() if f.series_or_movie == "TV" and f.status in ("Casting", "Auditioning")]

        self.movie_open_table.setRowCount(len(open_movies))
        for idx, f in enumerate(open_movies):
            d = self.engine.creatives.get(f.director_id)
            t_it = QTableWidgetItem(f.title)
            t_it.setData(Qt.ItemDataRole.UserRole, f.id)
            self.movie_open_table.setItem(idx, 0, t_it)
            self.movie_open_table.setItem(idx, 1, QTableWidgetItem(f"{f.studio_or_channel} ({f.studio_tier})"))
            self.movie_open_table.setItem(idx, 2, NumericTableItem(f"${f.budget:,}", float(f.budget)))
            self.movie_open_table.setItem(idx, 3, QTableWidgetItem(f.genre))
            self.movie_open_table.setItem(idx, 4, QTableWidgetItem(f"{d.name} ({d.fame})" if d else "TBA"))
            self.movie_open_table.setItem(idx, 5, QTableWidgetItem(f.submission_end_date))
            self.movie_open_table.setItem(idx, 6, QTableWidgetItem(f.filming_start_date))

        self.tv_open_table.setRowCount(len(open_tv))
        for idx, f in enumerate(open_tv):
            sr = self.engine.creatives.get(f.showrunner_id) if f.showrunner_id else None
            t_it = QTableWidgetItem(f.title)
            t_it.setData(Qt.ItemDataRole.UserRole, f.id)
            self.tv_open_table.setItem(idx, 0, t_it)
            self.tv_open_table.setItem(idx, 1, QTableWidgetItem(f"{f.studio_or_channel} ({f.studio_tier})"))
            ep_str = f"Pilot ({f.num_episodes} eps)" if f.is_pilot else f"Season {f.season} ({f.num_episodes} eps)"
            self.tv_open_table.setItem(idx, 2, QTableWidgetItem(ep_str))
            self.tv_open_table.setItem(idx, 3, QTableWidgetItem(f.genre))
            self.tv_open_table.setItem(idx, 4, QTableWidgetItem(f"{sr.name} ({sr.fame})" if sr else "TBA"))
            self.tv_open_table.setItem(idx, 5, QTableWidgetItem(f.submission_end_date))
            self.tv_open_table.setItem(idx, 6, QTableWidgetItem(f.filming_start_date))

        self.displayed_subs = list(reversed(self.engine.submissions))
        self.my_subs_table.setRowCount(len(self.displayed_subs))
        for idx, sub in enumerate(self.displayed_subs):
            act = self.engine.actors.get(sub.actor_id)
            film = self.engine.films.get(sub.film_id)
            if not act or not film or sub.role_index >= len(film.roles):
                continue
            role = film.roles[sub.role_index]
            c_it = QTableWidgetItem(act.name)
            c_it.setData(Qt.ItemDataRole.UserRole, film.id)
            self.my_subs_table.setItem(idx, 0, c_it)
            self.my_subs_table.setItem(idx, 1, QTableWidgetItem(film.title))
            self.my_subs_table.setItem(idx, 2, QTableWidgetItem(f"{film.studio_or_channel} ({film.studio_tier})"))
            self.my_subs_table.setItem(idx, 3, QTableWidgetItem(f"{role.role_name} ({role.role_type})"))
            st_it = QTableWidgetItem(sub.status)
            if sub.status in ("Cast", "Offered"):
                st_it.setForeground(QColor("#4ade80"))
            elif sub.status == "Auditioning":
                st_it.setForeground(QColor("#38bdf8"))
            elif sub.status in ("Rejected", "Lost"):
                st_it.setForeground(QColor("#f87171"))
            self.my_subs_table.setItem(idx, 4, st_it)
            self.my_subs_table.setItem(idx, 5, QTableWidgetItem(film.final_decision_date))

            outcome_str = f"Click to inspect project (Deadline: {film.submission_end_date})"
            if sub.status == "Auditioning":
                outcome_str = f"Auditioning — Decision on {film.final_decision_date}"
            elif role.audition_results:
                my_c = next((c for c in role.audition_results if c.actor_id == act.id), None)
                win_c = role.audition_results[0]
                if my_c and my_c.won:
                    outcome_str = f"WON ({my_c.points:.1f} pts) — Click to Sign Contract / Report!"
                elif my_c:
                    outcome_str = f"{my_c.points:.1f} pts vs {win_c.actor_name} ({win_c.points:.1f}) — Click for Scorecard"
            elif sub.status == "Rejected":
                outcome_str = "Rejected at submission screening"
            self.my_subs_table.setItem(idx, 6, QTableWidgetItem(outcome_str))

        self._refresh_role_finder_controls()
        self._refresh_role_finder_table()

    def _refresh_role_finder_controls(self) -> None:
        # Preserve selected client if still available
        prev_actor_id = self.rf_actor_combo.currentData() if self.rf_actor_combo.count() > 0 else None
        clients = sorted(self.engine.get_available_player_clients(), key=lambda a: a.name)

        self.rf_actor_combo.blockSignals(True)
        self.rf_actor_combo.clear()
        for a in clients:
            self.rf_actor_combo.addItem(f"{a.name} ({a.sex}, {a.age}y)", a.id)
        if prev_actor_id is not None:
            idx = self.rf_actor_combo.findData(prev_actor_id)
            if idx >= 0:
                self.rf_actor_combo.setCurrentIndex(idx)
        self.rf_actor_combo.blockSignals(False)

        # Populate genre dropdown with genres present in currently open castings
        prev_genre = self.rf_genre_combo.currentText()
        open_genres = sorted({f.genre for f in self.engine.films.values() if f.status == "Casting" and f.genre})
        self.rf_genre_combo.blockSignals(True)
        self.rf_genre_combo.clear()
        self.rf_genre_combo.addItem("All")
        for g in open_genres:
            self.rf_genre_combo.addItem(g)
        g_idx = self.rf_genre_combo.findText(prev_genre)
        if g_idx >= 0:
            self.rf_genre_combo.setCurrentIndex(g_idx)
        self.rf_genre_combo.blockSignals(False)

    def _clear_role_finder_filters(self) -> None:
        self.rf_search.blockSignals(True)
        self.rf_search.clear()
        self.rf_search.blockSignals(False)
        for combo in (self.rf_medium_combo, self.rf_roletype_combo, self.rf_genre_combo):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.rf_hide_ineligible_chk.blockSignals(True)
        self.rf_hide_ineligible_chk.setChecked(True)
        self.rf_hide_ineligible_chk.blockSignals(False)
        self._refresh_role_finder_table()

    def _refresh_role_finder_table(self, *_args) -> None:
        if not hasattr(self, "rf_table"):
            return
        self.rf_table.setUpdatesEnabled(False)
        self.rf_table.setSortingEnabled(False)
        self.rf_table.setRowCount(0)

        if self.rf_actor_combo.count() == 0:
            has_any_client = any(a.agency_id == 0 for a in self.engine.actors.values())
            if has_any_client:
                self.rf_summary_lbl.setText(
                    "<span style='color:#fbbf24;'>No available clients right now (all clients are currently submitted, auditioning, filming, or training).</span>"
                )
            else:
                self.rf_summary_lbl.setText(
                    "<span style='color:#fbbf24;'>Sign at least one actor in Talent Service to use the Role Finder.</span>"
                )
            self.rf_table.setSortingEnabled(True)
            self.rf_table.setUpdatesEnabled(True)
            return

        actor_id = int(self.rf_actor_combo.currentData())
        actor = self.engine.actors.get(actor_id)
        if not actor:
            self.rf_table.setSortingEnabled(True)
            self.rf_table.setUpdatesEnabled(True)
            return

        include_ineligible = not self.rf_hide_ineligible_chk.isChecked()
        matches = self.engine.find_matching_roles_for_actor(actor_id, include_ineligible=include_ineligible)

        q = self.rf_search.text().strip().lower()
        med_f = self.rf_medium_combo.currentText()
        rt_f = self.rf_roletype_combo.currentText()
        gen_f = self.rf_genre_combo.currentText()

        filtered = []
        for m in matches:
            film = m["film"]
            role = m["role"]
            if med_f != "All" and film.series_or_movie != med_f:
                continue
            if rt_f != "All" and role.role_type != rt_f:
                continue
            if gen_f != "All" and film.genre != gen_f:
                continue
            if q:
                hay = f"{film.title} {role.role_name} {role.role_type} {film.studio_or_channel} {film.genre}".lower()
                if q not in hay:
                    continue
            filtered.append(m)

        self.rf_table.setRowCount(len(filtered))
        for row, m in enumerate(filtered):
            film = m["film"]
            role = m["role"]
            eligible = m["eligible"]
            pct = m["match_pct"]
            sort_val = float(pct) if eligible else -1.0

            match_text = f"{pct}% {m['fit_label']}" if eligible else "Ineligible"
            m_it = NumericTableItem(match_text, sort_val)
            m_it.setData(Qt.ItemDataRole.UserRole, (film.id, role.index))
            if not eligible:
                m_it.setForeground(QColor("#f87171"))
            elif pct >= 80:
                m_it.setForeground(QColor("#4ade80"))
            elif pct >= 65:
                m_it.setForeground(QColor("#38bdf8"))
            elif pct >= 50:
                m_it.setForeground(QColor("#fbbf24"))
            else:
                m_it.setForeground(QColor("#94a3b8"))

            req_str = f"{role.sex} · {role.age_range} · Fame {int(getattr(role, 'desired_fame', 30))}+"
            self.rf_table.setItem(row, 0, m_it)
            self.rf_table.setItem(row, 1, QTableWidgetItem(film.title))
            self.rf_table.setItem(row, 2, QTableWidgetItem(film.series_or_movie))
            self.rf_table.setItem(row, 3, QTableWidgetItem(f"{film.studio_or_channel} ({film.studio_tier})"))
            self.rf_table.setItem(row, 4, QTableWidgetItem(film.genre))
            self.rf_table.setItem(row, 5, QTableWidgetItem(f"{role.role_name} ({role.role_type})"))
            self.rf_table.setItem(row, 6, QTableWidgetItem(req_str))
            self.rf_table.setItem(row, 7, QTableWidgetItem(film.submission_end_date))
            self.rf_table.setItem(row, 8, QTableWidgetItem(m["summary"]))

        avail_note = (
            "<span style='color:#4ade80;'>Available to submit</span>"
            if self.engine.is_actor_available_for_submission(actor.id)
            else f"<span style='color:#fbbf24;'>Currently {actor.schedule_status}</span>"
        )
        self.rf_summary_lbl.setText(
            f"Showing <b>{len(filtered)}</b> open roles ranked for <b style='color:#f4c552;'>{actor.name}</b> "
            f"({actor.sex}, {actor.age}y, {actor.look}, {actor.bodytype} — {avail_note}) · "
            f"<i style='color:#94a3b8;'>Click any row to open its Casting Notice pre-selected to that role.</i>"
        )

        self.rf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rf_table.setSortingEnabled(True)
        self.rf_table.setUpdatesEnabled(True)

    def _on_rf_table_clicked(self, row: int, _col: int) -> None:
        it = self.rf_table.item(row, 0)
        if not it:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        film_id, role_index = data
        actor_id = int(self.rf_actor_combo.currentData()) if self.rf_actor_combo.count() > 0 else None
        self._open_casting_notice(film_id, initial_role_index=role_index, preselect_actor_id=actor_id)

    def _open_role_finder_for_actor(self, actor_id: int) -> None:
        self._switch_page(3)
        self.casting_tabs.setCurrentIndex(3)
        self._refresh_role_finder_controls()
        idx = self.rf_actor_combo.findData(actor_id)
        if idx >= 0:
            self.rf_actor_combo.setCurrentIndex(idx)
        self._refresh_role_finder_table()

    def _on_casting_table_clicked(self, table: QTableWidget, row: int) -> None:
        it = table.item(row, 0)
        if it:
            fid = int(it.data(Qt.ItemDataRole.UserRole))
            self._open_casting_notice(fid)

    def _on_subs_table_clicked(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(getattr(self, "displayed_subs", [])):
            return
        sub = self.displayed_subs[row]
        film = self.engine.films.get(sub.film_id)
        if not film or sub.role_index >= len(film.roles):
            return
        role = film.roles[sub.role_index]
        if sub.status == "Offered" and role.offered_actor_id == sub.actor_id:
            dlg = RoleContractDialog(self.engine, self.assets, film.id, role.index, sub.actor_id, self)
            dlg.exec()
            self.refresh_all()
        elif role.audition_results:
            dlg = AuditionReportDialog(self.engine, film.id, role.index, self)
            dlg.exec()
        else:
            self._open_casting_notice(film.id)

    # =========================================================================
    # Page 4: Talent Service (Original TalentSearch.ui — General/Attributes Toggle & Single-Click!)
    # =========================================================================
    def _build_talent_service_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)

        filter_card = QFrame()
        filter_card.setObjectName("Card")
        f_vbox = QVBoxLayout(filter_card)

        # Row 1: Quick Search + Core Filters + View Toggle
        f_hbox = QHBoxLayout()
        self.ts_search_edit = QLineEdit()
        self.ts_search_edit.setPlaceholderText("Search actor name, skill, or nationality...")
        self.ts_search_edit.textChanged.connect(self._refresh_talent_service_page)
        f_hbox.addWidget(self.ts_search_edit, 1)

        f_hbox.addWidget(QLabel("Sex:"))
        self.ts_sex_combo = QComboBox()
        for s in ["Any", "Male", "Female"]:
            self.ts_sex_combo.addItem(s, s)
        self.ts_sex_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox.addWidget(self.ts_sex_combo)

        f_hbox.addWidget(QLabel("Fame:"))
        self.ts_fame_combo = QComboBox()
        for label, key in [
            ("Any", "Any"),
            ("80–100", (80, 100)),
            ("60–79", (60, 79)),
            ("40–59", (40, 59)),
            ("20–39", (20, 39)),
            ("0–19", (0, 19)),
        ]:
            self.ts_fame_combo.addItem(label, key)
        self.ts_fame_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox.addWidget(self.ts_fame_combo)

        f_hbox.addWidget(QLabel("Look:"))
        self.ts_look_combo = QComboBox()
        for lk in ["Any", "Striking", "Attractive", "Clean-Cut", "Rugged", "Everyday", "Distinctive"]:
            self.ts_look_combo.addItem(lk, lk)
        self.ts_look_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox.addWidget(self.ts_look_combo)

        self.ts_free_only_chk = QCheckBox("Free Agents Only")
        self.ts_free_only_chk.setChecked(True)
        self.ts_free_only_chk.toggled.connect(self._refresh_talent_service_page)
        f_hbox.addWidget(self.ts_free_only_chk)

        f_hbox.addSpacing(10)
        f_hbox.addWidget(QLabel("<b style='color:#38bdf8;'>VIEW:</b>"))
        self.ts_gen_btn = QPushButton("GENERAL")
        self.ts_gen_btn.setCheckable(True)
        self.ts_gen_btn.setChecked(True)
        self.ts_gen_btn.clicked.connect(lambda: self._set_ts_view_mode("GENERAL"))
        f_hbox.addWidget(self.ts_gen_btn)

        self.ts_attr_btn = QPushButton("ATTRIBUTES")
        self.ts_attr_btn.setCheckable(True)
        self.ts_attr_btn.clicked.connect(lambda: self._set_ts_view_mode("ATTRIBUTES"))
        f_hbox.addWidget(self.ts_attr_btn)
        f_vbox.addLayout(f_hbox)

        # Row 2: Role-Matching Filters (Body Type, Height, Ethnicity, Special Skill, Clear All)
        f_hbox2 = QHBoxLayout()
        f_hbox2.addWidget(QLabel("Body:"))
        self.ts_body_combo = QComboBox()
        for bt in ["Any", "Slim", "Average", "Curvy", "Athletic", "Muscular", "Chunky", "Overweight"]:
            self.ts_body_combo.addItem(bt, bt)
        self.ts_body_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox2.addWidget(self.ts_body_combo)

        f_hbox2.addWidget(QLabel("Height:"))
        self.ts_height_combo = QComboBox()
        for ht in ["Any", "Very short", "Short", "Medium", "Tall", "Very tall"]:
            self.ts_height_combo.addItem(ht, ht)
        self.ts_height_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox2.addWidget(self.ts_height_combo)

        f_hbox2.addWidget(QLabel("Ethnicity:"))
        self.ts_eth_combo = QComboBox()
        for eth in ["Any", "White", "Black", "Hispanic", "Asian", "Indian", "Arabic", "Native American"]:
            self.ts_eth_combo.addItem(eth, eth)
        self.ts_eth_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox2.addWidget(self.ts_eth_combo)

        f_hbox2.addWidget(QLabel("Special Skill:"))
        self.ts_skill_combo = QComboBox()
        self.ts_skill_combo.addItem("Any", "Any")
        for sk in sorted(self.engine.db.special_skills):
            self.ts_skill_combo.addItem(sk, sk)
        self.ts_skill_combo.currentIndexChanged.connect(self._refresh_talent_service_page)
        f_hbox2.addWidget(self.ts_skill_combo)

        clear_btn = QPushButton("CLEAR ALL")
        clear_btn.clicked.connect(self._clear_ts_filters)
        f_hbox2.addWidget(clear_btn)

        f_hbox2.addStretch(1)
        self.ts_matches_lbl = QLabel("0 matches")
        self.ts_matches_lbl.setStyleSheet("color:#f4c552; font-weight:bold; padding-left:8px;")
        f_hbox2.addWidget(self.ts_matches_lbl)
        f_vbox.addLayout(f_hbox2)

        for combo in (
            self.ts_sex_combo,
            self.ts_fame_combo,
            self.ts_look_combo,
            self.ts_body_combo,
            self.ts_height_combo,
            self.ts_eth_combo,
            self.ts_skill_combo,
        ):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(5)

        vbox.addWidget(filter_card)

        self.talent_table = QTableWidget(0, 10)
        self.talent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.talent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.talent_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.talent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.talent_table.setSortingEnabled(True)
        self.talent_table.setCursor(Qt.CursorShape.PointingHandCursor)
        # Single-click immediately opens the Actor Profile (where you can Scout or Sign them!)
        self.talent_table.cellClicked.connect(self._on_talent_clicked)
        vbox.addWidget(self.talent_table, 1)
        return page

    def _set_ts_view_mode(self, mode: str) -> None:
        self.ts_view_mode = mode
        self.ts_gen_btn.setChecked(mode == "GENERAL")
        self.ts_attr_btn.setChecked(mode == "ATTRIBUTES")
        self._refresh_talent_service_page()

    def _clear_ts_filters(self) -> None:
        self.ts_search_edit.clear()
        self.ts_sex_combo.setCurrentIndex(0)
        self.ts_fame_combo.setCurrentIndex(0)
        self.ts_look_combo.setCurrentIndex(0)
        self.ts_body_combo.setCurrentIndex(0)
        self.ts_height_combo.setCurrentIndex(0)
        self.ts_eth_combo.setCurrentIndex(0)
        self.ts_skill_combo.setCurrentIndex(0)
        self._refresh_talent_service_page()

    def _refresh_talent_service_page(self, *_args) -> None:
        if not hasattr(self, "talent_table"):
            return
        query = self.ts_search_edit.text().strip().lower()
        sex_f = self.ts_sex_combo.currentData()
        fame_f = self.ts_fame_combo.currentData()
        look_f = self.ts_look_combo.currentData()
        body_f = self.ts_body_combo.currentData()
        height_f = self.ts_height_combo.currentData()
        eth_f = self.ts_eth_combo.currentData()
        skill_f = self.ts_skill_combo.currentData()
        free_only = self.ts_free_only_chk.isChecked()

        matches: List[Actor] = []
        for a in self.engine.actors.values():
            if free_only and a.agency_id is not None:
                continue
            if sex_f != "Any" and a.sex != sex_f:
                continue
            if fame_f != "Any" and isinstance(fame_f, tuple):
                lo_f, hi_f = fame_f
                fv = int(round(max(0.0, min(100.0, a.fame_score))))
                if not (lo_f <= fv <= hi_f):
                    continue
            if look_f != "Any" and a.look != look_f:
                continue
            if body_f != "Any" and a.bodytype != body_f:
                continue
            if height_f != "Any" and a.height_category != height_f:
                continue
            if eth_f != "Any" and a.ethnicity != eth_f:
                continue
            if skill_f != "Any" and skill_f not in a.special_skills:
                continue
            if query:
                hay = f"{a.name} {a.personality} {' '.join(a.special_skills)} {a.nationality} {a.ethnicity}".lower()
                if query not in hay:
                    continue
            matches.append(a)

        self.ts_matches_lbl.setText(f"{len(matches)} matches (Click any actor to Scout / Sign)")
        self.talent_table.setUpdatesEnabled(False)
        self.talent_table.setSortingEnabled(False)
        self.talent_table.clear()

        if self.ts_view_mode == "GENERAL":
            # Clean 11 columns fitting 100% width with zero horizontal scrolling!
            cols = ["SEX", "NAME", "AGE", "FAME", "POTENTIAL", "NATIONALITY", "ETHNICITY", "LOOK", "BODY TYPE", "HEIGHT", "AGENCY"]
            self.talent_table.setColumnCount(len(cols))
            self.talent_table.setHorizontalHeaderLabels(cols)
            self.talent_table.setRowCount(len(matches))
            pot_colors = {"Generational": "#f4c552", "Elite": "#4ade80", "Star": "#38bdf8", "Solid": "#cbd5e1", "Fringe": "#94a3b8"}
            for row, a in enumerate(matches):
                ag = self.engine.agencies.get(a.agency_id) if a.agency_id is not None else None
                ag_name = ag.name if ag else "Free Agent"
                s_it = QTableWidgetItem(a.sex)
                s_it.setData(Qt.ItemDataRole.UserRole, a.id)
                n_it = QTableWidgetItem(a.name)
                if a.agency_id is None:
                    n_it.setForeground(QColor("#4ade80"))
                pot_known = a.potential_known or a.agency_id == 0
                p_it = NumericTableItem(a.display_potential, float(a.potential_rating) if pot_known else -1.0)
                p_it.setForeground(QColor(pot_colors.get(a.potential_label, "#94a3b8") if pot_known else "#64748b"))
                self.talent_table.setItem(row, 0, s_it)
                self.talent_table.setItem(row, 1, n_it)
                self.talent_table.setItem(row, 2, NumericTableItem(str(a.age), float(a.age)))
                f_val = int(round(max(0.0, min(100.0, a.fame_score))))
                self.talent_table.setItem(row, 3, NumericTableItem(str(f_val), float(f_val)))
                self.talent_table.setItem(row, 4, p_it)
                self.talent_table.setItem(row, 5, QTableWidgetItem(a.nationality))
                self.talent_table.setItem(row, 6, QTableWidgetItem(a.ethnicity))
                self.talent_table.setItem(row, 7, QTableWidgetItem(a.look))
                self.talent_table.setItem(row, 8, QTableWidgetItem(a.bodytype))
                self.talent_table.setItem(row, 9, NumericTableItem(f"{a.height_cm}cm ({a.height_category})", float(a.height_cm)))
                self.talent_table.setItem(row, 10, QTableWidgetItem(ag_name))
        else:
            # Exact 16 columns from TalentSearch.ui Attributes view — fits 100% width with zero horizontal scrolling!
            cols = ["SEX", "NAME", "AGE", "FAME", "CHAR.", "IMPR.", "VOC.", "PHYS.", "FAC.", "INTEL.", "CHRSM.", "HUM.", "COMM.", "CONF.", "PROF.", "STAM."]
            self.talent_table.setColumnCount(len(cols))
            self.talent_table.setHorizontalHeaderLabels(cols)
            self.talent_table.setRowCount(len(matches))
            for row, a in enumerate(matches):
                s_it = QTableWidgetItem(a.sex)
                s_it.setData(Qt.ItemDataRole.UserRole, a.id)
                n_it = QTableWidgetItem(a.name)
                if a.agency_id is None:
                    n_it.setForeground(QColor("#4ade80"))
                self.talent_table.setItem(row, 0, s_it)
                self.talent_table.setItem(row, 1, n_it)
                self.talent_table.setItem(row, 2, NumericTableItem(str(a.age), float(a.age)))
                f_val = int(round(max(0.0, min(100.0, a.fame_score))))
                self.talent_table.setItem(row, 3, NumericTableItem(f"{f_val}", float(f_val)))
                for idx, ak in enumerate(CORE_ATTRIBUTES):
                    disp = a.get_display_attribute(ak)
                    if "-" in disp:
                        parts = [p.strip() for p in disp.split("-") if p.strip().isdigit()]
                        sort_v = (sum(float(p) for p in parts) / len(parts)) if parts else 0.0
                    else:
                        sort_v = float(disp) if disp.isdigit() else 0.0
                    self.talent_table.setItem(row, 4 + idx, NumericTableItem(disp, sort_v))

        self.talent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.talent_table.setSortingEnabled(True)
        self.talent_table.setUpdatesEnabled(True)

    def _on_talent_clicked(self, row: int, _col: int) -> None:
        it = self.talent_table.item(row, 0)
        if it:
            self._open_actor_profile(int(it.data(Qt.ItemDataRole.UserRole)))

    # =========================================================================
    # Page 5: Box Office Chart (BoxOffice.ui)
    # =========================================================================
    def _build_box_office_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)
        bo_hdr = QLabel("<h3 style='color:#f4c552; margin:0;'>Hollywoodland Box Office Charts & Upcoming Releases — Click any movie to open its Full Profile & Cast</h3>")
        bo_hdr.setWordWrap(True)
        bo_hdr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        vbox.addWidget(bo_hdr)

        tabs = QTabWidget()
        self.bo_released_table = QTableWidget(0, 7)
        self.bo_released_table.setHorizontalHeaderLabels([
            "Movie Title", "Studio", "Genre", "Budget", "Worldwide Box Office Gross", "Box Office Butcher Review", "Release Date",
        ])
        self.bo_released_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bo_released_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bo_released_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.bo_released_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bo_released_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bo_released_table.cellClicked.connect(lambda r, _c: self._on_project_table_clicked(self.bo_released_table, r))
        tabs.addTab(self.bo_released_table, "Released Movies & Box Office Standings")

        self.bo_upcoming_table = QTableWidget(0, 6)
        self.bo_upcoming_table.setHorizontalHeaderLabels([
            "Movie Title", "Studio", "Genre", "Budget", "Production Status", "Slated Release Date",
        ])
        self.bo_upcoming_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bo_upcoming_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.bo_upcoming_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.bo_upcoming_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.bo_upcoming_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bo_upcoming_table.cellClicked.connect(lambda r, _c: self._on_project_table_clicked(self.bo_upcoming_table, r))
        tabs.addTab(self.bo_upcoming_table, "In Production & Upcoming Releases")

        vbox.addWidget(tabs, 1)
        return page

    def _refresh_box_office_page(self) -> None:
        rel = sorted(
            [f for f in self.engine.films.values() if f.series_or_movie == "Movie" and f.status in ("In Theaters", "Released")],
            key=lambda x: x.box_office_gross,
            reverse=True,
        )
        upc = [f for f in self.engine.films.values() if f.series_or_movie == "Movie" and f.status not in ("In Theaters", "Released")]

        self.bo_released_table.setRowCount(len(rel))
        for idx, f in enumerate(rel):
            title_tag = f"{f.title} [IN THEATERS - WK {f.box_office_weeks_run}]" if f.status == "In Theaters" else f.title
            t_it = QTableWidgetItem(title_tag)
            t_it.setData(Qt.ItemDataRole.UserRole, f.id)
            self.bo_released_table.setItem(idx, 0, t_it)
            self.bo_released_table.setItem(idx, 1, QTableWidgetItem(f.studio_or_channel))
            self.bo_released_table.setItem(idx, 2, QTableWidgetItem(f.genre))
            self.bo_released_table.setItem(idx, 3, NumericTableItem(f"${f.budget:,}", float(f.budget)))
            g_it = NumericTableItem(f"${f.box_office_gross:,}", float(f.box_office_gross))
            g_it.setForeground(QColor("#4ade80" if f.box_office_gross >= f.breakeven else "#f87171"))
            self.bo_released_table.setItem(idx, 4, g_it)
            self.bo_released_table.setItem(idx, 5, QTableWidgetItem(f"{f.review_score or 0}%"))
            self.bo_released_table.setItem(idx, 6, QTableWidgetItem(f.release_date))

        self.bo_upcoming_table.setRowCount(len(upc))
        for idx, f in enumerate(upc):
            t_it = QTableWidgetItem(f.title)
            t_it.setData(Qt.ItemDataRole.UserRole, f.id)
            self.bo_upcoming_table.setItem(idx, 0, t_it)
            self.bo_upcoming_table.setItem(idx, 1, QTableWidgetItem(f.studio_or_channel))
            self.bo_upcoming_table.setItem(idx, 2, QTableWidgetItem(f.genre))
            self.bo_upcoming_table.setItem(idx, 3, NumericTableItem(f"${f.budget:,}", float(f.budget)))
            self.bo_upcoming_table.setItem(idx, 4, QTableWidgetItem(f.status))
            self.bo_upcoming_table.setItem(idx, 5, QTableWidgetItem(f.release_date))

    # =========================================================================
    # Page 6: TV Ratings (TVRating.ui)
    # =========================================================================
    def _build_tv_ratings_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)
        tv_hdr = QLabel("<h3 style='color:#f4c552; margin:0;'>TV Network Scorecard, Pilots & 18-49 Demo Ratings — Click any series to open its Full Profile & Cast</h3>")
        tv_hdr.setWordWrap(True)
        tv_hdr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        vbox.addWidget(tv_hdr)

        self.tv_table = QTableWidget(0, 7)
        self.tv_table.setHorizontalHeaderLabels([
            "Series Title", "Channel / Network", "Genre", "Format", "Status", "Critic Review", "18-49 Demo Rating",
        ])
        self.tv_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tv_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tv_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tv_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tv_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tv_table.cellClicked.connect(lambda r, _c: self._on_project_table_clicked(self.tv_table, r))
        vbox.addWidget(self.tv_table, 1)
        return page

    def _refresh_tv_ratings_page(self) -> None:
        tvs = sorted(
            [f for f in self.engine.films.values() if f.series_or_movie == "TV"],
            key=lambda x: x.tv_average_rating,
            reverse=True,
        )
        self.tv_table.setRowCount(len(tvs))
        for idx, f in enumerate(tvs):
            t_it = QTableWidgetItem(f.title)
            t_it.setData(Qt.ItemDataRole.UserRole, f.id)
            self.tv_table.setItem(idx, 0, t_it)
            self.tv_table.setItem(idx, 1, QTableWidgetItem(f"{f.studio_or_channel} ({f.studio_tier})"))
            self.tv_table.setItem(idx, 2, QTableWidgetItem(f.genre))
            fmt = f"Pilot ({f.num_episodes} eps)" if f.is_pilot else f"Season {f.season} ({f.num_episodes} eps)"
            self.tv_table.setItem(idx, 3, QTableWidgetItem(fmt))
            self.tv_table.setItem(idx, 4, QTableWidgetItem(f.status))
            rev = f"{f.review_score}%" if f.review_score is not None else "Pending"
            self.tv_table.setItem(idx, 5, QTableWidgetItem(rev))
            rat = f"{f.tv_average_rating:.2f}" if f.tv_average_rating > 0 else "Upcoming"
            self.tv_table.setItem(idx, 6, QTableWidgetItem(rat))

    # =========================================================================
    # Page 7: Awards (Awards.ui)
    # =========================================================================
    def _build_awards_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)
        aw_hdr = QLabel(
            "<h3 style='color:#f4c552; margin:0;'>Annual Hollywoodland Award Ceremonies (Held Every January 15)</h3>"
            "<p style='color:#94a3b8; margin:2px 0;'>Featuring Thespian League Awards, Silver Sphere Awards, Association Awards, Fan Favorites, Indie Star Awards, and the dreaded Berry Awards.</p>"
        )
        aw_hdr.setWordWrap(True)
        aw_hdr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        vbox.addWidget(aw_hdr)

        self.awards_table = QTableWidget(0, 6)
        self.awards_table.setHorizontalHeaderLabels(["Year", "Award Ceremony", "Category", "Winner", "Agency", "Project"])
        self.awards_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.awards_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.awards_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.awards_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.awards_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.awards_table.cellClicked.connect(self._on_awards_table_clicked)
        vbox.addWidget(self.awards_table, 1)
        return page

    def _refresh_awards_page(self) -> None:
        self.awards_table.setRowCount(len(self.engine.awards))
        for idx, aw in enumerate(self.engine.awards):
            self.awards_table.setItem(idx, 0, QTableWidgetItem(str(aw.year)))
            self.awards_table.setItem(idx, 1, QTableWidgetItem(aw.ceremony_name))
            self.awards_table.setItem(idx, 2, QTableWidgetItem(aw.category_name))
            self.awards_table.setItem(idx, 3, QTableWidgetItem(aw.winner_actor_name))
            self.awards_table.setItem(idx, 4, QTableWidgetItem(aw.agency_name))
            self.awards_table.setItem(idx, 5, QTableWidgetItem(aw.project_title))

    # =========================================================================
    # Page 8: Top Actors Chart (ActorRankings.ui)
    # =========================================================================
    def _build_top_actors_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(16, 12, 16, 12)
        ta_hdr = QLabel("<h3 style='color:#f4c552; margin:0;'>Tinsel Town Top 100 Actors Star Power Chart (Single-click any actor to open profile)</h3>")
        ta_hdr.setWordWrap(True)
        ta_hdr.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        vbox.addWidget(ta_hdr)

        self.top_actors_table = QTableWidget(0, 7)
        self.top_actors_table.setHorizontalHeaderLabels([
            "Rank", "Actor Name", "Sex", "Age", "Fame (0-100)", "Represented By", "Awards Won",
        ])
        self.top_actors_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.top_actors_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.top_actors_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.top_actors_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_actors_table.cellClicked.connect(self._on_top_actors_clicked)
        vbox.addWidget(self.top_actors_table, 1)
        return page

    def _refresh_top_actors_page(self) -> None:
        top100 = sorted(self.engine.actors.values(), key=lambda a: a.actor_ranking)[:100]
        self.top_actors_table.setRowCount(len(top100))
        for idx, a in enumerate(top100):
            ag = self.engine.agencies.get(a.agency_id) if a.agency_id is not None else None
            ag_name = f"{ag.name} (YOUR CLIENT)" if (ag and ag.ours) else (ag.name if ag else "Free Agent")

            r_it = NumericTableItem(f"#{a.actor_ranking}", float(a.actor_ranking))
            r_it.setData(Qt.ItemDataRole.UserRole, a.id)
            n_it = QTableWidgetItem(a.name)
            if a.agency_id == 0:
                r_it.setForeground(QColor("#f4c552"))
                n_it.setForeground(QColor("#f4c552"))
            self.top_actors_table.setItem(idx, 0, r_it)
            self.top_actors_table.setItem(idx, 1, n_it)
            self.top_actors_table.setItem(idx, 2, QTableWidgetItem(a.sex))
            self.top_actors_table.setItem(idx, 3, NumericTableItem(str(a.age), float(a.age)))
            fv = int(round(max(0.0, min(100.0, a.fame_score))))
            self.top_actors_table.setItem(idx, 4, NumericTableItem(str(fv), float(fv)))
            self.top_actors_table.setItem(idx, 5, QTableWidgetItem(ag_name))
            self.top_actors_table.setItem(idx, 6, NumericTableItem(str(a.num_awards), float(a.num_awards)))

    def _on_top_actors_clicked(self, row: int, _col: int) -> None:
        it = self.top_actors_table.item(row, 0)
        if it:
            self._open_actor_profile(int(it.data(Qt.ItemDataRole.UserRole)))

    # =========================================================================
    # Global Refresh & Actions
    # =========================================================================
    def _update_nav_badges(self) -> None:
        unread_msgs = sum(1 for m in self.engine.messages if not m.was_read)
        my_clients = sum(1 for a in self.engine.actors.values() if a.agency_id == 0)
        open_castings = sum(1 for f in self.engine.films.values() if f.status == "Casting")

        self.nav_buttons[0].setText(f"Inbox ({unread_msgs})" if unread_msgs else "Inbox")
        self.nav_buttons[2].setText(f"My Actors ({my_clients})")
        self.nav_buttons[3].setText(f"Casting Calls ({open_castings})")

    def refresh_all(self) -> None:
        pa = self.engine.player_agency
        self.agency_badge_lbl.setText(f"{pa.name} · {pa.reputation} #{pa.ranking}")
        self.budget_lbl.setText(f"${pa.budget:,.0f}")
        self.date_lbl.setText(self.engine.pretty_date)
        self._update_nav_badges()

        idx = self.stack.currentIndex()
        if idx == 0:
            self._refresh_messages_page()
        elif idx == 1:
            self._refresh_my_agency_page()
        elif idx == 2:
            self._refresh_my_actors_page()
        elif idx == 3:
            self._refresh_casting_calls_page()
        elif idx == 4:
            self._refresh_talent_service_page()
        elif idx == 5:
            self._refresh_box_office_page()
        elif idx == 6:
            self._refresh_tv_ratings_page()
        elif idx == 7:
            self._refresh_awards_page()
        elif idx == 8:
            self._refresh_top_actors_page()

    def _on_next_day(self) -> None:
        ok, msg = self.engine.advance_day()
        if not ok:
            self._switch_page(0)
            self.show_toast(msg, True)
            return
        self.refresh_all()
        self.show_toast(msg, False)

    def _on_next_week(self) -> None:
        for _ in range(7):
            ok, msg = self.engine.advance_day()
            if not ok:
                self._switch_page(0)
                self.show_toast(msg, True)
                break
        self.refresh_all()
        self.show_toast(f"Advanced to {self.engine.pretty_date}.", False)

    def _open_actor_profile(self, actor_id: int) -> None:
        actor = self.engine.actors.get(actor_id)
        if not actor:
            return
        dlg = ActorProfileDialog(
            self.engine,
            self.assets,
            actor,
            on_refresh=self.refresh_all,
            parent=self,
            on_find_roles=self._open_role_finder_for_actor,
        )
        dlg.exec()
        self.refresh_all()

    def _on_project_table_clicked(self, table: QTableWidget, row: int) -> None:
        it = table.item(row, 0)
        if it:
            fid = it.data(Qt.ItemDataRole.UserRole)
            if fid is not None:
                self._open_project_profile(int(fid))

    def _on_awards_table_clicked(self, row: int, _col: int) -> None:
        it = self.awards_table.item(row, 5)
        if not it:
            return
        title = it.text().strip()
        film = next((f for f in self.engine.films.values() if f.title == title), None)
        if film:
            self._open_project_profile(film.id)

    def _open_project_profile(self, film_id: int) -> None:
        film = self.engine.films.get(film_id)
        if not film:
            return
        dlg = ProjectProfileDialog(
            self.engine,
            self.assets,
            film,
            on_refresh=self.refresh_all,
            parent=self,
            on_find_roles=self._open_role_finder_for_actor,
        )
        dlg.exec()
        self.refresh_all()

    def _open_casting_notice(
        self,
        film_id: int,
        initial_role_index: int = 0,
        preselect_actor_id: Optional[int] = None,
    ) -> None:
        film = self.engine.films.get(film_id)
        if not film:
            return
        dlg = CastingNoticeDialog(
            self.engine,
            self.assets,
            film,
            on_refresh=self.refresh_all,
            parent=self,
            initial_role_index=initial_role_index,
            preselect_actor_id=preselect_actor_id,
        )
        dlg.exec()
        self.refresh_all()

    def _on_save_game(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Hollywoodland Game", "hollywoodland_save.json", "JSON Save (*.json)")
        if path:
            self.engine.save_game(path)
            self.show_toast(f"Saved agency state to {path}", False)


def _choose_roster_pack_dialog() -> Optional[str]:
    from PySide6.QtWidgets import QDialog
    from hollywoodland.systems.roster_loader import list_roster_packs

    packs = list_roster_packs()
    if not packs:
        return None

    dlg = QDialog()
    dlg.setWindowTitle("HOLLYWOODLAND — Select Database")
    dlg.setStyleSheet(HOLLYWOODLAND_QSS)
    dlg.resize(520, 320)
    vb = QVBoxLayout(dlg)
    vb.setContentsMargins(20, 18, 20, 18)
    vb.setSpacing(10)

    vb.addWidget(QLabel("<h2 style='color:#f4c552; margin:0;'>Select Universe / Roster Pack</h2>"))
    vb.addWidget(QLabel(
        "<span style='color:#94a3b8;'>Choose the built-in fictional universe or load an external Roster Pack from the <b>rosters/</b> folder.</span>"
    ))

    lst = QListWidget()
    default_item = QListWidgetItem("Default — Fictional Hollywoodland Universe (Built-in)")
    default_item.setData(Qt.ItemDataRole.UserRole, None)
    lst.addItem(default_item)
    for p in packs:
        era_str = f" [{p['start_year']}–{p['end_year']}]" if p.get("start_year") and p.get("end_year") else ""
        proj_str = f", {p['project_count']} projects" if p.get("project_count") else ""
        label = f"{p.get('name', p['id'])}{era_str}  —  {p.get('actor_count', '?')} actors, {p.get('creative_count', '?')} creatives{proj_str}"
        it = QListWidgetItem(label)
        it.setData(Qt.ItemDataRole.UserRole, p["id"])
        lst.addItem(it)
    lst.setCurrentRow(0)
    vb.addWidget(lst, 1)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)
    start_btn = QPushButton("Launch Hollywoodland  ›")
    start_btn.setStyleSheet(
        "background-color:#d4a02c; color:#090b10; font-weight:900; padding:9px 18px; border-radius:7px;"
    )
    start_btn.clicked.connect(dlg.accept)
    btn_row.addWidget(start_btn)
    vb.addLayout(btn_row)

    lst.itemDoubleClicked.connect(lambda _it: dlg.accept())
    if dlg.exec() == QDialog.DialogCode.Accepted and lst.currentItem() is not None:
        return lst.currentItem().data(Qt.ItemDataRole.UserRole)
    return None


def launch_hollywoodland(
    player_name: str = "John Doe",
    agency_name: str = "Hollywoodland Talent",
    initial_budget: float = 50000.0,
    seed: Optional[int] = None,
    roster_pack: Optional[str] = None,
) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    selected_pack = roster_pack if roster_pack is not None else _choose_roster_pack_dialog()
    engine = HollywoodlandEngine(
        player_name=player_name,
        agency_name=agency_name,
        initial_budget=initial_budget,
        seed=seed,
        roster_pack=selected_pack,
    )
    win = HollywoodlandWindow(engine)
    win.show()
    app.exec()
