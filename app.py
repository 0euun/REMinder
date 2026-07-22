import base64
import html
import json
from collections import Counter
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import db
import llm

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    /* 우측 하단 프로필/호스팅 배지 */
    [data-testid="stDecoration"] {display: none;}
    a[href*="streamlit.io"] {display: none;}
    </style>
""", unsafe_allow_html=True)

db.init_db()

st.set_page_config(
    page_title="REMinder — 꿈일기",
    page_icon="🌙",
    layout="wide",
)

# ── Claude Design 목업(REMinder.dc.html)의 oklch 색상을 그대로 옮긴 토큰 ──
C = {
    "bg": "oklch(0.16 0.028 290)",
    "card": "oklch(0.2 0.03 290)",
    "card_soft": "oklch(0.22 0.035 290)",  # 입력창
    "border": "oklch(0.4 0.03 290 / 0.35)",
    "border_soft": "oklch(0.4 0.03 290 / 0.25)",
    "text": "oklch(0.95 0.015 290)",
    "text2": "oklch(0.85 0.02 290)",
    "text3": "oklch(0.8 0.02 290)",
    "muted": "oklch(0.6 0.02 290)",
    "muted2": "oklch(0.58 0.02 290)",
    "muted3": "oklch(0.72 0.02 290)",
    "muted4": "oklch(0.75 0.02 290)",
    "faint": "oklch(0.5 0.02 290)",
    "faint2": "oklch(0.55 0.02 290)",
    "accent": "oklch(0.78 0.09 290)",
    "chip": "oklch(0.28 0.03 290)",
    "chip_text": "oklch(0.85 0.02 290)",
    "chip2": "oklch(0.3 0.04 290)",
    "chip2_text": "oklch(0.85 0.02 290)",
    "toggle_off": "oklch(0.3 0.02 290)",
    "toggle_on": "oklch(0.6 0.09 290)",
    "heat_empty": "oklch(0.24 0.02 290)",
}

DREAM_TYPE_HUE = {
    "HAPPY": 350, "FUNNY": 70, "SAD": 250, "NIGHTMARE": 20,
    "ANNOYING": 40, "LUCID": 190, "NO_MEMORY": None, "OTHER": 290,
}
DREAM_TYPE_ORDER = ["HAPPY", "FUNNY", "SAD", "NIGHTMARE", "ANNOYING", "LUCID", "NO_MEMORY", "OTHER"]
LUCID_HUE = 190

NEUTRAL_PILL = ("oklch(0.22 0.035 290)", "oklch(0.4 0.03 290 / 0.35)", "oklch(0.78 0.02 290)")
TECH_PILL_ACTIVE = ("oklch(0.42 0.1 290 / 0.55)", "oklch(0.75 0.09 290 / 0.6)", "oklch(0.95 0.05 290)")


def _type_pill_colors(key: str, active: bool) -> tuple[str, str, str]:
    hue = DREAM_TYPE_HUE[key]
    if hue is None:
        if active:
            return "oklch(0.4 0.01 290)", "oklch(0.45 0.01 290 / 0.5)", "oklch(0.95 0.01 290)"
        return "oklch(0.24 0.02 290)", "oklch(0.4 0.03 290 / 0.35)", "oklch(0.7 0.01 290)"
    if active:
        return f"oklch(0.4 0.1 {hue} / 0.55)", f"oklch(0.75 0.09 {hue} / 0.6)", f"oklch(0.95 0.05 {hue})"
    return NEUTRAL_PILL


def _type_badge_colors(key: str) -> tuple[str, str]:
    hue = DREAM_TYPE_HUE[key]
    if hue is None:
        return "oklch(0.32 0.01 290)", "oklch(0.75 0.01 290)"
    return f"oklch(0.3 0.09 {hue} / 0.45)", f"oklch(0.88 0.06 {hue})"


def _type_chart_color(key: str) -> str:
    hue = DREAM_TYPE_HUE[key]
    return "oklch(0.5 0.01 290)" if hue is None else f"oklch(0.78 0.09 {hue})"


def dream_type_badge_html(dream_type_key: str) -> str:
    bg, text = _type_badge_colors(dream_type_key)
    label = DREAM_TYPE_LABELS.get(dream_type_key, dream_type_key)
    return f'<span class="type-badge" style="background:{bg};color:{text};">{html.escape(label)}</span>'


def score_badge_html(score) -> str:
    if not score:
        return ""
    return f'<span class="pill pill-score">회상 {score}</span>'


def fmt_date(iso_str: str) -> str:
    """'2026-07-20' → '07.20' (목업의 짧은 날짜 표기)"""
    try:
        y, m, d = iso_str.split("-")[:3]
        return f"{m}.{d}"
    except (ValueError, AttributeError):
        return iso_str


def render_html_button(content_html: str, container_key: str, button_key: str) -> bool:
    """HTML로 그린 행 전체를 클릭 가능하게 만든다 (투명 버튼을 위에 덮어씀).

    스타일 태그를 content_html과 별도의 st.markdown 호출로 주입하면, 그 호출
    자체가 보이지 않는 형제 element-container가 되어 부모의 flex gap만큼
    불필요한 여백을 만든다. 그래서 스타일과 콘텐츠를 하나의 markdown 호출로
    합쳐서 렌더링한다.
    """
    style = f"""
        <style>
        .st-key-{container_key} {{ position: relative !important; }}
        html body div.st-key-{container_key} div[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"]) {{
            height: auto !important; flex: 0 0 auto !important; max-height: none !important;
        }}
        html body div.st-key-{container_key} {{
            height: auto !important; flex: 0 0 auto !important; max-height: none !important;
        }}
        .st-key-{container_key} div[data-testid="stElementContainer"]:has(div[data-testid="stButton"]) {{
            position: absolute !important; inset: 0 !important; z-index: 2 !important; width: 100% !important; height: 100% !important;
        }}
        .st-key-{container_key} div[data-testid="stButton"] {{
            position: absolute !important; inset: 0 !important; height: 100% !important; width: 100% !important;
        }}
        .st-key-{container_key} div[data-testid="stButton"] button {{
            width: 100% !important; height: 100% !important; min-height: 0 !important;
            background: transparent !important; border: none !important;
            box-shadow: none !important; color: transparent !important; padding: 0 !important;
        }}
        </style>
        """
    with st.container(key=container_key):
        st.markdown(style + content_html, unsafe_allow_html=True)
        return st.button(" ", key=button_key)


# ── pill / badge UI 헬퍼 ──────────────────────────────────────
# Claude Design 목업의 알약(pill) 버튼·뱃지·세그먼트 탭을 실제 Streamlit
# 위젯(button) + 컨테이너 key 스코프 CSS로 재현한다. 목업의 onClick="{{...}}"는
# 정적 프리뷰용 가짜 바인딩이라 그대로 옮길 수 없어, 클릭 가능한 실제 st.button을
# 쓰고 색만 CSS로 입힌다.

def _pill_row_style(container_key: str, color_map: dict[int, tuple[str, str, str]], small: bool = False) -> str:
    pad = "6px 11px" if small else "8px 13px"
    font_size = "11.5px" if small else "12.5px"
    rules = [
        f"""
        .st-key-{container_key} {{
            display:flex !important; flex-direction:row !important;
            flex-wrap:wrap !important; gap:7px !important;
        }}
        .st-key-{container_key} button {{
            border-radius:100px !important; padding:{pad} !important;
            font-size:{font_size} !important; font-weight:600 !important;
            box-shadow:none !important; transition:all .15s ease; min-height:0 !important;
        }}
        """
    ]
    for i, (bg, border, text) in color_map.items():
        rules.append(
            f'.st-key-{container_key} > div[data-testid="stElementContainer"]:nth-child({i}) button {{'
            f'background:{bg} !important; border:1px solid {border} !important; '
            f'color:{text} !important; }}'
        )
    return "<style>" + "".join(rules) + "</style>"


def render_type_picker(state_key: str = "record_type") -> str:
    """꿈 타입 단일 선택 pill 버튼 행. 선택된 타입 키를 반환."""
    if state_key not in st.session_state:
        st.session_state[state_key] = DREAM_TYPE_ORDER[0]
    selected = st.session_state[state_key]

    color_map = {
        i: _type_pill_colors(k, k == selected)
        for i, k in enumerate(DREAM_TYPE_ORDER, start=1)
    }
    st.markdown(_pill_row_style("typepicker", color_map), unsafe_allow_html=True)

    with st.container(key="typepicker"):
        for k in DREAM_TYPE_ORDER:
            if st.button(DREAM_TYPE_LABELS[k], key=f"typepicker_btn_{k}"):
                st.session_state[state_key] = k
                st.rerun()
    return st.session_state[state_key]


def render_technique_picker(state_key: str = "record_techniques") -> list[str]:
    """기법 다중 선택 pill 그리드 + '+ 직접 추가' 팝오버. 선택 목록을 반환."""
    if state_key not in st.session_state:
        st.session_state[state_key] = []
    selected: list[str] = st.session_state[state_key]

    options = list(db.TECHNIQUES) + [t for t in selected if t not in db.TECHNIQUES]

    color_map = {
        i: (TECH_PILL_ACTIVE if name in selected else NEUTRAL_PILL)
        for i, name in enumerate(options, start=1)
    }
    st.markdown(
        _pill_row_style("techpicker", color_map, small=True)
        + '<style>.st-key-techpicker [data-testid="stPopover"] button {'
        + "border-radius:100px !important; padding:6px 11px !important; "
        + "font-size:11.5px !important; font-weight:600 !important; "
        + "background:transparent !important; border:1px dashed oklch(0.5 0.02 290 / 0.5) !important; "
        + f'color:{C["muted"]} !important; box-shadow:none !important; min-height:0 !important; }}</style>',
        unsafe_allow_html=True,
    )

    with st.container(key="techpicker"):
        for name in options:
            if st.button(name, key=f"techpicker_btn_{name}"):
                if name in selected:
                    selected.remove(name)
                else:
                    selected.append(name)
                st.session_state[state_key] = selected
                st.rerun()

        with st.popover("+ 직접 추가"):
            new_name = st.text_input(
                "기법 이름", key=f"{state_key}_new_input",
                label_visibility="collapsed", placeholder="예: 커스텀 기법",
            )
            if st.button("추가", key=f"{state_key}_new_add"):
                cleaned = new_name.strip()
                if cleaned and cleaned not in selected:
                    selected.append(cleaned)
                    st.session_state[state_key] = selected
                    st.rerun()

    return st.session_state[state_key]


def render_pill_tabs(options: list[tuple[str, str]], state_key: str, container_key: str) -> str:
    """세그먼트형 pill 탭 (대시보드 탭, 리포트 기간 선택 등). 선택된 key를 반환."""
    if state_key not in st.session_state:
        st.session_state[state_key] = options[0][0]
    selected = st.session_state[state_key]

    st.markdown(
        f"""
        <style>
        .st-key-{container_key} {{
            background: {C["card"]};
            border-radius: 100px;
            padding: 4px;
        }}
        .st-key-{container_key} div[data-testid="stHorizontalBlock"] {{
            flex-wrap: nowrap !important;
            flex-direction: row !important;
            gap: 4px !important;
        }}
        .st-key-{container_key} div[data-testid="stColumn"] {{
            width: auto !important;
            flex: 1 1 0 !important;
            min-width: 0 !important;
        }}
        .st-key-{container_key} button {{
            border-radius: 100px !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
            border: none !important;
            background: transparent !important;
            color: {C["muted"]} !important;
            min-height: 0 !important;
        }}
        .st-key-{container_key} button[kind="primary"] {{
            background: oklch(0.4 0.09 290) !important;
            color: oklch(0.97 0.02 290) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key=container_key):
        cols = st.columns(len(options))
        for col, (key, label) in zip(cols, options):
            with col:
                if st.button(
                    label,
                    key=f"{container_key}_{key}",
                    type="primary" if selected == key else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[state_key] = key
                    st.rerun()
    return st.session_state[state_key]


def render_switch_row(label: str, state_key: str, default: bool = False, card: bool = False) -> bool:
    """목업과 동일한 커스텀 스위치 행 (진짜 st.toggle 대신 HTML+오버레이 버튼으로 직접 구현)."""
    if state_key not in st.session_state:
        st.session_state[state_key] = default
    val = st.session_state[state_key]

    track_bg = C["toggle_on"] if val else C["toggle_off"]
    knob_pos = 18 if val else 2
    wrapper_style = (
        f'background:{C["card"]};border-radius:14px;padding:11px 14px;' if card
        else "padding:6px 0;"
    )
    content = (
        f'<div style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;{wrapper_style}">'
        f'<span style="font-size:12.5px;color:{C["text3"]};">{html.escape(label)}</span>'
        f'<div style="width:38px;height:22px;border-radius:100px;background:{track_bg};position:relative;flex:none;">'
        f'<div style="position:absolute;top:2px;left:{knob_pos}px;width:18px;height:18px;border-radius:50%;'
        f'background:oklch(0.97 0.01 290);transition:.15s;"></div></div></div>'
    )
    if render_html_button(content, f"switchrow_{state_key}", f"switchbtn_{state_key}"):
        st.session_state[state_key] = not val
        st.rerun()
    return st.session_state[state_key]


def render_rc_counter(label: str, state_key: str, default: int = 0) -> int:
    """+/- 카운터. 라벨 왼쪽, 카운터 그룹 오른쪽 (실제 st.button + 강제 가로배치 컬럼)."""
    if state_key not in st.session_state:
        st.session_state[state_key] = default
    val = st.session_state[state_key]

    st.markdown(
        """
        <style>
        .st-key-rc_row { margin-bottom: 4px; margin-top: -8px !important; }
        .st-key-rc_row > div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important; flex-direction: row !important;
            align-items: center !important;
        }
        .st-key-rc_group [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important; flex-direction: row !important;
            align-items: center !important; gap: 10px !important; justify-content: flex-end !important;
        }
        .st-key-rc_group [data-testid="stColumn"] { width: auto !important; flex: 0 0 auto !important; min-width: 0 !important; }
        .st-key-rc_group { margin-top: -28px !important; }
        .st-key-rc_group button {
            width: 26px !important; height: 26px !important; min-height: 0 !important;
            border-radius: 50% !important; background: oklch(0.26 0.04 290) !important;
            border: none !important; box-shadow: none !important;
            color: oklch(0.9 0.02 290) !important; font-size: 15px !important; padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="rc_row"):
        col_label, col_group = st.columns([3, 2])
        with col_label:
            st.markdown(
                f'<div style="font-size:12.5px;color:{C["text3"]};">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )
        with col_group:
            with st.container(key="rc_group"):
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button("−", key="rc_minus_btn"):
                        st.session_state[state_key] = max(0, val - 1)
                        st.rerun()
                with c2:
                    st.markdown(
                        f'<div style="font-size:13.5px;font-weight:700;color:{C["text"]};'
                        f'text-align:center;line-height:26px;">{val}</div>',
                        unsafe_allow_html=True,
                    )
                with c3:
                    if st.button("+", key="rc_plus_btn"):
                        st.session_state[state_key] = val + 1
                        st.rerun()
    return st.session_state[state_key]


# ── 커스텀 차트 헬퍼 (Altair 대신 목업과 동일한 SVG/div 마크업) ──

def svg_line_chart(values: list[float]) -> str:
    n = len(values)
    if n == 0:
        return f'<div style="font-size:12px;color:{C["muted"]};padding:20px 0;text-align:center;">데이터가 없습니다.</div>'
    coords = []
    for i, v in enumerate(values):
        x = (i / (n - 1) * 300) if n > 1 else 150.0
        y = 96 - (max(0.0, min(10.0, v)) / 10) * 86
        coords.append(f"{x:.1f},{y:.1f}")
    line = " ".join(coords)
    area = f"0,96 {line} 300,96"
    return (
        '<svg viewBox="0 0 300 100" style="width:100%;height:90px;display:block;">'
        f'<polygon points="{area}" fill="oklch(0.78 0.09 290 / 0.18)"></polygon>'
        f'<polyline points="{line}" fill="none" stroke="oklch(0.78 0.09 290)" '
        'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>'
        '</svg>'
    )


def donut_chart_html(dist: list[dict], total_count: int) -> str:
    present = [r for r in dist if r["cnt"] > 0]
    total = sum(r["cnt"] for r in present) or 1
    stops, cum, legend_rows = [], 0, []
    for r in present:
        key = r["dream_type"]
        pct = round(r["cnt"] / total * 100)
        color = _type_chart_color(key)
        stops.append(f"{color} {cum}% {cum + pct}%")
        cum += pct
        label = DREAM_TYPE_LABELS.get(key, key)
        legend_rows.append(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:{C["muted4"]};">'
            f'<span style="width:7px;height:7px;border-radius:50%;background:{color};"></span>{html.escape(label)} {pct}%</div>'
        )
    gradient = f"conic-gradient(from -90deg, {', '.join(stops)})" if stops else C["heat_empty"]
    return (
        '<div style="display:flex;align-items:center;gap:18px;">'
        '<div style="position:relative;width:96px;height:96px;flex:none;">'
        f'<div style="position:absolute;inset:0;border-radius:50%;background:{gradient};"></div>'
        f'<div style="position:absolute;inset:16px;border-radius:50%;background:{C["card"]};display:flex;'
        f'align-items:center;justify-content:center;font-size:11px;font-weight:700;color:{C["chip_text"]};">'
        f'{total_count}개</div></div>'
        f'<div style="display:flex;flex-direction:column;gap:5px;">{"".join(legend_rows)}</div></div>'
    )


def vbar_chart_html(items: list[tuple[str, float]], color: str, height_px: int = 72, label_size: str = "10px") -> str:
    if not items:
        return f'<div style="font-size:12px;color:{C["muted"]};padding:20px 0;text-align:center;">데이터가 없습니다.</div>'
    max_v = max(v for _, v in items) or 1
    bars = []
    for label, v in items:
        pct = round(v / max_v * 100) if max_v else 0
        bars.append(
            '<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;'
            f'justify-content:flex-end;height:100%;"><div style="width:100%;border-radius:6px 6px 0 0;'
            f'background:{color};height:{pct}%;"></div>'
            f'<span style="font-size:{label_size};color:{C["faint2"]};">{html.escape(str(label))}</span></div>'
        )
    return (
        f'<div style="display:flex;align-items:flex-end;gap:8px;height:{height_px}px;">'
        + "".join(bars) + "</div>"
    )


def hbar_progress_html(items: list[dict]) -> str:
    if not items:
        return f'<div style="font-size:12px;color:{C["muted"]};padding:12px 0;">데이터가 없습니다.</div>'
    rows = []
    for it in items:
        rows.append(
            '<div style="margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:11.5px;color:{C["text3"]};'
            f'margin-bottom:4px;"><span>{html.escape(it["label"])}</span><span>{html.escape(it["meta"])}</span></div>'
            f'<div style="height:7px;border-radius:100px;background:{C["chip"]};overflow:hidden;">'
            f'<div style="height:100%;width:{it["pct"]}%;background:{C["accent"]};border-radius:100px;"></div>'
            '</div></div>'
        )
    return "".join(rows)


def compare_groups_html(groups: list[dict]) -> str:
    rows = []
    for g in groups:
        rows.append(
            f'<div style="margin-bottom:12px;"><div style="font-size:11.5px;color:{C["text3"]};margin-bottom:5px;">'
            f'{html.escape(g["label"])}</div>'
            '<div style="display:flex;gap:6px;align-items:flex-end;height:40px;">'
            '<div style="flex:1;height:100%;display:flex;flex-direction:column;justify-content:flex-end;">'
            f'<div style="border-radius:5px 5px 0 0;background:oklch(0.76 0.09 350);height:{g["yes_pct"]}%;"></div></div>'
            '<div style="flex:1;height:100%;display:flex;flex-direction:column;justify-content:flex-end;">'
            f'<div style="border-radius:5px 5px 0 0;background:oklch(0.78 0.09 190);height:{g["no_pct"]}%;"></div></div>'
            '</div>'
            f'<div style="display:flex;justify-content:space-between;font-size:9.5px;color:{C["faint2"]};margin-top:3px;">'
            f'<span>했음 {g["yes"]}</span><span>안 함 {g["no"]}</span></div></div>'
        )
    return "".join(rows)


def _heat_level(value: float, sparse: bool) -> int:
    if not value:
        return 0
    if sparse:
        return 4
    return max(1, min(4, int(value)))


def calendar_heat_html(data: list[dict], date_col: str, value_col: str, hue: int, sparse: bool = False) -> str:
    end = date.today()
    start = end - timedelta(days=364)
    vals = {r[date_col]: r[value_col] for r in data}
    opacities = [0.12, 0.3, 0.5, 0.72, 0.95]

    cells = []
    d = start
    while d <= end:
        v = vals.get(d.isoformat(), 0)
        level = _heat_level(v, sparse)
        color = C["heat_empty"] if level == 0 else f"oklch(0.78 0.09 {hue} / {opacities[level]})"
        cells.append(f'<div style="aspect-ratio:1;border-radius:3px;background:{color};"></div>')
        d += timedelta(days=1)

    weeks = (end - start).days // 7 + 1
    return (
        f'<div style="display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,1fr);'
        f'grid-template-columns:repeat({weeks},1fr);gap:3px;">{"".join(cells)}</div>'
    )


def inject_style():
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

        html, body, [class*="css"] {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont,
                'Segoe UI', system-ui, sans-serif !important;
        }}
        .stApp {{ background: {C["bg"]} !important; }}
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none !important; }}
        ::-webkit-scrollbar {{ width: 0; height: 0; }}

        /* ── 타이틀 ──────────────────────────────────────── */
        h1, h2, h3 {{ letter-spacing: -0.02em; font-weight: 700 !important; color: {C["text"]} !important; }}
        .section-title {{ font-size: 16px; font-weight: 700; color: {C["text"]}; margin-bottom: 14px; }}

        /* ── 버튼 ────────────────────────────────────────── */
        .stButton button, .stFormSubmitButton button {{
            border-radius: 14px !important;
            font-weight: 600;
            transition: all 0.15s ease;
        }}
        button[kind="primary"] {{
            background: linear-gradient(135deg, oklch(0.7 0.1 290), oklch(0.68 0.1 320)) !important;
            color: oklch(0.14 0.02 290) !important;
            border: none !important;
            box-shadow: none !important;
        }}
        button[kind="secondary"] {{
            background: {C["card"]} !important;
            border: 1px solid {C["border"]} !important;
            color: {C["text3"]} !important;
        }}

        /* ── 토글 스위치 (st.toggle) ───────────────────────── */
        div[data-testid="stCheckbox"] label div:first-of-type {{
            background: {C["toggle_off"]} !important;
        }}
        div[data-testid="stCheckbox"] label:has(input:checked) div:first-of-type {{
            background: {C["toggle_on"]} !important;
        }}

        /* ── 입력 요소 ────────────────────────────────────── */
        div[data-baseweb="input"], div[data-baseweb="textarea"],
        div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {{
            background: {C["card_soft"]} !important;
            border: 1px solid {C["border"]} !important;
            border-radius: 14px !important;
        }}
        input, textarea {{ color: {C["text"]} !important; }}

        /* ── 슬라이더 (수면 시간) ──────────────────────────── */
        div[data-testid="stSlider"] label {{ display: none !important; }}
        div[data-testid="stSliderThumbValue"], div[data-testid="stSliderTickBar"] {{ display: none !important; }}
        div[data-testid="stSlider"] [role="group"] {{ margin-top: 4px !important; }}
        div[data-testid="stSlider"] {{ margin-bottom: -18px !important; }}

        /* ── 카드형 컨테이너 (expander, metric, popover) ──── */
        div[data-testid="stExpander"] {{
            background: {C["card"]};
            border-radius: 16px !important;
            border: 1px solid {C["border_soft"]} !important;
            overflow: hidden;
        }}
        div[data-testid="stPopoverBody"] {{
            background: {C["card"]} !important;
            border: 1px solid {C["border"]} !important;
            border-radius: 14px !important;
        }}
        div[data-testid="stMetric"] {{
            background: {C["card"]};
            border-radius: 16px;
            padding: 0.9rem 1rem;
        }}

        button[data-baseweb="tab"] {{ font-weight: 600; color: {C["muted"]} !important; }}
        div[data-baseweb="tab-highlight"] {{ background-color: {C["accent"]} !important; }}
        hr {{ border-color: {C["border_soft"]}; }}

        [data-testid="stAppDeployButton"], [data-testid="stMainMenuButton"] {{ display: none !important; }}
        [data-testid="stForm"] {{ border: none !important; padding: 0 !important; }}

        /* ── 스트릭 카드 (목업 그라디언트 카드) ───────────── */
        .stat-card {{
            background: linear-gradient(135deg, oklch(0.26 0.05 300 / 0.9), oklch(0.24 0.06 320 / 0.7));
            border: 1px solid oklch(0.5 0.05 300 / 0.3);
            border-radius: 20px;
            padding: 16px 18px;
            margin-bottom: 20px;
        }}
        .stat-card .stat-label {{ font-size: 11.5px; color: {C["muted3"]}; margin-top: 2px; }}
        .stat-card .stat-value {{ font-size: 20px; font-weight: 700; color: {C["text"]}; }}
        .stat-card .rc-tip {{
            font-size: 12px; line-height: 1.5; color: oklch(0.85 0.03 300);
            padding-top: 10px; margin-top: 10px; border-top: 1px solid oklch(0.6 0.05 300 / 0.25);
        }}

        .pill {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 100px;
            font-size: 10.5px;
            font-weight: 700;
            background: {C["chip"]};
            color: {C["chip_text"]};
            margin-right: 0.3rem;
        }}
        .pill-score {{ background: {C["chip"]}; color: {C["chip_text"]}; }}
        .type-badge {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 100px;
            font-size: 10.5px;
            font-weight: 700;
            margin-right: 0.3rem;
        }}
        .dream-card-meta {{ color: {C["muted2"]}; font-size: 11px; margin-bottom: 6px; }}
        .dream-card-title {{ font-size: 14px; font-weight: 600; color: {C["text2"]}; margin-bottom: 0.4rem; }}

        .tag-row {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 0.3rem; }}
        .tag-chip {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 100px;
            font-size: 10.5px;
            font-weight: 600;
            background: {C["chip2"]};
            color: {C["chip2_text"]};
        }}

        /* ── 카드 (st.container(key=...)) ─────────────────── */
        [class*="st-key-dcard_"], [class*="st-key-kpi_"], [class*="st-key-chartbox_"] {{
            background: {C["card"]} !important;
            border: none !important;
            border-radius: 18px !important;
            box-shadow: none !important;
        }}
        [class*="st-key-dcard_"] {{ padding: 14px 16px !important; }}
        [class*="st-key-kpi_"] {{ padding: 13px 14px !important; }}
        [class*="st-key-chartbox_"] {{ padding: 16px !important; }}
        [class*="st-key-dcard_"] [data-testid="stMarkdownContainer"],
        [class*="st-key-kpi_"] [data-testid="stMarkdownContainer"],
        [class*="st-key-chartbox_"] [data-testid="stMarkdownContainer"] {{
            margin: 0 !important;
        }}
        .st-key-kpi_row {{ background: transparent !important; border-radius: 0 !important; padding: 0 !important; }}
        .st-key-kpi_row [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; gap: 0.6rem !important; }}
        .st-key-kpi_row [data-testid="stColumn"] {{ flex: 1 1 45% !important; min-width: 140px !important; width: auto !important; }}

        /* ── 컨디션 접기/펼치기 헤더 ───────────────────────── */
        .st-key-cond_toggle button {{
            width: 100%; text-align: left; justify-content: flex-start !important;
            background: transparent !important; border: none !important; box-shadow: none !important;
            border-top: 1px solid {C["border_soft"]} !important; border-radius: 0 !important;
            padding: 12px 4px !important; font-size: 13px !important; font-weight: 600 !important;
            color: {C["text3"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_style()


def check_password() -> bool:
    """secrets.toml의 APP_PASSWORD와 대조하는 단순 비밀번호 게이트."""
    if st.session_state.get("authenticated"):
        return True

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<div style='height: 12vh'></div>", unsafe_allow_html=True)
        st.title(":material/nights_stay: REMinder")
        st.caption("오늘 밤 꿈을 기록해보세요.")
        app_password = st.secrets.get("APP_PASSWORD", "")
        if not app_password:
            st.error(".streamlit/secrets.toml에 APP_PASSWORD가 설정되어 있지 않습니다.")
            return False

        with st.form("login_form"):
            pw = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("입장", use_container_width=True, type="primary")
        if submitted:
            if pw == app_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    return False


if not check_password():
    st.stop()

DREAM_TYPE_LABELS = {k: v for k, v in db.DREAM_TYPES.items()}
DREAM_TYPE_OPTIONS = list(DREAM_TYPE_LABELS.keys())


# ── 상단 브랜드 헤더 (목업의 로고+날짜 바, 모든 화면에 공통) ──

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def top_header():
    today = date.today()
    today_label = f"{today.strftime('%Y.%m.%d')} ({WEEKDAY_KO[today.weekday()]})"
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="position:relative;width:22px;height:22px;">
                    <div style="position:absolute;inset:0;border-radius:50%;background:oklch(0.82 0.1 290);"></div>
                    <div style="position:absolute;top:-2px;left:6px;width:22px;height:22px;border-radius:50%;background:{C["bg"]};"></div>
                </div>
                <span style="font-size:17px;font-weight:700;color:{C["text"]};letter-spacing:-0.02em;">REMinder</span>
            </div>
            <span style="font-size:12px;color:{C["muted2"]};">{today_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def streak_card_html(streak: dict, with_tip: bool = True) -> str:
    tip = (
        f'<div class="rc-tip">🌙 Reality Check &nbsp;·&nbsp; 손가락을 보고 다시 세어보세요 — '
        f'숫자가 달라 보이면, 지금은 꿈입니다.</div>'
        if with_tip else ""
    )
    return (
        '<div class="stat-card"><div style="display:flex;gap:22px;">'
        f'<div><div class="stat-value">{streak["streak"]}일</div><div class="stat-label">연속 기록</div></div>'
        f'<div><div class="stat-value">{streak["total_days"]}일</div><div class="stat-label">전체 기록</div></div>'
        f'</div>{tip}</div>'
    )


# ── 꿈 기록 폼 ──────────────────────────────────────────────

def page_record():
    st.markdown('<div class="section-title">꿈 기록하기</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="font-size:12.5px;color:{C["muted"]};margin-bottom:8px;">꿈 타입</div>', unsafe_allow_html=True)
    dream_type_key = render_type_picker("record_type")

    st.markdown(f'<div style="font-size:12.5px;color:{C["muted"]};margin:18px 0 8px;">제목 (선택)</div>', unsafe_allow_html=True)
    title = st.text_input(
        "제목", key="record_title", placeholder="예: 하늘을 나는 도서관", label_visibility="collapsed",
    )

    st.markdown(f'<div style="font-size:12.5px;color:{C["muted"]};margin:14px 0 8px;">내용</div>', unsafe_allow_html=True)
    content = st.text_area(
        "꿈 내용", height=160, key="record_content",
        placeholder="기억나는 만큼 편하게 적어보세요...", label_visibility="collapsed",
    )

    if "record_conditions_open" not in st.session_state:
        st.session_state.record_conditions_open = True
    conditions_open = st.session_state.record_conditions_open
    chevron = "︿" if conditions_open else "﹀"
    with st.container(key="cond_toggle"):
        if st.button(f"수면 기법 & 컨디션 (선택)   {chevron}", key="cond_toggle_btn"):
            st.session_state.record_conditions_open = not conditions_open
            st.rerun()

    techniques: list[str] = st.session_state.get("record_techniques", [])
    sleep_hours = st.session_state.get("record_sleep", 0.0)
    alarm_used = st.session_state.get("record_alarm", False)
    caffeine_prev_day = st.session_state.get("record_caffeine", False)
    alcohol_prev_day = st.session_state.get("record_alcohol", False)
    reality_check_count = st.session_state.get("record_rc", 0)

    if conditions_open:
        st.markdown(f'<div style="font-size:12px;color:{C["muted"]};margin:6px 0 8px;">기법 (다중 선택)</div>', unsafe_allow_html=True)
        techniques = render_technique_picker("record_techniques")

        if techniques:
            desc_rows = "".join(
                f'<div style="font-size:11.5px;line-height:1.6;color:{C["muted3"]};padding:3px 0;">'
                f'<span style="color:oklch(0.85 0.03 290);font-weight:600;">{html.escape(t)}</span>'
                f' — {html.escape(db.TECHNIQUE_DESC.get(t, ""))}</div>'
                for t in techniques
            )
            st.markdown(
                f'<div style="background:{C["card"]};border-radius:14px;padding:10px 13px;margin-bottom:16px;">{desc_rows}</div>',
                unsafe_allow_html=True,
            )

        sleep_hours_display = st.session_state.get("record_sleep", 0.0)
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2px;">'
            f'<span style="font-size:12.5px;color:{C["text3"]};">수면 시간</span>'
            f'<span style="font-size:12.5px;font-weight:700;color:{C["text"]};">{sleep_hours_display}시간</span></div>',
            unsafe_allow_html=True,
        )
        sleep_hours = st.slider(
            "수면 시간", min_value=0.0, max_value=12.0, step=0.5,
            key="record_sleep", label_visibility="collapsed",
        )
        alarm_used = render_switch_row("알람 사용", "record_alarm")
        caffeine_prev_day = render_switch_row("전날 카페인", "record_caffeine")
        alcohol_prev_day = render_switch_row("전날 알코올", "record_alcohol")
        reality_check_count = render_rc_counter("어제 Reality Check 횟수", "record_rc")

    st.write("")
    analyze = render_switch_row("저장 후 AI 분석 바로 실행", "record_analyze", default=True, card=True)
    st.write("")
    submitted = st.button(
        "꿈 저장하기", use_container_width=True, type="primary", key="record_submit",
    )

    if submitted:
        if not content.strip():
            st.error("꿈 내용을 입력해주세요.")
            return

        dream_id = db.add_dream(
            dream_date=str(date.today()),
            content=content,
            title=title,
            dream_type=dream_type_key,
        )
        st.success(f"저장 완료 (ID: {dream_id})")

        has_condition = (
            bool(techniques) or sleep_hours > 0 or alarm_used
            or caffeine_prev_day or alcohol_prev_day or reality_check_count > 0
        )
        if has_condition:
            db.update_condition(
                dream_id,
                techniques_tried=techniques,
                sleep_hours=float(sleep_hours) if sleep_hours > 0 else None,
                alarm_used=alarm_used,
                caffeine_prev_day=caffeine_prev_day,
                alcohol_prev_day=alcohol_prev_day,
                reality_check_count=int(reality_check_count),
            )

        if dream_type_key == "NO_MEMORY":
            with st.spinner("회상 유도 질문 생성 중…"):
                questions = llm.get_partial_recall_prompt(content)
            q_rows = "".join(
                f'<div style="font-size:12.5px;color:{C["text3"]};line-height:1.6;padding:4px 0;">· {html.escape(q)}</div>'
                for q in questions
            )
            st.markdown(
                f'<div style="background:{C["card_soft"]};border-radius:16px;padding:14px 16px;margin:16px 0;">'
                f'<div style="font-size:12px;font-weight:600;color:{C["accent"]};margin-bottom:8px;">AI가 회상을 도와드릴게요</div>'
                f'{q_rows}</div>',
                unsafe_allow_html=True,
            )

        if analyze:
            with st.spinner("AI 분석 중…"):
                result = llm.analyze_dream(content, DREAM_TYPE_LABELS[dream_type_key])
            db.update_analysis(
                dream_id,
                analysis_text=result.get("analysis_text", ""),
                recall_score=result.get("recall_score"),
                recurring_people=result.get("recurring_people", []),
                recurring_places=result.get("recurring_places", []),
                recurring_emotions=result.get("recurring_emotions", []),
            )
            _show_analysis(result)


def _show_analysis(result: dict):
    st.divider()
    st.subheader(":material/auto_fix_high: AI 분석 결과")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(result.get("analysis_text", ""))
    with col2:
        score = result.get("recall_score")
        st.metric("회상 점수", f"{score}/10" if score is not None else "-")

    people = result.get("recurring_people", [])
    places = result.get("recurring_places", [])
    emotions = result.get("recurring_emotions", [])

    if any([people, places, emotions]):
        st.subheader(":material/repeat: 반복 요소")
        c1, c2, c3 = st.columns(3)
        for col, label, items in [(c1, "인물", people), (c2, "장소", places), (c3, "감정", emotions)]:
            with col:
                st.caption(label)
                if items:
                    chips = "".join(f'<span class="tag-chip">{html.escape(str(t))}</span>' for t in items)
                    st.markdown(f'<div class="tag-row">{chips}</div>', unsafe_allow_html=True)
                else:
                    st.caption("—")


# ── 꿈 목록 ─────────────────────────────────────────────────

def page_list():
    dreams = db.list_dreams(limit=100)

    if not dreams:
        st.markdown('<div class="section-title">꿈 목록</div>', unsafe_allow_html=True)
        st.info("아직 기록된 꿈이 없습니다.")
        return

    st.markdown(
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
        f'margin-top:-26px;margin-bottom:18px;">'
        f'<span style="font-size:16px;font-weight:700;color:{C["text"]};">꿈 목록</span>'
        f'<span style="font-size:12px;color:{C["muted2"]};">최근 {len(dreams)}개</span></div>',
        unsafe_allow_html=True,
    )

    for row in dreams:
        with st.container(border=True, key=f"dcard_{row['id']}"):
            score_pill = score_badge_html(row["recall_score"])
            expand_key = f"expand_{row['id']}"
            expanded = st.session_state.get(expand_key, False)
            chevron = "︿" if expanded else "﹀"
            header_html = (
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                f'<span style="font-size:11px;color:{C["muted2"]};">{fmt_date(row["dream_date"])}</span>'
                f'{dream_type_badge_html(row["dream_type"])}{score_pill}</div>'
                f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                f'<span style="font-size:14px;font-weight:600;color:{C["text2"]};">{html.escape(row["title"] or "(제목 없음)")}</span>'
                f'<span style="font-size:13px;color:{C["faint"]};">{chevron}</span></div>'
            )
            if render_html_button(header_html, f"dcardhdr_{row['id']}", f"toggle_{row['id']}"):
                st.session_state[expand_key] = not expanded
                st.rerun()

            if expanded:
                st.markdown(
                    f'<div style="margin-top:12px;padding-top:12px;border-top:1px solid {C["border_soft"]};">'
                    f'<div style="font-size:12.5px;line-height:1.6;color:{C["text3"]};margin-bottom:10px;">'
                    f'{html.escape(row["content"])}</div>'
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;font-size:11px;'
                    f'color:{C["faint2"]};margin-bottom:10px;">'
                    f'<div>수면 {row["sleep_hours"] or 0}h</div><div>RC {row["reality_check_count"] or 0}회</div>'
                    f'<div>알람 {"사용" if row["alarm_used"] else "미사용"}</div>'
                    f'<div>카페인 {"O" if row["caffeine_prev_day"] else "X"} · 알코올 {"O" if row["alcohol_prev_day"] else "X"}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

                if row["analysis_text"]:
                    people = json.loads(row["recurring_people"] or "[]")
                    places = json.loads(row["recurring_places"] or "[]")
                    emotions = json.loads(row["recurring_emotions"] or "[]")
                    tags = people + places + emotions
                    chips = "".join(f'<span class="tag-chip">{html.escape(str(t))}</span>' for t in tags)
                    st.markdown(
                        f'<div style="background:oklch(0.24 0.035 290);border-radius:12px;padding:10px 12px;margin-bottom:10px;">'
                        f'<div style="font-size:11px;font-weight:700;color:{C["accent"]};margin-bottom:4px;">AI 분석</div>'
                        f'<div style="font-size:12px;line-height:1.6;color:{C["text3"]};margin-bottom:8px;">'
                        f'{html.escape(row["analysis_text"])}</div>'
                        f'<div class="tag-row">{chips}</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <style>
                        .st-key-analyzebtn_{row['id']} button {{
                            background: oklch(0.28 0.04 290) !important; border: none !important;
                            box-shadow: none !important; color: oklch(0.9 0.02 290) !important;
                            font-weight: 700 !important; border-radius: 12px !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.container(key=f"analyzebtn_{row['id']}"):
                        if st.button("AI 분석 실행", key=f"analyze_{row['id']}", use_container_width=True):
                            with st.spinner("분석 중…"):
                                result = llm.analyze_dream(
                                    row["content"],
                                    DREAM_TYPE_LABELS.get(row["dream_type"], row["dream_type"]),
                                )
                            db.update_analysis(
                                row["id"],
                                analysis_text=result.get("analysis_text", ""),
                                recall_score=result.get("recall_score"),
                                recurring_people=result.get("recurring_people", []),
                                recurring_places=result.get("recurring_places", []),
                                recurring_emotions=result.get("recurring_emotions", []),
                            )
                            st.rerun()

                st.markdown(
                    f"""
                    <style>
                    .st-key-delbtn_{row['id']} {{ margin-top: -12px !important; }}
                    .st-key-delbtn_{row['id']} button {{
                        background: transparent !important; border: none !important; box-shadow: none !important;
                        color: {C["faint"]} !important; font-size: 11.5px !important; font-weight: 400 !important;
                        padding: 2px 0 !important; min-height: 0 !important;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                with st.container(key=f"delbtn_{row['id']}"):
                    if st.button("삭제", key=f"del_{row['id']}", use_container_width=True):
                        db.delete_dream(row["id"])
                        st.rerun()
        st.write("")


# ── 대시보드 ─────────────────────────────────────────────────

def page_dashboard():
    st.markdown('<div class="section-title">대시보드</div>', unsafe_allow_html=True)

    streak = db.get_streak()
    type_dist_kpi = db.get_type_distribution()
    trend_kpi = db.get_recall_trend(days=30)
    lucid_cnt = sum(r["cnt"] for r in type_dist_kpi if r["dream_type"] == "LUCID")
    avg_score = (
        round(sum(r["avg_score"] for r in trend_kpi) / len(trend_kpi), 1)
        if trend_kpi else None
    )

    kpis = [
        ("연속 기록일", f"{streak['streak']}일", "kpi_streak"),
        ("전체 기록일", f"{streak['total_days']}일", "kpi_total"),
        ("평균 회상 점수", f"{avg_score}" if avg_score is not None else "-", "kpi_score"),
        ("자각몽 횟수", f"{lucid_cnt}회", "kpi_lucid"),
    ]
    with st.container(key="kpi_row"):
        cols = st.columns(4)
        for col, (label, value, key) in zip(cols, kpis):
            with col:
                with st.container(border=True, key=key):
                    st.markdown(
                        f'<div style="font-size:19px;font-weight:700;color:{C["text"]};">{value}</div>'
                        f'<div style="font-size:11px;color:{C["muted"]};margin-top:3px;">{label}</div>',
                        unsafe_allow_html=True,
                    )
    st.write("")

    dash_tab = render_pill_tabs(
        [("score", "점수 & 분포"), ("calendar", "캘린더"), ("technique", "기법 & 컨디션")],
        state_key="dashboard_tab", container_key="dash_tabs",
    )
    st.write("")

    def chart_box(title: str, body_html: str, key: str):
        with st.container(border=True, key=key):
            st.markdown(
                f'<div style="font-size:12.5px;font-weight:700;color:{C["text2"]};margin-bottom:12px;">{title}</div>{body_html}',
                unsafe_allow_html=True,
            )

    # ── 점수 & 분포 ──────────────────────────────────────────
    if dash_tab == "score":
        trend = db.get_recall_trend(days=30)
        type_dist = db.get_type_distribution()
        lucid_trend = db.get_lucid_trend(months=6)
        dream_count = sum(r["cnt"] for r in type_dist)

        chart_box(
            "회상 점수 추이 · 최근 30일",
            svg_line_chart([r["avg_score"] for r in trend]),
            "chartbox_trend",
        )
        st.write("")
        chart_box("꿈 타입 분포", donut_chart_html(type_dist, dream_count), "chartbox_dist")
        st.write("")
        chart_box(
            "자각몽 빈도 · 최근 6개월",
            vbar_chart_html([(r["month"], r["lucid_cnt"]) for r in lucid_trend], _type_chart_color("LUCID")),
            "chartbox_lucid_monthly",
        )

    # ── 캘린더 ────────────────────────────────────────────────
    elif dash_tab == "calendar":
        activity = db.get_activity_calendar(days=365)
        lucid_cal = db.get_lucid_calendar(days=365)

        chart_box(
            "기록 캘린더 · 최근 1년",
            calendar_heat_html(activity, "dream_date", "cnt", 290),
            "chartbox_cal_record",
        )
        st.write("")
        lucid_only = [r for r in lucid_cal if r["is_lucid"]]
        chart_box(
            "자각몽 발생 캘린더 · 최근 1년",
            calendar_heat_html(lucid_only, "dream_date", "is_lucid", LUCID_HUE, sparse=True),
            "chartbox_cal_lucid",
        )

    # ── 기법 & 컨디션 ─────────────────────────────────────────
    elif dash_tab == "technique":
        technique_stats = db.get_technique_stats()
        condition_data = db.get_condition_recall_stats()

        if technique_stats:
            df_t = pd.DataFrame(technique_stats).sort_values("used", ascending=False)
            items = [
                {"label": r["technique"], "meta": f'{r["used"]}회 · 연관율 {r["lucid_rate"]}%', "pct": 0}
                for _, r in df_t.iterrows()
            ]
            max_used = df_t["used"].max() or 1
            for it, (_, r) in zip(items, df_t.iterrows()):
                it["pct"] = round(r["used"] / max_used * 100)
            chart_box("기법별 사용 횟수 & 자각몽 연관율", hbar_progress_html(items), "chartbox_tech")
        else:
            st.info("기법 데이터가 없습니다.\n꿈 기록 시 '수면 기법 & 컨디션' 섹션을 작성해보세요.")

        if condition_data:
            df_c = pd.DataFrame(condition_data)
            df_scored = df_c[df_c["recall_score"].notna()].copy()

            df_sleep = df_scored[
                df_scored["sleep_hours"].notna() & (df_scored["sleep_hours"] > 0)
            ].copy()
            if not df_sleep.empty:
                bins = [0, 5, 6, 7, 8, 9, 25]
                labels = ["~5h", "5~6h", "6~7h", "7~8h", "8~9h", "9h+"]
                df_sleep["bucket"] = pd.cut(df_sleep["sleep_hours"], bins=bins, labels=labels, right=False)
                grouped = df_sleep.groupby("bucket", observed=True)["recall_score"].mean().reset_index()
                st.write("")
                chart_box(
                    "수면 시간별 평균 회상 점수",
                    vbar_chart_html(
                        [(r["bucket"], r["recall_score"]) for _, r in grouped.iterrows()],
                        "oklch(0.76 0.09 250)", height_px=64, label_size="9.5px",
                    ),
                    "chartbox_sleep",
                )

            groups = []
            for col_name, label in [
                ("caffeine_prev_day", "카페인 섭취"),
                ("alcohol_prev_day", "알코올 섭취"),
                ("alarm_used", "알람 사용"),
            ]:
                sub = df_scored[df_scored[col_name].notna()]
                if sub.empty:
                    continue
                avg_yes = sub[sub[col_name] == 1]["recall_score"].mean()
                avg_no = sub[sub[col_name] == 0]["recall_score"].mean()
                if pd.isna(avg_yes) or pd.isna(avg_no):
                    continue
                groups.append({
                    "label": label,
                    "yes": round(float(avg_yes), 1), "no": round(float(avg_no), 1),
                    "yes_pct": round(float(avg_yes) / 10 * 100), "no_pct": round(float(avg_no) / 10 * 100),
                })
            if groups:
                st.write("")
                chart_box("컨디션별 평균 회상 점수 (섭취/사용 · 안 함)", compare_groups_html(groups), "chartbox_compare")

            df_rc = df_c[df_c["reality_check_count"] > 0].copy()
            if not df_rc.empty and df_rc["is_lucid"].notna().any():
                bins_rc = [0, 3, 6, 10, 100]
                labels_rc = ["1~2회", "3~5회", "6~9회", "10회+"]
                df_rc["rc_bucket"] = pd.cut(df_rc["reality_check_count"], bins=bins_rc, labels=labels_rc, right=False)
                grouped_rc = df_rc.groupby("rc_bucket", observed=True)["is_lucid"].mean().reset_index()
                grouped_rc["is_lucid"] = (grouped_rc["is_lucid"] * 100).round(1)
                st.write("")
                chart_box(
                    "Reality Check 횟수별 자각몽 발생률",
                    vbar_chart_html(
                        [(r["rc_bucket"], r["is_lucid"]) for _, r in grouped_rc.iterrows()],
                        C["accent"], height_px=64, label_size="9.5px",
                    ),
                    "chartbox_rc",
                )
        else:
            st.info("컨디션 데이터가 없습니다.\n꿈 기록 시 '수면 기법 & 컨디션' 섹션을 작성해보세요.")


# ── 검색 ─────────────────────────────────────────────────────

def page_search():
    st.markdown('<div class="section-title">검색</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .st-key-search_input div[data-baseweb="input"] { border-radius: 100px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="search_input"):
        query = st.text_input(
            "검색어", placeholder="제목, 내용, 분석 텍스트 검색",
            label_visibility="collapsed", icon=":material/search:",
        )

    st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
    use_ai = render_switch_row("AI 의미 검색", "search_ai_toggle", card=True)
    st.write("")

    if not query.strip():
        st.info("검색어를 입력하세요.")
        return

    if use_ai:
        with st.spinner("AI가 관련 꿈을 분석 중…"):
            all_rows = db.list_dreams(limit=500)
            all_dreams = [dict(r) for r in all_rows]
            matched_ids = set(llm.search_by_meaning(query, all_dreams))
            results = [d for d in all_dreams if d["id"] in matched_ids]
    else:
        results = db.search_dreams(query)

    st.markdown(
        f'<div style="font-size:11.5px;color:{C["faint2"]};margin-bottom:10px;">'
        f'{"AI 의미 검색" if use_ai else "키워드 검색"} 결과 {len(results)}개</div>',
        unsafe_allow_html=True,
    )
    if not results:
        st.info("검색 결과가 없습니다.")
        return

    for row in results:
        snippet = (row["content"] or row.get("analysis_text") or "").strip()
        if len(snippet) > 90:
            snippet = snippet[:90] + "…"
        st.markdown(
            f'<div style="background:{C["card"]};border-radius:16px;padding:13px 15px;margin-bottom:9px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">'
            f'<span style="font-size:10.5px;color:{C["muted2"]};">{fmt_date(row["dream_date"])}</span>'
            f'{dream_type_badge_html(row["dream_type"])}</div>'
            f'<div style="font-size:13.5px;font-weight:600;color:{C["text2"]};margin-bottom:4px;">'
            f'{html.escape(row["title"] or "(제목 없음)")}</div>'
            f'<div style="font-size:12px;color:{C["muted3"]};line-height:1.5;">{html.escape(snippet)}</div></div>',
            unsafe_allow_html=True,
        )


# ── 드림사인 & 리포트 ─────────────────────────────────────────

def page_dream_signs():
    st.markdown(
        f'<div class="section-title" style="margin-bottom:4px;">드림사인 & 리포트</div>'
        f'<div style="font-size:12px;color:{C["muted"]};margin-bottom:16px;">반복되는 상징을 읽어드려요</div>',
        unsafe_allow_html=True,
    )

    # ── 드림사인 클러스터링 ──────────────────────────────────
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{C["text2"]};margin-bottom:10px;">드림사인 Top 5</div>', unsafe_allow_html=True)

    elements = db.get_all_recurring_elements()
    if elements:
        freq_preview = Counter(elements).most_common(10)
        st.caption(
            "추출된 요소 상위 10개: "
            + ", ".join(f"{e}({c})" for e, c in freq_preview)
        )
    else:
        st.warning("아직 AI 분석된 꿈이 없습니다. 꿈을 기록하고 AI 분석을 먼저 실행해보세요.")

    if st.button("드림사인 분석 실행", use_container_width=True, disabled=not elements):
        with st.spinner(f"총 {len(elements)}개 요소 클러스터링 중…"):
            result = llm.cluster_dream_signs(elements)
        st.session_state["dream_signs_result"] = result

    if "dream_signs_result" in st.session_state:
        signs = st.session_state["dream_signs_result"].get("dream_signs", [])
        err = st.session_state["dream_signs_result"].get("error")
        if err:
            st.error(f"오류: {err}")
        elif signs:
            for i, sign in enumerate(signs, 1):
                related = sign.get("elements", [])
                tags = "".join(f'<span class="tag-chip">{html.escape(str(e))}</span>' for e in related)
                st.markdown(
                    f'<div style="background:{C["card"]};border-radius:16px;padding:13px 15px;margin:9px 0;">'
                    f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px;">'
                    f'<div style="display:flex;align-items:center;gap:8px;">'
                    f'<span style="font-size:11px;font-weight:700;color:{C["faint2"]};">{i:02d}</span>'
                    f'<span style="font-size:13.5px;font-weight:700;color:{C["text"]};">{html.escape(sign["sign"])}</span></div>'
                    f'<span style="font-size:11px;font-weight:700;padding:3px 9px;border-radius:100px;'
                    f'background:{C["chip2"]};color:{C["text2"]};">{sign.get("count", "?")}회</span></div>'
                    f'<div style="font-size:12px;color:{C["muted3"]};line-height:1.55;margin-bottom:7px;">'
                    f'{html.escape(sign.get("description", ""))}</div>'
                    f'<div class="tag-row">{tags}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("드림사인을 찾지 못했습니다. 꿈이 더 쌓이면 다시 시도해보세요.")

    # ── MILD 인텐션 ──────────────────────────────────────────
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{C["text2"]};margin:18px 0 10px;">MILD 인텐션</div>', unsafe_allow_html=True)

    top_signs = [e for e, _ in Counter(elements).most_common(5)] if elements else []
    custom_signs = st.text_input(
        "드림사인 (쉼표 구분, 직접 수정 가능)",
        value=", ".join(top_signs),
        placeholder="예: 학교, 가족, 높은 곳",
    )

    if st.button("인텐션 문장 생성", use_container_width=True):
        signs_list = [s.strip() for s in custom_signs.split(",") if s.strip()]
        with st.spinner("생성 중…"):
            intention = llm.generate_mild_intention(signs_list)
        st.session_state["mild_intention"] = intention

    if "mild_intention" in st.session_state:
        st.info(st.session_state["mild_intention"])
        st.caption("잠들기 전 이 문장을 10번 천천히 되뇌어보세요.")

    # ── 주간 리포트 ──────────────────────────────────────────
    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{C["text2"]};margin:18px 0 10px;">주간 리포트</div>', unsafe_allow_html=True)

    week_offset = int(render_pill_tabs(
        [("0", "이번주"), ("1", "지난주"), ("2", "2주 전"), ("3", "3주 전")],
        state_key="report_week_offset", container_key="report_period_tabs",
    ))
    st.write("")

    if st.button("리포트 생성", use_container_width=True):
        dreams = db.get_weekly_dreams(offset_days=week_offset * 7)
        if not dreams:
            st.warning("해당 기간에 기록된 꿈이 없습니다.")
        else:
            with st.spinner(f"꿈 {len(dreams)}개 분석 중…"):
                summary = llm.summarize_week(dreams)
            st.session_state["weekly_summary"] = summary
            st.session_state["weekly_summary_cnt"] = len(dreams)

    if "weekly_summary" in st.session_state:
        st.caption(f"꿈 {st.session_state['weekly_summary_cnt']}개 분석")
        st.write(st.session_state["weekly_summary"])


# ── 진입점 ───────────────────────────────────────────────────

NAV_PAGES = [
    ("record", "기록", ":material/edit_note:", page_record),
    ("list", "목록", ":material/format_list_bulleted:", page_list),
    ("dashboard", "대시보드", ":material/grid_view:", page_dashboard),
    ("search", "검색", ":material/search:", page_search),
    ("dream_signs", "리포트", ":material/auto_awesome:", page_dream_signs),
]

# 목업(REMinder.dc.html)의 커스텀 선 아이콘 — Material 아이콘 자리에 배경 이미지로 덮어씌운다.
NAV_ICON_SVG = {
    "record": (
        '<circle cx="12" cy="12" r="8.5" fill="none" stroke="{c}" stroke-width="1.8"/>'
        '<line x1="12" y1="8" x2="12" y2="16" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>'
        '<line x1="8" y1="12" x2="16" y2="12" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>'
    ),
    "list": (
        '<rect x="4" y="6" width="16" height="2.4" rx="1.2" fill="{c}"/>'
        '<rect x="4" y="11" width="16" height="2.4" rx="1.2" fill="{c}"/>'
        '<rect x="4" y="16" width="16" height="2.4" rx="1.2" fill="{c}"/>'
    ),
    "dashboard": (
        '<rect x="4" y="4" width="7" height="7" rx="1.6" fill="{c}"/>'
        '<rect x="13" y="4" width="7" height="7" rx="1.6" fill="{c}"/>'
        '<rect x="4" y="13" width="7" height="7" rx="1.6" fill="{c}"/>'
        '<rect x="13" y="13" width="7" height="7" rx="1.6" fill="{c}"/>'
    ),
    "search": (
        '<circle cx="10" cy="10" r="6.5" fill="none" stroke="{c}" stroke-width="1.8"/>'
        '<line x1="15" y1="15" x2="20" y2="20" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>'
    ),
    "dream_signs": (
        '<circle cx="12" cy="12" r="8" fill="{c}"/>'
        '<circle cx="16" cy="9" r="7.5" fill="oklch(0.14 0.026 290)"/>'
    ),
}


def _nav_icon_data_uri(page_key: str, color: str) -> str:
    body = NAV_ICON_SVG[page_key].format(c=color)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body}</svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def bottom_nav() -> str:
    if "page" not in st.session_state:
        st.session_state.page = NAV_PAGES[0][0]

    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 3.6rem !important; padding-bottom: 6rem; }}
        [data-testid="stSidebarUserContent"] {{ padding-bottom: 4.5rem; }}
        .st-key-bottom_nav {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 999999;
            background-color: oklch(0.14 0.026 290 / 0.9);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-top: 1px solid {C["border"]};
            padding: 0.75rem 0.5rem calc(0.75rem + env(safe-area-inset-bottom, 0px));
        }}
        .st-key-bottom_nav [data-testid="stHorizontalBlock"] {{
            flex-wrap: nowrap !important;
            gap: 0.25rem !important;
            margin: 0 !important;
        }}
        .st-key-bottom_nav > div[data-testid="stElementContainer"],
        .st-key-bottom_nav div[data-testid="stVerticalBlockBorderWrapper"] {{
            margin: 0 !important; padding: 0 !important;
        }}
        .st-key-bottom_nav [data-testid="stColumn"] {{
            width: auto !important;
            flex: 1 1 0 !important;
            min-width: 0 !important;
        }}
        .st-key-bottom_nav [data-testid="stHorizontalBlock"] {{ margin-top: -33px !important; }}
        .st-key-bottom_nav button {{
            width: 100%;
            padding: 0.25rem 0.25rem;
            font-size: 0.75rem;
            white-space: nowrap;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: {C["muted"]} !important;
            min-height: 0 !important;
        }}
        .st-key-bottom_nav button[kind="primary"] {{
            background: transparent !important;
            color: oklch(0.85 0.06 290) !important;
        }}
        .st-key-bottom_nav span[data-testid="stIconMaterial"] {{
            font-size: 0 !important;
            width: 20px !important; height: 20px !important;
            display: inline-block !important;
            background-size: contain !important; background-repeat: no-repeat !important;
            background-position: center !important;
        }}
        .st-key-bottom_nav button span[data-has-shortcut] {{
            display: flex !important; flex-direction: column !important;
            align-items: center !important; justify-content: center !important;
            gap: 3px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="bottom_nav"):
        cols = st.columns(len(NAV_PAGES))
        for col, (key, label, icon, _) in zip(cols, NAV_PAGES):
            with col:
                active = st.session_state.page == key
                icon_color = "oklch(0.85 0.06 290)" if active else C["muted"]
                data_uri = _nav_icon_data_uri(key, icon_color)
                st.markdown(
                    f'<style>.st-key-nav_{key} span[data-testid="stIconMaterial"] {{'
                    f'background-image: url("{data_uri}") !important; }}</style>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    label,
                    icon=icon,
                    key=f"nav_{key}",
                    type="primary" if active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.page = key
                    st.rerun()

    return st.session_state.page


top_header()
st.markdown(streak_card_html(db.get_streak()), unsafe_allow_html=True)
current_page = bottom_nav()
next(p for p in NAV_PAGES if p[0] == current_page)[3]()
