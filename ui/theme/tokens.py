"""
Design tokens for DataLens AI.

Defines all visual constants (colors, spacing, radii, fonts, shadows)
used throughout the application. Tokens are referenced by the CSS
generator and UI components to ensure visual consistency.

Font: Inter (fallback system-ui).
Style: Enterprise SaaS analytics — clean, spacious, strong hierarchy.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorPalette:
    """Color palette for a theme variant."""
    # Backgrounds
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_card: str
    bg_hover: str
    bg_input: str
    # Text
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverse: str
    # Brand / Accent
    accent_primary: str
    accent_secondary: str
    accent_hover: str
    # Semantic
    success: str
    warning: str
    error: str
    info: str
    # Severity
    severity_critical: str
    severity_high: str
    severity_medium: str
    severity_low: str
    # Chart palette (colorblind-safe)
    chart_colors: tuple
    # Borders & Dividers
    border: str
    border_light: str
    divider: str
    # Shadows
    shadow_sm: str
    shadow_md: str
    shadow_lg: str


DARK_PALETTE = ColorPalette(
    bg_primary="#0E1117",
    bg_secondary="#1A1F2E",
    bg_tertiary="#232B3D",
    bg_card="#1A1F2E",
    bg_hover="#252D40",
    bg_input="#1A1F2E",
    text_primary="#FAFAFA",
    text_secondary="#B0B8C8",
    text_muted="#6B7280",
    text_inverse="#0E1117",
    accent_primary="#4A9EFF",
    accent_secondary="#7C3AED",
    accent_hover="#3B82F6",
    success="#10B981",
    warning="#F59E0B",
    error="#EF4444",
    info="#3B82F6",
    severity_critical="#EF4444",
    severity_high="#F97316",
    severity_medium="#F59E0B",
    severity_low="#3B82F6",
    chart_colors=(
        "#4A9EFF", "#F59E0B", "#10B981", "#EF4444",
        "#8B5CF6", "#EC4899", "#14B8A6", "#F97316",
        "#6366F1", "#84CC16", "#06B6D4", "#E11D48",
    ),
    border="#2D3748",
    border_light="#374151",
    divider="#1F2937",
    shadow_sm="0 1px 2px rgba(0,0,0,0.3)",
    shadow_md="0 4px 6px rgba(0,0,0,0.4)",
    shadow_lg="0 10px 25px rgba(0,0,0,0.5)",
)

LIGHT_PALETTE = ColorPalette(
    bg_primary="#FFFFFF",
    bg_secondary="#F8FAFC",
    bg_tertiary="#F1F5F9",
    bg_card="#FFFFFF",
    bg_hover="#F1F5F9",
    bg_input="#F8FAFC",
    text_primary="#1E293B",
    text_secondary="#475569",
    text_muted="#94A3B8",
    text_inverse="#FFFFFF",
    accent_primary="#2563EB",
    accent_secondary="#7C3AED",
    accent_hover="#1D4ED8",
    success="#059669",
    warning="#D97706",
    error="#DC2626",
    info="#2563EB",
    severity_critical="#DC2626",
    severity_high="#EA580C",
    severity_medium="#D97706",
    severity_low="#2563EB",
    chart_colors=(
        "#2563EB", "#D97706", "#059669", "#DC2626",
        "#7C3AED", "#DB2777", "#0D9488", "#EA580C",
        "#4F46E5", "#65A30D", "#0891B2", "#BE123C",
    ),
    border="#E2E8F0",
    border_light="#F1F5F9",
    divider="#E2E8F0",
    shadow_sm="0 1px 2px rgba(0,0,0,0.05)",
    shadow_md="0 4px 6px rgba(0,0,0,0.07)",
    shadow_lg="0 10px 25px rgba(0,0,0,0.1)",
)


@dataclass(frozen=True)
class Spacing:
    """Spacing scale (in rem)."""
    xs: str = "0.25rem"
    sm: str = "0.5rem"
    md: str = "1rem"
    lg: str = "1.5rem"
    xl: str = "2rem"
    xxl: str = "3rem"
    xxxl: str = "4rem"


@dataclass(frozen=True)
class BorderRadius:
    """Border radius scale."""
    sm: str = "4px"
    md: str = "8px"
    lg: str = "12px"
    xl: str = "16px"
    full: str = "9999px"


@dataclass(frozen=True)
class FontSize:
    """Font size scale."""
    xs: str = "0.75rem"
    sm: str = "0.875rem"
    base: str = "1rem"
    lg: str = "1.125rem"
    xl: str = "1.25rem"
    xxl: str = "1.5rem"
    xxxl: str = "2rem"
    display: str = "2.5rem"
    hero: str = "3.5rem"


@dataclass(frozen=True)
class FontWeight:
    """Font weight scale."""
    normal: int = 400
    medium: int = 500
    semibold: int = 600
    bold: int = 700


@dataclass(frozen=True)
class Transition:
    """CSS transition presets."""
    fast: str = "all 0.15s ease"
    normal: str = "all 0.25s ease"
    slow: str = "all 0.4s ease"
    spring: str = "all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)"


# Singleton instances
SPACING = Spacing()
RADIUS = BorderRadius()
FONT_SIZE = FontSize()
FONT_WEIGHT = FontWeight()
TRANSITION = Transition()

FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"


def get_palette(theme: str = "dark") -> ColorPalette:
    """Get the color palette for the specified theme."""
    return DARK_PALETTE if theme == "dark" else LIGHT_PALETTE
