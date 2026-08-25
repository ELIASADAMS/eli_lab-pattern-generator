import math
import random
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser

from PIL import Image, ImageDraw, ImageTk, ImageFilter

try:
    from opensimplex import OpenSimplex
except Exception:
    OpenSimplex = None


class PatternGen:
    def __init__(self, root):
        self.root = root
        self.root.title("Semi-Random Pattern Generator")
        self.root.geometry("1120x780")
        self.root.minsize(960, 680)

        self.width = tk.IntVar(value=1600)
        self.height = tk.IntVar(value=1600)
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

        self.img = None
        self.photo = None
        self.elements = []

        self._build_ui()
        self.generate()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        controls = ttk.Frame(main)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        canvas_frame = ttk.Frame(main)
        canvas_frame.grid(row=0, column=1, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#222", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        ttk.Label(controls, text="Pattern Generator", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, pady=(0, 8), sticky="w"
        )

        def add_entry(label, var, row):
            ttk.Label(controls, text=label).grid(row=row, column=0, sticky="w", pady=(6, 0))
            ttk.Entry(controls, textvariable=var, width=18).grid(row=row + 1, column=0, sticky="we")

        add_entry("Width", self.width, 1)
        add_entry("Height", self.height, 3)
        add_entry("Seed", self.seed, 5)

        ttk.Label(controls, text="Background").grid(row=7, column=0, sticky="w", pady=(6, 0))
        bg_row = ttk.Frame(controls)
        bg_row.grid(row=8, column=0, sticky="we")
        ttk.Entry(bg_row, textvariable=self.bg, width=14).pack(side="left", fill="x", expand=True)
        ttk.Button(bg_row, text="Pick", command=self.pick_bg).pack(side="left", padx=4)

        ttk.Label(controls, text="Palette mode").grid(row=9, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            controls,
            textvariable=self.palette_mode,
            values=["random", "pastel", "neon", "earth", "mono"],
            state="readonly",
            width=16,
        ).grid(row=10, column=0, sticky="we")

        ttk.Label(controls, text="Symmetry").grid(row=11, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            controls,
            textvariable=self.symmetry,
            values=["none", "mirror", "radial"],
            state="readonly",
            width=16,
        ).grid(row=12, column=0, sticky="we")

        ttk.Label(controls, text="Density").grid(row=13, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0.05, to=1.0, variable=self.shape_density, orient="horizontal").grid(
            row=14, column=0, sticky="we"
        )

        ttk.Label(controls, text="Complexity").grid(row=15, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0.1, to=1.0, variable=self.complexity, orient="horizontal").grid(
            row=16, column=0, sticky="we"
        )

        ttk.Label(controls, text="Grid size").grid(row=17, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=4, to=40, variable=self.grid_size, orient="horizontal").grid(
            row=18, column=0, sticky="we"
        )

        ttk.Label(controls, text="Noise scale").grid(row=19, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0.001, to=0.05, variable=self.noise_scale, orient="horizontal").grid(
            row=20, column=0, sticky="we"
        )

        ttk.Label(controls, text="Noise amplitude").grid(row=21, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0, to=180, variable=self.noise_amp, orient="horizontal").grid(
            row=22, column=0, sticky="we"
        )

        ttk.Label(controls, text="Noise octaves").grid(row=23, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=1, to=6, variable=self.noise_octaves, orient="horizontal").grid(
            row=24, column=0, sticky="we"
        )

        ttk.Label(controls, text="Blur").grid(row=25, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0.0, to=4.0, variable=self.blur_amount, orient="horizontal").grid(
            row=26, column=0, sticky="we"
        )

        ttk.Label(controls, text="Elements").grid(row=27, column=0, sticky="w", pady=(8, 0))
        for i, (text, var) in enumerate(
                [
                    ("Noise flow", self.use_noise),
                    ("Lines", self.use_lines),
                    ("Circles", self.use_circles),
                    ("Blocks", self.use_blocks),
                    ("Triangles", self.use_triangles),
                    ("Gradients", self.use_gradients),
                    ("Export SVG", self.export_svg),
                ],
                start=28,
        ):
            ttk.Checkbutton(controls, text=text, variable=var).grid(row=i, column=0, sticky="w")

        btns = ttk.Frame(controls)
        btns.grid(row=36, column=0, pady=12, sticky="we")
        ttk.Button(btns, text="Generate", command=self.generate).pack(side="left", fill="x", expand=True)
        ttk.Button(btns, text="Save PNG", command=self.save_png).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(btns, text="Save SVG", command=self.save_svg).pack(side="left", fill="x", expand=True)
        ttk.Button(controls, text="Randomize", command=self.randomize).grid(row=37, column=0, sticky="we")

    def pick_bg(self):
        c = colorchooser.askcolor(self.bg.get())[1]
        if c:
            self.bg.set(c)

    def randomize(self):
        self.seed.set(str(random.randint(0, 10 ** 9)))
        self.palette_mode.set(random.choice(["random", "pastel", "neon", "earth", "mono"]))
        self.symmetry.set(random.choice(["none", "mirror", "radial"]))
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

    def generate(self):
        w, h = int(self.width.get()), int(self.height.get())
        seed_txt = self.seed.get().strip()
        rng = random.Random(seed_txt if seed_txt else None)
        bg_rgba = self.hex_to_rgba(self.bg.get())

        self.img = Image.new("RGBA", (w, h), bg_rgba)
        d = ImageDraw.Draw(self.img, "RGBA")
        pal = self.palette(rng)
        grid = max(4, int(self.grid_size.get()))
        step_x = w / grid
        step_y = h / grid
        density = float(self.shape_density.get())
        complexity = float(self.complexity.get())

        noise_gen = None
        if self.use_noise.get() and OpenSimplex is not None:
            try:
                noise_seed = int(seed_txt) if seed_txt.isdigit() else rng.randint(0, 10 ** 9)
            except Exception:
                noise_seed = rng.randint(0, 10 ** 9)
            noise_gen = OpenSimplex(noise_seed)

        if self.use_gradients.get():
            for y in range(h):
                t = y / max(1, h - 1)
                r = int(bg_rgba[0] * (1 - t))
                g = int(bg_rgba[1] * (1 - t))
                b = int(bg_rgba[2] * (1 - t))
                d.line((0, y, w, y), fill=(r, g, b, 24))

        self.elements = []
        scale = float(self.noise_scale.get())
        amp = float(self.noise_amp.get())
        octaves = int(self.noise_octaves.get())

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

                n = self.noise_value(cx, cy, noise_gen, scale, octaves)
                cx += n * amp
                cy += n * amp
                cx = max(0, min(w, cx))
                cy = max(0, min(h, cy))

                shapes = []
                if self.use_blocks.get():
                    shapes.append("block")
                if self.use_circles.get():
                    shapes.append("circle")
                if self.use_lines.get():
                    shapes.append("line")
                if self.use_triangles.get():
                    shapes.append("tri")
                if not shapes:
                    shapes = ["block"]

                shape = rng.choice(shapes)
                c = rng.choice(pal)
                alpha = rng.randint(80, 220)
                fill = (c[0], c[1], c[2], alpha)

                if shape == "block":
                    pad = rng.uniform(0.02, 0.34) * min(step_x, step_y)
                    rr = rng.uniform(0, 28)
                    box = (x0 + pad, y0 + pad, x1 - pad, y1 - pad)
                    d.rounded_rectangle(box, radius=rr, fill=fill)
                    self.elements.append(("rect", box, fill, rr))

                elif shape == "circle":
                    r = min(step_x, step_y) * rng.uniform(0.12, 0.5)
                    box = (cx - r, cy - r, cx + r, cy + r)
                    d.ellipse(box, fill=fill)
                    self.elements.append(("circle", box, fill, None))

                elif shape == "line":
                    pts = [
                        (x0 + rng.random() * step_x, y0 + rng.random() * step_y)
                        for _ in range(2 + int(complexity * 6))
                    ]
                    pts = self.add_symmetry(pts, w, h)
                    width = max(1, int(rng.uniform(1, 7)))
                    d.line(pts, fill=fill, width=width)
                    self.elements.append(("line", pts, fill, width))

                elif shape == "tri":
                    pts = [
                        (cx, y0 + rng.random() * step_y),
                        (x0 + rng.random() * step_x, y1 - rng.random() * step_y * 0.1),
                        (x1 - rng.random() * step_x, y1 - rng.random() * step_y * 0.1),
                    ]
                    d.polygon(pts, fill=fill)
                    self.elements.append(("polygon", pts, fill, None))

                if rng.random() < 0.18 * complexity:
                    for _ in range(rng.randint(1, 3)):
                        ox = cx + rng.randint(-int(step_x * 0.2), int(step_x * 0.2))
                        oy = cy + rng.randint(-int(step_y * 0.2), int(step_y * 0.2))
                        rr = rng.randint(2, int(max(3, min(step_x, step_y) * 0.08)))
                        dot = (ox - rr, oy - rr, ox + rr, oy + rr)
                        d.ellipse(dot, fill=(255, 255, 255, rng.randint(25, 110)))
                        self.elements.append(("circle", dot, (255, 255, 255, 90), None))

        if self.blur_amount.get() > 0:
            self.img = self.img.filter(ImageFilter.GaussianBlur(self.blur_amount.get()))

        self._preview()

    def _preview(self):
        preview = self.img.copy()
        preview.thumbnail((820, 760))
        self.photo = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        self.canvas.config(width=preview.width, height=preview.height)
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

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
        if not self.export_svg.get() or not self.elements:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG", "*.svg")],
            initialfile="pattern.svg",
        )
        if not path:
            return

        w, h = int(self.width.get()), int(self.height.get())
        bg = self.bg.get().strip() or "#111111"

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<rect width="100%" height="100%" fill="{bg}"/>'
        ]

        for kind, data, fill, extra in self.elements:
            color = self.svg_color(fill)
            opacity = fill[3] / 255.0

            if kind == "rect":
                x0, y0, x1, y1 = data
                rx = extra or 0
                parts.append(
                    f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{(x1 - x0):.2f}" height="{(y1 - y0):.2f}" '
                    f'rx="{rx:.2f}" ry="{rx:.2f}" fill="{color}" fill-opacity="{opacity:.3f}"/>'
                )

            elif kind == "circle":
                x0, y0, x1, y1 = data
                cx = (x0 + x1) / 2
                cy = (y0 + y1) / 2
                r = min((x1 - x0), (y1 - y0)) / 2
                parts.append(
                    f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{color}" fill-opacity="{opacity:.3f}"/>'
                )

            elif kind == "polygon":
                pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in data)
                parts.append(
                    f'<polygon points="{pts}" fill="{color}" fill-opacity="{opacity:.3f}"/>'
                )

            elif kind == "line":
                pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in data)
                parts.append(
                    f'<polyline points="{pts}" fill="none" stroke="{color}" '
                    f'stroke-opacity="{opacity:.3f}" stroke-width="{extra:.2f}" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                )

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
