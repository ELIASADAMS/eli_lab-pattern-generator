"""Application entry point for the eli_lab Pattern Generator."""

from .ui import MainWindow, build_app


def main() -> int:
    app = build_app()
    window = MainWindow()
    window.aspect.currentTextChanged.connect(window._aspect_preview_changed)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
