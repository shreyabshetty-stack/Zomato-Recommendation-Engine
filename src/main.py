"""
Zomato AI Recommendations — Streamlit App  (Phase 5 — Fixed Layout)
Desktop-first | 1280px+ | Zomato-inspired warm-red theme

Key fixes vs previous version:
  - block-container padding restored (was 0, causing left-clipping of labels)
  - Left panel background applied via CSS [data-testid="column"] selector
    (Streamlit widgets cannot be nested inside custom HTML <div> wrappers)
  - Native Streamlit labels styled directly instead of hidden + re-injected
  - Nav bar uses negative margin trick to stay full-width despite padding
  - Card rendering via st.components.v1.html (bypasses Streamlit HTML sanitiser)

Run:
    $env:PYTHONPATH = "d:\\Zomato Reccomendation"
    .venv\\Scripts\\streamlit.exe run src/main.py
"""
from __future__ import annotations

import html as _html
import logging

import streamlit as st
import streamlit.components.v1 as components

from src.config import validate_config
from src.data.preprocessor import get_available_locations, get_catalog
from src.engine.recommender import get_recommendations
from src.input.validator import validate_preferences
from src.output.renderer import RenderedCard, render_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zomato AI Recommendations",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS  — single injected stylesheet
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fonts ───────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

html, body, [class*="css"], [data-testid="stHeader"], [data-testid="stSidebar"] {
    font-family: 'Inter', sans-serif !important;
    color: #e3e2e2 !important;
}

/* ── Hide Streamlit chrome ───────────────────────────────────────────────── */
#MainMenu, footer, header, .stDeployButton { visibility: hidden !important; }

/* ── Page background ─────────────────────────────────────────────────────── */
.stApp { background: #0F1115 !important; }

/* ── block-container: keep horizontal padding so labels aren't clipped ───── */
.block-container {
    padding-top: 0 !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}

/* ── Navigation bar ──────────────────────────────────────────────────────── */
.zai-nav {
    backdrop-filter: blur(20px);
    background: rgba(18, 20, 20, 0.7);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    margin-top: 0;
    margin-left: -2rem;
    margin-right: -2rem;
    padding: 0 40px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 48px;
}
.zai-nav-left  { display: flex; align-items: center; gap: 12px; }
.zai-nav-logo  { font-size: 2.2rem; line-height: 1; }
.zai-nav-title { font-size: 1.5rem; font-weight: 700; color: #e3e2e2; letter-spacing: -0.02em; }
.zai-nav-right { }
.zai-nav-tag   {
    font-size: 14px;
    color: #ffb3b1 !important;
    font-weight: 700 !important;
    text-decoration: none !important;
    border-bottom: 2px solid #ffb3b1 !important;
    padding-bottom: 4px !important;
    transition: all 0.2s ease !important;
}
.zai-nav-tag:hover {
    color: #ffffff !important;
    border-bottom-color: #ffffff !important;
}

/* ── Left column: Crimson Ether styling ──────────────────────────────────── */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child,
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child,
div[data-testid="column"]:first-child:not(div[data-testid="column"] div[data-testid="column"]),
div[data-testid="stColumn"]:first-child:not(div[data-testid="stColumn"] div[data-testid="stColumn"]) {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    align-self: flex-start !important;
    height: fit-content !important;
}

div[data-testid="stForm"] {
    background: #1D2128 !important;
    border: 1px solid #2A2F38 !important;
    border-radius: 16px !important;
    padding: 32px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
}

div[data-testid="stForm"] [data-testid="stVerticalBlock"] {
    gap: 12px !important;
}

/* ── Section titles inside panels ────────────────────────────────────────── */
.panel-title {
    font-size: 24px;
    font-weight: 600;
    color: #e3e2e2;
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 16px;
    border-bottom: 1px solid #2A2F38;
    margin-bottom: 16px;
}
.results-title {
    font-size: 24px;
    font-weight: 600;
    color: #e3e2e2;
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 24px;
    border-bottom: 1px solid #2A2F38;
    margin-bottom: 24px;
}

/* ── Streamlit form labels ────────────────────────────────────────────────── */
.stSelectbox > label,
.stTextInput > label,
.stTextArea > label,
.stSlider > label {
    font-size: 14px !important;
    font-weight: 500 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    color: #e4bebc !important; /* on-surface-variant */
    margin-bottom: 8px !important;
    margin-top: 24px !important;
    display: block !important;
}
/* first field in form shouldn't have top margin */
[data-testid="column"]:first-child .stSelectbox:first-of-type > label {
    margin-top: 0 !important;
}

/* ── Budget helper text ──────────────────────────────────────────────────── */
.budget-helper {
    font-size: 12px;
    color: #e4bebc;
    opacity: 0.6;
    margin-top: 4px;
    margin-bottom: 8px;
    line-height: 1.4;
}

/* ── Widget borders & focus ──────────────────────────────────────────────── */
div[data-baseweb="select"] > div {
    background: #121414 !important;
    border: 1px solid #2A2F38 !important;
    border-radius: 8px !important;
    color: #e3e2e2 !important;
    transition: all 0.3s ease;
    min-height: 48px !important;
}
div[data-baseweb="select"] > div:focus-within {
    border-color: #ffb3b1 !important;
    box-shadow: 0 0 15px rgba(226, 55, 68, 0.15) !important;
}
div[data-baseweb="input"] > div {
    background: #121414 !important;
    border: 1px solid #2A2F38 !important;
    border-radius: 8px !important;
    min-height: 48px !important;
    color: #e3e2e2 !important;
    transition: all 0.3s ease;
}
div[data-baseweb="input"] > div:focus-within {
    border-color: #ffb3b1 !important;
    box-shadow: 0 0 15px rgba(226, 55, 68, 0.15) !important;
}
div[data-baseweb="textarea"] > div {
    background: #121414 !important;
    border: 1px solid #2A2F38 !important;
    border-radius: 8px !important;
    color: #e3e2e2 !important;
    transition: all 0.3s ease;
}
div[data-baseweb="textarea"] > div:focus-within {
    border-color: #ffb3b1 !important;
    box-shadow: 0 0 15px rgba(226, 55, 68, 0.15) !important;
}

/* ensure text fields color inside inputs/textarea is white */
input, textarea, select {
    color: #e3e2e2 !important;
}

/* ── Rating slider ───────────────────────────────────────────────────────── */
.stSlider label {
    display: none !important;
}
.stSlider [data-testid="stSliderTickBar"] {
    display: none !important;
}
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: #E23744 !important;
    border-color: #ffb3b1 !important;
}
.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
    display: none !important;
}
.stSlider [data-baseweb="slider"] > div:nth-child(2) {
    background: #E23744 !important;
}

/* ── CTA button ──────────────────────────────────────────────────────────── */
.stButton > button,
div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    background: #E23744 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 20px !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 16px 0 !important;
    box-shadow: 0 0 15px rgba(226, 55, 68, 0.2) !important;
    transition: all 0.3s ease-in-out !important;
    margin-top: 16px !important;
}
.stButton > button:hover,
div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
    box-shadow: 0 0 25px rgba(226, 55, 68, 0.4) !important;
    transform: scale(1.01) !important;
    background: #C72D39 !important;
}

/* ── Rating live badge ───────────────────────────────────────────────────── */
.rating-badge {
    font-size: 14px;
    color: #ffb3b1;
    font-weight: 500;
    margin-top: -4px;
    margin-bottom: 12px;
}

/* ── Filter chips row ────────────────────────────────────────────────────── */
.chips-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
.chip {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1D2128; border: 1px solid #2A2F38;
    color: #e4bebc; font-size: 14px; font-weight: 500;
    padding: 6px 16px; border-radius: 9999px;
}

/* ── AI summary banner ───────────────────────────────────────────────────── */
.ai-banner {
    background: linear-gradient(135deg, rgba(226, 55, 68, 0.15) 0%, rgba(37, 42, 51, 1) 100%);
    border: 1px solid rgba(226, 55, 68, 0.3);
    box-shadow: 0 0 20px rgba(226, 55, 68, 0.1);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    display: flex; gap: 16px; align-items: flex-start;
    position: relative;
    overflow: hidden;
}
.ai-banner::after {
    content: '';
    position: absolute;
    right: -40px;
    bottom: -40px;
    width: 160px;
    height: 160px;
    background: rgba(226, 55, 68, 0.1);
    filter: blur(60px);
    border-radius: 50%;
    pointer-events: none;
}
.ai-banner-icon { font-size: 32px; color: #E23744; flex-shrink: 0; }
.ai-banner-text { font-size: 18px; color: #e3e2e2; line-height: 28px; font-style: italic; opacity: 0.9; }

/* ── Relaxed-filter amber warning ────────────────────────────────────────── */
.relaxed-warn {
    background: rgba(217, 119, 6, 0.15);
    border: 1px solid rgba(217, 119, 6, 0.3);
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 24px;
    font-size: 16px;
    color: #fde68a;
    display: flex;
    gap: 12px;
    align-items: center;
}

/* ── Validation error text ───────────────────────────────────────────────── */
.val-err {
    color: #ffb4ab; font-size: 14px; font-weight: 500;
    margin-top: 8px; display: flex; align-items: center; gap: 6px;
}

/* ── Error bar (server failures) ─────────────────────────────────────────── */
.err-bar {
    background: rgba(147, 0, 10, 0.2);
    border: 1px solid rgba(255, 180, 171, 0.2);
    border-radius: 12px;
    padding: 16px 24px;
    margin: 0 0 24px 0;
    font-size: 16px;
    color: #ffdad6;
    display: flex;
    align-items: center;
    gap: 12px;
}

/* ── Empty / no-results states ───────────────────────────────────────────── */
.empty-state {
    text-align: center; padding: 64px 24px;
    color: #e4bebc;
}
.empty-icon  { font-size: 48px; margin-bottom: 16px; }
.empty-title { font-size: 20px; font-weight: 600; color: #e3e2e2; margin-bottom: 12px; }
.empty-sub   { font-size: 16px; line-height: 24px; color: #e4bebc; opacity: 0.8; }

.no-results {
    text-align: center; padding: 48px 24px;
    background: rgba(147, 0, 10, 0.05);
    border: 1.5px dashed rgba(255, 180, 171, 0.3);
    border-radius: 16px;
}
.no-results-title { font-size: 20px; font-weight: 700; color: #ffb4ab; margin-bottom: 12px; }
.no-results-tips  { font-size: 16px; color: #e4bebc; line-height: 24px; opacity: 0.9; }

/* ── Skeleton shimmer ────────────────────────────────────────────────────── */
@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
.sk-line {
    background: linear-gradient(90deg,#181B20 25%,#2A2F38 50%,#181B20 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px; display: block;
}
.sk-card {
    background: #181B20; border: 1px solid #2A2F38; border-radius: 16px;
    padding: 24px; margin-bottom: 24px;
}
.sk-h  { height: 24px; width: 50%; margin-bottom: 16px; }
.sk-m  { height: 20px; width: 70%; margin-bottom: 16px; }
.sk-l1 { height: 16px; width: 90%; margin-bottom: 12px; }
.sk-l2 { height: 16px; width: 75%; }
.sk-msg {
    text-align: center; font-size: 16px; font-weight: 500;
    color: #E23744; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: center; gap: 8px;
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.zai-footer {
    text-align: center; padding: 32px 0;
    font-size: 14px; color: #e4bebc; opacity: 0.6;
    border-top: 1px solid rgba(255, 255, 255, 0.05); margin-top: 48px;
}

/* ── Powered-by caption ──────────────────────────────────────────────────── */
.powered-by {
    font-size: 14px; color: #e4bebc; opacity: 0.6;
    text-align: right; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Card HTML renderer  (runs inside st.components.v1.html — no sanitiser)
# ─────────────────────────────────────────────────────────────────────────────
_CARD_CSS = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
body { background: transparent; }
.card {
    background: #181B20; border: 1px solid #2A2F38; border-radius: 16px;
    padding: 24px; margin-bottom: 24px;
    display: flex; gap: 24px; align-items: flex-start;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    transition: all 0.3s ease;
}
.card:hover {
    transform: translateY(-4px);
    border-color: rgba(226, 55, 68, 0.4);
    box-shadow: 0 12px 24px -10px rgba(0,0,0,0.5);
}
.badge {
    width: 48px; height: 48px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 20px; flex-shrink: 0;
}
.b1 { background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); color: #eab308; }
.b2 { background: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.3); color: #94a3b8; }
.b3 { background: rgba(180, 83, 9, 0.1); border: 1px solid rgba(180, 83, 9, 0.3); color: #b45309; }
.bn { background: rgba(227, 226, 226, 0.05); border: 1px solid rgba(227, 226, 226, 0.2); color: #a0a0a0; }

.body { flex: 1; min-width: 0; }
.name {
    font-size: 24px; font-weight: 600; color: #e3e2e2;
    margin-bottom: 8px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
}
.pills { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; align-items: center; }
.p { display: inline-block; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 4px; }
.pc { background: #1a1c1c; color: #e3e2e2; border: 1px solid rgba(91, 64, 63, 0.2); }
.pr-star { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; }
.pk { font-size: 12px; color: #e4bebc; font-weight: 600; }
.po { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
.pt { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.3); }

.expl {
    font-size: 16px; color: #e4bebc; line-height: 24px;
    background: rgba(13, 14, 15, 0.5); padding: 16px;
    border-radius: 8px; border-left: 4px solid #E23744;
}
.expl-title { font-weight: bold; color: #E23744; margin-right: 8px; font-style: italic; }
.votes { font-size: 12px; color: #e4bebc; opacity: 0.6; margin-top: 12px; }
</style>
"""


def _badge_html(rank: int) -> str:
    css = {1: "b1", 2: "b2", 3: "b3"}.get(rank, "bn")
    lbl = {1: "#1", 2: "#2", 3: "#3"}.get(rank, f"#{rank}")
    return f'<div class="badge {css}">{lbl}</div>'


def _card_html(card: RenderedCard) -> str:
    name     = _html.escape(card.name)
    expl     = _html.escape(card.explanation)

    cuisines = "".join(
        f'<span class="p pc">{_html.escape(c.strip())}</span>'
        for c in card.cuisines.split(",")[:3] if c.strip()
    )
    rating_p = f'<span class="pr-star" style="color:#facc15;"><span style="color:#facc15; font-size:18px; margin-right:4px;">★</span><span style="font-weight:700; font-size:20px;">{card.rating:.1f}</span></span>'
    cost_p   = f'<span class="pk" style="font-size:12px; color:#e4bebc;">₹{card.cost_for_two:,} for two</span>'
    votes    = f'<div class="votes">👥 {card.votes:,} votes</div>' if card.votes else ""
    border_color = {1: "#E23744", 2: "#94a3b8", 3: "#b45309"}.get(card.rank, "#E23744")

    return f"""
<div class="card">
  {_badge_html(card.rank)}
  <div class="body">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; gap: 12px;">
      <div>
        <div class="name">{name}</div>
        <div class="pills">{cuisines}</div>
      </div>
      <div style="text-align:right; display:flex; flex-direction:column; align-items:flex-end; gap:6px; flex-shrink:0;">
        {rating_p}
        {cost_p}
      </div>
    </div>
    <div class="expl" style="border-left-color: {border_color};">
      <span class="expl-title" style="color: {border_color};">AI Review:</span>{expl}
    </div>
    {votes}
  </div>
</div>"""


def _cards_component(cards: list[RenderedCard]) -> None:
    inner = "".join(_card_html(c) for c in cards)
    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,700;0,800;1,400&display=swap" rel="stylesheet">
{_CARD_CSS}
</head><body>{inner}</body></html>"""
    # Calculate height dynamically with generous bounds.
    height_calc = 100 + len(cards) * 270
    components.html(full_html, height=max(350, height_calc), scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# Skeleton cards
# ─────────────────────────────────────────────────────────────────────────────
def _skeletons_html(n: int = 3) -> str:
    s = """<div class="sk-card">
        <span class="sk-line sk-h"></span>
        <span class="sk-line sk-m"></span>
        <span class="sk-line sk-l1"></span>
        <span class="sk-line sk-l2"></span>
    </div>"""
    return s * n


# ─────────────────────────────────────────────────────────────────────────────
# Filter chips
# ─────────────────────────────────────────────────────────────────────────────
def _chips_html(location: str, budget: str, cuisine: str, rating: float) -> str:
    chips = [
        f'<span class="chip">📍 {_html.escape(location)}</span>',
        f'<span class="chip">💰 {_html.escape(budget)} budget</span>',
    ]
    if cuisine:
        chips.append(f'<span class="chip">🍜 {_html.escape(cuisine)}</span>')
    if rating > 0:
        chips.append(f'<span class="chip">⭐ {rating:.1f}+</span>')
    return f'<div class="chips-row">{"".join(chips)}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "rendered": None,
    "snap": None,
    "errors": [],
    "server_error": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# Cached data
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading restaurant catalog…")
def _catalog():
    return get_catalog()


@st.cache_resource(show_spinner=False)
def _locations():
    return get_available_locations()


@st.cache_resource(show_spinner=False)
def _cuisines(catalog):
    cuisines_set = set()
    for r in catalog:
        for c in r.cuisines:
            cuisines_set.add(c)
    return ["All Cuisines"] + sorted(list(cuisines_set))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:

    # Load data
    try:
        catalog   = _catalog()
        locations = _locations()
    except Exception as exc:
        st.error(f"Failed to load restaurant catalog: {exc}")
        return

    # ── Navigation bar ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="zai-nav">
        <div class="zai-nav-left" style="display: flex; align-items: center; gap: 16px;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" style="height: 40px; width: 40px;">
                <defs>
                    <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#FF5252" />
                        <stop offset="100%" stop-color="#E23744" />
                    </linearGradient>
                </defs>
                <rect x="10" y="10" width="80" height="80" rx="20" fill="url(#logo-grad)" />
                <path d="M38 35 v18 M34 35 v10 M42 35 v10 M38 53 v15" stroke="white" stroke-width="4" stroke-linecap="round"/>
                <path d="M62 35 c-5 0-8 4-8 10 c0 6 3 10 8 10 s8-4 8-10 c0-6-3-10-8-10 z M62 55 v13" fill="white" stroke="white" stroke-width="2" stroke-linejoin="round"/>
                <path d="M72 20 l2 4 l4 2 l-4 2 l-2 4 l-2-4 l-4-2 l4-2 z" fill="#facc15" />
            </svg>
            <span class="zai-nav-title">Zomato AI Recommendations</span>
        </div>
        <div class="zai-nav-right">
            <a href="#" class="zai-nav-tag">Find your perfect restaurant</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Error bar (server / API failures) ─────────────────────────────────────
    if st.session_state.server_error:
        st.markdown(
            f'<div class="err-bar"><span class="material-symbols-outlined" style="color:#ffdad6; font-size: 20px;">report</span>'
            f'<span>Server Error: {st.session_state.server_error}. Results may vary.</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("✕ Dismiss", key="dismiss_err"):
            st.session_state.server_error = None
            st.rerun()

    # ── API key warning ───────────────────────────────────────────────────────
    if not validate_config():
        st.markdown(
            '<div class="err-bar">🔑 <strong>GROQ_API_KEY not set.</strong> '
            'Add it to your <code>.env</code> file to enable AI recommendations.</div>',
            unsafe_allow_html=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Two-column layout
    # ─────────────────────────────────────────────────────────────────────────
    left, right = st.columns([40, 60], gap="large")

    # ══════════════════════════════════════════════════════════════════════════
    # LEFT  — Preference form
    # ══════════════════════════════════════════════════════════════════════════
    with left:
        with st.form(key="preferences_form", clear_on_submit=False):
            st.markdown('<div class="panel-title" style="margin-top: 0;"><span class="material-symbols-outlined" style="font-variation-settings: \'FILL\' 1; color:#E23744; font-size: 28px;">tune</span>Your Preferences</div>', unsafe_allow_html=True)
            # Location — Streamlit selectbox (label styled via CSS above)
            location = st.selectbox(
                "Location",
                options=[""] + locations,
                index=0,
                key="sel_location",
            )

            # Location suggest error if present
            loc_errors = [e for e in st.session_state.errors if "location" in e.lower() or "locality" in e.lower() or "city" in e.lower()]
            if loc_errors:
                st.markdown('<p style="color:#ffb4ab; font-size:12px; margin-top: -8px; margin-bottom: 8px; font-weight: 500;">Please specify a more precise locality.</p>', unsafe_allow_html=True)
                # Remove from errors display so it doesn't duplicate
                st.session_state.errors = [e for e in st.session_state.errors if e not in loc_errors]

            # Side-by-side Budget and Cuisine dropdowns
            col_budget, col_cuisine = st.columns(2)
            with col_budget:
                budget = st.selectbox(
                    "Budget",
                    options=["Low", "Medium", "High"],
                    index=1,
                    key="sel_budget",
                    format_func=lambda b: {
                        "Low":    "Low <₹500",
                        "Medium": "Medium ₹501-1500",
                        "High":   "High >₹1500",
                    }[b],
                )
            with col_cuisine:
                all_cuisines = _cuisines(catalog)
                cuisine_selected = st.selectbox(
                    "Cuisine",
                    options=all_cuisines,
                    index=0,
                    key="sel_cuisine",
                )

            # Rating slider label side-by-side
            slider_val = st.session_state.get("sld_rating", 4.2)
            st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:24px; margin-bottom:8px;"><span style="font-size:14px; font-weight:500; color:#e4bebc;">Min. Rating</span><span style="font-size:14px; font-weight:700; color:#ffb3b1;">{slider_val:.1f}+ ★</span></div>', unsafe_allow_html=True)

            min_rating = st.slider(
                "Minimum rating",
                min_value=0.0, max_value=5.0,
                value=4.2, step=0.1,
                key="sld_rating",
                label_visibility="collapsed"
            )

            # Additional preferences
            additional = st.text_area(
                "Describe your cravings",
                placeholder="I'm looking for a quiet place with great sourdough pizza and candlelight...",
                height=64,
                key="txt_additional",
            )

            # Validation errors
            for err in st.session_state.errors:
                st.markdown(
                    f'<div class="val-err">⚠ {_html.escape(err)}</div>',
                    unsafe_allow_html=True,
                )

            # CTA button
            submit = st.form_submit_button("✨  Get Recommendations", use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # RIGHT  — Results panel
    # ══════════════════════════════════════════════════════════════════════════
    with right:
        st.markdown('<div class="results-title">🍴 Recommendations</div>', unsafe_allow_html=True)

        # ── Handle submit ─────────────────────────────────────────────────────
        if submit:
            st.session_state.errors      = []
            st.session_state.server_error = None
            st.session_state.rendered    = None

            cuisine_val = None if cuisine_selected == "All Cuisines" else cuisine_selected

            prefs, errors = validate_preferences(
                location=location or "",
                budget=budget,
                cuisine=cuisine_val,
                min_rating=min_rating if min_rating > 0 else None,
                additional_preferences=additional.strip() or None,
                available_locations=locations,
            )

            if errors:
                st.session_state.errors = errors
            else:
                # Show loading skeleton immediately, then run pipeline
                with st.spinner("🤖  AI is ranking restaurants for you…"):
                    try:
                        result = get_recommendations(prefs, catalog)  # type: ignore[arg-type]
                        st.session_state.rendered = render_result(result)
                        st.session_state.snap = {
                            "location": prefs.location,      # type: ignore[union-attr]
                            "budget":   prefs.budget.value,  # type: ignore[union-attr]
                            "cuisine":  cuisine_selected,
                            "rating":   min_rating,
                        }
                    except ValueError as exc:
                        st.session_state.server_error = str(exc)
                    except RuntimeError as exc:
                        st.session_state.server_error = str(exc)
                    except Exception as exc:
                        logger.exception("Pipeline error")
                        st.session_state.server_error = str(exc)

            st.rerun()

        # ── Display results ───────────────────────────────────────────────────
        rendered = st.session_state.rendered
        snap     = st.session_state.snap
        errors   = st.session_state.errors

        # Validation error summary
        if errors:
            st.markdown("""
            <div style="background:#FFF0F0;border:1.5px solid #FCCDD0;
                 border-radius:12px;padding:14px 18px;margin-bottom:16px;">
                <strong style="color:#B91C2C;font-size:0.9rem;">
                    Please fix the errors in the form to continue.
                </strong>
            </div>""", unsafe_allow_html=True)

        # Has results
        elif rendered is not None and snap is not None:

            # Filter chips (active filters parameters)
            st.markdown(
                _chips_html(snap["location"], snap["budget"], snap["cuisine"], snap["rating"]),
                unsafe_allow_html=True,
            )

            # Relaxed-filter warning
            if rendered.filters_relaxed:
                relaxed_names = []
                for f in rendered.filters_relaxed:
                    name = {
                        "cuisine": "Cuisine",
                        "budget": "Budget",
                        "min_rating": "Rating"
                    }.get(f, f.title())
                    relaxed_names.append(name)
                
                if len(relaxed_names) == 1:
                    filter_str = f"'{relaxed_names[0]}'"
                else:
                    filter_str = f" and ".join([f"'{n}'" for n in relaxed_names])
                
                st.markdown(f"""
                <div class="relaxed-warn">
                    <span class="material-symbols-outlined" style="color: #fde68a; font-size: 20px;">info</span>
                    <span style="font-size: 14px;">We've relaxed your {filter_str} filter{"s" if len(relaxed_names) > 1 else ""} slightly to show more relevant matches.</span>
                </div>""", unsafe_allow_html=True)



            # No results
            if not rendered.cards:
                st.markdown("""
                <div class="no-results">
                    <div class="no-results-title">😕 No restaurants matched your filters</div>
                    <div class="no-results-tips">
                        Try broadening your search:<br>
                        • Remove the cuisine filter<br>
                        • Lower the minimum rating<br>
                        • Switch to a different budget tier
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                _cards_component(rendered.cards)
                st.markdown(
                    f'<div class="powered-by">Powered by Groq LLM · '
                    f'{rendered.total_candidates_shown} result(s)</div>',
                    unsafe_allow_html=True,
                )

        # Empty state
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <div class="empty-title">Your top picks will appear here</div>
                <div class="empty-sub">
                    Set your location and preferences on the left,<br>
                    then click <strong>Get Recommendations</strong> to discover great restaurants.
                </div>
            </div>""", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="zai-footer">
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 12px; opacity: 0.6;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" style="height: 24px; width: 24px; filter: grayscale(100%) contrast(1.2);">
                <defs>
                    <linearGradient id="footer-logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#FF5252" />
                        <stop offset="100%" stop-color="#E23744" />
                    </linearGradient>
                </defs>
                <rect x="10" y="10" width="80" height="80" rx="20" fill="url(#footer-logo-grad)" />
                <path d="M38 35 v18 M34 35 v10 M42 35 v10 M38 53 v15" stroke="white" stroke-width="4" stroke-linecap="round"/>
                <path d="M62 35 c-5 0-8 4-8 10 c0 6 3 10 8 10 s8-4 8-10 c0-6-3-10-8-10 z M62 55 v13" fill="white" stroke="white" stroke-width="2" stroke-linejoin="round"/>
                <path d="M72 20 l2 4 l4 2 l-4 2 l-2 4 l-2-4 l-4-2 l4-2 z" fill="#facc15" />
            </svg>
            <span style="font-size: 14px; font-weight: 500; color: #e4bebc;">Zomato AI Recommendations</span>
        </div>
        <p style="margin-bottom: 16px;">© 2026 Zomato AI Recommendations. Powered by advanced semantic search and culinary neural networks.</p>
        <div style="display: flex; justify-content: center; gap: 24px;">
            <a href="#" style="color: #e4bebc; text-decoration: none; font-size: 14px; transition: color 0.2s;">Privacy</a>
            <a href="#" style="color: #e4bebc; text-decoration: none; font-size: 14px; transition: color 0.2s;">Terms</a>
            <a href="#" style="color: #e4bebc; text-decoration: none; font-size: 14px; transition: color 0.2s;">API Access</a>
        </div>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

