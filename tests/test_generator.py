from pattern_app.generator import PatternConfig, PatternRenderer, hex_to_rgba


def test_hex_to_rgba():
    assert hex_to_rgba("#abc") == (170, 187, 204, 255)
    assert hex_to_rgba("112233") == (17, 34, 51, 255)


def test_config_normalization():
    config = PatternConfig(
        width=1,
        height=90000,
        grid_size=100,
        density=-1,
        blur=20,
        field_strength=9,
        palette_size=99,
        layer_count=99,
    ).normalized()
    assert config.width == 64
    assert config.height == 8192
    assert config.grid_size == 48
    assert config.density == 0.02
    assert config.blur == 12
    assert config.field_strength == 1.5
    assert config.palette_size == 12
    assert config.layer_count == 8


def test_seeded_generation_is_deterministic():
    renderer = PatternRenderer()
    config = PatternConfig(width=320, height=180, seed="12345", grid_size=8)
    first = renderer.generate(config)
    second = renderer.generate(config)
    assert first.seed == second.seed == "12345"
    assert first.image.tobytes() == second.image.tobytes()
    assert "<svg" in first.svg
    assert "<polyline" in first.svg or "<polygon" in first.svg or "<circle" in first.svg


def test_behavior_profiles_are_renderable():
    renderer = PatternRenderer()
    base = PatternConfig(width=180, height=120, seed="behavior-test", grid_size=7)
    for behavior in ("calm", "organic", "architectural", "chaotic", "ritual"):
        result = renderer.generate(PatternConfig(**{**base.to_dict(), "behavior": behavior}))
        assert result.image.size == (180, 120)
        assert result.seed == "behavior-test"
        assert result.svg.endswith("</svg>")


def test_symmetry_is_reproducible():
    renderer = PatternRenderer()
    for symmetry in ("none", "mirror", "grid", "radial"):
        config = PatternConfig(width=220, height=140, seed="symmetry", grid_size=6, symmetry=symmetry)
        first = renderer.generate(config)
        second = renderer.generate(config)
        assert first.image.tobytes() == second.image.tobytes()


def test_weighted_shape_configuration_is_valid():
    config = PatternConfig(
        seed="weights",
        use_blocks=True,
        use_circles=True,
        use_lines=True,
        use_triangles=True,
        block_weight=3,
        circle_weight=0,
        line_weight=1,
        triangle_weight=2,
    ).normalized()
    assert config.block_weight == 3
    assert config.circle_weight == 0
    assert config.line_weight == 1
    assert config.triangle_weight == 2
