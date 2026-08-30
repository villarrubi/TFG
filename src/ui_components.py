"""Sistema visual compartido por las pantallas Streamlit."""

from html import escape
from textwrap import dedent

import streamlit as st


def aplicar_estilos_base(extra_css: str = "") -> None:
    """Aplica la identidad visual común y los estilos de los componentes."""
    st.markdown(
        dedent(
            f"""
        <style>
        :root {{
            --ink-950: #07131f;
            --ink-900: #0b1f33;
            --ink-800: #12304a;
            --ink-600: #49657a;
            --ink-500: #6a8192;
            --surface: #ffffff;
            --canvas: #f4f7f9;
            --line: #dce5ea;
            --teal-700: #0f766e;
            --teal-600: #0d9488;
            --teal-100: #ccfbf1;
            --shadow-sm: 0 8px 24px rgba(7, 19, 31, 0.06);
            --shadow-md: 0 18px 48px rgba(7, 19, 31, 0.10);
        }}
        html, body, [class*="css"] {{
            font-family: Inter, "Segoe UI", Arial, sans-serif;
        }}
        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 7% 0%, rgba(13, 148, 136, 0.08), transparent 27rem),
                radial-gradient(circle at 94% 13%, rgba(14, 116, 144, 0.07), transparent 25rem),
                var(--canvas);
        }}
        [data-testid="stHeader"] {{
            min-height: 0;
            height: 0;
            background: transparent;
        }}
        [data-testid="stToolbar"] {{ display: none !important; }}
        [data-testid="stAppDeployButton"] {{ display: none !important; }}
        [data-testid="stDecoration"] {{ display: none; }}
        #MainMenu, footer {{ visibility: hidden; }}
        .block-container {{
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 4rem;
        }}
        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {{ display: none !important; }}
        h1, h2, h3, h4 {{ color: var(--ink-900); letter-spacing: -0.025em; }}
        h3 {{ margin-top: 1.6rem !important; }}
        p, label, [data-testid="stCaptionContainer"] {{ color: var(--ink-600); }}
        code {{ border-radius: 6px; color: var(--teal-700); }}
        hr {{ border-color: var(--line); margin: 1.8rem 0; }}

        .app-brandbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
            min-height: 76px;
            padding: 15px 18px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 18px;
            color: #ffffff;
            background: linear-gradient(120deg, rgba(13, 148, 136, 0.18), transparent 45%), var(--ink-950);
            box-shadow: var(--shadow-md);
        }}
        .app-brand {{ display: flex; align-items: center; gap: 13px; min-width: 0; }}
        .app-brand-mark {{
            display: grid;
            place-items: center;
            width: 44px;
            height: 44px;
            flex: 0 0 44px;
            border: 1px solid rgba(153, 246, 228, 0.35);
            border-radius: 13px;
            color: #99f6e4;
            background: rgba(15, 118, 110, 0.22);
        }}
        .app-brand-mark svg {{ width: 25px; height: 25px; }}
        .app-brand-name {{
            color: #ffffff;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.1;
        }}
        .app-brand-subtitle {{ margin-top: 4px; color: #a9bbc8; font-size: 0.76rem; }}
        .app-brand-meta {{ display: flex; align-items: center; gap: 8px; white-space: nowrap; }}
        .app-live-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #2dd4bf;
            box-shadow: 0 0 0 5px rgba(45, 212, 191, 0.12);
        }}
        .app-brand-chip {{
            padding: 7px 10px;
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 999px;
            color: #c9d7e0;
            background: rgba(255, 255, 255, 0.05);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .st-key-top_navigation {{
            margin: 9px 0 24px;
            padding: 5px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.84);
            box-shadow: var(--shadow-sm);
            backdrop-filter: blur(10px);
        }}
        .st-key-top_navigation [data-testid="stHorizontalBlock"] {{ gap: 5px; }}
        .st-key-top_navigation .stButton > button {{
            min-height: 39px;
            border: 0;
            border-radius: 9px;
            color: var(--ink-600);
            background: transparent;
            box-shadow: none;
        }}
        .st-key-top_navigation .stButton > button:hover {{
            color: var(--ink-900);
            background: #edf3f5;
            transform: none;
        }}
        .st-key-top_navigation .stButton > button:disabled {{
            opacity: 1;
            color: #ffffff;
            background: var(--ink-900);
        }}
        .st-key-top_navigation .stButton > button:disabled p {{ color: #ffffff !important; }}

        .page-hero {{
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 30px;
            min-height: 190px;
            margin: 0 0 24px;
            padding: 30px 32px;
            border: 1px solid rgba(15, 118, 110, 0.2);
            border-radius: 22px;
            color: #ffffff;
            background: radial-gradient(circle at 92% 8%, rgba(45, 212, 191, 0.24), transparent 17rem), linear-gradient(125deg, #0b1f33 0%, #103249 58%, #0f5a59 125%);
            box-shadow: var(--shadow-md);
        }}
        .page-hero::after {{
            content: "";
            position: absolute;
            right: -70px;
            bottom: -120px;
            width: 310px;
            height: 310px;
            border: 1px solid rgba(153, 246, 228, 0.12);
            border-radius: 50%;
            box-shadow: 0 0 0 48px rgba(153, 246, 228, 0.035), 0 0 0 96px rgba(153, 246, 228, 0.02);
        }}
        .page-hero-copy {{ position: relative; z-index: 1; max-width: 780px; }}
        .page-eyebrow {{
            margin-bottom: 10px;
            color: #80e8d8;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }}
        .page-title {{
            margin: 0;
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 3.35rem);
            font-weight: 850;
            line-height: 1.02;
            letter-spacing: -0.045em;
        }}
        .page-description {{
            max-width: 720px;
            margin: 14px 0 0;
            color: #c2d2dc;
            font-size: 0.98rem;
            line-height: 1.55;
        }}
        .page-hero-aside {{
            position: relative;
            z-index: 1;
            min-width: 190px;
            padding: 13px 15px;
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 14px;
            color: #d9e5eb;
            background: rgba(3, 15, 25, 0.32);
            font-size: 0.78rem;
            line-height: 1.45;
            backdrop-filter: blur(8px);
        }}
        .page-hero-aside strong {{ display: block; margin-bottom: 3px; color: #ffffff; font-size: 0.9rem; }}

        .section-heading {{ display: flex; align-items: flex-start; gap: 12px; margin: 24px 0 13px; }}
        .section-index {{
            display: grid;
            place-items: center;
            width: 30px;
            height: 30px;
            flex: 0 0 30px;
            border-radius: 9px;
            color: var(--teal-700);
            background: var(--teal-100);
            font-size: 0.78rem;
            font-weight: 850;
        }}
        .section-title {{ color: var(--ink-900); font-size: 1.02rem; font-weight: 800; line-height: 1.2; }}
        .section-copy {{ margin-top: 3px; color: var(--ink-500); font-size: 0.82rem; line-height: 1.35; }}

        .ui-grid {{ display: grid; gap: 14px; margin: 14px 0 24px; }}
        .ui-grid-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .ui-grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
        .ui-grid-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
        .ui-card {{
            position: relative;
            overflow: hidden;
            min-height: 132px;
            padding: 17px 18px;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.94);
            box-shadow: var(--shadow-sm);
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
        }}
        .ui-card::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--teal-600), #38bdf8);
            opacity: 0.72;
        }}
        .ui-card:hover {{
            border-color: #bfd0d8;
            box-shadow: 0 14px 34px rgba(7, 19, 31, 0.09);
            transform: translateY(-2px);
        }}
        .ui-label {{
            color: var(--ink-500);
            font-size: 0.69rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 9px;
        }}
        .ui-value {{ color: var(--ink-900); font-size: 1.08rem; font-weight: 800; line-height: 1.25; }}
        .ui-note {{ color: var(--ink-500); font-size: 0.82rem; margin-top: 10px; line-height: 1.45; }}
        .ui-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border-radius: 999px;
            padding: 5px 9px;
            font-size: 0.73rem;
            font-weight: 800;
        }}
        .ui-pill::before {{ content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }}
        .ui-ok {{ border: 1px solid #a7f3d0; background: #ecfdf5; color: #08775d; }}
        .ui-warn {{ border: 1px solid #fed7aa; background: #fff7ed; color: #a0460b; }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: var(--line) !important;
            border-radius: 16px !important;
            background: rgba(255, 255, 255, 0.84);
            box-shadow: var(--shadow-sm);
        }}
        [data-testid="stMetric"] {{
            min-height: 112px;
            padding: 15px 16px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }}
        [data-testid="stMetricLabel"] {{ color: var(--ink-500); font-size: 0.76rem; font-weight: 750; }}
        [data-testid="stMetricValue"] {{ color: var(--ink-900); font-weight: 820; letter-spacing: -0.03em; }}

        .stButton > button, .stDownloadButton > button {{
            min-height: 42px;
            border: 1px solid #c9d6dc;
            border-radius: 10px;
            color: var(--ink-800);
            background: #ffffff;
            font-weight: 760;
            box-shadow: 0 2px 5px rgba(7, 19, 31, 0.03);
            transition: border-color 140ms ease, background 140ms ease, transform 140ms ease, box-shadow 140ms ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            border-color: #8eaab5;
            color: var(--ink-950);
            background: #f8fbfc;
            box-shadow: 0 7px 18px rgba(7, 19, 31, 0.08);
            transform: translateY(-1px);
        }}
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{
            outline: 3px solid rgba(13, 148, 136, 0.22);
            outline-offset: 2px;
        }}
        .stButton > button[kind="primary"] {{
            border-color: var(--teal-700);
            color: #ffffff;
            background: linear-gradient(135deg, var(--teal-700), #0e6370);
            box-shadow: 0 9px 20px rgba(15, 118, 110, 0.18);
        }}
        .stButton > button[kind="primary"]:hover {{
            border-color: #0b625d;
            color: #ffffff;
            background: linear-gradient(135deg, #0b625d, #0b5360);
        }}
        .stButton > button[kind="primary"] p {{ color: #ffffff !important; }}
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {{
            border-color: #cbd8de !important;
            border-radius: 10px !important;
            background: #ffffff !important;
        }}
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within {{
            border-color: var(--teal-600) !important;
            box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.1) !important;
        }}
        [data-testid="stFileUploaderDropzone"] {{
            min-height: 165px;
            border: 1px dashed #9fb6c1;
            border-radius: 14px;
            background: #f8fbfc;
        }}
        [data-testid="stFileUploaderDropzone"]:hover {{ border-color: var(--teal-600); background: #f0fdfa; }}
        [data-testid="stAlert"] {{ border-radius: 12px; border-width: 1px; }}
        [data-testid="stExpander"] {{
            overflow: hidden;
            border-color: var(--line);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.78);
        }}
        [data-testid="stExpander"] summary {{ color: var(--ink-800); font-weight: 700; }}
        [data-baseweb="tab-list"] {{
            gap: 5px;
            padding: 5px;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: #edf3f5;
        }}
        [data-baseweb="tab"] {{
            min-height: 39px;
            padding: 7px 15px;
            border-radius: 9px;
            color: var(--ink-600);
            font-weight: 750;
        }}
        [data-baseweb="tab"][aria-selected="true"] {{
            color: var(--ink-900);
            background: #ffffff;
            box-shadow: 0 3px 10px rgba(7, 19, 31, 0.08);
        }}
        [data-baseweb="tab-highlight"] {{ display: none; }}
        [data-testid="stDataFrame"], [data-testid="stTable"] {{
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 12px;
        }}
        [data-testid="stCode"] {{ border: 1px solid #1d3446; border-radius: 12px; box-shadow: var(--shadow-sm); }}

        @media (max-width: 980px) {{
            .ui-grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .page-hero-aside {{ display: none; }}
            .page-hero {{ min-height: 175px; }}
        }}
        @media (max-width: 820px) {{
            .ui-grid-2, .ui-grid-3 {{ grid-template-columns: 1fr; }}
            .app-brand-meta {{ display: none; }}
            .st-key-top_navigation [data-testid="stHorizontalBlock"] {{
                flex-direction: row !important;
                flex-wrap: wrap !important;
            }}
            .st-key-top_navigation [data-testid="stColumn"] {{
                flex: 1 1 calc(33.333% - 6px) !important;
                width: calc(33.333% - 6px) !important;
                min-width: calc(33.333% - 6px) !important;
            }}
        }}
        @media (max-width: 620px) {{
            .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
            .ui-grid-4 {{ grid-template-columns: 1fr; }}
            .page-hero {{ min-height: 0; padding: 24px 21px; border-radius: 18px; }}
            .page-title {{ font-size: 2rem; }}
            .app-brandbar {{ min-height: 68px; border-radius: 15px; }}
            .app-brand-subtitle {{ display: none; }}
            .st-key-top_navigation [data-testid="stColumn"] {{
                flex: 1 1 calc(50% - 5px) !important;
                width: calc(50% - 5px) !important;
                min-width: calc(50% - 5px) !important;
            }}
        }}
        {extra_css}
        </style>
        """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_html(markup: str) -> None:
    """Renderiza HTML quitando la sangría accidental de bloques multilínea."""
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def render_marca() -> None:
    """Muestra la cabecera persistente del producto."""
    render_html(
        """
        <div class="app-brandbar">
            <div class="app-brand">
                <div class="app-brand-mark" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                        <path d="M12 3 5 6v5c0 4.6 2.7 8.1 7 10 4.3-1.9 7-5.4 7-10V6l-7-3Z"/>
                        <path d="m8.6 12 2.2 2.2 4.7-4.8"/>
                    </svg>
                </div>
                <div>
                    <div class="app-brand-name">Phishing Defense</div>
                    <div class="app-brand-subtitle">Centro de seguridad y análisis de correo</div>
                </div>
            </div>
            <div class="app-brand-meta">
                <span class="app-live-dot"></span>
                <span class="app-brand-chip">Cliente · Servidor</span>
                <span class="app-brand-chip">API 1.0</span>
            </div>
        </div>
        """
    )


def encabezado_pagina(
    etiqueta: str,
    titulo: str,
    descripcion: str,
    detalle_titulo: str = "Backend central",
    detalle: str = "Procesamiento remoto mediante HTTP/JSON",
) -> None:
    """Muestra una cabecera de página homogénea y accesible."""
    render_html(
        f"""
        <section class="page-hero">
            <div class="page-hero-copy">
                <div class="page-eyebrow">{escape(etiqueta)}</div>
                <h1 class="page-title">{escape(titulo)}</h1>
                <p class="page-description">{escape(descripcion)}</p>
            </div>
            <div class="page-hero-aside">
                <strong>{escape(detalle_titulo)}</strong>
                {escape(detalle)}
            </div>
        </section>
        """
    )


def encabezado_seccion(indice: str, titulo: str, descripcion: str = "") -> None:
    """Introduce un bloque funcional con número y una breve orientación."""
    copy = f'<div class="section-copy">{escape(descripcion)}</div>' if descripcion else ""
    render_html(
        f"""
        <div class="section-heading">
            <div class="section-index">{escape(str(indice))}</div>
            <div>
                <div class="section-title">{escape(titulo)}</div>
                {copy}
            </div>
        </div>
        """
    )


def estado_badge(ok: bool, texto_ok: str = "Listo", texto_warn: str = "Pendiente") -> str:
    """Devuelve un badge HTML de estado con texto y un indicador redundante."""
    clase = "ui-ok" if ok else "ui-warn"
    texto = texto_ok if ok else texto_warn
    return f'<span class="ui-pill {clase}">{escape(texto)}</span>'
