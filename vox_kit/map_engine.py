"""Natural Earth 1:50m engraved map builder, mipmap cache, camera projection, and region painting."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .palette import C_BOARD, C_INK, C_YELLOW, get_font

_CODE_RE = re.compile(r"^[A-Z0-9_-]{2,8}$")


@dataclass(frozen=True)
class MapProjection:
    """
    Equirectangular cosine-corrected archival map projection.

    Default bbox (-115..65 lon, -38..68 lat) spans South America (Brazil/Colombia),
    the Atlantic Ocean, Europe, Turkey, and continental USA in a single map.
    """

    lon_min: float = -115.0
    lon_max: float = 65.0
    lat_min: float = -38.0
    lat_max: float = 68.0
    map_w: int = 5400

    def __post_init__(self) -> None:
        if not (-180.0 <= self.lon_min < self.lon_max <= 180.0):
            raise ValueError(f"Invalid longitude bounds: [{self.lon_min}, {self.lon_max}]")
        if not (-90.0 <= self.lat_min < self.lat_max <= 90.0):
            raise ValueError(f"Invalid latitude bounds: [{self.lat_min}, {self.lat_max}]")
        if not (64 <= int(self.map_w) <= 20000):
            raise ValueError(f"map_w must be between 64 and 20000, got {self.map_w}")

    @property
    def mid_lat(self) -> float:
        mid = 0.5 * (self.lat_min + self.lat_max)
        return max(-45.0, min(45.0, mid))

    @property
    def cos_mid(self) -> float:
        return math.cos(math.radians(self.mid_lat))

    @property
    def map_h(self) -> int:
        lon_span = max(1e-6, self.lon_max - self.lon_min)
        lat_span = max(1e-6, self.lat_max - self.lat_min)
        raw_h = int(round(self.map_w * lat_span / (lon_span * self.cos_mid)))
        return max(64, (raw_h // 8) * 8)

    def ll_to_map(self, lon: float, lat: float) -> Tuple[float, float]:
        x = (lon - self.lon_min) / (self.lon_max - self.lon_min) * self.map_w
        y = (self.lat_max - lat) / (self.lat_max - self.lat_min) * self.map_h
        return x, y

    def map_to_ll(self, mx: float, my: float) -> Tuple[float, float]:
        lon = self.lon_min + (mx / self.map_w) * (self.lon_max - self.lon_min)
        lat = self.lat_max - (my / self.map_h) * (self.lat_max - self.lat_min)
        return lon, lat

    def to_dict(self) -> dict:
        return {
            "lon_min": self.lon_min,
            "lon_max": self.lon_max,
            "lat_min": self.lat_min,
            "lat_max": self.lat_max,
            "map_w": self.map_w,
            "map_h": self.map_h,
            "mid_lat": self.mid_lat,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MapProjection":
        return cls(
            lon_min=float(data["lon_min"]),
            lon_max=float(data["lon_max"]),
            lat_min=float(data["lat_min"]),
            lat_max=float(data["lat_max"]),
            map_w=int(data["map_w"]),
        )


def _iter_rings(geom: dict):
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon" and coords:
        yield coords[0]
    elif gtype == "MultiPolygon":
        for poly in coords:
            if poly:
                yield poly[0]


def _ring_in_bbox(ring: Sequence[Sequence[float]], proj: MapProjection) -> bool:
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (
        max(lons) >= proj.lon_min - 5.0
        and min(lons) <= proj.lon_max + 5.0
        and max(lats) >= proj.lat_min - 5.0
        and min(lats) <= proj.lat_max + 5.0
    )


def _sanitize_country_code(code: str) -> str:
    clean = str(code).strip().upper()
    if not _CODE_RE.match(clean):
        raise ValueError(f"Invalid country code: {code!r}")
    return clean


def _draw_compass_rose(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float = 1.0) -> None:
    r_big = 135.0 * scale
    r_sm = 78.0 * scale
    draw.ellipse(
        [(cx - r_big * 0.72, cy - r_big * 0.72), (cx + r_big * 0.72, cy + r_big * 0.72)],
        outline=C_INK,
        width=max(2, int(round(3 * scale))),
    )
    draw.ellipse(
        [(cx - r_big * 0.62, cy - r_big * 0.62), (cx + r_big * 0.62, cy + r_big * 0.62)],
        outline=C_INK,
        width=max(1, int(round(2 * scale))),
    )
    for k in range(8):
        ang = k * math.pi / 4.0
        rad = r_big if k % 2 == 0 else r_sm
        tip = (cx + math.sin(ang) * rad, cy - math.cos(ang) * rad)
        l_pt = (cx + math.sin(ang - 0.32) * (26.0 * scale), cy - math.cos(ang - 0.32) * (26.0 * scale))
        r_pt = (cx + math.sin(ang + 0.32) * (26.0 * scale), cy - math.cos(ang + 0.32) * (26.0 * scale))
        draw.polygon([(cx, cy), l_pt, tip], fill=C_INK, outline=C_INK)
        draw.polygon([(cx, cy), r_pt, tip], fill=C_BOARD, outline=C_INK)


def build_map_cache(
    geojson_path: Union[str, Path],
    out_dir: Union[str, Path],
    countries: Sequence[str] = ("BRA", "COL", "TUR"),
    projection: Optional[MapProjection] = None,
    labels: Optional[Sequence[Tuple[str, float, float, str, int, int, Tuple[int, int, int]]]] = None,
) -> dict:
    """
    Build engraved Natural Earth mipmaps (mip0..mip2.png), meta.json, and per-country masks.

    Matches country features by ADM0_A3 or ISO_A3 properties.
    """
    proj = projection or MapProjection()
    gpath = Path(geojson_path)
    odir = Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    codes = [_sanitize_country_code(c) for c in countries]
    geo = json.loads(gpath.read_text(encoding="utf-8"))

    map_w, map_h = proj.map_w, proj.map_h
    scale_factor = map_w / 5400.0

    land_all = Image.new("L", (map_w, map_h), 0)
    d_all = ImageDraw.Draw(land_all)

    country_masks: Dict[str, Image.Image] = {c: Image.new("L", (map_w, map_h), 0) for c in codes}
    country_draws: Dict[str, ImageDraw.ImageDraw] = {c: ImageDraw.Draw(m) for c, m in country_masks.items()}

    border_rings: List[List[Tuple[float, float]]] = []
    featured_rings: List[List[Tuple[float, float]]] = []

    for feat in geo.get("features", []):
        props = feat.get("properties") or {}
        adm = str(props.get("ADM0_A3") or "").strip().upper()
        iso = str(props.get("ISO_A3") or "").strip().upper()
        matched_code = None
        for c in codes:
            if c == adm or c == iso:
                matched_code = c
                break

        geom = feat.get("geometry")
        if not geom:
            continue
        for ring in _iter_rings(geom):
            if len(ring) < 3 or not _ring_in_bbox(ring, proj):
                continue
            pts = [proj.ll_to_map(float(p[0]), float(p[1])) for p in ring]
            d_all.polygon(pts, fill=255)
            border_rings.append(pts)
            if matched_code is not None:
                country_draws[matched_code].polygon(pts, fill=255)
                featured_rings.append(pts)

    land_arr = np.array(land_all) > 127
    featured_arr = np.zeros((map_h, map_w), dtype=bool)
    for c in codes:
        featured_arr |= np.array(country_masks[c]) > 127

    canvas = np.empty((map_h, map_w, 3), dtype=np.uint8)
    canvas[:] = C_BOARD

    # 1. Sea wavy engraving lines
    yy, xx = np.mgrid[0:map_h, 0:map_w]
    wave_period = max(8, int(round(22 * scale_factor)))
    wave_len = max(32.0, 115.0 * scale_factor)
    wave_y = yy + (2.5 * scale_factor * np.sin(xx * (2.0 * math.pi / wave_len))).astype(np.int32)
    sea_waves = (~land_arr) & ((wave_y % wave_period) == 0)
    canvas[sea_waves] = (214, 209, 200)

    # 2. 4 coast-parallel ocean contour rings
    half_w, half_h = max(4, map_w // 2), max(4, map_h // 2)
    half_land = land_all.resize((half_w, half_h), Image.Resampling.NEAREST)
    for dist_px, alpha in [(8, 0.34), (19, 0.25), (32, 0.18), (48, 0.12)]:
        scaled_dist = max(4, int(round(dist_px * scale_factor)))
        r = max(3, (scaled_dist // 2) * 2 + 1)
        d_out = half_land.filter(ImageFilter.MaxFilter(r))
        d_in = half_land.filter(ImageFilter.MaxFilter(max(3, r - 2)))
        ring_half = (np.array(d_out) > 127) & ~(np.array(d_in) > 127)
        ring = np.repeat(np.repeat(ring_half, 2, axis=0), 2, axis=1)[:map_h, :map_w]
        ring &= ~land_arr
        canvas[ring] = ((1.0 - alpha) * canvas[ring] + alpha * np.array(C_INK)).astype(np.uint8)

    # 3. Land diagonal hatch + featured country cross-hatch
    hatch_step = max(8, int(round(22 * scale_factor)))
    hatch_w = max(1, int(round(2 * scale_factor)))
    diag1 = land_arr & (((xx + yy) % hatch_step) < hatch_w)
    canvas[diag1] = (204, 199, 190)

    feat_step = max(6, int(round(13 * scale_factor)))
    feat_h1 = featured_arr & (((xx + yy) % feat_step) < hatch_w)
    feat_h2 = featured_arr & (((xx - yy) % feat_step) < hatch_w)
    canvas[feat_h1 | feat_h2] = (176, 170, 160)

    img = Image.fromarray(canvas, "RGB")
    draw = ImageDraw.Draw(img)

    # 4. Dotted 10-degree graticule
    dash_step = max(8, int(round(18 * scale_factor)))
    dash_len = max(2, int(round(4 * scale_factor)))
    grat_w = max(1, int(round(2 * scale_factor)))
    lon_start = int(math.ceil(proj.lon_min / 10.0) * 10)
    lon_end = int(math.floor(proj.lon_max / 10.0) * 10)
    for lon in range(lon_start, lon_end + 1, 10):
        gx, _ = proj.ll_to_map(float(lon), proj.mid_lat)
        for gy in range(0, map_h, dash_step):
            draw.line([(gx, gy), (gx, gy + dash_len)], fill=(185, 180, 171), width=grat_w)
    lat_start = int(math.ceil(proj.lat_min / 10.0) * 10)
    lat_end = int(math.floor(proj.lat_max / 10.0) * 10)
    for lat in range(lat_start, lat_end + 1, 10):
        _, gy = proj.ll_to_map(proj.lon_min, float(lat))
        for gx in range(0, map_w, dash_step):
            draw.line([(gx, gy), (gx + dash_len, gy)], fill=(185, 180, 171), width=grat_w)

    # 5. Country borders & crisp coast outline
    bw_all = max(2, int(round(3 * scale_factor)))
    for pts in border_rings:
        draw.line(pts + [pts[0]], fill=(88, 84, 80), width=bw_all)

    coast_k = max(3, int(round(5 * scale_factor)) | 1)
    edge_land = land_all.filter(ImageFilter.MaxFilter(coast_k))
    coast_mask = (np.array(edge_land) > 127) & ~land_arr
    arr_tmp = np.array(img)
    arr_tmp[coast_mask] = C_INK
    img = Image.fromarray(arr_tmp, "RGB")
    draw = ImageDraw.Draw(img)

    bw_feat = max(3, int(round(5 * scale_factor)))
    for pts in featured_rings:
        draw.line(pts + [pts[0]], fill=C_INK, width=bw_feat)

    # 6. Compass rose in open Atlantic if inside bbox
    compass_lon, compass_lat = -35.0, 20.0
    if proj.lon_min + 10.0 <= compass_lon <= proj.lon_max - 10.0 and proj.lat_min + 10.0 <= compass_lat <= proj.lat_max - 10.0:
        cx, cy = proj.ll_to_map(compass_lon, compass_lat)
        _draw_compass_rose(draw, cx, cy, scale=scale_factor)

    # 7. Optional subtle engraved map labels
    if labels:
        for text, lon, lat, font_key, sz, spacing, color in labels:
            f = get_font(font_key, max(12, int(round(sz * scale_factor))))
            x0, y0 = proj.ll_to_map(lon, lat)
            sp = int(round(spacing * scale_factor))
            widths = [
                (f.getbbox(ch)[2] - f.getbbox(ch)[0]) if ch != " " else max(4, int(round(sz * scale_factor / 3.0)))
                for ch in text
            ]
            total = sum(widths) + sp * max(0, len(text) - 1)
            cur_x = x0 - total / 2.0
            for ch, cw in zip(text, widths):
                draw.text((cur_x, y0 - int(round(sz * scale_factor / 2.0))), ch, font=f, fill=color)
                cur_x += cw + sp

    # Save mip0, mip1, mip2 and country masks
    mip_paths: List[str] = []
    mip0_path = odir / "mip0.png"
    img.save(mip0_path, optimize=False)
    mip_paths.append(mip0_path.name)

    mip1 = img.resize((max(4, map_w // 2), max(4, map_h // 2)), Image.Resampling.LANCZOS)
    mip1_path = odir / "mip1.png"
    mip1.save(mip1_path, optimize=False)
    mip_paths.append(mip1_path.name)

    mip2 = mip1.resize((max(4, map_w // 4), max(4, map_h // 4)), Image.Resampling.LANCZOS)
    mip2_path = odir / "mip2.png"
    mip2.save(mip2_path, optimize=False)
    mip_paths.append(mip2_path.name)

    mask_files: Dict[str, str] = {}
    for code, mask_im in country_masks.items():
        fname = f"mask_{code}.png"
        mask_im.save(odir / fname, optimize=False)
        mask_files[code] = fname

    meta = {
        "projection": proj.to_dict(),
        "countries": codes,
        "mips": mip_paths,
        "masks": mask_files,
    }
    (odir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def paint_region(
    frame_arr: np.ndarray,
    mask_full: Image.Image,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    reveal_p: float,
    color: Tuple[int, int, int] = C_YELLOW,
) -> None:
    """Multiply-tint a country region bottom-to-top onto frame_arr (H, W, 3 uint8) in-place."""
    if reveal_p <= 0.005:
        return
    h, w = frame_arr.shape[:2]
    crop_m = mask_full.crop((x0, y0, x1, y1)).resize((w, h), Image.Resampling.BILINEAR)
    m = np.array(crop_m, dtype=np.float32) / 255.0
    if m.max() < 0.01:
        return
    rows = np.where(m.max(axis=1) > 0.1)[0]
    if len(rows) == 0:
        return
    rp = max(0.0, min(1.0, float(reveal_p)))
    cut_y = int(rows[-1]) - (int(rows[-1]) - int(rows[0]) + 24) * rp
    eff = m * np.clip((np.arange(h, dtype=np.float32)[:, None] - cut_y) / 20.0, 0.0, 1.0) * 0.88
    tint = np.array(color, dtype=np.float32) / 255.0
    bf = frame_arr.astype(np.float32) / 255.0
    blended = bf * (1.0 - eff[:, :, None]) + (bf * tint[None, None, :]) * eff[:, :, None]
    frame_arr[:] = np.clip(blended * 255.0, 0.0, 255.0).astype(np.uint8)


def _safe_cache_child(base_dir: Path, filename: str) -> Path:
    """Resolve a cache-relative filename and guarantee it cannot escape base_dir."""
    if not isinstance(filename, str) or not filename or "\x00" in filename:
        raise ValueError(f"Invalid cache filename: {filename!r}")
    rel = Path(filename)
    if rel.is_absolute():
        raise ValueError(f"Absolute path not allowed in map cache meta.json: {filename!r}")
    resolved = (base_dir / rel).resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError(f"Path traversal blocked in map cache meta.json: {filename!r}") from exc
    return resolved


class MapCamera:
    """Mipmap-backed archival map camera with smooth pan/zoom, country highlights, and geodesic arcs."""

    def __init__(self, cache_dir: Union[str, Path]):
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        meta_path = self.cache_dir / "meta.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Map cache meta.json not found in {self.cache_dir}")
        self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.projection = MapProjection.from_dict(self.meta["projection"])
        self.mips: List[Image.Image] = [
            Image.open(_safe_cache_child(self.cache_dir, name)).convert("RGB")
            for name in self.meta["mips"]
        ]
        self.masks: Dict[str, Image.Image] = {}
        for code, fname in self.meta.get("masks", {}).items():
            clean_code = _sanitize_country_code(code)
            p = _safe_cache_child(self.cache_dir, fname)
            if p.is_file():
                self.masks[clean_code] = Image.open(p).convert("L")

    def compute_viewport(
        self,
        lon: float,
        lat: float,
        zoom: float,
        w: int,
        h: int,
    ) -> Tuple[float, float, float, float, float, float, float]:
        """Return (cam_cx, cam_cy, x0, y0, x1, y1, eff_zoom) safely clamped inside the map."""
        map_w, map_h = self.projection.map_w, self.projection.map_h
        min_zoom = max((w + 8.0) / map_w, (h + 8.0) / map_h)
        eff_zoom = max(float(zoom), min_zoom)
        cam_cx, cam_cy = self.projection.ll_to_map(lon, lat)
        hw = (w / 2.0) / eff_zoom
        hh = (h / 2.0) / eff_zoom
        pad_x = min(4.0, max(0.0, (map_w - 2.0 * hw) * 0.25))
        pad_y = min(4.0, max(0.0, (map_h - 2.0 * hh) * 0.25))
        cam_cx = max(hw + pad_x, min(map_w - hw - pad_x, cam_cx))
        cam_cy = max(hh + pad_y, min(map_h - hh - pad_y, cam_cy))
        return cam_cx, cam_cy, cam_cx - hw, cam_cy - hh, cam_cx + hw, cam_cy + hh, eff_zoom

    def render_view(
        self,
        lon: float,
        lat: float,
        zoom: float,
        w: int,
        h: int,
        highlights: Optional[Dict[str, Tuple[float, Tuple[int, int, int]]]] = None,
    ) -> Image.Image:
        """Render a (w, h) RGB map viewport with optional per-country progressive highlights."""
        _, _, x0, y0, x1, y1, eff_zoom = self.compute_viewport(lon, lat, zoom, w, h)
        mip_lvl = max(0, min(len(self.mips) - 1, int(math.floor(math.log2(1.0 / eff_zoom) + 0.15))))
        sm = 1 << mip_lvl
        view = self.mips[mip_lvl].crop((x0 / sm, y0 / sm, x1 / sm, y1 / sm)).resize(
            (w, h), Image.Resampling.BILINEAR
        )
        if not highlights:
            return view

        arr = np.array(view, dtype=np.uint8)
        for code, spec in highlights.items():
            mask = self.masks.get(code.upper())
            if mask is None:
                continue
            reveal_p, col = spec
            paint_region(arr, mask, x0, y0, x1, y1, reveal_p, color=col)
        return Image.fromarray(arr, "RGB")

    def project(
        self,
        lon: float,
        lat: float,
        cam_cx: float,
        cam_cy: float,
        zoom: float,
        w: int,
        h: int,
    ) -> Tuple[float, float]:
        """Project geographic (lon, lat) into screen coordinates (sx, sy) for the given camera."""
        mx, my = self.projection.ll_to_map(lon, lat)
        return (mx - cam_cx) * zoom + w / 2.0, (my - cam_cy) * zoom + h / 2.0

    @staticmethod
    def geodesic_arc_points(
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
        n: int = 64,
        lift: float = 0.18,
    ) -> List[Tuple[float, float]]:
        """
        Compute n (lon, lat) points along a graceful great-circle-like arched route.

        `lift` bends the arc slightly perpendicular/northward for clean ocean ribbon aesthetics.
        """
        steps = max(2, int(n))
        p1_lon, p1_lat = math.radians(lon1), math.radians(lat1)
        p2_lon, p2_lat = math.radians(lon2), math.radians(lat2)

        def to_vec(lo: float, la: float) -> Tuple[float, float, float]:
            return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))

        v1 = to_vec(p1_lon, p1_lat)
        v2 = to_vec(p2_lon, p2_lat)
        dot = max(-1.0, min(1.0, v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]))
        omega = math.acos(dot)
        chord_deg = math.hypot(lon2 - lon1, lat2 - lat1)

        pts: List[Tuple[float, float]] = []
        for i in range(steps):
            t = i / (steps - 1)
            if omega < 1e-6:
                lo_deg = lon1 + (lon2 - lon1) * t
                la_deg = lat1 + (lat2 - lat1) * t
            else:
                so = math.sin(omega)
                w1 = math.sin((1.0 - t) * omega) / so
                w2 = math.sin(t * omega) / so
                vx = w1 * v1[0] + w2 * v2[0]
                vy = w1 * v1[1] + w2 * v2[1]
                vz = w1 * v1[2] + w2 * v2[2]
                lo_deg = math.degrees(math.atan2(vy, vx))
                la_deg = math.degrees(math.atan2(vz, math.hypot(vx, vy)))

            # Arch lift perpendicular to chord (biased gently poleward for editorial map clarity)
            arch = math.sin(math.pi * t) * float(lift) * chord_deg
            la_deg = max(-85.0, min(85.0, la_deg + arch))
            pts.append((lo_deg, la_deg))
        return pts

    def screen_arc_points(
        self,
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
        cam_cx: float,
        cam_cy: float,
        zoom: float,
        w: int,
        h: int,
        n: int = 64,
        lift: float = 0.18,
    ) -> List[Tuple[float, float]]:
        """Project a geodesic arc directly to screen coordinates for draw_red_ribbon."""
        geo_pts = self.geodesic_arc_points(lon1, lat1, lon2, lat2, n=n, lift=lift)
        return [self.project(lo, la, cam_cx, cam_cy, zoom, w, h) for lo, la in geo_pts]
