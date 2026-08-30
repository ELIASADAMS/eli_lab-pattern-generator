from __future__ import annotations

import html
import math
import random
import time
from dataclasses import asdict, dataclass, replace

from PIL import Image, ImageDraw, ImageFilter

try:
    from opensimplex import OpenSimplex
except ImportError:  # pragma: no cover
    OpenSimplex = None


PALETTES = {
    "neon": [(255, 50, 120), (60, 255, 180), (90, 120, 255), (255, 220, 60), (225, 80, 255)],
    "earth": [(82, 56, 40), (155, 110, 70), (214, 187, 140), (72, 93, 62), (30, 30, 30)],
    "mono": [(30, 30, 30), (90, 90, 90), (150, 150, 150), (220, 220, 220)],
    "ice": [(210, 240, 255), (130, 205, 240), (70, 150, 200), (235, 250, 255), (45, 85, 120)],
    "ritual": [(24, 18, 18), (100, 30, 30), (160, 55, 45), (215, 140, 70), (235, 210, 150)],
}


@dataclass(slots=True)
class PatternConfig:
    width: int = 1600
    height: int = 900
    seed: str = ""
    background: str = "#111111"
    density: float = 0.55
    complexity: float = 0.65

    # Composition
    composition_mode: str = "balanced"
    symmetry: str = "none"
    focal_x: float = 0.5
    focal_y: float = 0.5
    focal_strength: float = 0.6
    edge_bias: float = 0.0
    cluster_count: int = 4
    cluster_strength: float = 0.25
    spacing: float = 0.15
    jitter: float = 0.08

    # Field dynamics
    field_mode: str = "noise"
    field_strength: float = 0.65
    field_scale: float = 0.012
    field_curvature: float = 0.35
    field_steps: int = 24
    field_step_size: float = 18.0
    noise_octaves: int = 3

    # Geometry
    grid_size: int = 14
    shape_scale: float = 0.72
    scale_variance: float = 0.35
    rotation: float = 0.0
    rotation_jitter: float = 0.7
    corner_roundness: float = 0.35
    line_complexity: float = 0.55
    overlap: float = 0.2
    use_blocks: bool = True
    use_circles: bool = True
    use_lines: bool = True
    use_triangles: bool = True
    block_weight: float = 1.0
    circle_weight: float = 1.0
    line_weight: float = 1.0
    triangle_weight: float = 1.0

    # Color
    palette_mode: str = "random"
    palette_size: int = 6
    saturation: float = 1.0
    contrast: float = 0.5
    hue_jitter: float = 0.08
    opacity_min: float = 0.3
    opacity_max: float = 0.85
    color_coherence: float = 0.6

    # Layers / surface
    layer_count: int = 1
    depth: float = 0.45
    accent_density: float = 0.25
    gradient: bool = False
    blur: float = 0.0

    # Controlled chaos
    behavior: str = "organic"
    mutation: float = 0.25
    asymmetry: float = 0.35

    def normalized(self) -> "PatternConfig":
        return replace(
            self,
            width=max(64, min(8192, int(self.width))),
            height=max(64, min(8192, int(self.height))),
            seed=str(self.seed).strip(),
            background=self.background.strip() or "#111111",
            density=max(0.02, min(1.0, float(self.density))),
            complexity=max(0.05, min(1.0, float(self.complexity))),
            composition_mode=self.composition_mode if self.composition_mode in {"balanced", "focal", "clustered", "edge", "diagonal"} else "balanced",
            symmetry=self.symmetry if self.symmetry in {"none", "mirror", "radial", "grid"} else "none",
            focal_x=max(0.0, min(1.0, float(self.focal_x))),
            focal_y=max(0.0, min(1.0, float(self.focal_y))),
            focal_strength=max(0.0, min(1.0, float(self.focal_strength))),
            edge_bias=max(-1.0, min(1.0, float(self.edge_bias))),
            cluster_count=max(1, min(24, int(self.cluster_count))),
            cluster_strength=max(0.0, min(1.0, float(self.cluster_strength))),
            spacing=max(0.0, min(1.0, float(self.spacing))),
            jitter=max(0.0, min(1.0, float(self.jitter))),
            field_mode=self.field_mode if self.field_mode in {"none", "noise", "swirl", "vortex", "waves", "radial"} else "noise",
            field_strength=max(0.0, min(1.5, float(self.field_strength))),
            field_scale=max(0.0005, min(0.08, float(self.field_scale))),
            field_curvature=max(0.0, min(1.0, float(self.field_curvature))),
            field_steps=max(4, min(96, int(self.field_steps))),
            field_step_size=max(1.0, min(80.0, float(self.field_step_size))),
            noise_octaves=max(1, min(8, int(self.noise_octaves))),
            grid_size=max(4, min(48, int(self.grid_size))),
            shape_scale=max(0.05, min(1.5, float(self.shape_scale))),
            scale_variance=max(0.0, min(1.0, float(self.scale_variance))),
            rotation=float(self.rotation) % 360.0,
            rotation_jitter=max(0.0, min(3.14, float(self.rotation_jitter))),
            corner_roundness=max(0.0, min(1.0, float(self.corner_roundness))),
            line_complexity=max(0.05, min(1.0, float(self.line_complexity))),
            overlap=max(0.0, min(1.0, float(self.overlap))),
            use_blocks=bool(self.use_blocks),
            use_circles=bool(self.use_circles),
            use_lines=bool(self.use_lines),
            use_triangles=bool(self.use_triangles),
            block_weight=max(0.0, float(self.block_weight)),
            circle_weight=max(0.0, float(self.circle_weight)),
            line_weight=max(0.0, float(self.line_weight)),
            triangle_weight=max(0.0, float(self.triangle_weight)),
            palette_mode=self.palette_mode if self.palette_mode in set(PALETTES) | {"random", "pastel"} else "random",
            palette_size=max(2, min(12, int(self.palette_size))),
            saturation=max(0.0, min(1.5, float(self.saturation))),
            contrast=max(0.0, min(1.0, float(self.contrast))),
            hue_jitter=max(0.0, min(1.0, float(self.hue_jitter))),
            opacity_min=max(0.05, min(1.0, float(self.opacity_min))),
            opacity_max=max(0.05, min(1.0, float(self.opacity_max))),
            color_coherence=max(0.0, min(1.0, float(self.color_coherence))),
            layer_count=max(1, min(8, int(self.layer_count))),
            depth=max(0.0, min(1.0, float(self.depth))),
            accent_density=max(0.0, min(1.0, float(self.accent_density))),
            gradient=bool(self.gradient),
            blur=max(0.0, min(12.0, float(self.blur))),
            behavior=self.behavior if self.behavior in {"calm", "organic", "architectural", "chaotic", "ritual"} else "organic",
            mutation=max(0.0, min(1.0, float(self.mutation))),
            asymmetry=max(0.0, min(1.0, float(self.asymmetry))),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class RenderResult:
    image: Image.Image
    svg: str
    seed: str
    elapsed: float


def hex_to_rgba(value: str) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid background color: {value!r}")
    try:
        rgb = tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise ValueError(f"Invalid background color: {value!r}") from exc
    return (*rgb, 255)


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]},{c[1]},{c[2]})"


def _rotate(points, angle, cx, cy):
    ca, sa = math.cos(angle), math.sin(angle)
    return [(cx + (x-cx)*ca - (y-cy)*sa, cy + (x-cx)*sa + (y-cy)*ca) for x, y in points]


class PatternRenderer:
    """Procedural renderer where composition, field, geometry, color and chaos interact."""

    BEHAVIOR_FACTORS = {
        "calm": (0.55, 0.55, 0.45, 0.60, 0.55),
        "organic": (1.00, 1.00, 1.00, 1.00, 1.00),
        "architectural": (0.12, 0.20, 0.20, 0.55, 0.35),
        "chaotic": (1.25, 1.30, 1.55, 1.35, 1.35),
        "ritual": (1.05, 1.20, 0.60, 0.80, 0.70),
    }

    def generate(self, config: PatternConfig) -> RenderResult:
        cfg = self._apply_behavior(config.normalized())
        started = time.perf_counter()
        seed = cfg.seed or str(random.SystemRandom().randint(0, 2**31 - 1))
        rng = random.Random(seed)
        bg = hex_to_rgba(cfg.background)
        noise = self._make_noise(seed, cfg)
        palette = self._palette(rng, cfg)

        image = Image.new("RGBA", (cfg.width, cfg.height), bg)
        draw = ImageDraw.Draw(image, "RGBA")
        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.width}" height="{cfg.height}" viewBox="0 0 {cfg.width} {cfg.height}">',
            f'<rect width="100%" height="100%" fill="{html.escape(cfg.background)}"/>',
        ]
        if cfg.gradient:
            self._gradient(draw, svg, cfg, bg)
        for layer in range(cfg.layer_count):
            layer_rng = random.Random(f"{seed}:layer:{layer}")
            self._draw_flow(draw, svg, cfg, layer_rng, palette, noise, layer)
            self._draw_shapes(draw, svg, cfg, layer_rng, palette, noise, layer)
        self._draw_accents(draw, svg, cfg, rng, palette)
        if cfg.blur > 0:
            image = image.filter(ImageFilter.GaussianBlur(cfg.blur))
        svg.append("</svg>")
        return RenderResult(image, "\n".join(svg), seed, time.perf_counter() - started)

    @staticmethod
    def _apply_behavior(cfg: PatternConfig) -> PatternConfig:
        fs, fc, rj, sv, mut = PatternRenderer.BEHAVIOR_FACTORS.get(cfg.behavior, PatternRenderer.BEHAVIOR_FACTORS["organic"])
        return replace(
            cfg,
            field_strength=min(1.5, cfg.field_strength * fs),
            field_curvature=min(1.0, cfg.field_curvature * fc),
            rotation_jitter=min(3.14, cfg.rotation_jitter * rj),
            scale_variance=min(1.0, cfg.scale_variance * sv),
            mutation=min(1.0, cfg.mutation * mut),
            jitter=min(1.0, cfg.jitter * (0.7 + 0.3 * mut)),
            cluster_strength=min(1.0, cfg.cluster_strength * (0.75 + 0.25 * fs)),
        )

    @staticmethod
    def _palette(rng, cfg):
        if cfg.palette_mode == "random":
            base = [(rng.randint(20, 255), rng.randint(20, 255), rng.randint(20, 255)) for _ in range(cfg.palette_size)]
        elif cfg.palette_mode == "pastel":
            base = [(rng.randint(150, 240), rng.randint(150, 240), rng.randint(150, 240)) for _ in range(cfg.palette_size)]
        else:
            source = PALETTES[cfg.palette_mode]
            base = [source[i % len(source)] for i in range(cfg.palette_size)]
        return [PatternRenderer._adjust_color(c, rng, cfg) for c in base]

    @staticmethod
    def _adjust_color(color, rng, cfg):
        r, g, b = [v / 255 for v in color]
        mx, mn = max(r, g, b), min(r, g, b)
        d = mx - mn
        l = (mx + mn) / 2
        s = 0 if d == 0 else d / (1 - abs(2 * l - 1))
        s = max(0, min(1, s * cfg.saturation))
        if d == 0: h = 0
        elif mx == r: h = ((g - b) / d) % 6
        elif mx == g: h = (b - r) / d + 2
        else: h = (r - g) / d + 4
        h = (h * 60 + rng.uniform(-cfg.hue_jitter, cfg.hue_jitter) * 360) % 360
        l = max(0.05, min(0.95, 0.5 + (l - 0.5) * (1 + cfg.contrast)))
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2
        if h < 60: rr, gg, bb = c, x, 0
        elif h < 120: rr, gg, bb = x, c, 0
        elif h < 180: rr, gg, bb = 0, c, x
        elif h < 240: rr, gg, bb = 0, x, c
        elif h < 300: rr, gg, bb = x, 0, c
        else: rr, gg, bb = c, 0, x
        return (int((rr + m) * 255), int((gg + m) * 255), int((bb + m) * 255))

    @staticmethod
    def _make_noise(seed, cfg):
        if cfg.field_mode == "none" or OpenSimplex is None:
            return None
        try: numeric_seed = int(seed)
        except ValueError: numeric_seed = random.Random(seed).randint(0, 2**31 - 1)
        try: return OpenSimplex(numeric_seed)
        except Exception: return None

    @staticmethod
    def _noise_value(x, y, gen, cfg):
        if gen is None: return 0.0
        total = 0.0; amplitude = 1.0; frequency = cfg.field_scale; total_amp = 0.0
        for _ in range(cfg.noise_octaves):
            value = gen.noise2(x * frequency, y * frequency) if hasattr(gen, "noise2") else gen.noise2d(x * frequency, y * frequency)
            total += value * amplitude; total_amp += amplitude; amplitude *= 0.5; frequency *= 2.0
        return total / max(1e-6, total_amp)

    def _field_angle(self, x, y, cfg, noise):
        nx, ny = x / cfg.width - 0.5, y / cfg.height - 0.5
        if cfg.field_mode == "radial": return math.atan2(ny, nx) + math.pi / 2
        if cfg.field_mode in {"swirl", "vortex"}: return math.atan2(ny, nx) + math.pi / 2 + math.atan2(ny, nx) * (2.0 if cfg.field_mode == "vortex" else 1.0)
        if cfg.field_mode == "waves": return math.sin(nx * 8 + ny * 5) * math.pi + math.radians(cfg.rotation)
        if cfg.field_mode == "noise" and noise is not None: return self._noise_value(x, y, noise, cfg) * math.tau * (1.2 + cfg.field_curvature * 3)
        return math.radians(cfg.rotation)

    def _choose_color(self, rng, palette, cfg, x, y):
        if len(palette) == 1 or cfg.color_coherence <= 0: return rng.choice(palette)
        index = int(((x / max(1, cfg.width)) * 0.6 + (y / max(1, cfg.height)) * 0.4) * len(palette)) % len(palette)
        if rng.random() > cfg.color_coherence: index = (index + rng.randrange(len(palette))) % len(palette)
        return palette[index]

    def _composition_probability(self, x, y, cfg, clusters, gx=0, gy=0):
        nx, ny = x / cfg.width, y / cfg.height; p = 1.0
        if cfg.symmetry == "radial": p *= 1.0 + (1.0 - min(1.0, abs(math.hypot(nx-.5, ny-.5)-.28)*3))*.45
        elif cfg.symmetry == "mirror": p *= 1.0 + (1.0 - abs(nx-.5)*2)*.22
        elif cfg.symmetry == "grid": p *= 1.0 + .15*(math.cos(nx*math.pi*4)*math.cos(ny*math.pi*4))
        if cfg.composition_mode == "focal":
            p = 1 + cfg.focal_strength * (1 - min(1, math.hypot(nx - cfg.focal_x, ny - cfg.focal_y) * 1.8))
        elif cfg.composition_mode == "clustered":
            d = min(math.hypot(x-cx, y-cy) for cx, cy in clusters) / max(1.0, math.hypot(cfg.width, cfg.height)); p = .45 + (1-min(1,d*2.5))*cfg.cluster_strength*2.4
        elif cfg.composition_mode == "edge":
            p = 1 + cfg.edge_bias * (.5-min(nx,1-nx,ny,1-ny))*2
        elif cfg.composition_mode == "diagonal": p = .6 + .8*(1-abs(nx-ny))
        else: p = 1 + cfg.asymmetry*(nx-.5)*.25
        if cfg.cluster_strength and cfg.composition_mode != "clustered":
            d=min(math.hypot(x-cx,y-cy) for cx,cy in clusters)/max(1.0,math.hypot(cfg.width,cfg.height)); p*=1+cfg.cluster_strength*(1-min(1,d*3))*.55
        return max(.05,min(2,p))

    def _draw_flow(self, draw, svg, cfg, rng, palette, noise, layer):
        if cfg.field_mode == "none": return
        count = max(4, int(cfg.grid_size*(1.2+cfg.field_strength*3)*(0.65+layer*.15)*(0.65+cfg.complexity*.55)))
        for _ in range(count):
            x,y=rng.uniform(0,cfg.width),rng.uniform(0,cfg.height); points=[(x,y)]; angle=self._field_angle(x,y,cfg,noise)
            for _step in range(cfg.field_steps):
                local=self._field_angle(x,y,cfg,noise); angle=angle*(1-cfg.field_curvature)+local*cfg.field_curvature+rng.uniform(-cfg.jitter,cfg.jitter)*cfg.mutation
                x+=math.cos(angle)*cfg.field_step_size*cfg.field_strength; y+=math.sin(angle)*cfg.field_step_size*cfg.field_strength
                if not(0<=x<=cfg.width and 0<=y<=cfg.height): break
                points.append((x,y))
            if len(points)<2: continue
            c=self._choose_color(rng,palette,cfg,x,y); a=int(255*rng.uniform(cfg.opacity_min*.55,cfg.opacity_max*.75)); width=max(1,int(rng.uniform(1,2+cfg.depth*4)))
            draw.line(points,fill=(*c,a),width=width,joint='curve'); attr=' '.join(f'{px:.1f},{py:.1f}' for px,py in points); svg.append(f'<polyline points="{attr}" fill="none" stroke="{_rgb(c)}" stroke-opacity="{a/255:.3f}" stroke-width="{width}" stroke-linecap="round"/>')

    @staticmethod
    def _weighted_shapes(cfg):
        choices=[(n,w) for n,en,w in (("block",cfg.use_blocks,cfg.block_weight),("circle",cfg.use_circles,cfg.circle_weight),("line",cfg.use_lines,cfg.line_weight),("tri",cfg.use_triangles,cfg.triangle_weight)) if en and w>0]
        return choices or [("block",1.0)]

    @staticmethod
    def _pick_weighted(rng, choices):
        total=sum(w for _,w in choices); needle=rng.random()*total
        for name,weight in choices:
            needle-=weight
            if needle<=0:return name
        return choices[-1][0]

    @staticmethod
    def _symmetry_instances(cx,cy,rotation,cfg):
        if cfg.symmetry=='mirror': return [(cx,cy,rotation),(cfg.width-cx,cy,-rotation)]
        if cfg.symmetry=='grid': return [(cx,cy,rotation),(cfg.width-cx,cy,-rotation),(cx,cfg.height-cy,-rotation),(cfg.width-cx,cfg.height-cy,rotation)]
        if cfg.symmetry=='radial':
            ox,oy=cfg.width/2,cfg.height/2; out=[]
            for i in range(4):
                a=i*math.tau/4; dx,dy=cx-ox,cy-oy; out.append((ox+dx*math.cos(a)-dy*math.sin(a),oy+dx*math.sin(a)+dy*math.cos(a),rotation+a))
            return out
        return [(cx,cy,rotation)]

    def _draw_shapes(self,draw,svg,cfg,rng,palette,noise,layer):
        choices=self._weighted_shapes(cfg); sx,sy=cfg.width/cfg.grid_size,cfg.height/cfg.grid_size; cr=random.Random(f'{cfg.seed}:clusters:{layer}'); clusters=[(cr.uniform(0,cfg.width),cr.uniform(0,cfg.height)) for _ in range(cfg.cluster_count)]
        for gy in range(cfg.grid_size):
            for gx in range(cfg.grid_size):
                x0,y0=gx*sx,gy*sy; cx,cy=x0+sx/2,y0+sy/2; probability=min(1,.05+.85*cfg.density*self._composition_probability(cx,cy,cfg,clusters,gx,gy)*(0.65+0.35*cfg.complexity))
                if rng.random()>probability:continue
                n=self._noise_value(cx,cy,noise,cfg); fa=self._field_angle(cx,cy,cfg,noise); cx+=math.cos(fa)*n*cfg.field_strength*cfg.jitter*sx; cy+=math.sin(fa)*n*cfg.field_strength*cfg.jitter*sy
                scale=cfg.shape_scale*(1-cfg.spacing*.28)*(1+rng.uniform(-cfg.scale_variance,cfg.scale_variance)); scale*=1+cfg.overlap*.8*rng.uniform(-1,1); w,h=sx*scale,sy*scale; rotation=math.radians(cfg.rotation)+rng.uniform(-cfg.rotation_jitter,cfg.rotation_jitter)+fa*cfg.field_curvature*.15
                color=self._choose_color(rng,palette,cfg,cx,cy); alpha=int(255*rng.uniform(cfg.opacity_min,cfg.opacity_max)); shape=self._pick_weighted(rng,choices)
                for ix,iy,irot in self._symmetry_instances(cx,cy,rotation,cfg): self._shape(draw,svg,cfg,rng,shape,ix,iy,w,h,irot,color,alpha)

    def _shape(self,draw,svg,cfg,rng,shape,cx,cy,w,h,rotation,color,alpha):
        fill=(*color,alpha)
        if shape=='circle':
            r=min(w,h)/2; draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=fill); svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{_rgb(color)}" fill-opacity="{alpha/255:.3f}"/>'); return
        if shape=='tri':
            pts=_rotate([(cx,cy-h/2),(cx-w/2,cy+h/2),(cx+w/2,cy+h/2)],rotation,cx,cy); draw.polygon(pts,fill=fill); attr=' '.join(f'{x:.1f},{y:.1f}' for x,y in pts); svg.append(f'<polygon points="{attr}" fill="{_rgb(color)}" fill-opacity="{alpha/255:.3f}"/>'); return
        if shape=='line':
            count=2+int(cfg.line_complexity*7); pts=[]
            for i in range(count):
                t=i/max(1,count-1); pts.append((cx-w/2+t*w,cy+math.sin(t*math.pi*2+rotation)*h*.25+rng.uniform(-cfg.jitter,cfg.jitter)*h))
            pts=_rotate(pts,rotation,cx,cy); width=max(1,int(1+cfg.depth*5)); draw.line(pts,fill=fill,width=width,joint='curve'); attr=' '.join(f'{x:.1f},{y:.1f}' for x,y in pts); svg.append(f'<polyline points="{attr}" fill="none" stroke="{_rgb(color)}" stroke-opacity="{alpha/255:.3f}" stroke-width="{width}" stroke-linecap="round"/>'); return
        pad=(1-cfg.corner_roundness)*min(w,h)*.08; pts=[(cx-w/2+pad,cy-h/2+pad),(cx+w/2-pad,cy-h/2+pad),(cx+w/2-pad,cy+h/2-pad),(cx-w/2+pad,cy+h/2-pad)]; pts=_rotate(pts,rotation,cx,cy); draw.polygon(pts,fill=fill); attr=' '.join(f'{x:.1f},{y:.1f}' for x,y in pts); svg.append(f'<polygon points="{attr}" fill="{_rgb(color)}" fill-opacity="{alpha/255:.3f}"/>')

    @staticmethod
    def _draw_accents(draw,svg,cfg,rng,palette):
        count=int(cfg.grid_size*cfg.grid_size*cfg.accent_density*.08)
        for _ in range(count):
            x,y=rng.uniform(0,cfg.width),rng.uniform(0,cfg.height); c=rng.choice(palette); r=rng.uniform(1,8)*(0.5+cfg.depth); a=int(255*rng.uniform(cfg.opacity_min*.4,cfg.opacity_max*.55)); draw.ellipse((x-r,y-r,x+r,y+r),fill=(*c,a)); svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{_rgb(c)}" fill-opacity="{a/255:.3f}"/>')

    @staticmethod
    def _gradient(draw,svg,cfg,bg):
        r,g,b,_=bg
        for y in range(cfg.height):
            t=y/max(1,cfg.height-1); draw.line((0,y,cfg.width,y),fill=(int(r*(1-t)),int(g*(1-t)),int(b*(1-t)),255))
        svg.append('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="white" stop-opacity="0.14"/><stop offset="1" stop-color="black" stop-opacity="0.18"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#bg)"/>')


__all__=["PatternConfig","PatternRenderer","RenderResult","hex_to_rgba"]
