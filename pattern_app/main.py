"""Application entry point for the eli_lab Pattern Generator."""

try:
    from .ui import MainWindow, build_app
except ImportError:  # pragma: no cover - direct execution compatibility
    from ui import MainWindow, build_app


def main() -> int:
    app = build_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
