from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from .generator import PatternConfig, PatternRenderer


def pil_to_qimage(image) -> QImage:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = rgba.tobytes("raw", "RGBA")
    return QImage(data, width, height, width * 4, QImage.Format_RGBA8888).copy()


class WorkerSignals(QObject):
    finished = Signal(object, int)
    failed = Signal(str, int)


class RenderTask(QRunnable):
    def __init__(self, renderer, config, generation_id):
        super().__init__()
        self.renderer = renderer
        self.config = config
        self.generation_id = generation_id
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            self.signals.finished.emit(self.renderer.generate(self.config), self.generation_id)
        except Exception as exc:
            self.signals.failed.emit(str(exc), self.generation_id)


class Slider(QWidget):
    valueChanged = Signal(float)

    def __init__(self, minimum, maximum, value, decimals=2, step=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step or max((maximum - minimum) / 100, 0.0001))
        self.spin.setValue(value)
        layout.addWidget(self.spin)
        self.spin.valueChanged.connect(self.valueChanged)

    def value(self):
        return self.spin.value()

    def setValue(self, value):
        self.spin.setValue(value)


class Preview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(500, 380)
        self.setFrameShape(QFrame.StyledPanel)
        self._image = None
        self.setText("Generate a pattern")

    def set_image(self, image):
        self._image = image
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        if self._image is None:
            return
        self.setPixmap(QPixmap.fromImage(self._image).scaled(
            self.size() - QSize(20, 20), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class MainWindow(QMainWindow):
    APP_NAME = "eli_lab Pattern Generator"

    def __init__(self):
        super().__init__()
        self.renderer = PatternRenderer()
        self.pool = QThreadPool.globalInstance()
        self.result = None
        self.render_id = 0
        self.settings = QSettings("eli_lab", "PatternGenerator")
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(180)
        self.debounce.timeout.connect(self.generate)
        self.setWindowTitle(self.APP_NAME)
        self.resize(1540, 940)
        self.setMinimumSize(1140, 740)
        self._build_ui()
        self._build_menu()
        self._restore_geometry()
        self._connect_auto_preview()
        self.generate()

    def _group(self, title):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setContentsMargins(10, 10, 10, 10)
        form.setVerticalSpacing(7)
        return box, form

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        controls = QFrame(); controls.setObjectName("Controls")
        left = QVBoxLayout(controls); left.setContentsMargins(12, 12, 12, 12)
        title = QLabel("eli_lab / PATTERN GENERATOR"); title.setObjectName("Header"); left.addWidget(title)
        subtitle = QLabel("Procedural composition laboratory"); subtitle.setObjectName("SubHeader"); left.addWidget(subtitle)
        tabs = QTabWidget(); scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(tabs); left.addWidget(scroll, 1)
        tabs.addTab(self._composition_tab(), "Composition")
        tabs.addTab(self._field_tab(), "Field")
        tabs.addTab(self._geometry_tab(), "Geometry")
        tabs.addTab(self._color_tab(), "Color")
        tabs.addTab(self._layers_tab(), "Layers")
        tabs.addTab(self._behavior_tab(), "Behavior")
        root.addWidget(controls, 0)
        right = QVBoxLayout()
        self.preview = Preview(); right.addWidget(self.preview, 1)
        row = QHBoxLayout(); self.status = QLabel("Ready"); self.seed_label = QLabel("")
        row.addWidget(self.status); row.addStretch(1); row.addWidget(self.seed_label); right.addLayout(row)
        root.addLayout(right, 1)

    def _composition_tab(self):
        page = QWidget(); layout = QVBoxLayout(page)
        box, f = self._group("Canvas")
        self.width = QSpinBox(); self.width.setRange(64, 8192); self.width.setValue(1600)
        self.height = QSpinBox(); self.height.setRange(64, 8192); self.height.setValue(900)
        self.seed = QLineEdit(); self.seed.setPlaceholderText("Fixed seed = reproducible artwork")
        self.background = QLineEdit("#111111")
        self.aspect = QComboBox(); self.aspect.addItems(["custom", "square", "landscape", "portrait", "ultrawide"])
        self.symmetry = QComboBox(); self.symmetry.addItems(["none", "mirror", "radial", "grid"])
        self.palette_mode = QComboBox(); self.palette_mode.addItems(["random", "pastel", "neon", "earth", "mono", "ice", "ritual"])
        f.addRow("Width", self.width); f.addRow("Height", self.height); f.addRow("Seed", self.seed); f.addRow("Aspect", self.aspect); f.addRow("Symmetry", self.symmetry)
        bg = QHBoxLayout(); bg.addWidget(self.background); pick = QPushButton("Pick"); pick.clicked.connect(self.pick_background); bg.addWidget(pick); f.addRow("Background", bg)
        f.addRow("Palette", self.palette_mode)
        layout.addWidget(box)
        box, f = self._group("Spatial composition")
        self.composition_mode = QComboBox(); self.composition_mode.addItems(["balanced", "focal", "clustered", "edge", "diagonal"])
        self.focal_x = Slider(0, 1, .5, 2); self.focal_y = Slider(0, 1, .5, 2); self.focal_strength = Slider(0, 1, .6, 2)
        self.edge_bias = Slider(-1, 1, 0, 2); self.cluster_count = QSpinBox(); self.cluster_count.setRange(1, 24); self.cluster_count.setValue(4)
        self.cluster_strength = Slider(0, 1, .25, 2); self.spacing = Slider(0, 1, .15, 2); self.jitter = Slider(0, 1, .08, 2)
        f.addRow("Mode", self.composition_mode); f.addRow("Focal X", self.focal_x); f.addRow("Focal Y", self.focal_y); f.addRow("Focal strength", self.focal_strength)
        f.addRow("Edge bias", self.edge_bias); f.addRow("Cluster count", self.cluster_count); f.addRow("Cluster strength", self.cluster_strength); f.addRow("Spacing", self.spacing); f.addRow("Position jitter", self.jitter)
        layout.addWidget(box); layout.addStretch(1); return page

    def _field_tab(self):
        page = QWidget(); layout = QVBoxLayout(page)
        box, f = self._group("Vector field")
        self.field_mode = QComboBox(); self.field_mode.addItems(["none", "noise", "swirl", "vortex", "waves", "radial"])
        self.field_strength = Slider(0, 1.5, .65, 2); self.field_scale = Slider(.0005, .08, .012, 4); self.field_curvature = Slider(0, 1, .35, 2)
        self.field_steps = QSpinBox(); self.field_steps.setRange(4, 96); self.field_steps.setValue(24); self.field_step_size = Slider(1, 80, 18, 1); self.noise_octaves = QSpinBox(); self.noise_octaves.setRange(1, 8); self.noise_octaves.setValue(3)
        f.addRow("Field", self.field_mode); f.addRow("Strength", self.field_strength); f.addRow("Scale", self.field_scale); f.addRow("Curvature", self.field_curvature); f.addRow("Steps", self.field_steps); f.addRow("Step size", self.field_step_size); f.addRow("Octaves", self.noise_octaves)
        layout.addWidget(box)
        hint = QLabel("The same field drives flow lines and geometry drift. Curvature determines how strongly local direction replaces the previous direction."); hint.setWordWrap(True); layout.addWidget(hint); layout.addStretch(1); return page

    def _geometry_tab(self):
        page = QWidget(); layout = QVBoxLayout(page)
        box, f = self._group("Geometry")
        self.grid_size = QSpinBox(); self.grid_size.setRange(4, 64); self.grid_size.setValue(14); self.shape_scale = Slider(.05, 1.5, .72, 2); self.scale_variance = Slider(0, 1, .35, 2)
        self.rotation = Slider(0, 360, 0, 0, 1); self.rotation_jitter = Slider(0, 3.14, .7, 2); self.corner_roundness = Slider(0, 1, .35, 2); self.line_complexity = Slider(.05, 1, .55, 2); self.overlap = Slider(0, 1, .2, 2)
        for label,w in [("Grid",self.grid_size),("Shape scale",self.shape_scale),("Scale variance",self.scale_variance),("Rotation",self.rotation),("Rotation jitter",self.rotation_jitter),("Corner roundness",self.corner_roundness),("Line complexity",self.line_complexity),("Overlap",self.overlap)]: f.addRow(label,w)
        layout.addWidget(box)
        box, f = self._group("Primitive probability")
        self.use_blocks = QCheckBox("Blocks"); self.use_blocks.setChecked(True); self.block_weight = Slider(0,3,1,2)
        self.use_circles = QCheckBox("Circles"); self.use_circles.setChecked(True); self.circle_weight = Slider(0,3,1,2)
        self.use_lines = QCheckBox("Lines"); self.use_lines.setChecked(True); self.line_weight = Slider(0,3,1,2)
        self.use_triangles = QCheckBox("Triangles"); self.use_triangles.setChecked(True); self.triangle_weight = Slider(0,3,1,2)
        for cb,wt in [(self.use_blocks,self.block_weight),(self.use_circles,self.circle_weight),(self.use_lines,self.line_weight),(self.use_triangles,self.triangle_weight)]:
            row=QHBoxLayout(); row.addWidget(cb); row.addWidget(QLabel("weight")); row.addWidget(wt); f.addRow(row)
        layout.addWidget(box); layout.addStretch(1); return page

    def _color_tab(self):
        page=QWidget(); layout=QVBoxLayout(page); box,f=self._group("Color behavior")
        self.palette_size=QSpinBox(); self.palette_size.setRange(2,12); self.palette_size.setValue(6)
        self.saturation=Slider(0,1.5,1,2); self.contrast=Slider(0,1,.5,2); self.hue_jitter=Slider(0,1,.08,2); self.opacity_min=Slider(.05,1,.3,2); self.opacity_max=Slider(.05,1,.85,2); self.color_coherence=Slider(0,1,.6,2)
        for label,w in [("Palette size",self.palette_size),("Saturation",self.saturation),("Contrast",self.contrast),("Hue jitter",self.hue_jitter),("Opacity min",self.opacity_min),("Opacity max",self.opacity_max),("Color coherence",self.color_coherence)]: f.addRow(label,w)
        layout.addWidget(box); layout.addStretch(1); return page

    def _layers_tab(self):
        page=QWidget(); layout=QVBoxLayout(page); box,f=self._group("Depth & surface")
        self.layer_count=QSpinBox(); self.layer_count.setRange(1,8); self.layer_count.setValue(1); self.depth=Slider(0,1,.45,2); self.accent_density=Slider(0,1,.25,2); self.gradient=QCheckBox("Gradient background"); self.blur=Slider(0,12,0,1)
        f.addRow("Layer count",self.layer_count); f.addRow("Depth",self.depth); f.addRow("Accent density",self.accent_density); f.addRow("",self.gradient); f.addRow("Raster blur",self.blur)
        layout.addWidget(box); hint=QLabel("More layers add independent deterministic scales. Blur only affects PNG; SVG remains procedural vector geometry."); hint.setWordWrap(True); layout.addWidget(hint); layout.addStretch(1); return page

    def _behavior_tab(self):
        page=QWidget(); layout=QVBoxLayout(page); box,f=self._group("Controlled behavior")
        self.behavior=QComboBox(); self.behavior.addItems(["calm","organic","architectural","chaotic","ritual"]); self.mutation=Slider(0,1,.25,2); self.asymmetry=Slider(0,1,.35,2)
        f.addRow("Behavior preset",self.behavior); f.addRow("Mutation",self.mutation); f.addRow("Asymmetry",self.asymmetry)
        layout.addWidget(box); row=QHBoxLayout(); r=QPushButton("Randomize system"); r.clicked.connect(self.randomize); g=QPushButton("Generate"); g.clicked.connect(self.generate); row.addWidget(r); row.addWidget(g); layout.addLayout(row)
        hint=QLabel("Presets are parameter bundles. Start from a behavior, then push individual variables to make your own system."); hint.setWordWrap(True); layout.addWidget(hint); layout.addStretch(1); return page

    def _build_menu(self):
        menu=self.menuBar().addMenu("File")
        for text,slot in [("Save PNG",self.save_png),("Save SVG",self.save_svg),("Save preset",self.save_preset),("Load preset",self.load_preset)]:
            a=QAction(text,self); a.triggered.connect(slot); menu.addAction(a)
        menu.addSeparator(); a=QAction("Quit",self); a.triggered.connect(self.close); menu.addAction(a)

    def _connect_auto_preview(self):
        controls=[self.width,self.height,self.seed,self.background,self.aspect,self.symmetry,self.palette_mode,self.composition_mode,self.focal_x,self.focal_y,self.focal_strength,self.edge_bias,self.cluster_count,self.cluster_strength,self.spacing,self.jitter,self.field_mode,self.field_strength,self.field_scale,self.field_curvature,self.field_steps,self.field_step_size,self.noise_octaves,self.grid_size,self.shape_scale,self.scale_variance,self.rotation,self.rotation_jitter,self.corner_roundness,self.line_complexity,self.overlap,self.use_blocks,self.use_circles,self.use_lines,self.use_triangles,self.block_weight,self.circle_weight,self.line_weight,self.triangle_weight,self.palette_size,self.saturation,self.contrast,self.hue_jitter,self.opacity_min,self.opacity_max,self.color_coherence,self.layer_count,self.depth,self.accent_density,self.gradient,self.blur,self.behavior,self.mutation,self.asymmetry]
        for w in controls:
            if isinstance(w,QLineEdit): w.textChanged.connect(self._request)
            elif isinstance(w,QSpinBox): w.valueChanged.connect(self._request)
            elif isinstance(w,QComboBox): w.currentTextChanged.connect(self._request)
            elif isinstance(w,QCheckBox): w.toggled.connect(self._request)
            elif isinstance(w,Slider): w.valueChanged.connect(self._request)

    def _request(self,*_): self.debounce.start()

    def _config(self):
        return PatternConfig(width=self.width.value(),height=self.height.value(),seed=self.seed.text(),background=self.background.text(),composition_mode=self.composition_mode.currentText(),symmetry=self.symmetry.currentText(),focal_x=self.focal_x.value(),focal_y=self.focal_y.value(),focal_strength=self.focal_strength.value(),edge_bias=self.edge_bias.value(),cluster_count=self.cluster_count.value(),cluster_strength=self.cluster_strength.value(),spacing=self.spacing.value(),jitter=self.jitter.value(),field_mode=self.field_mode.currentText(),field_strength=self.field_strength.value(),field_scale=self.field_scale.value(),field_curvature=self.field_curvature.value(),field_steps=self.field_steps.value(),field_step_size=self.field_step_size.value(),noise_octaves=self.noise_octaves.value(),grid_size=self.grid_size.value(),shape_scale=self.shape_scale.value(),scale_variance=self.scale_variance.value(),rotation=self.rotation.value(),rotation_jitter=self.rotation_jitter.value(),corner_roundness=self.corner_roundness.value(),line_complexity=self.line_complexity.value(),overlap=self.overlap.value(),use_blocks=self.use_blocks.isChecked(),use_circles=self.use_circles.isChecked(),use_lines=self.use_lines.isChecked(),use_triangles=self.use_triangles.isChecked(),block_weight=self.block_weight.value(),circle_weight=self.circle_weight.value(),line_weight=self.line_weight.value(),triangle_weight=self.triangle_weight.value(),palette_mode=self.palette_mode.currentText(),palette_size=self.palette_size.value(),saturation=self.saturation.value(),contrast=self.contrast.value(),hue_jitter=self.hue_jitter.value(),opacity_min=min(self.opacity_min.value(),self.opacity_max.value()),opacity_max=max(self.opacity_min.value(),self.opacity_max.value()),color_coherence=self.color_coherence.value(),layer_count=self.layer_count.value(),depth=self.depth.value(),accent_density=self.accent_density.value(),gradient=self.gradient.isChecked(),blur=self.blur.value(),behavior=self.behavior.currentText(),mutation=self.mutation.value(),asymmetry=self.asymmetry.value())

    def generate(self):
        self.debounce.stop(); self.render_id+=1; self.status.setText("Rendering…")
        task=RenderTask(self.renderer,self._config(),self.render_id); task.signals.finished.connect(self._finished); task.signals.failed.connect(self._failed); self.pool.start(task)

    def _finished(self,result,render_id):
        if render_id!=self.render_id:return
        self.result=result; self.preview.set_image(pil_to_qimage(result.image)); self.seed_label.setText(f"seed: {result.seed}"); self.status.setText(f"Ready · {result.elapsed:.2f}s · {result.image.width}×{result.image.height}")

    def _failed(self,message,render_id):
        if render_id!=self.render_id:return
        self.status.setText("Generation failed"); QMessageBox.critical(self,self.APP_NAME,message)

    def pick_background(self):
        c=QColorDialog.getColor(QColor(self.background.text()),self,"Background color")
        if c.isValid(): self.background.setText(c.name())

    def randomize(self):
        self.seed.setText(str(random.randint(0,2**31-1))); self.behavior.setCurrentText(random.choice(["calm","organic","architectural","chaotic","ritual"])); self.composition_mode.setCurrentText(random.choice(["balanced","focal","clustered","edge","diagonal"])); self.symmetry.setCurrentText(random.choice(["none","mirror","radial","grid"])); self.field_mode.setCurrentText(random.choice(["noise","swirl","vortex","waves","radial"])); self.grid_size.setValue(random.randint(8,28))
        for w,lo,hi in [(self.shape_scale,.4,1.1),(self.scale_variance,.12,.8),(self.rotation,0,360),(self.overlap,.02,.65),(self.field_strength,.2,1.2),(self.field_curvature,.05,.95),(self.mutation,.02,.85),(self.asymmetry,0,.9),(self.cluster_strength,.02,.8),(self.focal_strength,0,.95)]: w.setValue(random.uniform(lo,hi))
        self.generate()

    def apply_aspect(self):
        mode=self.aspect.currentText(); ratios={"square":(1,1),"landscape":(16,9),"portrait":(9,16),"ultrawide":(21,9)}
        if mode in ratios:
            rw,rh=ratios[mode]; self.height.setValue(self.width.value() if mode=="square" else max(64,round(self.width.value()*rh/rw)))
        self.generate()

    def save_png(self):
        if self.result is None:return
        path,_=QFileDialog.getSaveFileName(self,"Save PNG","pattern.png","PNG (*.png)")
        if path:self.result.image.save(path)

    def save_svg(self):
        if self.result is None:return
        path,_=QFileDialog.getSaveFileName(self,"Save SVG","pattern.svg","SVG (*.svg)")
        if path:Path(path).write_text(self.result.svg,encoding="utf-8")

    def save_preset(self):
        path,_=QFileDialog.getSaveFileName(self,"Save preset","pattern-preset.json","JSON (*.json)")
        if path:Path(path).write_text(json.dumps(self._config().to_dict(),indent=2),encoding="utf-8")

    def load_preset(self):
        path,_=QFileDialog.getOpenFileName(self,"Load preset","","JSON (*.json)")
        if not path:return
        try:
            c=PatternConfig(**json.loads(Path(path).read_text(encoding="utf-8"))).normalized()
            self.width.setValue(c.width);self.height.setValue(c.height);self.seed.setText(c.seed);self.background.setText(c.background);self.symmetry.setCurrentText(c.symmetry);self.composition_mode.setCurrentText(c.composition_mode);self.focal_x.setValue(c.focal_x);self.focal_y.setValue(c.focal_y);self.focal_strength.setValue(c.focal_strength);self.edge_bias.setValue(c.edge_bias);self.cluster_count.setValue(c.cluster_count);self.cluster_strength.setValue(c.cluster_strength);self.spacing.setValue(c.spacing);self.jitter.setValue(c.jitter);self.field_mode.setCurrentText(c.field_mode);self.field_strength.setValue(c.field_strength);self.field_scale.setValue(c.field_scale);self.field_curvature.setValue(c.field_curvature);self.field_steps.setValue(c.field_steps);self.field_step_size.setValue(c.field_step_size);self.noise_octaves.setValue(c.noise_octaves);self.grid_size.setValue(c.grid_size);self.shape_scale.setValue(c.shape_scale);self.scale_variance.setValue(c.scale_variance);self.rotation.setValue(c.rotation);self.rotation_jitter.setValue(c.rotation_jitter);self.corner_roundness.setValue(c.corner_roundness);self.line_complexity.setValue(c.line_complexity);self.overlap.setValue(c.overlap);self.use_blocks.setChecked(c.use_blocks);self.use_circles.setChecked(c.use_circles);self.use_lines.setChecked(c.use_lines);self.use_triangles.setChecked(c.use_triangles);self.block_weight.setValue(c.block_weight);self.circle_weight.setValue(c.circle_weight);self.line_weight.setValue(c.line_weight);self.triangle_weight.setValue(c.triangle_weight);self.palette_mode.setCurrentText(c.palette_mode);self.palette_size.setValue(c.palette_size);self.saturation.setValue(c.saturation);self.contrast.setValue(c.contrast);self.hue_jitter.setValue(c.hue_jitter);self.opacity_min.setValue(c.opacity_min);self.opacity_max.setValue(c.opacity_max);self.color_coherence.setValue(c.color_coherence);self.layer_count.setValue(c.layer_count);self.depth.setValue(c.depth);self.accent_density.setValue(c.accent_density);self.gradient.setChecked(c.gradient);self.blur.setValue(c.blur);self.behavior.setCurrentText(c.behavior);self.mutation.setValue(c.mutation);self.asymmetry.setValue(c.asymmetry);self.generate()
        except Exception as exc:QMessageBox.critical(self,"Load preset",str(exc))

    def _restore_geometry(self):
        g=self.settings.value("geometry")
        if g is not None:self.restoreGeometry(g)

    def closeEvent(self,event):
        self.settings.setValue("geometry",self.saveGeometry());super().closeEvent(event)


def build_app():
    app=QApplication.instance() or QApplication(sys.argv); app.setApplicationName(MainWindow.APP_NAME); app.setOrganizationName("eli_lab"); app.setStyle("Fusion"); app.setStyleSheet("""
        QMainWindow,QWidget{background:#151515;color:#e9e9e9;} QFrame#Controls{background:#1c1c1c;border:1px solid #333;border-radius:8px;} QLabel#Header{font-size:16px;font-weight:700;letter-spacing:1px;} QLabel#SubHeader{color:#9b9b9b;} QGroupBox{border:1px solid #343434;border-radius:6px;margin-top:8px;padding-top:10px;} QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;} QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox{background:#101010;border:1px solid #3b3b3b;padding:5px;border-radius:4px;} QPushButton{background:#292929;border:1px solid #444;padding:7px 10px;border-radius:4px;} QPushButton:hover{background:#343434;}
    """); return app


def main():
    app=build_app(); window=MainWindow(); window.show(); return app.exec()


if __name__=="__main__": raise SystemExit(main())
