import random
import math
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
from PIL import Image, ImageDraw, ImageTk

class PatternGen:
    def __init__(self, root):
        self.root = root
        self.root.title("Semi-Random Pattern Generator")
        self.root.geometry("1100x760")
        self.root.minsize(900, 650)

        self.width = tk.IntVar(value=1400)
        self.height = tk.IntVar(value=1400)
        self.seed = tk.StringVar(value="")
        self.bg = tk.StringVar(value="#111111")
        self.palette_mode = tk.StringVar(value="random")
        self.shape_density = tk.DoubleVar(value=0.55)
        self.symmetry = tk.StringVar(value="none")
        self.grid_size = tk.IntVar(value=12)
        self.complexity = tk.DoubleVar(value=0.65)
        self.use_noise = tk.BooleanVar(value=True)
        self.use_lines = tk.BooleanVar(value=True)
        self.use_circles = tk.BooleanVar(value=True)
        self.use_blocks = tk.BooleanVar(value=True)
        self.use_triangles = tk.BooleanVar(value=True)
        self.use_gradients = tk.BooleanVar(value=False)

        self.img = None
        self.photo = None

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

        def add_entry(label, var, row):
            ttk.Label(controls, text=label).grid(row=row, column=0, sticky="w", pady=(6, 0))
            e = ttk.Entry(controls, textvariable=var, width=18)
            e.grid(row=row + 1, column=0, sticky="we")

        ttk.Label(controls, text="Pattern Generator", font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, pady=(0, 8), sticky="w"
        )
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
            values=["none", "mirror", "radial", "grid"],
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

        ttk.Label(controls, text="Elements").grid(row=19, column=0, sticky="w", pady=(8, 0))
        for i, (text, var) in enumerate(
            [
                ("Noise dots", self.use_noise),
                ("Lines", self.use_lines),
                ("Circles", self.use_circles),
                ("Blocks", self.use_blocks),
                ("Triangles", self.use_triangles),
                ("Gradients", self.use_gradients),
            ],
            start=20,
        ):
            ttk.Checkbutton(controls, text=text, variable=var).grid(row=i, column=0, sticky="w")

        btns = ttk.Frame(controls)
        btns.grid(row=26, column=0, pady=12, sticky="we")
        ttk.Button(btns, text="Generate", command=self.generate).pack(side="left", fill="x", expand=True)
        ttk.Button(btns, text="Save PNG", command=self.save).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(btns, text="Randomize", command=self.randomize).pack(side="left", fill="x", expand=True)

    def pick_bg(self):
        c = colorchooser.askcolor(self.bg.get())[1]
        if c:
            self.bg.set(c)

    def randomize(self):
        self.seed.set(str(random.randint(0, 10**9)))
        self.palette_mode.set(random.choice(["random", "pastel", "neon", "earth", "mono"]))
        self.symmetry.set(random.choice(["none", "mirror", "radial", "grid"]))
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

        bg = self.bg.get() or "#111111"
        self.img = Image.new("RGBA", (w, h), bg)
        d = ImageDraw.Draw(self.img, "RGBA")
        pal = self.palette(rng)

        grid = max(4, int(self.grid_size.get()))
        step_x = w / grid
        step_y = h / grid
        density = float(self.shape_density.get())
        complexity = float(self.complexity.get())

        if self.use_gradients.get():
            for y in range(h):
                d.line((0, y, w, y), fill=(255, 255, 255, 4))

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
                    pad = rng.uniform(0.05, 0.35) * min(step_x, step_y)
                    d.rounded_rectangle(
                        (x0 + pad, y0 + pad, x1 - pad, y1 - pad),
                        radius=rng.uniform(0, 30),
                        fill=fill,
                    )

                elif shape == "circle":
                    r = min(step_x, step_y) * rng.uniform(0.15, 0.48)
                    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)

                elif shape == "line":
                    pts = [
                        (x0 + rng.random() * step_x, y0 + rng.random() * step_y)
                        for _ in range(2 + int(complexity * 5))
                    ]
                    pts = self.add_symmetry(pts, w, h)
                    d.line(pts, fill=fill, width=max(1, int(rng.uniform(1, 8))))

                elif shape == "tri":
                    pts = [
                        (cx, y0 + rng.random() * step_y),
                        (x0 + rng.random() * step_x, y1 - rng.random() * step_y * 0.1),
                        (x1 - rng.random() * step_x, y1 - rng.random() * step_y * 0.1),
                    ]
                    d.polygon(pts, fill=fill)

                if rng.random() < 0.22 * complexity:
                    for _ in range(rng.randint(1, 3)):
                        ox = cx + rng.randint(-int(step_x * 0.2), int(step_x * 0.2))
                        oy = cy + rng.randint(-int(step_y * 0.2), int(step_y * 0.2))
                        rr = rng.randint(2, int(max(3, min(step_x, step_y) * 0.08)))
                        d.ellipse((ox - rr, oy - rr, ox + rr, oy + rr), fill=(255, 255, 255, rng.randint(30, 110)))

        if self.use_noise.get():
            count = int(w * h * 0.0015 * density)
            for _ in range(count):
                x = rng.randint(0, w - 1)
                y = rng.randint(0, h - 1)
                v = rng.randint(150, 255)
                d.point((x, y), fill=(v, v, v, rng.randint(30, 120)))

        self._preview()

    def _preview(self):
        if self.img is None:
            return
        preview = self.img.copy()
        preview.thumbnail((780, 720))
        self.photo = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        self.canvas.config(width=preview.width, height=preview.height)
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

    def save(self):
        if self.img is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            initialfile="pattern.png",
        )
        if path:
            self.img.save(path)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    app = PatternGen(root)
    root.mainloop()