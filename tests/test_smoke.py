"""
Smoke tests for DataLens AI Phase 0 scaffold.

Verifies that core modules import correctly, DatasetBundle works,
logging refuses DataFrames, and theme tokens/CSS are valid.
"""

import pytest
import pandas as pd


class TestImports:
    """Verify all core modules import without errors."""

    def test_import_state(self):
        from core.utils.state import DatasetBundle, FileMeta, TransformRecord
        assert DatasetBundle is not None
        assert FileMeta is not None
        assert TransformRecord is not None

    def test_import_logging(self):
        from core.utils.logging import get_logger, log_metadata, log_error, TimingContext
        assert get_logger is not None
        assert log_metadata is not None
        assert log_error is not None
        assert TimingContext is not None

    def test_import_theme_tokens(self):
        from ui.theme.tokens import (
            DARK_PALETTE, LIGHT_PALETTE, SPACING, RADIUS,
            FONT_SIZE, FONT_WEIGHT, TRANSITION, get_palette,
        )
        assert DARK_PALETTE is not None
        assert LIGHT_PALETTE is not None

    def test_import_theme_css(self):
        from ui.theme.css import generate_css, inject_css
        assert generate_css is not None
        assert inject_css is not None

    def test_import_pages(self):
        from ui.pages import (
            dashboard, upload, profile, quality, cleaning,
            exploratory, statistics, anomalies, correlations,
            kpis, insights, explorer, reports, settings,
        )
        # Verify each page has a page() function
        for module in [
            dashboard, upload, profile, quality, cleaning,
            exploratory, statistics, anomalies, correlations,
            kpis, insights, explorer, reports, settings,
        ]:
            assert hasattr(module, "page"), f"{module.__name__} missing page() function"
            assert callable(module.page)

    def test_page_registry_targets_exist(self):
        from pathlib import Path

        from ui.pages.registry import get_page_files

        required = ["home", "overview", "data_quality", "clean", "analysis", "report"]

        page_files = get_page_files()

        for key in required:
            assert key in page_files, f"Page registry missing {key}"
            page_path = page_files[key]
            assert Path(page_path).is_file(), f"Page target file missing for {key}: {page_path}"


class TestDatasetBundle:
    """Verify DatasetBundle creation and behavior."""

    def test_create_bundle(self):
        from core.utils.state import DatasetBundle, FileMeta

        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        meta = FileMeta(
            name="test.csv",
            size_bytes=100,
            rows=3,
            cols=2,
            extension=".csv",
        )
        bundle = DatasetBundle(
            original_df=df.copy(),
            working_df=df.copy(),
            file_meta=meta,
        )
        assert bundle.original_df.shape == (3, 2)
        assert bundle.working_df.shape == (3, 2)
        assert bundle.file_meta.name == "test.csv"
        assert bundle.is_demo is False
        assert bundle.transformation_history == []
        assert bundle.load_warnings == []
        assert bundle.profile is None
        assert bundle.quality_result is None

    def test_df_hash_deterministic(self):
        from core.utils.state import compute_df_hash

        df = pd.DataFrame({"x": [1, 2, 3]})
        h1 = compute_df_hash(df)
        h2 = compute_df_hash(df)
        assert h1 == h2

    def test_df_hash_different_for_different_data(self):
        from core.utils.state import compute_df_hash

        df1 = pd.DataFrame({"x": [1, 2, 3]})
        df2 = pd.DataFrame({"x": [4, 5, 6]})
        assert compute_df_hash(df1) != compute_df_hash(df2)


class TestLogging:
    """Verify logging sanitization."""

    def test_sanitize_dataframe(self):
        from core.utils.logging import _sanitize_value

        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        result = _sanitize_value(df)
        assert "DataFrame" in str(result)
        assert "shape" in str(result)
        # Should NOT contain actual data values
        assert "1" not in str(result) or "col1" in str(result)

    def test_sanitize_series(self):
        from core.utils.logging import _sanitize_value

        s = pd.Series([1, 2, 3], name="test")
        result = _sanitize_value(s)
        assert "Series" in str(result)
        assert "name=test" in str(result)

    def test_sanitize_plain_value(self):
        from core.utils.logging import _sanitize_value

        assert _sanitize_value(42) == 42
        assert _sanitize_value("hello") == "hello"

    def test_get_logger(self):
        from core.utils.logging import get_logger

        logger = get_logger("test")
        assert logger.name == "datalens.test"

    def test_timing_context(self):
        import time
        from core.utils.logging import get_logger, TimingContext

        logger = get_logger("timing_test")
        with TimingContext(logger, "test_op") as ctx:
            time.sleep(0.01)
        assert ctx.duration >= 0.01


class TestTheme:
    """Verify theme tokens and CSS generation."""

    def test_dark_palette_has_all_fields(self):
        from ui.theme.tokens import DARK_PALETTE

        assert DARK_PALETTE.bg_primary == "#0E1117"
        assert DARK_PALETTE.accent_primary == "#4A9EFF"
        assert len(DARK_PALETTE.chart_colors) == 12

    def test_light_palette_has_all_fields(self):
        from ui.theme.tokens import LIGHT_PALETTE

        assert LIGHT_PALETTE.bg_primary == "#FFFFFF"
        assert LIGHT_PALETTE.accent_primary == "#2563EB"
        assert len(LIGHT_PALETTE.chart_colors) == 12

    def test_get_palette(self):
        from ui.theme.tokens import get_palette, DARK_PALETTE, LIGHT_PALETTE

        assert get_palette("dark") is DARK_PALETTE
        assert get_palette("light") is LIGHT_PALETTE

    def test_generate_css_dark(self):
        from ui.theme.css import generate_css

        css = generate_css("dark")
        assert "<style>" in css
        assert "</style>" in css
        assert "#0E1117" in css  # dark bg
        assert "Inter" in css  # font family
        assert "fadeIn" in css  # animations

    def test_generate_css_light(self):
        from ui.theme.css import generate_css

        css = generate_css("light")
        assert "<style>" in css
        assert "#FFFFFF" in css  # light bg

    def test_css_contains_interactive_classes(self):
        from ui.theme.css import generate_css

        css = generate_css("dark")
        # Check for interactive component classes
        assert "animate-fade-in" in css
        assert "animate-slide-in" in css
        assert "datalens-card" in css
        assert "metric-card" in css
        assert "kpi-card" in css
        assert "score-ring" in css
        assert "severity-badge" in css
        assert "feature-card" in css
        assert "upload-zone" in css
        assert "empty-state" in css
        assert "hero-title" in css
        assert "privacy-notice" in css
        # Check animations exist
        assert "@keyframes fadeIn" in css
        assert "@keyframes pulse-critical" in css
        assert "@keyframes ringFill" in css
