from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL.ImageQt import ImageQt
from PySide6.QtCore import QObject, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from .generator import PatternConfig, PatternRenderer
except ImportError:  # pragma: no cover - supports ``python pattern_app/main.py``
    from generator import PatternConfig, PatternRenderer


class WorkerSignals(QObject):
    finished = Signal(object, int)
    failed = Signal(str, int)


class RenderTask(QRunnable):
    def __init__(self, renderer: PatternRenderer, config: PatternConfig, generation_id: int):
        super().__init__()
        self.renderer = renderer
        self.config = config
        self.generation_id = generation_id
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.renderer.generate(self.config)
            self.signals.finished.emit(result, self.generation_id)
        except Exception as exc:  # pragma: no cover
            self.signals.failed.emit(str(exc), self.generation_id)


class LabeledSlider(QWidget):
    valueChanged = Signal(float)

    def __init__(self, minimum: float, maximum: float, value: float, decimals: int = 2, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(52)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.value_label)
        self._min, self._max, self._decimals = minimum, maximum, decimals
        self.slider.valueChanged.connect(self._on_slider)
        self.setValue(value)

    def _on_slider(self, raw: int):
        value = self.value()
        self.value_label.setText(f"{value:.{self._decimals}f}")
        self.valueChanged.emit(value)

    def value(self) -> float:
        return self._min + (self._max - self._min) * self.slider.value() / 1000

    def setValue(self, value: float):
        normalized = (float(value) - self._min) / (self._max - self._min)
        self.slider.setValue(int(max(0, min(1, normalized)) * 1000))
        self._on_slider(self.slider.value())


class PreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setFrameShape(QFrame.StyledPanel)
        self.setText("Generate a pattern")
        self._image: QImage | None = None

    def set_image(self, image: QImage):
        self._image = image
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self):
        if self._image is None or self.width() <= 0 or self.height() <= 0:
            return
        pixmap = QPixmap.fromImage(self._image).scaled(
            self.size() - QSize(20, 20), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(pixmap)


class MainWindow(QMainWindow):
    APP_NAME = "eli_lab Pattern Generator"

    def __init__(self):
        super().__init__()
        self.renderer = PatternRenderer()
        self.pool = QThreadPool.globalInstance()
        self.current_result = None
        self.generation_id = 0
        self._settings = QSettings("EliLab", "PatternGenerator")
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(220)
        self._debounce.timeout.connect(self.generate)
        self.setWindowTitle(self.APP_NAME)
        self.resize(1500, 900)
        self.setMinimumSize(1100, 720)
        self._build_ui()
        self._build_menu()
        self._restore_window_state()
        self._wire_auto_preview()
        self.generate()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QFrame()
        left.setObjectName("ControlPanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        header = QLabel("ELI LAB / PATTERN GENERATOR")
        header.setObjectName("Header")
        left_layout.addWidget(header)
        sub = QLabel("Procedural image + SVG generator")
        sub.setObjectName("SubHeader")
        left_layout.addWidget(sub)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        tabs = QTabWidget()
        scroll.setWidget(tabs)
        left_layout.addWidget(scroll, 1)
        tabs.addTab(self._core_tab(), "Core")
        tabs.addTab(self._shape_tab(), "Shapes")
        tabs.addTab(self._noise_tab(), "Noise")
        tabs.addTab(self._effect_tab(), "Effects")
        tabs.addTab(self._export_tab(), "Export")
        root.addWidget(left, 0)

        preview_frame = QFrame()
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = PreviewWidget()
        preview_layout.addWidget(self.preview, 1)
        status_row = QHBoxLayout()
        self.status = QLabel("Ready")
        self.seed_status = QLabel("")
        status_row.addWidget(self.status)
        status_row.addStretch(1)
        status_row.addWidget(self.seed_status)
        preview_layout.addLayout(status_row)
        root.addWidget(preview_frame, 1)

    @staticmethod
    def _group(title: str):
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setContentsMargins(10, 10, 10, 10)
        form.setVerticalSpacing(8)
        return box, form

    def _core_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        box, form = self._group("Canvas")
        self.width = QSpinBox(); self.width.setRange(64, 8192); self.width.setValue(1600)
        self.height = QSpinBox(); self.height.setRange(64, 8192); self.height.setValue(900)
        self.seed = QLineEdit(); self.seed.setPlaceholderText("Leave blank for a fresh seed")
        self.background = QLineEdit("#111111")
        self.aspect = QComboBox(); self.aspect.addItems(["custom", "square", "landscape", "portrait", "ultrawide"])
        aspect_apply = QPushButton("Apply aspect"); aspect_apply.clicked.connect(self.apply_aspect)
        bg_pick = QPushButton("Pick"); bg_pick.clicked.connect(self.pick_background)
        bg_row = QHBoxLayout(); bg_row.addWidget(self.background); bg_row.addWidget(bg_pick)
        form.addRow("Width", self.width); form.addRow("Height", self.height); form.addRow("Seed", self.seed)
        form.addRow("Aspect", self.aspect); form.addRow("", aspect_apply); form.addRow("Background", bg_row)
        self.palette = QComboBox(); self.palette.addItems(["random", "pastel", "neon", "earth", "mono"])
        self.symmetry = QComboBox(); self.symmetry.addItems(["none", "mirror", "radial", "grid"])
        form.addRow("Palette", self.palette); form.addRow("Symmetry", self.symmetry)
        layout.addWidget(box)
        box2, form2 = self._group("Generation")
        self.density = LabeledSlider(0.02, 1.0, 0.55, decimals=2)
        self.complexity = LabeledSlider(0.05, 1.0, 0.65, decimals=2)
        self.grid = LabeledSlider(4, 48, 14, decimals=0)
        form2.addRow("Density", self.density); form2.addRow("Complexity", self.complexity); form2.addRow("Grid", self.grid)
        self.auto_preview = QCheckBox("Auto preview"); self.auto_preview.setChecked(True)
        form2.addRow("", self.auto_preview)
        layout.addWidget(box2); layout.addStretch(1)
        return page

    def _shape_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        box, form = self._group("Primitive selection")
        self.use_blocks = QCheckBox("Blocks"); self.use_blocks.setChecked(True)
        self.use_circles = QCheckBox("Circles"); self.use_circles.setChecked(True)
        self.use_lines = QCheckBox("Lines"); self.use_lines.setChecked(True)
        self.use_triangles = QCheckBox("Triangles"); self.use_triangles.setChecked(True)
        for widget in (self.use_blocks, self.use_circles, self.use_lines, self.use_triangles): form.addRow("", widget)
        layout.addWidget(box)
        hint = QLabel("The generator chooses among enabled primitives per grid cell. Symmetry is applied to line geometry.")
        hint.setWordWrap(True); layout.addWidget(hint); layout.addStretch(1)
        return page

    def _noise_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        box, form = self._group("Flow field")
        self.use_noise = QCheckBox("Enable noise field"); self.use_noise.setChecked(True)
        self.noise_scale = LabeledSlider(0.0005, 0.08, 0.012, decimals=4)
        self.noise_amplitude = LabeledSlider(0, 240, 60, decimals=1)
        self.noise_octaves = QSpinBox(); self.noise_octaves.setRange(1, 8); self.noise_octaves.setValue(3)
        form.addRow("", self.use_noise); form.addRow("Scale", self.noise_scale); form.addRow("Amplitude", self.noise_amplitude); form.addRow("Octaves", self.noise_octaves)
        layout.addWidget(box); layout.addStretch(1)
        return page

    def _effect_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        box, form = self._group("Finish")
        self.gradient = QCheckBox("Gradient background")
        self.use_accents = QCheckBox("Accent marks"); self.use_accents.setChecked(True)
        self.blur = LabeledSlider(0, 12, 0, decimals=1)
        form.addRow("", self.gradient); form.addRow("", self.use_accents); form.addRow("Blur", self.blur)
        layout.addWidget(box)
        randomize = QPushButton("Randomize parameters"); randomize.clicked.connect(self.randomize); layout.addWidget(randomize)
        layout.addStretch(1); return page

    def _export_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        self.generate_button = QPushButton("Generate"); self.generate_button.clicked.connect(self.generate)
        buttons = (
            self.generate_button,
            QPushButton("Save PNG"), QPushButton("Save SVG"), QPushButton("Save preset JSON"), QPushButton("Load preset JSON")
        )
        buttons[1].clicked.connect(self.save_png); buttons[2].clicked.connect(self.save_svg)
        buttons[3].clicked.connect(self.save_preset); buttons[4].clicked.connect(self.load_preset)
        for button in buttons: layout.addWidget(button)
        layout.addStretch(1); return page

    def _build_menu(self):
        menu = self.menuBar().addMenu("File")
        action = QAction("Save PNG", self); action.triggered.connect(self.save_png); menu.addAction(action)
        action = QAction("Save SVG", self); action.triggered.connect(self.save_svg); menu.addAction(action)
        menu.addSeparator()
        action = QAction("Quit", self); action.triggered.connect(self.close); menu.addAction(action)

    def _wire_auto_preview(self):
        widgets = [self.width, self.height, self.seed, self.background, self.palette, self.symmetry, self.grid, self.use_blocks, self.use_circles, self.use_lines, self.use_triangles, self.use_noise, self.noise_octaves, self.gradient, self.use_accents]
        for widget in widgets:
            if isinstance(widget, QLineEdit): widget.textChanged.connect(self._request_preview)
            elif isinstance(widget, QSpinBox): widget.valueChanged.connect(self._request_preview)
            elif isinstance(widget, QComboBox): widget.currentTextChanged.connect(self._request_preview)
            else: widget.toggled.connect(self._request_preview)
        for slider in (self.density, self.complexity, self.noise_scale, self.noise_amplitude, self.blur):
            slider.valueChanged.connect(lambda _value: self._request_preview())

    def _request_preview(self, *args):
        if self.auto_preview.isChecked(): self._debounce.start()

    def _config(self) -> PatternConfig:
        return PatternConfig(
            width=self.width.value(), height=self.height.value(), seed=self.seed.text(), background=self.background.text(),
            palette_mode=self.palette.currentText(), density=self.density.value(), complexity=self.complexity.value(),
            grid_size=round(self.grid.value()), symmetry=self.symmetry.currentText(), use_noise=self.use_noise.isChecked(),
            use_lines=self.use_lines.isChecked(), use_circles=self.use_circles.isChecked(), use_blocks=self.use_blocks.isChecked(),
            use_triangles=self.use_triangles.isChecked(), use_accents=self.use_accents.isChecked(), gradient=self.gradient.isChecked(),
            noise_scale=self.noise_scale.value(), noise_amplitude=self.noise_amplitude.value(), noise_octaves=self.noise_octaves.value(),
            blur=self.blur.value(),
        )

    @Slot()
    def generate(self):
        self._debounce.stop(); self.generation_id += 1
        task = RenderTask(self.renderer, self._config(), self.generation_id)
        self.status.setText("Rendering…"); self.generate_button.setEnabled(False)
        task.signals.finished.connect(self._render_finished); task.signals.failed.connect(self._render_failed)
        self.pool.start(task)

    @Slot(object, int)
    def _render_finished(self, result, generation_id: int):
        if generation_id != self.generation_id: return
        self.current_result = result
        self.seed_status.setText(f"seed: {result.seed}")
        self.preview.set_image(QImage(ImageQt(result.image).copy()))
        self.status.setText(f"Ready · {result.elapsed:.2f}s · {result.image.width}×{result.image.height}")
        self.generate_button.setEnabled(True)

    @Slot(str, int)
    def _render_failed(self, message: str, generation_id: int):
        if generation_id != self.generation_id: return
        self.status.setText("Generation failed"); self.generate_button.setEnabled(True)
        QMessageBox.critical(self, "Pattern Generator", message)

    def apply_aspect(self):
        mode = self.aspect.currentText(); ratios = {"square": (1, 1), "landscape": (16, 9), "portrait": (9, 16), "ultrawide": (21, 9)}
        if mode in ratios:
            rw, rh = ratios[mode]
            self.height.setValue(self.width.value() if mode == "square" else max(64, round(self.width.value() * rh / rw)))
        self.generate()

    def pick_background(self):
        color = QColorDialog.getColor(QColor(self.background.text()), self, "Background color")
        if color.isValid(): self.background.setText(color.name())

    def randomize(self):
        import random
        self.seed.setText(str(random.randint(0, 2**31 - 1)))
        self.palette.setCurrentText(random.choice(["random", "pastel", "neon", "earth", "mono"]))
        self.symmetry.setCurrentText(random.choice(["none", "mirror", "radial", "grid"]))
        self.density.setValue(random.uniform(0.25, 0.85)); self.complexity.setValue(random.uniform(0.3, 0.95))
        self.grid.setValue(random.randint(7, 28)); self.noise_scale.setValue(random.uniform(0.004, 0.03))
        self.noise_amplitude.setValue(random.uniform(20, 110)); self.noise_octaves.setValue(random.randint(2, 5))
        self.generate()

    def save_png(self):
        if self.current_result is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save PNG", "pattern.png", "PNG (*.png)")
        if path: self.current_result.image.save(path)

    def save_svg(self):
        if self.current_result is None: return
        path, _ = QFileDialog.getSaveFileName(self, "Save SVG", "pattern.svg", "SVG (*.svg)")
        if path: Path(path).write_text(self.current_result.svg, encoding="utf-8")

    def save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save preset", "pattern-preset.json", "JSON (*.json)")
        if path: Path(path).write_text(json.dumps(self._config().to_dict(), indent=2), encoding="utf-8")

    def load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load preset", "", "JSON (*.json)")
        if not path: return
        try:
            config = PatternConfig(**json.loads(Path(path).read_text(encoding="utf-8"))).normalized()
            self.width.setValue(config.width); self.height.setValue(config.height); self.seed.setText(config.seed)
            self.background.setText(config.background); self.palette.setCurrentText(config.palette_mode); self.density.setValue(config.density)
            self.complexity.setValue(config.complexity); self.grid.setValue(config.grid_size); self.symmetry.setCurrentText(config.symmetry)
            self.use_noise.setChecked(config.use_noise); self.use_lines.setChecked(config.use_lines); self.use_circles.setChecked(config.use_circles)
            self.use_blocks.setChecked(config.use_blocks); self.use_triangles.setChecked(config.use_triangles); self.use_accents.setChecked(config.use_accents)
            self.gradient.setChecked(config.gradient); self.noise_scale.setValue(config.noise_scale); self.noise_amplitude.setValue(config.noise_amplitude)
            self.noise_octaves.setValue(config.noise_octaves); self.blur.setValue(config.blur); self.generate()
        except Exception as exc:
            QMessageBox.critical(self, "Load preset", f"Could not load preset:\n{exc}")

    def _restore_window_state(self):
        geometry = self._settings.value("geometry")
        if geometry is not None: self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry()); super().closeEvent(event)


def build_app() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(MainWindow.APP_NAME); app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QWidget { background: #151515; color: #e9e9e9; }
        QFrame#ControlPanel { background: #1c1c1c; border: 1px solid #333; border-radius: 8px; }
        QLabel#Header { font-size: 16px; font-weight: 700; letter-spacing: 1px; }
        QLabel#SubHeader { color: #9b9b9b; }
        QGroupBox { border: 1px solid #343434; border-radius: 6px; margin-top: 8px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        QLineEdit, QSpinBox, QComboBox { background: #101010; border: 1px solid #3b3b3b; padding: 5px; border-radius: 4px; }
        QPushButton { background: #292929; border: 1px solid #444; padding: 7px 10px; border-radius: 4px; }
        QPushButton:hover { background: #343434; }
        QTabWidget::pane { border: 0; }
        QTabBar::tab { padding: 7px 12px; }
    """)
    return app


def main() -> int:
    app = build_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
