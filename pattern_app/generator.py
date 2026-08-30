from __future__ import annotations

import html
import math
import random
import time
from dataclasses import asdict, dataclass

from PIL import Image, ImageDraw, ImageFilter

try:
    from opensimplex import OpenSimplex
except ImportError:  # pragma: no cover - optional dependency at import time
    OpenSimplex = None


@dataclass(slots=True)
class PatternConfig:
    width: int = 1600
    height: int = 900
    seed: str = ""
    background: str = "#111111"
    palette_mode: str = "random"
    density: float = 0.55
    complexity: float = 0.65
    grid_size: int = 14
    symmetry: str = "none"
    use_noise: bool = True
    use_lines: bool = True
    use_circles: bool = True
    use_blocks: bool = True
    use_triangles: bool = True
    use_accents: bool = True
    gradient: bool = False
    noise_scale: float = 0.012
    noise_amplitude: float = 60.0
    noise_octaves: int = 3
    blur: float = 0.0

    def normalized(self) -> "PatternConfig":
        return PatternConfig(
            width=min(8192, max(64, int(self.width))),
            height=min(8192, max(64, int(self.height))),
            seed=str(self.seed).strip(),
            background=self.background.strip() or "#111111",
            palette_mode=self.palette_mode if self.palette_mode in PALETTES else "random",
            density=min(1.0, max(0.02, float(self.density))),
            complexity=min(1.0, max(0.05, float(self.complexity))),
            grid_size=min(48, max(4, int(self.grid_size))),
            symmetry=self.symmetry if self.symmetry in {"none", "mirror", "radial", "grid"} else "none",
            use_noise=bool(self.use_noise),
            use_lines=bool(self.use_lines),
            use_circles=bool(self.use_circles),
            use_blocks=bool(self.use_blocks),
            use_triangles=bool(self.use_triangles),
            use_accents=bool(self.use_accents),
            gradient=bool(self.gradient),
            noise_scale=min(0.08, max(0.0005, float(self.noise_scale))),
            noise_amplitude=min(240.0, max(0.0, float(self.noise_amplitude))),
            noise_octaves=min(8, max(1, int(self.noise_octaves))),
            blur=min(12.0, max(0.0, float(self.blur))),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RenderResult:
    image: Image.Image
    svg: str
    seed: str
    elapsed: float


PALETTES = {
    "neon": [
        (255, 50, 120, 255),
        (60, 255, 180, 255),
        (90, 120, 255, 255),
        (255, 220, 60, 255),
        (225, 80, 255, 255),
    ],
    "earth": [
        (82, 56, 40, 255),
        (155, 110, 70, 255),
        (214, 187, 140, 255),
        (72, 93, 62, 255),
        (30, 30, 30, 255),
    ],
    "mono": [(30, 30, 30, 255), (90, 90, 90, 255), (150, 150, 150, 255), (220, 220, 220, 255)],
}


def _rgba(color: tuple[int, int, int, int]) -> str:
    return f"rgb({color[0]},{color[1]},{color[2]})"


def hex_to_rgba(value: str) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid background color: {value!r}")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)) + (255,)
    except ValueError as exc:
        raise ValueError(f"Invalid background color: {value!r}") from exc


class PatternRenderer:
    """Deterministic procedural pattern renderer shared by the GUI and tests."""

    def generate(self, config: PatternConfig) -> RenderResult:
        cfg = config.normalized()
        started = time.perf_counter()
        seed = cfg.seed or str(random.SystemRandom().randint(0, 2**31 - 1))
        rng = random.Random(seed)
        bg = hex_to_rgba(cfg.background)
        palette = self.palette(rng, cfg.palette_mode)
        noise = self._make_noise(seed, cfg)

        image = Image.new("RGBA", (cfg.width, cfg.height), bg)
        draw = ImageDraw.Draw(image, "RGBA")
        svg: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{cfg.width}" height="{cfg.height}" viewBox="0 0 {cfg.width} {cfg.height}">',
        ]
        svg.append(f'<rect width="100%" height="100%" fill="{html.escape(cfg.background)}"/>')

        if cfg.gradient:
            self._draw_gradient(draw, svg, cfg, bg)
        if cfg.use_noise:
            self._draw_flow(draw, svg, cfg, rng, palette, noise)
        self._draw_shapes(draw, svg, cfg, rng, palette, noise)
        if cfg.use_accents:
            self._draw_accents(draw, svg, cfg, rng, palette)

        if cfg.blur > 0:
            image = image.filter(ImageFilter.GaussianBlur(cfg.blur))

        svg.append("</svg>")
        return RenderResult(image=image, svg="\n".join(svg), seed=seed, elapsed=time.perf_counter() - started)

    @staticmethod
    def palette(rng: random.Random, mode: str) -> list[tuple[int, int, int, int]]:
        if mode in PALETTES:
            return list(PALETTES[mode])
        if mode == "pastel":
            return [(rng.randint(140, 240), rng.randint(140, 240), rng.randint(140, 240), 255) for _ in range(8)]
        return [(rng.randint(20, 255), rng.randint(20, 255), rng.randint(20, 255), 255) for _ in range(12)]

    @staticmethod
    def _make_noise(seed: str, cfg: PatternConfig):
        if not cfg.use_noise or OpenSimplex is None:
            return None
        try:
            noise_seed = int(seed)
        except ValueError:
            noise_seed = random.Random(seed).randint(0, 2**31 - 1)
        try:
            return OpenSimplex(noise_seed)
        except Exception:
            return None

    @staticmethod
    def _noise_value(x: float, y: float, generator, scale: float, octaves: int) -> float:
        if generator is None:
            return 0.0
        total = 0.0
        amplitude = 1.0
        frequency = scale
        for _ in range(octaves):
            if hasattr(generator, "noise2"):
                value = generator.noise2(x * frequency, y * frequency)
            else:
                value = generator.noise2d(x * frequency, y * frequency)
            total += value * amplitude
            amplitude *= 0.5
            frequency *= 2.0
        return total

    @staticmethod
    def _symmetry_points(points: list[tuple[float, float]], cfg: PatternConfig) -> list[tuple[float, float]]:
        w, h = cfg.width, cfg.height
        if cfg.symmetry == "mirror":
            return points + [(w - x, y) for x, y in points]
        if cfg.symmetry == "grid":
            mirrors = []
            for x, y in points:
                mirrors.extend(((x, y), (w - x, y), (x, h - y), (w - x, h - y)))
            return mirrors
        if cfg.symmetry == "radial":
            cx, cy = w / 2, h / 2
            out = []
            for x, y in points:
                dx, dy = x - cx, y - cy
                for step in range(4):
                    angle = step * math.tau / 4
                    out.append((cx + dx * math.cos(angle) - dy * math.sin(angle), cy + dx * math.sin(angle) + dy * math.cos(angle)))
            return out
        return points

    def _draw_gradient(self, draw: ImageDraw.ImageDraw, svg: list[str], cfg: PatternConfig, bg: tuple[int, int, int, int]) -> None:
        r, g, b, _ = bg
        for y in range(cfg.height):
            t = y / max(1, cfg.height - 1)
            line = (int(r * (1 - t)), int(g * (1 - t)), int(b * (1 - t)), 180)
            draw.line((0, y, cfg.width, y), fill=line)
        svg.append(
            '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{_rgba(bg)}" stop-opacity="1"/>'
            '<stop offset="1" stop-color="#000000" stop-opacity="0.1"/>'
            '</linearGradient></defs>'
        )
        svg.append('<rect width="100%" height="100%" fill="url(#bg)"/>')

    def _draw_flow(self, draw, svg: list[str], cfg: PatternConfig, rng: random.Random, palette, noise) -> None:
        count = max(6, int(cfg.grid_size * cfg.grid_size * (0.16 + cfg.complexity * 0.16)))
        for _ in range(count):
            x, y = rng.uniform(0, cfg.width), rng.uniform(0, cfg.height)
            points = [(x, y)]
            steps = rng.randint(10, 32 + int(cfg.complexity * 24))
            step_len = rng.uniform(8, 22 + cfg.complexity * 10)
            for _ in range(steps):
                n = self._noise_value(x, y, noise, cfg.noise_scale, cfg.noise_octaves)
                angle = n * math.tau * 2.1 + rng.uniform(-0.25, 0.25)
                x += math.cos(angle) * step_len
                y += math.sin(angle) * step_len
                if not (0 <= x <= cfg.width and 0 <= y <= cfg.height):
                    break
                points.append((x, y))
            if len(points) < 2:
                continue
            color = rng.choice(palette)
            alpha = rng.randint(35, 125)
            width = max(1, int(rng.uniform(1, 2.5 + cfg.complexity * 3.5)))
            draw.line(points, fill=(*color[:3], alpha), width=width, joint="curve")
            points_attr = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
            svg.append(
                f'<polyline points="{points_attr}" fill="none" stroke="{_rgba(color)}" '
                f'stroke-opacity="{alpha / 255:.3f}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
            )

    def _draw_shapes(self, draw, svg: list[str], cfg: PatternConfig, rng: random.Random, palette, noise) -> None:
        step_x = cfg.width / cfg.grid_size
        step_y = cfg.height / cfg.grid_size
        enabled = [
            name
            for name, flag in (("block", cfg.use_blocks), ("circle", cfg.use_circles), ("line", cfg.use_lines), ("tri", cfg.use_triangles))
            if flag
        ] or ["block"]

        for gy in range(cfg.grid_size):
            for gx in range(cfg.grid_size):
                if rng.random() > cfg.density:
                    continue
                x0, y0 = gx * step_x, gy * step_y
                x1, y1 = x0 + step_x, y0 + step_y
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                n = self._noise_value(cx, cy, noise, cfg.noise_scale, cfg.noise_octaves)
                cx = max(0, min(cfg.width, cx + n * cfg.noise_amplitude))
                cy = max(0, min(cfg.height, cy + n * cfg.noise_amplitude))
                color = rng.choice(palette)
                alpha = rng.randint(75, 220)
                fill = (*color[:3], alpha)
                shape = rng.choice(enabled)
                if shape == "block":
                    pad = rng.uniform(0.03, 0.28) * min(step_x, step_y)
                    radius = rng.uniform(1, 26) * (0.4 + cfg.complexity * 0.6)
                    box = (x0 + pad, y0 + pad, x1 - pad, y1 - pad)
                    draw.rounded_rectangle(box, radius=radius, fill=fill)
                    svg.append(f'<rect x="{box[0]:.1f}" y="{box[1]:.1f}" width="{box[2]-box[0]:.1f}" height="{box[3]-box[1]:.1f}" rx="{radius:.1f}" fill="{_rgba(color)}" fill-opacity="{alpha / 255:.3f}"/>')
                elif shape == "circle":
                    radius = min(step_x, step_y) * rng.uniform(0.12, 0.48)
                    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=fill)
                    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" fill="{_rgba(color)}" fill-opacity="{alpha / 255:.3f}"/>')
                elif shape == "line":
                    points = [(x0 + rng.random() * step_x, y0 + rng.random() * step_y) for _ in range(2 + int(cfg.complexity * 6))]
                    points = self._symmetry_points(points, cfg)
                    stroke_width = max(1, int(rng.uniform(1, 6)))
                    draw.line(points, fill=fill, width=stroke_width)
                    attr = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
                    svg.append(f'<polyline points="{attr}" fill="none" stroke="{_rgba(color)}" stroke-opacity="{alpha / 255:.3f}" stroke-width="{stroke_width}" stroke-linecap="round"/>')
                else:
                    points = [
                        (cx, y0 + rng.random() * step_y),
                        (x0 + rng.random() * step_x, y1 - rng.random() * step_y * 0.15),
                        (x1 - rng.random() * step_x, y1 - rng.random() * step_y * 0.15),
                    ]
                    draw.polygon(points, fill=fill)
                    attr = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
                    svg.append(f'<polygon points="{attr}" fill="{_rgba(color)}" fill-opacity="{alpha / 255:.3f}"/>')

                if rng.random() < 0.12 + cfg.complexity * 0.15:
                    for _ in range(rng.randint(1, 3)):
                        radius = rng.uniform(1, max(2.0, min(step_x, step_y) * 0.045))
                        ox = cx + rng.uniform(-step_x * 0.18, step_x * 0.18)
                        oy = cy + rng.uniform(-step_y * 0.18, step_y * 0.18)
                        accent = (255, 255, 255, rng.randint(30, 120))
                        draw.ellipse((ox - radius, oy - radius, ox + radius, oy + radius), fill=accent)
                        svg.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="{radius:.1f}" fill="#ffffff" fill-opacity="{accent[3] / 255:.3f}"/>')

    @staticmethod
    def _draw_accents(draw, svg: list[str], cfg: PatternConfig, rng: random.Random, palette) -> None:
        count = max(10, int(cfg.grid_size * (1.6 + cfg.complexity * 2.2)))
        for _ in range(count):
            color = rng.choice(palette)
            alpha = rng.randint(20, 100)
            x, y = rng.uniform(0, cfg.width), rng.uniform(0, cfg.height)
            kind = rng.choice(("dot", "ring", "chip"))
            if kind == "dot":
                radius = rng.uniform(1, 8)
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color[:3], alpha))
                svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{_rgba(color)}" fill-opacity="{alpha / 255:.3f}"/>')
            elif kind == "ring":
                radius = rng.uniform(5, 22)
                stroke = max(1, int(rng.uniform(1, 3)))
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(*color[:3], alpha), width=stroke)
                svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="none" stroke="{_rgba(color)}" stroke-opacity="{alpha / 255:.3f}" stroke-width="{stroke}"/>')
            else:
                width, height = rng.uniform(6, 36), rng.uniform(3, 18)
                draw.rounded_rectangle((x - width / 2, y - height / 2, x + width / 2, y + height / 2), radius=min(8, height / 2), fill=(*color[:3], alpha))
                svg.append(f'<rect x="{x-width/2:.1f}" y="{y-height/2:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{min(8,height/2):.1f}" fill="{_rgba(color)}" fill-opacity="{alpha / 255:.3f}"/>')


__all__ = ["PatternConfig", "PatternRenderer", "RenderResult", "hex_to_rgba"]
