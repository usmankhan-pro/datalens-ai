"""
CSS generator for DataLens AI themes.

Generates the complete CSS stylesheet based on the current theme's
design tokens. Injected into every page via st.markdown.
"""

import streamlit as st

from ui.theme.tokens import (
    get_palette,
    SPACING,
    RADIUS,
    FONT_SIZE,
    FONT_WEIGHT,
    TRANSITION,
    FONT_FAMILY,
)


def generate_css(theme: str = "dark") -> str:
    """
    Generate the complete CSS stylesheet for the given theme.

    Args:
        theme: 'dark' or 'light'

    Returns:
        Complete CSS string wrapped in <style> tags for st.markdown.
    """
    p = get_palette(theme)
    return f"""
<style>
    /* ========== Google Fonts ========== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ========== CSS Variables ========== */
    :root {{
        --bg-primary: {p.bg_primary};
        --bg-secondary: {p.bg_secondary};
        --bg-tertiary: {p.bg_tertiary};
        --bg-card: {p.bg_card};
        --bg-hover: {p.bg_hover};
        --text-primary: {p.text_primary};
        --text-secondary: {p.text_secondary};
        --text-muted: {p.text_muted};
        --accent-primary: {p.accent_primary};
        --accent-hover: {p.accent_hover};
        --success: {p.success};
        --warning: {p.warning};
        --error: {p.error};
        --info: {p.info};
        --border: {p.border};
        --shadow-sm: {p.shadow_sm};
        --shadow-md: {p.shadow_md};
        --shadow-lg: {p.shadow_lg};
        --radius-sm: {RADIUS.sm};
        --radius-md: {RADIUS.md};
        --radius-lg: {RADIUS.lg};
        --font-family: {FONT_FAMILY};
        --transition-fast: {TRANSITION.fast};
        --transition-normal: {TRANSITION.normal};
    }}

    /* ========== Base ========== */
    .stApp {{
        font-family: var(--font-family);
        background-color: var(--bg-primary);
        color: var(--text-primary);
    }}

    /* ========== Sidebar ========== */
    section[data-testid="stSidebar"] {{
        background-color: {p.bg_secondary};
        border-right: 1px solid {p.border};
        transition: var(--transition-normal);
    }}

    section[data-testid="stSidebar"] .stMarkdown p {{
        color: {p.text_secondary};
    }}

    /* ========== Cards ========== */
    .datalens-card {{
        background: {p.bg_card};
        border: 1px solid {p.border};
        border-radius: {RADIUS.lg};
        padding: {SPACING.lg};
        transition: {TRANSITION.normal};
        box-shadow: {p.shadow_sm};
    }}

    .datalens-card:hover {{
        box-shadow: {p.shadow_md};
        border-color: {p.accent_primary};
        transform: translateY(-2px);
    }}

    /* ========== Metric Cards ========== */
    .metric-card {{
        background: {p.bg_card};
        border: 1px solid {p.border};
        border-radius: {RADIUS.lg};
        padding: {SPACING.lg};
        text-align: center;
        transition: {TRANSITION.normal};
    }}

    .metric-card:hover {{
        border-color: {p.accent_primary};
        box-shadow: {p.shadow_md};
    }}

    .metric-value {{
        font-size: {FONT_SIZE.xxxl};
        font-weight: {FONT_WEIGHT.bold};
        color: {p.accent_primary};
        line-height: 1.2;
    }}

    .metric-label {{
        font-size: {FONT_SIZE.sm};
        color: {p.text_secondary};
        margin-top: {SPACING.xs};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* ========== KPI Cards ========== */
    .kpi-card {{
        background: {p.bg_card};
        border: 1px solid {p.border};
        border-radius: {RADIUS.lg};
        padding: {SPACING.lg};
        transition: {TRANSITION.normal};
        position: relative;
        overflow: hidden;
    }}

    .kpi-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, {p.accent_primary}, {p.accent_secondary});
    }}

    .kpi-card:hover {{
        transform: translateY(-3px);
        box-shadow: {p.shadow_lg};
    }}

    /* ========== Score Ring ========== */
    .score-ring-container {{
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .score-ring {{
        transition: stroke-dashoffset 1.5s ease-in-out;
    }}

    /* ========== Severity Badges ========== */
    .severity-badge {{
        display: inline-flex;
        align-items: center;
        padding: {SPACING.xs} {SPACING.sm};
        border-radius: {RADIUS.full};
        font-size: {FONT_SIZE.xs};
        font-weight: {FONT_WEIGHT.semibold};
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .severity-critical {{
        background: {p.severity_critical}20;
        color: {p.severity_critical};
        animation: pulse-critical 2s infinite;
    }}

    .severity-high {{
        background: {p.severity_high}20;
        color: {p.severity_high};
    }}

    .severity-medium {{
        background: {p.severity_medium}20;
        color: {p.severity_medium};
    }}

    .severity-low {{
        background: {p.severity_low}20;
        color: {p.severity_low};
    }}

    /* ========== Feature Cards (Landing) ========== */
    .feature-card {{
        background: {p.bg_card};
        border: 1px solid {p.border};
        border-radius: {RADIUS.lg};
        padding: {SPACING.xl};
        text-align: center;
        transition: {TRANSITION.normal};
        cursor: default;
    }}

    .feature-card:hover {{
        transform: translateY(-4px);
        box-shadow: {p.shadow_lg};
        border-color: {p.accent_primary};
    }}

    .feature-card-icon {{
        font-size: 2.5rem;
        margin-bottom: {SPACING.md};
    }}

    .feature-card-title {{
        font-size: {FONT_SIZE.lg};
        font-weight: {FONT_WEIGHT.semibold};
        color: {p.text_primary};
        margin-bottom: {SPACING.sm};
    }}

    .feature-card-desc {{
        font-size: {FONT_SIZE.sm};
        color: {p.text_secondary};
        line-height: 1.6;
    }}

    /* ========== Buttons ========== */
    .stButton > button {{
        border-radius: {RADIUS.md};
        font-weight: {FONT_WEIGHT.medium};
        font-family: var(--font-family);
        transition: {TRANSITION.fast};
        border: 1px solid transparent;
    }}

    .stButton > button:hover {{
        transform: scale(1.02);
        box-shadow: {p.shadow_md};
    }}

    /* ========== Tables ========== */
    .stDataFrame {{
        border-radius: {RADIUS.md};
        overflow: hidden;
    }}

    /* ========== Tabs ========== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: {SPACING.xs};
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: {RADIUS.md} {RADIUS.md} 0 0;
        padding: {SPACING.sm} {SPACING.lg};
        font-weight: {FONT_WEIGHT.medium};
        transition: {TRANSITION.fast};
    }}

    /* ========== Expander ========== */
    .streamlit-expanderHeader {{
        font-weight: {FONT_WEIGHT.medium};
        transition: {TRANSITION.fast};
    }}

    /* ========== Animations ========== */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes slideIn {{
        from {{ opacity: 0; transform: translateX(-10px); }}
        to {{ opacity: 1; transform: translateX(0); }}
    }}

    @keyframes pulse-critical {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
    }}

    @keyframes countUp {{
        from {{ opacity: 0; transform: translateY(5px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes ringFill {{
        from {{ stroke-dashoffset: 283; }}
    }}

    @keyframes scaleIn {{
        from {{ opacity: 0; transform: scale(0.95); }}
        to {{ opacity: 1; transform: scale(1); }}
    }}

    .animate-fade-in {{
        animation: fadeIn 0.5s ease forwards;
    }}

    .animate-slide-in {{
        animation: slideIn 0.4s ease forwards;
    }}

    .animate-scale-in {{
        animation: scaleIn 0.3s ease forwards;
    }}

    /* Staggered fade-in for children */
    .stagger-fade > * {{
        opacity: 0;
        animation: fadeIn 0.5s ease forwards;
    }}
    .stagger-fade > *:nth-child(1) {{ animation-delay: 0.1s; }}
    .stagger-fade > *:nth-child(2) {{ animation-delay: 0.2s; }}
    .stagger-fade > *:nth-child(3) {{ animation-delay: 0.3s; }}
    .stagger-fade > *:nth-child(4) {{ animation-delay: 0.4s; }}

    /* ========== Empty State ========== */
    .empty-state {{
        text-align: center;
        padding: {SPACING.xxxl} {SPACING.xl};
        color: {p.text_muted};
    }}

    .empty-state-icon {{
        font-size: 3rem;
        margin-bottom: {SPACING.md};
        opacity: 0.5;
    }}

    .empty-state-title {{
        font-size: {FONT_SIZE.xl};
        font-weight: {FONT_WEIGHT.semibold};
        color: {p.text_secondary};
        margin-bottom: {SPACING.sm};
    }}

    .empty-state-desc {{
        font-size: {FONT_SIZE.base};
        color: {p.text_muted};
        max-width: 400px;
        margin: 0 auto;
        line-height: 1.6;
    }}

    /* ========== Upload Zone ========== */
    .upload-zone {{
        border: 2px dashed {p.border};
        border-radius: {RADIUS.lg};
        padding: {SPACING.xxxl};
        text-align: center;
        transition: {TRANSITION.normal};
        background: {p.bg_secondary};
    }}

    .upload-zone:hover {{
        border-color: {p.accent_primary};
        background: {p.bg_hover};
    }}

    /* ========== Tooltip ========== */
    .info-tooltip {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: {p.bg_tertiary};
        color: {p.text_muted};
        font-size: 11px;
        cursor: help;
        margin-left: {SPACING.xs};
        transition: {TRANSITION.fast};
    }}

    .info-tooltip:hover {{
        background: {p.accent_primary};
        color: white;
    }}

    /* ========== Hero Section ========== */
    .hero-title {{
        font-size: {FONT_SIZE.hero};
        font-weight: {FONT_WEIGHT.bold};
        line-height: 1.1;
        margin-bottom: {SPACING.md};
        background: linear-gradient(135deg, {p.accent_primary}, {p.accent_secondary});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: fadeIn 0.8s ease forwards;
    }}

    .hero-subtitle {{
        font-size: {FONT_SIZE.xl};
        color: {p.text_secondary};
        max-width: 600px;
        line-height: 1.6;
        animation: fadeIn 1s ease 0.2s forwards;
        opacity: 0;
    }}

    /* ========== Privacy Notice ========== */
    .privacy-notice {{
        background: {p.bg_tertiary};
        border: 1px solid {p.border};
        border-radius: {RADIUS.md};
        padding: {SPACING.md} {SPACING.lg};
        font-size: {FONT_SIZE.sm};
        color: {p.text_muted};
        display: flex;
        align-items: center;
        gap: {SPACING.sm};
    }}

    /* ========== Scrollbar ========== */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {p.bg_primary};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {p.border};
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {p.text_muted};
    }}

    /* ========== Responsive ========== */
    @media (max-width: 768px) {{
        .hero-title {{
            font-size: {FONT_SIZE.xxxl};
        }}
        .hero-subtitle {{
            font-size: {FONT_SIZE.base};
        }}
    }}
</style>
"""


def inject_css(theme: str = "dark") -> None:
    """Inject the theme CSS into the current Streamlit page."""
    st.markdown(generate_css(theme), unsafe_allow_html=True)
