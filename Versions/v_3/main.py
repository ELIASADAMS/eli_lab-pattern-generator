import math
import random
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk, filedialog, colorchooser

from PIL import Image, ImageDraw, ImageTk, ImageFilter

try:
    from opensimplex import OpenSimplex
except Exception:
    OpenSimplex = None


@dataclass
class PatternConfig:
    width: int
    height: int
    seed: str
    bg: str
    palette_mode: str
    shape_density: float
    symmetry: str
    grid_size: int
    complexity: float
    use_noise: bool
    use_lines: bool
    use_circles: bool
    use_blocks: bool
    use_triangles: bool
    use_gradients: bool
    export_svg: bool
    noise_scale: float
    noise_amp: float
    noise_octaves: int
    blur_amount: float
    aspect_mode: str


class PatternGen:
    def __init__(self, root):
        self.root = root
        self.root.title("Semi-Random Pattern Generator")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 720)

        self.width = tk.IntVar(value=1600)
        self.height = tk.IntVar(value=900)
        self.seed = tk.StringVar(value="")
        self.bg = tk.StringVar(value="#111111")
        self.palette_mode = tk.StringVar(value="random")
        self.shape_density = tk.DoubleVar(value=0.55)
        self.symmetry = tk.StringVar(value="none")
        self.grid_size = tk.IntVar(value=14)
        self.complexity = tk.DoubleVar(value=0.65)
        self.use_noise = tk.BooleanVar(value=True)
        self.use_lines = tk.BooleanVar(value=True)
        self.use_circles = tk.BooleanVar(value=True)
        self.use_blocks = tk.BooleanVar(value=True)
        self.use_triangles = tk.BooleanVar(value=True)
        self.use_gradients = tk.BooleanVar(value=False)
        self.export_svg = tk.BooleanVar(value=True)
        self.noise_scale = tk.DoubleVar(value=0.012)
        self.noise_amp = tk.DoubleVar(value=60)
        self.noise_octaves = tk.IntVar(value=3)
        self.blur_amount = tk.DoubleVar(value=0.0)
        self.aspect_mode = tk.StringVar(value="custom")

        self.img = None
        self.photo = None
        self.elements = []
        self._preview_size = (820, 760)

        self._build_ui()

        for var in [
            self.width, self.height, self.seed, self.bg, self.palette_mode,
            self.shape_density, self.symmetry, self.grid_size, self.complexity,
            self.use_noise, self.use_lines, self.use_circles, self.use_blocks,
            self.use_triangles, self.use_gradients, self.export_svg,
            self.noise_scale, self.noise_amp, self.noise_octaves, self.blur_amount
        ]:
            var.trace_add("write", self.schedule_generate)

        self.generate()

    def schedule_generate(self, *args):
        if hasattr(self, "_regen_job") and self._regen_job:
            self.root.after_cancel(self._regen_job)
        self._regen_job = self.root.after(200, self.generate)

    class ScrollableFrame(ttk.Frame):
        def __init__(self, container, *args, **kwargs):
            super().__init__(container, *args, **kwargs)
            self.canvas = tk.Canvas(self, highlightthickness=0, bg="#d9d9d9")
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.inner = ttk.Frame(self.canvas)

            self.inner.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            )

            self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.canvas.bind("<Configure>", self._on_canvas_configure)
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

            self.canvas.pack(side="left", fill="both", expand=True)
            self.scrollbar.pack(side="right", fill="y")

        def _on_canvas_configure(self, event):
            self.canvas.itemconfig(self.window_id, width=event.width)

        def _on_mousewheel(self, event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_ui(self):
        self.root.geometry("1280x820")
        self.root.minsize(980, 680)

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0, minsize=360)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(right, bg="#222", highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        self.preview_canvas.bind("<Configure>", self._on_preview_resize)

        self.scroll = self.ScrollableFrame(left)
        self.scroll.grid(row=0, column=0, sticky="nsew")

        notebook = ttk.Notebook(self.scroll.inner)
        notebook.pack(fill="both", expand=True)

        core_tab = ttk.Frame(notebook, padding=10)
        shape_tab = ttk.Frame(notebook, padding=10)
        noise_tab = ttk.Frame(notebook, padding=10)
        effect_tab = ttk.Frame(notebook, padding=10)
        export_tab = ttk.Frame(notebook, padding=10)

        notebook.add(core_tab, text="Core")
        notebook.add(shape_tab, text="Shapes")
        notebook.add(noise_tab, text="Noise")
        notebook.add(effect_tab, text="Effects")
        notebook.add(export_tab, text="Export")

        for tab in (core_tab, shape_tab, noise_tab, effect_tab, export_tab):
            tab.columnconfigure(0, weight=1)

        def add_row(parent, row, label, widget):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(6, 2))
            widget.grid(row=row + 1, column=0, sticky="we")

        # Core tab
        add_row(core_tab, 0, "Width", ttk.Entry(core_tab, textvariable=self.width))
        add_row(core_tab, 2, "Height", ttk.Entry(core_tab, textvariable=self.height))
        add_row(core_tab, 4, "Seed", ttk.Entry(core_tab, textvariable=self.seed))

        action_row = ttk.Frame(core_tab)
        action_row.grid(row=15, column=0, sticky="we", pady=(12, 0))
        action_row.columnconfigure(0, weight=1)

        ttk.Label(core_tab, text="Aspect mode").grid(row=6, column=0, sticky="w", pady=(6, 2))
        ttk.Combobox(
            core_tab,
            textvariable=self.aspect_mode,
            values=["custom", "square", "landscape", "portrait", "ultrawide"],
            state="readonly",
        ).grid(row=7, column=0, sticky="we")

        ttk.Button(core_tab, text="Apply Aspect", command=self.apply_aspect_mode).grid(
            row=8, column=0, sticky="we", pady=(10, 0)
        )

        ttk.Label(core_tab, text="Background").grid(row=9, column=0, sticky="w", pady=(10, 2))
        bg_row = ttk.Frame(core_tab)
        bg_row.grid(row=10, column=0, sticky="we")
        bg_row.columnconfigure(0, weight=1)
        ttk.Entry(bg_row, textvariable=self.bg).grid(row=0, column=0, sticky="we")
        ttk.Button(bg_row, text="Pick", command=self.pick_bg).grid(row=0, column=1, padx=(6, 0))

        ttk.Label(core_tab, text="Palette mode").grid(row=11, column=0, sticky="w", pady=(10, 2))
        ttk.Combobox(
            core_tab,
            textvariable=self.palette_mode,
            values=["random", "pastel", "neon", "earth", "mono"],
            state="readonly",
        ).grid(row=12, column=0, sticky="we")

        ttk.Label(core_tab, text="Symmetry").grid(row=13, column=0, sticky="w", pady=(10, 2))
        ttk.Combobox(
            core_tab,
            textvariable=self.symmetry,
            values=["none", "mirror", "radial"],
            state="readonly",
        ).grid(row=14, column=0, sticky="we")

        # Shapes tab
        ttk.Label(shape_tab, text="Density").grid(row=0, column=0, sticky="w", pady=(6, 2))
        ttk.Scale(shape_tab, from_=0.05, to=1.0, variable=self.shape_density, orient="horizontal").grid(
            row=1, column=0, sticky="we"
        )

        ttk.Label(shape_tab, text="Complexity").grid(row=2, column=0, sticky="w", pady=(10, 2))
        ttk.Scale(shape_tab, from_=0.1, to=1.0, variable=self.complexity, orient="horizontal").grid(
            row=3, column=0, sticky="we"
        )

        ttk.Label(shape_tab, text="Grid size").grid(row=4, column=0, sticky="w", pady=(10, 2))
        ttk.Scale(shape_tab, from_=4, to=40, variable=self.grid_size, orient="horizontal").grid(
            row=5, column=0, sticky="we"
        )

        ttk.Checkbutton(shape_tab, text="Blocks", variable=self.use_blocks).grid(row=6, column=0, sticky="w",
                                                                                 pady=(10, 0))
        ttk.Checkbutton(shape_tab, text="Circles", variable=self.use_circles).grid(row=7, column=0, sticky="w")
        ttk.Checkbutton(shape_tab, text="Lines", variable=self.use_lines).grid(row=8, column=0, sticky="w")
        ttk.Checkbutton(shape_tab, text="Triangles", variable=self.use_triangles).grid(row=9, column=0, sticky="w")

        # Noise tab
        ttk.Checkbutton(noise_tab, text="Enable noise flow", variable=self.use_noise).grid(row=0, column=0, sticky="w",
                                                                                           pady=(6, 0))

        ttk.Label(noise_tab, text="Noise scale").grid(row=1, column=0, sticky="w", pady=(10, 2))
        ttk.Scale(noise_tab, from_=0.001, to=0.05, variable=self.noise_scale, orient="horizontal").grid(
            row=2, column=0, sticky="we"
        )

        ttk.Label(noise_tab, text="Noise amplitude").grid(row=3, column=0, sticky="w", pady=(10, 2))
        ttk.Scale(noise_tab, from_=0, to=180, variable=self.noise_amp, orient="horizontal").grid(
            row=4, column=0, sticky="we"
        )

        ttk.Label(noise_tab, text="Noise octaves").grid(row=5, column=0, sticky="w", pady=(10, 2))
        ttk.Scale(noise_tab, from_=1, to=6, variable=self.noise_octaves, orient="horizontal").grid(
            row=6, column=0, sticky="we"
        )

        # Effects tab
        ttk.Checkbutton(effect_tab, text="Background gradient", variable=self.use_gradients).grid(
            row=0, column=0, sticky="w", pady=(6, 0)
        )

        ttk.Label(effect_tab, text="Blur").grid(row=1, column=0, sticky="w", pady=(10, 2))
        ttk.Scale(effect_tab, from_=0.0, to=4.0, variable=self.blur_amount, orient="horizontal").grid(
            row=2, column=0, sticky="we"
        )

        ttk.Button(effect_tab, text="Randomize parameters", command=self.randomize).grid(
            row=3, column=0, sticky="we", pady=(16, 0)
        )

        # Export tab
        ttk.Checkbutton(export_tab, text="Enable SVG export", variable=self.export_svg).grid(
            row=0, column=0, sticky="w", pady=(6, 0)
        )

        ttk.Button(export_tab, text="Generate", command=self.generate).grid(row=1, column=0, sticky="we", pady=(12, 0))
        ttk.Button(export_tab, text="Save PNG", command=self.save_png).grid(row=2, column=0, sticky="we", pady=(8, 0))
        ttk.Button(export_tab, text="Save SVG", command=self.save_svg).grid(row=3, column=0, sticky="we", pady=(8, 0))

    def _on_preview_resize(self, event):
        if self.img is None:
            return
        self._preview_size = (max(100, event.width - 10), max(100, event.height - 10))
        self._preview()

    def _preview(self):
        if self.img is None:
            return
        preview = self.img.copy()
        preview.thumbnail(self._preview_size)
        self.photo = ImageTk.PhotoImage(preview)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            self._preview_size[0] // 2,
            self._preview_size[1] // 2,
            anchor="center",
            image=self.photo,
        )

    def apply_aspect_mode(self):
        mode = self.aspect_mode.get()
        if mode == "square":
            self.height.set(self.width.get())
        elif mode == "landscape":
            self.width.set(1600)
            self.height.set(900)
        elif mode == "portrait":
            self.width.set(900)
            self.height.set(1600)
        elif mode == "ultrawide":
            self.width.set(1920)
            self.height.set(720)
        self.generate()

    def pick_bg(self):
        c = colorchooser.askcolor(self.bg.get())[1]
        if c:
            self.bg.set(c)

    def randomize(self):
        self.seed.set(str(random.randint(0, 10 ** 9)))
        self.palette_mode.set(random.choice(["random", "pastel", "neon", "earth", "mono"]))
        self.symmetry.set(random.choice(["none", "mirror", "radial"]))
        self.complexity.set(round(random.uniform(0.35, 0.95), 2))
        self.shape_density.set(round(random.uniform(0.25, 0.85), 2))
        self.generate()

    def palette(self, rng):
        mode = self.palette_mode.get()
        if mode == "pastel":
            return [(rng.randint(140, 240), rng.randint(140, 240), rng.randint(140, 240), 255) for _ in range(8)]
        if mode == "neon":
            return [(255, 50, 120, 255), (60, 255, 180, 255), (90, 120, 255, 255), (255, 220, 60, 255)]
        if mode == "earth":
            return [
                (82, 56, 40, 255),
                (155, 110, 70, 255),
                (214, 187, 140, 255),
                (72, 93, 62, 255),
                (30, 30, 30, 255),
            ]
        if mode == "mono":
            return [(30, 30, 30, 255), (90, 90, 90, 255), (150, 150, 150, 255), (220, 220, 220, 255)]
        return [(rng.randint(20, 255), rng.randint(20, 255), rng.randint(20, 255), 255) for _ in range(12)]

    def hex_to_rgba(self, s):
        s = s.strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) != 6:
            return (17, 17, 17, 255)
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

    def svg_color(self, rgba):
        return f"rgb({rgba[0]},{rgba[1]},{rgba[2]})"

    def noise_value(self, x, y, gen, scale, octaves):
        if gen is None:
            return 0.0
        value = 0.0
        amp = 1.0
        freq = scale
        for _ in range(octaves):
            try:
                v = gen.noise2(x * freq, y * freq)
            except Exception:
                v = gen.noise2d(x * freq, y * freq)
            value += v * amp
            amp *= 0.5
            freq *= 2.0
        return value

    def add_symmetry(self, pts, w, h):
        sym = self.symmetry.get()
        if sym == "mirror":
            return pts + [(w - x, y) for x, y in pts]
        if sym == "radial":
            cx, cy = w / 2, h / 2
            out = []
            for x, y in pts:
                dx, dy = x - cx, y - cy
                for a in range(4):
                    ang = a * math.pi / 2
                    rx = cx + dx * math.cos(ang) - dy * math.sin(ang)
                    ry = cy + dx * math.sin(ang) + dy * math.cos(ang)
                    out.append((rx, ry))
            return out
        return pts

    def _get_config(self):
        return PatternConfig(
            width=max(1, int(self.width.get())),
            height=max(1, int(self.height.get())),
            seed=self.seed.get().strip(),
            bg=self.bg.get().strip() or "#111111",
            palette_mode=self.palette_mode.get(),
            shape_density=float(self.shape_density.get()),
            symmetry=self.symmetry.get(),
            grid_size=max(4, int(self.grid_size.get())),
            complexity=float(self.complexity.get()),
            use_noise=bool(self.use_noise.get()),
            use_lines=bool(self.use_lines.get()),
            use_circles=bool(self.use_circles.get()),
            use_blocks=bool(self.use_blocks.get()),
            use_triangles=bool(self.use_triangles.get()),
            use_gradients=bool(self.use_gradients.get()),
            export_svg=bool(self.export_svg.get()),
            noise_scale=float(self.noise_scale.get()),
            noise_amp=float(self.noise_amp.get()),
            noise_octaves=max(1, int(self.noise_octaves.get())),
            blur_amount=float(self.blur_amount.get()),
            aspect_mode=self.aspect_mode.get(),
        )

    def _prepare_rng(self, cfg):
        seed_txt = cfg.seed
        return random.Random(seed_txt if seed_txt else None)

    def _make_noise(self, cfg, rng):
        if not cfg.use_noise or OpenSimplex is None:
            return None
        try:
            noise_seed = int(cfg.seed) if cfg.seed.isdigit() else rng.randint(0, 10 ** 9)
        except Exception:
            noise_seed = rng.randint(0, 10 ** 9)
        return OpenSimplex(noise_seed)

    def _draw_background(self, d, bg_rgba, cfg):
        if not cfg.use_gradients:
            return
        w, h = cfg.width, cfg.height
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(bg_rgba[0] * (1 - t))
            g = int(bg_rgba[1] * (1 - t))
            b = int(bg_rgba[2] * (1 - t))
            d.line((0, y, w, y), fill=(r, g, b, 24))

    def _draw_flow_layer(self, d, cfg, rng, pal, noise_gen):
        if not cfg.use_noise or noise_gen is None:
            return

        w, h = cfg.width, cfg.height
        count = max(8, int(cfg.grid_size * cfg.grid_size * 0.18 * cfg.complexity))
        for _ in range(count):
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            pts = [(x, y)]
            steps = rng.randint(10, 34)
            step_len = rng.uniform(8, 24)
            for _ in range(steps):
                n = self.noise_value(x, y, noise_gen, cfg.noise_scale, cfg.noise_octaves)
                ang = (n * math.tau * 2.2) + rng.uniform(-0.3, 0.3)
                x += math.cos(ang) * step_len
                y += math.sin(ang) * step_len
                if x < 0 or x > w or y < 0 or y > h:
                    break
                pts.append((x, y))
            if len(pts) > 1:
                c = rng.choice(pal)
                alpha = rng.randint(40, 120)
                width = max(1, int(rng.uniform(1, 4 + cfg.complexity * 3)))
                d.line(pts, fill=(c[0], c[1], c[2], alpha), width=width, joint="curve")

    def _draw_shape_layer(self, d, cfg, rng, pal, noise_gen):
        w, h = cfg.width, cfg.height
        grid = cfg.grid_size
        step_x = w / grid
        step_y = h / grid
        density = cfg.shape_density
        complexity = cfg.complexity

        for gy in range(grid):
            for gx in range(grid):
                if rng.random() > density:
                    continue

                x0 = gx * step_x
                y0 = gy * step_y
                x1 = x0 + step_x
                y1 = y0 + step_y
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2

                n = self.noise_value(cx, cy, noise_gen, cfg.noise_scale, cfg.noise_octaves)
                cx = max(0, min(w, cx + n * cfg.noise_amp))
                cy = max(0, min(h, cy + n * cfg.noise_amp))

                shapes = []
                if cfg.use_blocks:
                    shapes.append("block")
                if cfg.use_circles:
                    shapes.append("circle")
                if cfg.use_lines:
                    shapes.append("line")
                if cfg.use_triangles:
                    shapes.append("tri")
                if not shapes:
                    shapes = ["block"]

                shape = rng.choice(shapes)
                c = rng.choice(pal)
                alpha = rng.randint(80, 220)
                fill = (c[0], c[1], c[2], alpha)

                if shape == "block":
                    pad = rng.uniform(0.02, 0.34) * min(step_x, step_y)
                    rr = rng.uniform(0, 28) * (0.35 + complexity * 0.65)
                    box = (x0 + pad, y0 + pad, x1 - pad, y1 - pad)
                    d.rounded_rectangle(box, radius=rr, fill=fill)

                elif shape == "circle":
                    r = min(step_x, step_y) * rng.uniform(0.12, 0.5)
                    box = (cx - r, cy - r, cx + r, cy + r)
                    d.ellipse(box, fill=fill)

                elif shape == "line":
                    pts = [
                        (x0 + rng.random() * step_x, y0 + rng.random() * step_y)
                        for _ in range(2 + int(complexity * 6))
                    ]
                    pts = self.add_symmetry(pts, w, h)
                    width = max(1, int(rng.uniform(1, 7)))
                    d.line(pts, fill=fill, width=width)

                elif shape == "tri":
                    pts = [
                        (cx, y0 + rng.random() * step_y),
                        (x0 + rng.random() * step_x, y1 - rng.random() * step_y * 0.1),
                        (x1 - rng.random() * step_x, y1 - rng.random() * step_y * 0.1),
                    ]
                    d.polygon(pts, fill=fill)

                if rng.random() < 0.18 * complexity:
                    for _ in range(rng.randint(1, 3)):
                        ox = cx + rng.randint(-int(step_x * 0.2), int(step_x * 0.2))
                        oy = cy + rng.randint(-int(step_y * 0.2), int(step_y * 0.2))
                        rr = rng.randint(2, int(max(3, min(step_x, step_y) * 0.08)))
                        dot = (ox - rr, oy - rr, ox + rr, oy + rr)
                        d.ellipse(dot, fill=(255, 255, 255, rng.randint(25, 110)))

    def _draw_accent_layer(self, d, cfg, rng, pal):
        w, h = cfg.width, cfg.height
        accent_count = max(10, int(cfg.grid_size * cfg.complexity * 2.5))
        for _ in range(accent_count):
            c = rng.choice(pal)
            alpha = rng.randint(20, 100)
            fill = (c[0], c[1], c[2], alpha)
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            kind = rng.choice(["dot", "ring", "chip"])
            if kind == "dot":
                r = rng.uniform(1, 8)
                d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
            elif kind == "ring":
                r = rng.uniform(5, 22)
                d.ellipse((x - r, y - r, x + r, y + r), outline=fill, width=max(1, int(rng.uniform(1, 3))))
            else:
                ww = rng.uniform(6, 36)
                hh = rng.uniform(3, 18)
                d.rounded_rectangle((x - ww / 2, y - hh / 2, x + ww / 2, y + hh / 2), radius=min(8, hh / 2), fill=fill)

    def _draw_layers(self, d, cfg, rng, pal, noise_gen, bg_rgba):
        self._draw_background(d, bg_rgba, cfg)
        self._draw_flow_layer(d, cfg, rng, pal, noise_gen)
        self._draw_shape_layer(d, cfg, rng, pal, noise_gen)
        self._draw_accent_layer(d, cfg, rng, pal)

    def _preview(self):
        if self.img is None:
            return
        preview = self.img.copy()
        preview.thumbnail(self._preview_size)
        self.photo = ImageTk.PhotoImage(preview)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            preview.width // 2,
            preview.height // 2,
            anchor="center",
            image=self.photo,
        )

    def generate(self):
        cfg = self._get_config()
        rng = self._prepare_rng(cfg)
        bg_rgba = self.hex_to_rgba(cfg.bg)
        pal = self.palette(rng)
        noise_gen = self._make_noise(cfg, rng)

        self.img = Image.new("RGBA", (cfg.width, cfg.height), bg_rgba)
        d = ImageDraw.Draw(self.img, "RGBA")
        self.elements = []

        self._draw_layers(d, cfg, rng, pal, noise_gen, bg_rgba)

        if cfg.blur_amount > 0:
            self.img = self.img.filter(ImageFilter.GaussianBlur(cfg.blur_amount))

        self._preview()

    def save_png(self):
        if self.img is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile="pattern.png",
        )
        if path:
            self.img.save(path)

    def save_svg(self):
        if not self.export_svg.get():
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG", "*.svg")],
            initialfile="pattern.svg",
        )
        if not path or self.img is None:
            return

        w, h = int(self.width.get()), int(self.height.get())
        bg = self.bg.get().strip() or "#111111"
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<rect width="100%" height="100%" fill="{bg}"/>'
        ]

        parts.append("</svg>")
        Path(path).write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    app = PatternGen(root)
    root.mainloop()
