from __future__ import annotations
import os
import random
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap, QPen, QBrush

from hollywoodland.models.entities import Actor
from hollywoodland.systems.db_loader import STEAM_ASSETS_DIR


def _parse_rgb(color_str: str) -> Optional[Tuple[int, int, int]]:
    parts = [p.strip() for p in color_str.split(",")]
    if len(parts) == 3:
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None
    return None


def _age_in_range(age: int, range_str: Optional[str]) -> bool:
    if not range_str or "-" not in range_str:
        return True
    try:
        lo_s, hi_s = range_str.split("-", 1)
        return int(lo_s) <= age <= int(hi_s)
    except ValueError:
        return True


def _tint_rgba(img: Image.Image, rgb: Tuple[int, int, int]) -> Image.Image:
    """Replicates Cattle Call's portrait.fs shader: gl_FragColor = tex * vec4(ambient, 1)."""
    if rgb == (255, 255, 255):
        return img
    r_m, g_m, b_m = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    r, g, b, a = img.split()
    r = r.point(lambda x: int(x * r_m))
    g = g.point(lambda x: int(x * g_m))
    b = b.point(lambda x: int(x * b_m))
    return Image.merge("RGBA", (r, g, b, a))


class PortraitCompositor:
    """Parses Cattle Call's scripts/snapshots.xml and composites real layered PNG portraits."""

    def __init__(self) -> None:
        self.available = False
        self.root_dir = os.path.join(STEAM_ASSETS_DIR, "textures", "portraits")
        self.data: Dict[str, Dict[str, Any]] = {}
        self._img_cache: Dict[str, Image.Image] = {}
        self._load_xml()

    def _load_xml(self) -> None:
        xml_path = os.path.join(STEAM_ASSETS_DIR, "scripts", "snapshots.xml")
        if not os.path.exists(xml_path):
            return
        try:
            with open(xml_path, "rb") as f:
                raw = f.read()
            if raw.startswith(b"\xff\xfe"):
                txt = raw.decode("utf-16le")
            else:
                txt = raw.decode("utf-8", errors="replace")
            # Strip misleading <?xml ... encoding="UTF-8"?> header when decoded from UTF-16
            if txt.lstrip().startswith("<?xml"):
                end_decl = txt.find("?>")
                if end_decl != -1:
                    txt = txt[end_decl + 2 :]
            root = ET.fromstring(txt)
        except Exception:
            return

        for sex in ("male", "female"):
            sex_el = root.find(sex)
            if sex_el is None:
                continue
            parts_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
            parts_el = sex_el.find("parts")
            if parts_el is not None:
                for cat_el in parts_el:
                    cat_name = cat_el.tag.lower()  # e.g. backgrounds, bodies, heads, hairs...
                    cat_dict: Dict[str, Dict[str, Any]] = {}
                    for item_el in cat_el:
                        iname = item_el.attrib.get("name", "")
                        layers = [
                            {"file": lay.attrib.get("file", ""), "color": lay.attrib.get("color", "")}
                            for lay in item_el.findall("layer")
                        ]
                        cat_dict[iname] = {
                            "name": iname,
                            "bodytypes": [x.strip().lower() for x in item_el.attrib.get("bodytypes", "all").split(",")],
                            "agerange": item_el.attrib.get("agerange", ""),
                            "layers": layers,
                        }
                    parts_map[cat_name] = cat_dict

            eth_map: Dict[str, Dict[str, Any]] = {}
            eths_el = sex_el.find("ethnicities")
            if eths_el is not None:
                for eth_el in eths_el:
                    ename = eth_el.tag.lower()
                    allowed: Dict[str, List[str]] = {}
                    for tag in ("backgrounds", "bodies", "eyebrows", "eyes", "glasses", "facialhairs", "hairs", "heads", "mouths", "noses"):
                        t_el = eth_el.find(tag)
                        if t_el is not None and t_el.text:
                            allowed[tag] = [x.strip() for x in t_el.text.split(",") if x.strip()]

                    skin_colors = [dict(el.attrib) for el in eth_el.findall("skincolor")]
                    hair_colors = [dict(el.attrib) for el in eth_el.findall("haircolor")]
                    cloth_colors = [dict(el.attrib) for el in eth_el.findall("clothcolor")]
                    eye_colors = [dict(el.attrib) for el in eth_el.findall("eyecolor")]
                    glass_colors = [dict(el.attrib) for el in eth_el.findall("glassescolor")]

                    eth_map[ename] = {
                        "allowed": allowed,
                        "skincolor": skin_colors,
                        "haircolor": hair_colors,
                        "clothcolor": cloth_colors,
                        "eyecolor": eye_colors,
                        "glassescolor": glass_colors,
                    }

            self.data[sex] = {"parts": parts_map, "ethnicities": eth_map}

        self.available = bool(self.data)

    def _load_png(self, sex: str, rel_file: str) -> Optional[Image.Image]:
        key = f"{sex}/{rel_file}".lower()
        if key in self._img_cache:
            return self._img_cache[key]
        full = os.path.join(self.root_dir, sex, rel_file.replace("/", os.sep))
        if not os.path.exists(full):
            return None
        try:
            im = Image.open(full).convert("RGBA")
            self._img_cache[key] = im
            return im
        except Exception:
            return None

    def render_portrait(self, actor: Actor, size: int = 128) -> Optional[QPixmap]:
        if not self.available:
            return None
        sex = "male" if actor.sex == "Male" else "female"
        sex_data = self.data.get(sex)
        if not sex_data:
            return None

        eth_key = actor.ethnicity.lower().replace(" ", "")
        eth_data = sex_data["ethnicities"].get(eth_key) or sex_data["ethnicities"].get("white")
        if not eth_data:
            return None

        rng = random.Random(actor.portrait_seed or (actor.id * 7919))
        parts = sex_data["parts"]
        allowed = eth_data["allowed"]

        # Pick color palette
        skin = rng.choice(eth_data["skincolor"]) if eth_data["skincolor"] else {"fill": "240,200,170", "shadow": "215,175,145", "outline": "0,0,0"}
        valid_hairs = [hc for hc in eth_data["haircolor"] if _age_in_range(actor.age, hc.get("agerange"))]
        hair = rng.choice(valid_hairs or eth_data["haircolor"] or [{"fill": "40,30,20", "shadow": "20,15,10", "outline": "0,0,0", "highlight": "255,244,229"}])
        cloth = rng.choice(eth_data["clothcolor"]) if eth_data["clothcolor"] else {"primary": "50,80,140", "secondary": "220,220,220"}
        eye = rng.choice(eth_data["eyecolor"]) if eth_data["eyecolor"] else {"fill": "80,60,40"}
        glass = rng.choice(eth_data["glassescolor"]) if eth_data["glassescolor"] else {"fill": "20,20,20"}

        palette: Dict[str, Tuple[int, int, int]] = {
            "skin": _parse_rgb(skin.get("fill", "240,200,170")) or (240, 200, 170),
            "skinshadow": _parse_rgb(skin.get("shadow", "215,175,145")) or (215, 175, 145),
            "skinoutline": _parse_rgb(skin.get("outline", "0,0,0")) or (0, 0, 0),
            "hair": _parse_rgb(hair.get("fill", "40,30,20")) or (40, 30, 20),
            "hairshadow": _parse_rgb(hair.get("shadow", "20,15,10")) or (20, 15, 10),
            "hairoutline": _parse_rgb(hair.get("outline", "0,0,0")) or (0, 0, 0),
            "hairhighlight": _parse_rgb(hair.get("highlight", "255,244,229")) or (255, 244, 229),
            "clothprimary": _parse_rgb(cloth.get("primary", "50,80,140")) or (50, 80, 140),
            "clothsecondary": _parse_rgb(cloth.get("secondary", "220,220,220")) or (220, 220, 220),
            "eye": _parse_rgb(eye.get("fill", "80,60,40")) or (80, 60, 40),
            "glasses": _parse_rgb(glass.get("fill", "20,20,20")) or (20, 20, 20),
        }

        def pick_part(cat: str, optional_prob: float = 1.0) -> Optional[Dict[str, Any]]:
            if optional_prob < 1.0 and rng.random() > optional_prob:
                return None
            cat_dict = parts.get(cat, {})
            names = allowed.get(cat, list(cat_dict.keys()))
            cands = [cat_dict[n] for n in names if n in cat_dict]
            if cat == "bodies":
                bt = actor.bodytype.lower()
                bt_cands = [c for c in cands if "all" in c["bodytypes"] or bt in c["bodytypes"]]
                if bt_cands:
                    cands = bt_cands
            age_cands = [c for c in cands if _age_in_range(actor.age, c.get("agerange"))]
            if age_cands:
                cands = age_cands
            return rng.choice(cands) if cands else None

        # Authentic back-to-front layer order
        chosen = [
            pick_part("backgrounds"),
            pick_part("bodies"),
            pick_part("heads"),
            pick_part("mouths"),
            pick_part("noses"),
            pick_part("eyes"),
            pick_part("eyebrows"),
            pick_part("facialhairs", optional_prob=0.35 if sex == "male" else 0.0),
            pick_part("hairs"),
            pick_part("glasses", optional_prob=0.16),
        ]

        canvas: Optional[Image.Image] = None
        for part in chosen:
            if not part:
                continue
            for lay in part["layers"]:
                raw_im = self._load_png(sex, lay["file"])
                if raw_im is None:
                    continue
                if canvas is None:
                    canvas = Image.new("RGBA", raw_im.size, (30, 35, 50, 255))
                col_key = lay.get("color", "").strip().lower()
                if col_key in palette:
                    tinted = _tint_rgba(raw_im, palette[col_key])
                else:
                    lit_rgb = _parse_rgb(col_key)
                    tinted = _tint_rgba(raw_im, lit_rgb) if lit_rgb else raw_im
                if tinted.size != canvas.size:
                    tinted = tinted.resize(canvas.size, Image.Resampling.LANCZOS)
                canvas = Image.alpha_composite(canvas, tinted)

        if canvas is None:
            return None

        if canvas.size != (size, size):
            canvas = canvas.resize((size, size), Image.Resampling.LANCZOS)

        data = canvas.tobytes("raw", "RGBA")
        qimg = QImage(data, size, size, QImage.Format.Format_RGBA8888).copy()

        # Draw crisp Fame Tier badge along the bottom edge
        painter = QPainter(qimg)
        badge_colors = {
            "A-lister": "#f59e0b",
            "Notable": "#a855f7",
            "Average": "#3b82f6",
            "Relatively unknown": "#10b981",
            "Unknown": "#475569",
        }
        b_col = QColor(badge_colors.get(actor.fame_tier, "#475569"))
        b_col.setAlpha(225)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(b_col))
        painter.drawRoundedRect(4, size - 22, size - 8, 18, 4, 4)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", max(7, size // 16), QFont.Weight.Bold))
        painter.drawText(
            QRect(4, size - 22, size - 8, 18),
            Qt.AlignmentFlag.AlignCenter,
            f"FAME {int(round(max(0.0, min(100.0, actor.fame_score))))}",
        )
        painter.end()

        return QPixmap.fromImage(qimg)


class AssetManager:
    """Loads Steam textures and composites real layered character portraits for Hollywoodland."""

    def __init__(self) -> None:
        self.pixmap_cache: Dict[str, QPixmap] = {}
        self.portrait_cache: Dict[str, QPixmap] = {}
        self.compositor = PortraitCompositor()

    def get_texture(self, rel_path: str, width: int = 0, height: int = 0) -> Optional[QPixmap]:
        if not rel_path:
            return None
        key = f"{rel_path}:{width}x{height}"
        if key in self.pixmap_cache:
            return self.pixmap_cache[key]

        norm_rel = rel_path.replace("/", os.sep).replace("\\", os.sep)
        candidates = [
            os.path.join(STEAM_ASSETS_DIR, norm_rel),
            os.path.join(STEAM_ASSETS_DIR, "textures", norm_rel),
        ]
        for base_cand in list(candidates):
            if not os.path.splitext(base_cand)[1]:
                for ext in (".png", ".jpg", ".tga"):
                    candidates.append(base_cand + ext)

        for full_path in candidates:
            if os.path.exists(full_path) and os.path.isfile(full_path):
                pm = QPixmap(full_path)
                if not pm.isNull():
                    if width > 0 and height > 0:
                        pm = pm.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.pixmap_cache[key] = pm
                    return pm
        return None

    def get_actor_portrait(self, actor: Actor, size: int = 128) -> QPixmap:
        # Include bodytype and fame_tier in cache key so portrait updates live when actor transforms body or rises in fame!
        cache_key = f"{actor.id}:{actor.bodytype}:{actor.fame_tier}:{actor.portrait_path}:{size}"
        if cache_key in self.portrait_cache:
            return self.portrait_cache[cache_key]

        # 0. Try custom Roster Pack portrait (e.g., downloaded TMDb headshot)
        if actor.portrait_path and os.path.exists(actor.portrait_path):
            raw_pm = QPixmap(actor.portrait_path)
            if not raw_pm.isNull():
                # Center-crop to square favoring upper face area
                w, h = raw_pm.width(), raw_pm.height()
                side = min(w, h)
                x0 = (w - side) // 2
                y0 = max(0, int((h - side) * 0.22))
                cropped = raw_pm.copy(x0, y0, side, side).scaled(
                    size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
                )
                self.portrait_cache[cache_key] = cropped
                return cropped

        # 1. Try authentic layered PNG portrait from snapshots.xml
        pm = self.compositor.render_portrait(actor, size)
        if pm is not None and not pm.isNull():
            self.portrait_cache[cache_key] = pm
            return pm

        # 2. Fallback vector portrait if Steam assets aren't present
        rng = random.Random(actor.portrait_seed or actor.id)
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor("#1e293b"))
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor("#f4c552"))
        painter.setFont(QFont("Segoe UI", max(10, size // 5), QFont.Weight.Bold))
        initials = "".join(p[0] for p in actor.name.split()[:2]).upper()
        painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        pm = QPixmap.fromImage(img)
        self.portrait_cache[cache_key] = pm
        return pm
