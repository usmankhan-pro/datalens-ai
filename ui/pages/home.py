"""Home page combining the landing view and dataset upload controls."""

import streamlit as st


def page() -> None:
    from core.utils.state import has_dataset
    from ui.pages import dashboard, upload

    if has_dataset():
        upload._render_loaded_state()
    elif st.session_state.get("home_show_uploader"):
        st.title("Upload a dataset")
        upload._render_upload_zone()
        if st.button("Back to Home", key="home_upload_back_button"):
            st.session_state["home_show_uploader"] = False
            st.rerun()
    else:
        dashboard._render_landing()
        st.divider()
        st.subheader("Upload a dataset")
        upload._render_upload_zone()