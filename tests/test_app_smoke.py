from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "app.py"
PAGE_PATHS = {
    "home": "home",
    "overview": "overview",
    "data_quality": "data_quality",
    "clean": "cleaning",
    "analysis": "analysis",
    "report": "report",
}


def _demo_bundle():
    from core.utils.state import DatasetBundle, FileMeta
    from data.demo.generator import generate_demo_dataset

    df, _ = generate_demo_dataset()
    return DatasetBundle(
        original_df=df.copy(),
        working_df=df.copy(),
        file_meta=FileMeta(
            name="Synthetic Demo Dataset",
            size_bytes=int(df.memory_usage(deep=True).sum()),
            rows=len(df),
            cols=len(df.columns),
            extension=".csv",
        ),
        is_demo=True,
    )


def _render_page(page_key):
    from ui.pages import analysis, cleaning, data_quality, home, overview, report

    page_modules = {
        "home": home,
        "overview": overview,
        "data_quality": data_quality,
        "clean": cleaning,
        "analysis": analysis,
        "report": report,
    }
    page_modules[page_key].page()


def _page_app(page_key, bundle=None):
    app = AppTest.from_function(_render_page, args=(page_key,), default_timeout=30)
    if bundle is not None:
        app.session_state["datalens_dataset_bundle"] = bundle
    return app


def test_app_loads_without_exception():
    app = AppTest.from_file(str(APP_PATH)).run()

    assert not app.exception


def test_demo_button_loads_dataset_without_exception():
    app = AppTest.from_file(str(APP_PATH)).run(timeout=30)
    app.button(key="home_demo_btn").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["datalens_dataset_bundle"].is_demo


def test_all_pages_render_without_dataset():
    for page_key in PAGE_PATHS:
        app = _page_app(page_key).run()
        assert not app.exception, f"Page failed without a dataset: {page_key}"

        if page_key == "overview":
            assert any("Upload a dataset first" in item.value for item in app.info)
        elif page_key == "home":
            assert any("Upload Dataset" in button.label for button in app.button)
        else:
            markdown = " ".join(item.value for item in app.markdown)
            assert "No Dataset Loaded" in markdown, page_key


def test_all_pages_render_with_demo_dataset():
    demo_bundle = _demo_bundle()
    for page_key in PAGE_PATHS:
        app = _page_app(page_key, demo_bundle).run()
        assert not app.exception, f"Page failed with the demo dataset: {page_key}"


def test_all_fixture_files_return_data_or_friendly_error():
    from core.ingestion import load_file

    fixture_dir = Path(__file__).parent / "fixtures"
    fixture_paths = sorted(fixture_dir.iterdir())
    assert fixture_paths

    for fixture_path in fixture_paths:
        result = load_file(fixture_path.read_bytes(), fixture_path.name)
        if result.success:
            assert result.df is not None
        else:
            assert result.errors
            assert all("Traceback" not in error for error in result.errors)