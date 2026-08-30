from pattern_app.generator import PatternConfig, PatternRenderer, hex_to_rgba


def test_hex_to_rgba():
    assert hex_to_rgba("#abc") == (170, 187, 204, 255)
    assert hex_to_rgba("112233") == (17, 34, 51, 255)


def test_seeded_generation_is_deterministic():
    renderer = PatternRenderer()
    config = PatternConfig(width=320, height=180, seed="12345", grid_size=8)
    first = renderer.generate(config)
    second = renderer.generate(config)
    assert first.seed == second.seed == "12345"
    assert first.image.tobytes() == second.image.tobytes()
    assert "<svg" in first.svg
    assert "<polyline" in first.svg or "<rect" in first.svg


def test_config_normalization():
    config = PatternConfig(width=1, height=90000, grid_size=100, density=-1, blur=20).normalized()
    assert config.width == 64
    assert config.height == 8192
    assert config.grid_size == 48
    assert config.density == 0.02
    assert config.blur == 12
